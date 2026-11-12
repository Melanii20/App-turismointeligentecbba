"""Parte A de la sesión: correcciones del informe (lugares fuera de Cochabamba, estado de la API)."""

import pytest
from fastapi.testclient import TestClient

import modelo
from db import conectar
from servicios import grafo, router_reglas


def sin_web(*a, **k):
    raise AssertionError("No debe ir a internet")


@pytest.fixture(scope="module")
def conn():
    c = conectar()
    yield c
    c.close()


@pytest.mark.parametrize("pregunta,esperado", [
    ("Cuéntame del Museo del Louvre", "No tengo información sobre Museo del Louvre. Puedo contarte de los museos de Cochabamba que tengo registrados."),
    ("¿Cómo llego a la Torre Eiffel?", "No tengo información sobre Torre Eiffel. Puedo contarte de las torres de Cochabamba que tengo registradas."),
    ("¿Cuánto cuesta entrar al Parque Güell?", "No tengo información sobre Parque Güell. Puedo contarte de los parques de Cochabamba que tengo registrados."),
])
def test_lugar_fuera_de_cochabamba_nunca_dice_lo_que_mejor_encaja(conn, pregunta, esperado):
    r = grafo.procesar(conn, pregunta, {}, vectorizar=modelo.vectorizar_pregunta, web=sin_web)
    assert r["respuesta"] == esperado
    assert "mejor encaja" not in r["respuesta"]
    assert r["acciones"] == []


def test_lugar_de_cochabamba_que_no_esta_en_la_base_no_inventa_datos_operativos(conn):
    r = grafo.procesar(conn, "¿A qué hora abre el Museo Fantasma de Cochabamba?", {}, vectorizar=modelo.vectorizar_pregunta, web=sin_web)
    assert r["respuesta"] == "No tengo datos verificados de Museo Fantasma."


def test_detecta_el_nombre_del_lugar():
    assert router_reglas.lugar_no_registrado("Cuéntame del Museo del Louvre", [])["lugar"] == "Museo del Louvre"
    assert router_reglas.lugar_no_registrado("¿Qué museos hay?", []) is None
    assert router_reglas.lugar_no_registrado("Cuéntame del Museo del Louvre", [3]) is None


def test_estado_dice_que_esta_configurado_sin_mostrar_claves():
    from main import app
    with TestClient(app) as c:
        cuerpo = c.get("/api/estado").json()
    assert cuerpo["estado"] == "ok" and cuerpo["base_de_datos"] is True
    for clave in ("gemini", "tavily", "wikipedia"):
        assert isinstance(cuerpo[clave], bool)
    assert "key" not in str(cuerpo).lower()
