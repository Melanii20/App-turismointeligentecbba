"""Pruebas de fuentes y del grafo completo.

Regla clave: un sitio que no está en la base NUNCA llega a la web. La web (Tavily / Wikipedia) se simula
(no se usa internet) y se falla si el grafo intenta llamarla donde no debe.
"""

import pytest
from fastapi.testclient import TestClient

import modelo
from api import rutas
from db import conectar
from servicios import grafo
from servicios.herramientas import buscar_web as h_web
from servicios.herramientas.buscar_web import IntentoWeb, ResultadoWeb

PLAZA_14 = (-17.3935, -66.1570)


def web_prohibida(*args, **kwargs):
    raise AssertionError("¡Se llamó a la web donde no se debe!")


def web_simulada(conn, consulta, tema):
    return IntentoWeb(creditos_tavily=1, resultado=ResultadoWeb(
        titulo="La Llorona de Cochabamba", tema=tema, url="https://es.wikipedia.org/wiki/Llorona", dominio="es.wikipedia.org",
        texto="La Llorona es una leyenda popular de Cochabamba. Se dice que una mujer llora de noche por sus hijos.",
    ))


@pytest.fixture(scope="module")
def conn():
    c = conectar()
    yield c
    c.close()


def preguntar(conn, pregunta, contexto=None, ubicacion=None, web=web_prohibida):
    lat, lng = ubicacion or (None, None)
    return grafo.procesar(conn, pregunta, contexto or {}, lat, lng, vectorizar=modelo.vectorizar_pregunta, web=web)


@pytest.mark.parametrize("pregunta", [
    "Cuéntame sobre el Museo del Louvre",
    "¿Cuál es la leyenda del Museo del Louvre?",
    "¿Cómo llego a la Torre Eiffel?",
    "¿A qué hora abre la Iglesia de San Pedro Apóstol de Roma?",
    "¿Cuánto cuesta entrar al Parque Güell?",
    "¿Cuál es la historia del Teatro Colón de Buenos Aires?",
    "¿Qué se escucha en la Plaza de Mayo?",
])
def test_un_sitio_que_no_esta_en_la_base_nunca_llega_a_la_web(conn, pregunta):
    r = preguntar(conn, pregunta)               # web_prohibida lanza error si se llama
    assert r["fuente"] not in ("wikipedia", "web") and r["nivel_fuente"] in ("ninguna", "base")


def test_un_borrador_tampoco_llega_a_la_web(conn):
    r = preguntar(conn, "Cuéntame del Cristo de la Concordia")   # id 1, en borrador
    assert r["fuente"] == "sistema" and r["respuesta"].startswith(grafo.SIN_INFORMACION[:-1])
    assert r["nivel_fuente"] == "ninguna"


def test_eventos_nunca_usan_la_web(conn):
    r = preguntar(conn, "¿Cuándo es la fiesta de Urkupiña?")
    assert r["intencion"] == "eventos" and r["fuente"] not in ("wikipedia", "web")


def test_dato_operativo_de_un_plato_no_va_a_la_web(conn):
    r = preguntar(conn, "¿Cuánto cuesta un silpancho?")
    assert r["eje_dato"] == "operativo" and r["respuesta"].startswith(grafo.SIN_DATO_VERIFICADO)


def test_saberes_si_la_base_no_tiene_nada_va_a_la_web_y_la_cita(conn):
    r = preguntar(conn, "¿Cuál es la leyenda de la Llorona?", web=web_simulada)
    assert r["intencion"] == "saberes" and r["fuente"] == "wikipedia" and r["nivel_fuente"] == "web"
    assert "información de internet" in r["respuesta"] and r["respuesta"].startswith("Según Wikipedia")
    assert r["fuentes"][0]["url"] == "https://es.wikipedia.org/wiki/Llorona" and r["creditos_tavily"] == 1


def test_saberes_primero_la_base_si_tiene_la_respuesta(conn):
    # La Casona Santiváñez nombrada -> informacion, resuelta por la base, sin la web.
    r = preguntar(conn, "Cuéntame la leyenda de la Casona Santiváñez")
    assert r["intencion"] == "informacion" and r["fuente"] == "base_verificada"


