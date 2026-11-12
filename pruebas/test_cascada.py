"""Parte C: regla de dos ejes y cascada narrativa N1 a N4 (sin LLM real y sin internet)."""

import pytest

import modelo
from db import conectar
from servicios import cascada, grafo, router_reglas
from servicios.herramientas import buscar_en_base as h_base
from servicios.herramientas import buscar_web as h_web
from servicios.herramientas.buscar_web import IntentoWeb, ResultadoWeb


def web_prohibida(*a, **k):
    raise AssertionError("¡Se llamó a la web donde no se debe!")


def web_de(titulo="Silpancho", dominio="es.wikipedia.org", texto="El silpancho es un plato típico de Cochabamba con carne apanada y arroz."):
    def f(conn, consulta, tema):
        return IntentoWeb(creditos_tavily=1, resultado=ResultadoWeb(
            titulo=titulo, texto=texto, url=f"https://{dominio}/wiki/{titulo}", dominio=dominio, tema=tema))
    return f


@pytest.fixture(scope="module")
def conn():
    c = conectar()
    yield c
    c.close()


def preguntar(conn, pregunta, contexto=None, web=web_prohibida, ubicacion=None):
    lat, lng = ubicacion or (None, None)
    return grafo.procesar(conn, pregunta, contexto or {}, lat, lng, vectorizar=modelo.vectorizar_pregunta, web=web)


# ---------- ejes ----------
@pytest.mark.parametrize("texto,intencion,eje", [
    ("a que hora abre el convento", "datos_practicos", "operativo"),
    ("el cristo tiene piso tactil", "informacion", "operativo"),
    ("cuentame del cristo", "informacion", "narrativo"),
    ("que es el silpancho", "saberes", "narrativo"),
    ("de donde viene la fiesta de urkupina", "saberes", "narrativo"),
    ("como llego a la cancha", "como_llegar", "operativo"),
])
def test_eje_del_dato(texto, intencion, eje):
    assert router_reglas.eje_dato(texto, intencion) == eje


def test_pregunta_compuesta_se_divide_en_dos_partes():
    assert router_reglas.dividir_compuesta("que es la chicha y donde la puedo probar") == ("que es la chicha", "donde la puedo probar")
    assert router_reglas.dividir_compuesta("donde queda la cancha y a que hora abre") is None


# ---------- N1: documentos ----------
def test_leyenda_sale_del_documento_con_titulo_y_pagina_sin_creditos(conn):
    r = preguntar(conn, "Cuéntame la leyenda de la piedra que canta")
    assert r["nivel_fuente"] == "documento" and r["fuente"] == "base_verificada" and r["creditos_tavily"] == 0
    assert "Guía de prueba de Cochabamba (FICTICIO)" in r["respuesta"] and "página" in r["respuesta"]
    assert "Guía de prueba" in r["fuentes"][0]["nombre"]


def test_respuesta_corta_de_la_base_ofrece_saber_mas(conn):
    r = preguntar(conn, "Cuéntame la leyenda de la piedra que canta")
    assert r["respuesta"].endswith("¿Quieres saber más?") and r["escuchar_despues"] is True
    p = r["accion_pendiente"]
    assert p["tipo"] == "mas_informacion" and p["nivel_siguiente"] == "cache_web" and p["tema"] == "leyenda"


def test_si_a_saber_mas_baja_a_la_web_solo_para_lo_narrativo(conn):
    r1 = preguntar(conn, "Cuéntame la leyenda de la piedra que canta")
    llamadas = []

    def web(conn_, consulta, tema):
        llamadas.append(tema)
        return web_de("Piedra", texto="La piedra que canta es una leyenda de Cochabamba narrada por los pastores.")(conn_, consulta, tema)
    r2 = preguntar(conn, "sí", contexto={"accion_pendiente": r1["accion_pendiente"]}, web=web)
    assert llamadas == ["leyenda"] and r2["nivel_fuente"] == "web" and r2["creditos_tavily"] == 1
    assert r2["intencion"] == "confirmacion" and "información de internet" in r2["respuesta"]
    r3 = preguntar(conn, "no gracias", contexto={"accion_pendiente": r1["accion_pendiente"]})
    assert r3["respuesta"] == "Está bien." and r3["accion_pendiente"] is None


def test_cuentame_mas_tambien_baja_de_nivel(conn):
    r1 = preguntar(conn, "Cuéntame la leyenda de la piedra que canta")
    r2 = preguntar(conn, "cuéntame más", contexto={"accion_pendiente": r1["accion_pendiente"], "turnos": []},
                   web=web_de("Piedra", texto="La piedra que canta es una leyenda de Cochabamba."))
    assert r2["intencion"] == "mas_informacion" and r2["nivel_fuente"] == "web"


# ---------- documentos nunca para lo operativo (B4) ----------
@pytest.mark.parametrize("pregunta", [
    "¿El mirador de la piedra tiene piso táctil?",
    "¿A qué hora abre el mirador de la piedra?",
    "¿Cuánto cuesta entrar al mirador de la piedra?",
])
def test_un_documento_nunca_responde_datos_operativos(conn, pregunta):
    r = preguntar(conn, pregunta)
    assert r["nivel_fuente"] != "documento" and "50 bolivianos" not in r["respuesta"] and "7 de la mañana" not in r["respuesta"]
    assert "piso táctil" not in r["respuesta"].lower() or "No tengo" in r["respuesta"]


