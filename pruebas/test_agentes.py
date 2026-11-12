"""Parte D: agentes de Pydantic AI probados con FunctionModel/TestModel (sin gastar cuota de Gemini).

Las llamadas reales (3 de humo) están aparte, en pruebas/humo_agentes.py.
"""

import asyncio

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

import config
import modelo
from db import conectar
from servicios import cascada, grafo
from servicios.agentes import agente_clasificador, agente_saberes, agente_sitios, ejecucion, proveedor
from servicios.herramientas.buscar_web import IntentoWeb, ResultadoWeb


@pytest.fixture(scope="module")
def conn():
    c = conectar()
    yield c
    c.close()


def _salida(info: AgentInfo, **campos):
    """Respuesta final estructurada: llama a la herramienta de salida del agente."""
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, campos)])


def modelo_falso(texto="Texto de prueba del agente.", intencion="saberes", registro=None):
    """FunctionModel que contesta según el tipo de salida que pide el agente."""
    def fn(mensajes, info: AgentInfo):
        if registro is not None:
            registro.append(str(mensajes))
        props = info.output_tools[0].parameters_json_schema.get("properties", {})
        if "intencion" in props:
            return _salida(info, intencion=intencion, eje_dato="narrativo", sitio=None)
        return _salida(info, texto=texto)
    return FunctionModel(fn)


def web_simulada(conn_, consulta, tema):
    return IntentoWeb(creditos_tavily=1, resultado=ResultadoWeb(
        titulo="Silpancho", texto="El silpancho es un plato típico de Cochabamba con carne apanada y arroz.",
        url="https://es.wikipedia.org/wiki/Silpancho", dominio="es.wikipedia.org", tema=tema))


# ---------- agente clasificador ----------
def test_clasificador_devuelve_salida_tipada():
    ej = agente_clasificador.clasificar("Me da curiosidad lo que comen los cochabambinos", modelo=modelo_falso(intencion="saberes"))
    assert ej.salida.intencion == "saberes" and ej.salida.eje_dato == "narrativo" and ej.solicitudes == 1


def test_clasificador_con_testmodel_respeta_el_esquema():
    ej = agente_clasificador.clasificar("algo", modelo=TestModel(custom_output_args={"intencion": "itinerario", "eje_dato": "narrativo", "sitio": None}))
    assert ej.salida.intencion == "itinerario"


def test_grafo_usa_el_clasificador_solo_si_ninguna_regla_coincide(conn, monkeypatch):
    monkeypatch.setattr(proveedor, "modelo", lambda: modelo_falso(intencion="saberes"))
    r = grafo.procesar(conn, "Me da curiosidad lo que comen los cochabambinos", {}, vectorizar=modelo.vectorizar_pregunta, web=web_simulada)
    assert r["intencion"] == "saberes" and r["uso_llm"] is True and r["motivo_sin_llm"] is None
    # una pregunta que las reglas sí entienden no llama al LLM
    r2 = grafo.procesar(conn, "¿Qué puedes hacer?", {}, vectorizar=modelo.vectorizar_pregunta, web=web_simulada)
    assert r2["intencion"] == "ayuda" and r2["uso_llm"] is False


# ---------- agente de sitios ----------
def test_agente_sitios_redacta_y_el_texto_lleva_la_fecha_de_verificacion(conn, monkeypatch):
    monkeypatch.setattr(proveedor, "modelo", lambda: modelo_falso(texto="La Catedral es una iglesia de piedra con eco suave."))
    r = grafo.procesar(conn, "Cuéntame de la Catedral Metropolitana", {}, vectorizar=modelo.vectorizar_pregunta, web=web_simulada)
    assert r["uso_llm"] is True and "eco suave" in r["respuesta"] and "verificaci" in r["respuesta"].lower()
    assert r["nivel_fuente"] == "base" and r["creditos_tavily"] == 0


def test_agente_sitios_no_tiene_herramientas_ni_web():
    assert not agente_sitios.agente._function_toolset.tools


# ---------- agente de saberes: herramientas y orden ----------
def test_agente_saberes_no_puede_usar_la_web_antes_de_la_base(conn):
    llamadas_web = []

    def web(c_, consulta, tema):
        llamadas_web.append(consulta)
        return web_simulada(c_, consulta, tema)

    cas = cascada.Cascada(conn, "silpancho", None, None, [], "gastronomia", True, web)   # no se consultó nada todavía
    pasos = {"n": 0}

    def fn(mensajes, info: AgentInfo):
        pasos["n"] += 1
        if pasos["n"] == 1:   # el «LLM» intenta ir directo a la web
            return ModelResponse(parts=[ToolCallPart("buscar_web", {"consulta": "silpancho"})])
        return _salida(info, texto="No tengo información sobre eso.")

    res = agente_saberes.agente.run_sync("¿Qué es el silpancho?", model=FunctionModel(fn), deps=agente_saberes.DepsSaberes(cas))
    devueltas = [p.content for m in res.all_messages() for p in m.parts if isinstance(p, ToolReturnPart) and p.tool_name == "buscar_web"]
    assert devueltas and "NO PERMITIDO" in devueltas[0]
    assert llamadas_web == []                         # la web nunca se llamó