def test_tavily_se_descarta_si_no_habla_de_cochabamba(monkeypatch, conn):
    class Falso:
        def search(self, **kw):
            return {"results": [{"title": "Leyenda de Tokio", "url": "https://es.wikipedia.org/wiki/Tokio",
                                 "content": "Una leyenda de Japón.", "score": 0.9}]}
    monkeypatch.setattr(h_web.config, "TAVILY_API_KEY", "x")
    monkeypatch.setattr(h_web, "_cliente_tavily", lambda: Falso())
    intento = h_web.buscar_web(conn, "leyenda tokio", "leyenda")
    assert intento.resultado is None and intento.creditos_tavily == 1


def test_web_guarda_en_cache_y_la_usa(monkeypatch, conn):
    llamadas = []

    class Falso:
        def search(self, **kw):
            llamadas.append(kw)
            return {"results": [{"title": "ZZ Prueba Cochabamba", "url": "https://es.wikipedia.org/wiki/ZZ",
                                 "content": "Tradición zzprueba de Cochabamba de prueba.", "score": 0.9}]}
    monkeypatch.setattr(h_web.config, "TAVILY_API_KEY", "x")
    monkeypatch.setattr(h_web, "_cliente_tavily", lambda: Falso())
    try:
        primera = h_web.buscar_web(conn, "zzprueba", "tradicion")
        assert primera.resultado and not primera.resultado.desde_cache and primera.creditos_tavily == 1
        assert llamadas[0]["include_domains_mode"] == "restrict" and llamadas[0]["search_depth"] == "basic"
        assert llamadas[0]["country"] == "bolivia" and llamadas[0]["include_answer"] is False and llamadas[0]["max_results"] == 3
        segunda = h_web.buscar_en_cache(conn, "zzprueba", "tradicion")
        assert segunda and segunda.desde_cache and len(llamadas) == 1      # no volvió a internet
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contenido_web WHERE titulo = 'ZZ Prueba Cochabamba'")
        conn.commit()


def test_como_llegar_con_verbo_de_ir_abre_la_navegacion(conn):
    r = preguntar(conn, "Llévame a la Catedral Metropolitana", ubicacion=PLAZA_14)
    assert r["acciones"] and r["acciones"][0]["tipo"] == "abrir_navegacion"
    assert r["respuesta"].endswith("Te abro la navegación.") and not r["escuchar_despues"]


def test_donde_queda_ofrece_llevar_y_el_si_lo_ejecuta(conn):
    r1 = preguntar(conn, "¿Dónde queda la Catedral Metropolitana?")
    assert r1["acciones"] == [] and r1["escuchar_despues"] and r1["respuesta"].endswith("¿Quieres que te lleve?")
    pendiente = r1["accion_pendiente"]
    assert pendiente["tipo"] == "abrir_navegacion"
    r2 = preguntar(conn, "sí", contexto={"accion_pendiente": pendiente, "ultimo_sitio_id": r1["sitio_id"]})
    assert r2["intencion"] == "confirmacion" and r2["acciones"] == [pendiente]
    r3 = preguntar(conn, "mejor no", contexto={"accion_pendiente": pendiente})
    assert r3["acciones"] == [] and r3["accion_pendiente"] is None and r3["respuesta"] == "Está bien."


def test_sitio_de_contexto_si_no_se_nombra(conn):
    r1 = preguntar(conn, "¿Dónde queda la Catedral Metropolitana?")
    r2 = preguntar(conn, "¿Cómo llego?", contexto={"ultimo_sitio_id": r1["sitio_id"]})
    assert r2["sitio_id"] == r1["sitio_id"]
    r3 = preguntar(conn, "¿Cómo llego?")
    assert r3["respuesta"] == grafo.ACLARAR_SITIO


def test_cercania_necesita_ubicacion(conn):
    assert "necesito tu ubicación" in preguntar(conn, "¿Qué hay cerca de mí?")["respuesta"]
    r = preguntar(conn, "¿Qué hay cerca de mí?", ubicacion=PLAZA_14)
    assert r["intencion"] == "cercania" and "Plaza 14 de Septiembre" in r["respuesta"]
    assert r["accion_pendiente"] and r["escuchar_despues"]