def test_buscar_en_base_marca_el_origen(conn):
    v = modelo.vectorizar_pregunta("leyenda de la piedra que canta")
    res = h_base.buscar_en_base(conn, "leyenda de la piedra que canta", v, vectorizar=modelo.vectorizar_pregunta)
    assert res.hallazgos and res.hallazgos[0].origen == "documento" and res.hallazgos[0].pagina in (1, 2)


def test_un_documento_en_borrador_no_entra_al_rag(conn):
    with conn.cursor() as cur:
        cur.execute("UPDATE documentos SET estado = 'borrador' WHERE titulo LIKE 'Guía de prueba de Cochabamba%'")
    conn.commit()
    try:
        r = preguntar(conn, "Cuéntame la leyenda de la piedra que canta", web=lambda *a, **k: IntentoWeb())
        assert r["nivel_fuente"] == "ninguna"          # un borrador no existe para el asistente
    finally:
        with conn.cursor() as cur:
            cur.execute("UPDATE documentos SET estado = 'verificado' WHERE titulo LIKE 'Guía de prueba de Cochabamba%'")
        conn.commit()


# ---------- N2 / N3 / N4 ----------
def test_web_y_cache_con_citas(conn, monkeypatch):
    monkeypatch.setattr(h_web.config, "TAVILY_API_KEY", "x")

    class Falso:
        llamadas = 0

        def search(self, **kw):
            Falso.llamadas += 1
            return {"results": [{"title": "Zzzplato Cochabamba", "url": "https://es.wikipedia.org/wiki/Zzzplato",
                                 "content": "El zzzplato es una comida típica de Cochabamba con papa y maíz.", "score": 0.8}]}
    monkeypatch.setattr(h_web, "_cliente_tavily", lambda: Falso())
    try:
        r1 = grafo.procesar(conn, "¿Qué es el zzzplato, una comida típica?", {}, vectorizar=modelo.vectorizar_pregunta)
        assert r1["nivel_fuente"] == "web" and r1["creditos_tavily"] == 1 and "información de internet" in r1["respuesta"]
        assert r1["respuesta"].startswith("Según Wikipedia (información de internet)")
        r2 = grafo.procesar(conn, "¿Qué es el zzzplato, una comida típica?", {}, vectorizar=modelo.vectorizar_pregunta)
        assert r2["nivel_fuente"] == "cache_web" and r2["creditos_tavily"] == 0 and Falso.llamadas == 1
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contenido_web WHERE titulo = 'Zzzplato Cochabamba'")
        conn.commit()


def test_contenido_descartado_no_se_usa_desde_la_cache(conn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO contenido_web (fuente, tema, titulo, url, texto, dominio, estado_revision) VALUES "
            "('tavily','gastronomia','Qqqplato Cochabamba','https://x/q','El qqqplato es típico de Cochabamba.','x','descartado')"
        )
    conn.commit()
    try:
        assert h_web.buscar_en_cache(conn, "qqqplato", "gastronomia") is None
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contenido_web WHERE titulo = 'Qqqplato Cochabamba'")
        conn.commit()


def test_n4_ofrece_una_alternativa_de_la_base(conn):
    r = preguntar(conn, "¿Quién fue zxqvnombre, un personaje histórico?", web=lambda *a, **k: IntentoWeb())
    assert r["nivel_fuente"] == "ninguna" and r["respuesta"].startswith("No tengo información sobre eso, pero puedo contarte de ")


@pytest.mark.parametrize("pregunta", ["¿Quién ganó el partido de fútbol?", "¿Cuál es el clima de hoy?", "¿Qué es la fotosíntesis?"])
def test_lo_ajeno_o_fuera_de_cochabamba_nunca_va_a_la_web(conn, pregunta):
    r = preguntar(conn, pregunta)                  # web_prohibida
    assert r["nivel_fuente"] == "ninguna" and r["fuente"] == "sistema"


def test_orden_de_la_cascada_se_impone_en_el_codigo(conn):
    cas = cascada.Cascada(conn, "silpancho", None, None, [], "gastronomia", True, web_prohibida)
    with pytest.raises(cascada.OrdenInvalido):
        cas.en_cache()
    with pytest.raises(cascada.OrdenInvalido):
        cas.en_web()
    cas.base_consultada, cas.base = True, h_base.ResultadoBase()
    with pytest.raises(cascada.OrdenInvalido):
        cas.en_web()                                # falta consultar la caché
    cas.cache_consultada = True
    cas.web_permitida = False
    with pytest.raises(cascada.OrdenInvalido):
        cas.en_web()                                # tema fuera de alcance


# ---------- compuestas ----------
def test_pregunta_compuesta_resuelve_cada_parte_con_su_regla(conn):
    r = preguntar(conn, "¿Qué es el silpancho y dónde lo puedo probar?", web=web_de())
    assert "información de internet" in r["respuesta"] and "No tengo ese dato verificado" in r["respuesta"]
    assert r["acciones"] == [] and r["accion_pendiente"] is None