def test_agente_saberes_la_web_se_abre_solo_despues_de_base_y_cache_sin_resultado(conn):
    llamadas_web = []

    def web(c_, consulta, tema):
        llamadas_web.append(consulta)
        return web_simulada(c_, consulta, tema)

    cas = cascada.Cascada(conn, "zzzqqq", modelo.vectorizar_pregunta("zzzqqq"), modelo.vectorizar_pregunta, [], "gastronomia", True, web)
    orden = iter([("buscar_en_base", {"consulta": "zzzqqq"}), ("buscar_en_cache", {"consulta": "zzzqqq"}), ("buscar_web", {"consulta": "zzzqqq"})])

    def fn(mensajes, info: AgentInfo):
        try:
            nombre, args = next(orden)
            return ModelResponse(parts=[ToolCallPart(nombre, args)])
        except StopIteration:
            return _salida(info, texto="Según Wikipedia (información de internet), el silpancho es un plato típico.")

    res = agente_saberes.agente.run_sync("zzzqqq", model=FunctionModel(fn), deps=agente_saberes.DepsSaberes(cas))
    assert llamadas_web == ["zzzqqq"] and cas.creditos_tavily == 1
    assert cas.herramientas_usadas == ["buscar_en_base", "buscar_en_cache", "buscar_web"]
    assert "NO PERMITIDO" not in str(res.all_messages())


def test_limite_de_solicitudes_del_agente_de_saberes_es_3(conn):
    cas = cascada.Cascada(conn, "x", modelo.vectorizar_pregunta("x"), modelo.vectorizar_pregunta, [], "historia", True, web_simulada)

    def fn(mensajes, info: AgentInfo):               # nunca termina: pide herramientas sin parar
        return ModelResponse(parts=[ToolCallPart("buscar_en_base", {"consulta": "x"})])

    ej = ejecucion.ejecutar(agente_saberes.agente, "x", solicitudes_max=3, deps=agente_saberes.DepsSaberes(cas), modelo=FunctionModel(fn))
    assert ej.salida is None and ej.motivo_sin_llm == "limite_solicitudes"


def test_los_agentes_simples_tienen_limite_de_1_solicitud():
    def fn(mensajes, info: AgentInfo):
        return ModelResponse(parts=[TextPart("sin formato")])      # no es una salida válida: se reintenta

    ej = ejecucion.ejecutar(agente_clasificador.agente, "x", solicitudes_max=1, modelo=FunctionModel(fn))
    assert ej.salida is None and ej.motivo_sin_llm in ("limite_solicitudes", "salida_invalida")


# ---------- cuota, errores y tiempo: plantilla con uso_llm=false y motivo ----------
def test_error_429_cae_a_la_plantilla_y_cita_la_fuente(conn, monkeypatch):
    def fn(mensajes, info):
        raise RuntimeError("429 RESOURCE_EXHAUSTED: cuota agotada")
    monkeypatch.setattr(proveedor, "modelo", lambda: FunctionModel(fn))
    r = grafo.procesar(conn, "Cuéntame de la Catedral Metropolitana", {}, vectorizar=modelo.vectorizar_pregunta, web=web_simulada)
    assert r["uso_llm"] is False and r["motivo_sin_llm"] == "limite_cuota_429"
    assert "Según la verificación de" in r["respuesta"]


def test_saberes_con_error_usa_plantilla_que_lee_el_fragmento_y_cita(conn, monkeypatch):
    def fn(mensajes, info):
        raise RuntimeError("fallo de red")
    monkeypatch.setattr(proveedor, "modelo", lambda: FunctionModel(fn))
    r = grafo.procesar(conn, "Cuéntame la leyenda de la piedra que canta", {}, vectorizar=modelo.vectorizar_pregunta, web=web_simulada)
    assert r["uso_llm"] is False and r["motivo_sin_llm"] == "error_api" and r["nivel_fuente"] == "documento"
    assert "Guía de prueba de Cochabamba (FICTICIO)" in r["respuesta"]


def test_mas_de_15_segundos_cae_a_la_plantilla(conn, monkeypatch):
    async def lento(mensajes, info):
        await asyncio.sleep(3)
        return _salida(info, texto="tarde")
    monkeypatch.setattr(config, "AGENTE_TIMEOUT_S", 0.3)
    monkeypatch.setattr(proveedor, "modelo", lambda: FunctionModel(lento))
    r = grafo.procesar(conn, "Cuéntame de la Catedral Metropolitana", {}, vectorizar=modelo.vectorizar_pregunta, web=web_simulada)
    assert r["uso_llm"] is False and r["motivo_sin_llm"] == "tiempo_agotado" and r["respuesta"]


def test_sin_clave_responde_con_plantillas(conn):
    # la configuración de pruebas no tiene modelo (conftest): el sistema sigue funcionando
    r = grafo.procesar(conn, "Cuéntame de la Catedral Metropolitana", {}, vectorizar=modelo.vectorizar_pregunta, web=web_simulada)
    assert r["uso_llm"] is False and r["motivo_sin_llm"] in ("sin_clave", "sin_proveedor", "sin_modelo")


# ---------- privacidad ----------
def test_nunca_se_envia_la_ubicacion_ni_datos_personales_al_llm(conn, monkeypatch):
    registro = []
    monkeypatch.setattr(proveedor, "modelo", lambda: modelo_falso(registro=registro))
    grafo.procesar(conn, "Cuéntame de la Catedral Metropolitana, mi correo es ana@correo.com y mi cel 71234567",
                   {}, -17.3935, -66.1570, vectorizar=modelo.vectorizar_pregunta, web=web_simulada)
    enviado = " ".join(registro)
    assert registro and "17.3935" not in enviado and "66.157" not in enviado
    assert "ana@correo.com" not in enviado and "71234567" not in enviado


def test_limpiar_pregunta():
    assert "[dato personal]" in ejecucion.limpiar_pregunta("escríbeme a juan@x.com")
    assert "71234567" not in ejecucion.limpiar_pregunta("llámame al 7123 4567")