def test_compartir_prepara_el_mensaje(conn):
    r = preguntar(conn, "Avisa a mi familia", contexto={"ultimo_sitio_id": preguntar(conn, "¿Dónde queda la Catedral Metropolitana?")["sitio_id"]})
    assert r["acciones"][0]["tipo"] == "compartir" and "Catedral" in r["acciones"][0]["texto"]
    sin_ubic = preguntar(conn, "Dile a mi familia dónde estoy")
    assert "No tengo tu ubicación" in sin_ubic["respuesta"] and sin_ubic["acciones"] == []


def test_fuera_de_alcance_y_ayuda(conn):
    assert preguntar(conn, "¿Quién ganó el partido de fútbol?")["intencion"] == "fuera_de_alcance"
    assert preguntar(conn, "¿Qué puedes hacer?")["respuesta"] == grafo.AYUDA


def test_sin_llm_el_sistema_responde_con_plantilla(conn):
    r = preguntar(conn, "Cuéntame sobre la Catedral Metropolitana")
    assert r["fuente"] == "base_verificada" and r["uso_llm"] is False
    assert "Según la verificación de" in r["respuesta"]


# ---------- API (contrato JSON) ----------
@pytest.fixture(scope="module")
def cliente():
    from main import app
    with TestClient(app) as c:
        yield c


def test_contrato_de_api_consulta(cliente):
    r = cliente.post("/api/consulta", json={
        "pregunta": "¿Cómo llego a la Catedral Metropolitana?", "canal": "app",
        "contexto": {"turnos": [], "ultimo_sitio_id": None}, "latitud": PLAZA_14[0], "longitud": PLAZA_14[1],
    })
    assert r.status_code == 200
    cuerpo = r.json()
    for clave in ("respuesta", "intencion", "uso_llm", "fuente", "fuentes", "sitio_id", "acciones", "escuchar_despues", "contexto"):
        assert clave in cuerpo, clave
    assert set(cuerpo["contexto"]) == {"turnos", "ultimo_sitio_id", "accion_pendiente"}
    assert cuerpo["fuente"] == "base_verificada" and cuerpo["acciones"][0]["tipo"] == "abrir_navegacion"


def test_api_limites_de_entrada(cliente):
    assert cliente.post("/api/consulta", json={"pregunta": "x" * 301}).status_code == 422
    assert cliente.post("/api/consulta", json={"pregunta": ""}).status_code == 422
    assert cliente.post("/api/consulta", json={"pregunta": "hola", "canal": "otro"}).status_code == 422
    assert cliente.post("/api/consulta", json={"pregunta": "hola", "latitud": 200, "longitud": 0}).status_code == 422


def test_api_historial_maximo_6_turnos(cliente):
    turnos = [{"pregunta": f"p{i}", "respuesta": f"r{i}"} for i in range(10)]
    r = cliente.post("/api/consulta", json={"pregunta": "¿Qué puedes hacer?", "contexto": {"turnos": turnos}})
    assert len(r.json()["contexto"]["turnos"]) == 6


def test_api_no_guarda_la_pregunta_en_las_metricas(cliente):
    cliente.post("/api/consulta", json={"pregunta": "pregunta secreta de prueba xyz ayuda", "latitud": -17.39, "longitud": -66.15})
    c = conectar()
    try:
        with c.cursor() as cur:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'metricas_consulta'")
            columnas = {f[0] for f in cur.fetchall()}
            cur.execute("SELECT count(*) FROM metricas_consulta")
            assert cur.fetchone()[0] >= 1
    finally:
        c.close()
    # Solo datos de uso: nunca el texto de la pregunta, la ubicación ni un identificador de la persona.
    assert columnas == {
        "id", "fecha", "canal", "intencion", "uso_llm", "fuente", "sitio_id", "similitud_maxima", "tiempo_ms",
        "nivel_fuente", "eje_dato", "creditos_tavily", "motivo_sin_llm",
    }


def test_api_eventos_hoy_y_estado(cliente):
    r = cliente.get("/api/eventos/hoy", params={"latitud": PLAZA_14[0], "longitud": PLAZA_14[1]})
    assert r.status_code == 200 and "eventos" in r.json()
    assert cliente.get("/api/estado").json()["estado"] == "ok"
    assert cliente.get("/api/eventos/hoy", params={"latitud": 999, "longitud": 0}).status_code == 422
