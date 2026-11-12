"""Pruebas de las herramientas con la base de prueba (necesita el contenedor postgres-tesis).

Se ejecutan con los sitios y eventos de datos_prueba.sql. Ninguna prueba modifica datos reales.
"""

from datetime import date, time

import pytest

import modelo
from db import conectar
from servicios import geo
from servicios.herramientas import (
    armar_itinerario as h_it, armar_mensaje_compartir as h_msg, buscar_sitios as h_bus,
    como_llegar as h_ll, datos, datos_practicos as h_dp, eventos as h_ev, sitios_cercanos as h_cer,
)

PLAZA_14 = (-17.393500, -66.157000)


@pytest.fixture(scope="module")
def conn():
    c = conectar()
    yield c
    c.close()


@pytest.fixture(scope="module")
def vectorizar():
    return modelo.vectorizar_pregunta


def test_un_borrador_nunca_aparece(conn, vectorizar):
    # El Cristo de la Concordia (id 1) está en borrador en la base.
    r = h_bus.buscar_sitios(conn, "Cuéntame del Cristo de la Concordia", vectorizar("Cristo de la Concordia"))
    assert 1 not in [s["id"] for s in r.sitios]
    assert datos.obtener_sitio(conn, 1) is None
    assert 1 not in [i for i, _ in datos.sitios_verificados(conn)]


def test_el_filtro_de_piso_tactil_es_exacto(conn, vectorizar):
    pregunta = "¿Qué lugares tienen piso táctil?"
    r = h_bus.buscar_sitios(conn, pregunta, vectorizar(pregunta))
    assert r.filtros.piso_tactil
    assert r.sitios, "debería haber sitios de prueba con piso táctil"
    assert all(s["acceso_piso_tactil"] is True for s in r.sitios)


def test_el_filtro_de_ruido_bajo_es_exacto(conn, vectorizar):
    pregunta = "Quiero un lugar tranquilo y sin ruido"
    r = h_bus.buscar_sitios(conn, pregunta, vectorizar(pregunta))
    assert r.sitios and all(s["acceso_nivel_ruido"] == "bajo" for s in r.sitios)


def test_busqueda_por_nombre(conn, vectorizar):
    pregunta = "Háblame del Palacio Portales"
    r = h_bus.buscar_sitios(conn, pregunta, vectorizar(pregunta))
    assert r.por_nombre and r.sitios[0]["nombre"] == "Palacio Portales"


def test_pregunta_fuera_de_alcance_no_devuelve_sitios(conn, vectorizar):
    pregunta = "¿Cuál es la capital de Japón?"
    r = h_bus.buscar_sitios(conn, pregunta, vectorizar(pregunta))
    assert r.sitios == []


def test_sitios_cercanos_ordenados_por_distancia(conn):
    sitios = h_cer.sitios_cercanos(conn, *PLAZA_14, radio_km=1.5, limite=5)
    distancias = [s["distancia_m"] for s in sitios]
    assert sitios and distancias == sorted(distancias)
    assert sitios[0]["nombre"] == "Plaza 14 de Septiembre" and distancias[0] < 100
    assert all(d <= 1500 for d in distancias)


def test_haversine_conocida():
    # Un grado de latitud son unos 111 km.
    assert 110_000 < geo.distancia_m(0, 0, 1, 0) < 112_000
    assert geo.distancia_m(-17.39, -66.15, -17.39, -66.15) == 0


def test_datos_practicos_no_inventa_lo_que_falta(conn):
    sitio = {"id": 1, "nombre": "Sitio X", "horario": "9 a 17", "costo_ingreso": None, "duracion_visita": None, "servicios": None}
    frases = h_dp.frases(sitio, h_dp.datos_practicos(sitio, ["horario", "costo"]))
    assert "9 a 17" in frases[0]
    assert frases[1].startswith("Todavía no tengo registrado el costo")


def test_campos_pedidos_de_datos_practicos():
    assert h_dp.campos_pedidos("a que hora abre el museo") == ["horario"]
    assert "costo" in h_dp.campos_pedidos("cuanto cuesta entrar")
    assert h_dp.campos_pedidos("hay banos") == ["servicios"]


def test_como_llegar_lee_la_referencia_de_la_entrada(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM sitios_turisticos WHERE nombre = 'Catedral Metropolitana'")
        sitio = datos.obtener_sitio(conn, cur.fetchone()[0])
    r = h_ll.como_llegar(sitio, *PLAZA_14)
    texto = " ".join(h_ll.frases(r))
    assert r.tiene_coordenadas and r.distancia_m is not None and r.distancia_m < 300
    assert "Para reconocer la entrada" in texto and "en línea recta" in texto


def test_como_llegar_sin_ubicacion_no_calcula_distancia(conn):
    sitio = datos.obtener_sitio(conn, datos.sitios_verificados(conn)[0][0])
    assert h_ll.como_llegar(sitio).distancia_m is None


def test_eventos_el_mas_cercano_va_primero():
    lejos = {"nombre": "Lejos", "latitud": -17.45, "longitud": -66.20, "fecha_inicio": date(2026, 1, 1)}
    cerca = {"nombre": "Cerca", "latitud": -17.3936, "longitud": -66.1571, "fecha_inicio": date(2026, 1, 1)}
    sin = {"nombre": "SinCoordenadas", "latitud": None, "longitud": None, "fecha_inicio": date(2026, 1, 1)}
    orden = h_ev._con_distancia([sin, lejos, cerca], *PLAZA_14)
    assert orden[0]["nombre"] == "Cerca" and orden[0]["distancia_m"] < 100


def test_eventos_por_fecha_y_de_hoy(conn):
    todos = h_ev.eventos_por_fecha(conn, date(2000, 1, 1), date(2100, 1, 1))
    assert len(todos) >= 1 and all("nombre" in e for e in todos)
    hoy = h_ev.eventos_de_hoy(conn)
    assert all(e["fecha_inicio"] <= datos.hoy(conn) <= (e["fecha_fin"] or e["fecha_inicio"]) for e in hoy)


def test_rangos_de_fecha():
    lunes = date(2026, 11, 9)
    assert h_ev.rango_de_la_pregunta("que hay hoy", lunes)[:2] == (lunes, lunes)
    assert h_ev.rango_de_la_pregunta("que hay manana", lunes)[0] == date(2026, 11, 10)
    sab, dom, _ = h_ev.rango_de_la_pregunta("que hay este fin de semana", lunes)
    assert (sab.weekday(), dom.weekday()) == (5, 6)


def test_frase_de_evento_con_hora():
    e = {"nombre": "Feria", "fecha_inicio": date(2026, 11, 14), "fecha_fin": None, "zona": "Plaza",
         "hora_inicio": time(9, 0), "hora_fin": time(18, 0), "distancia_m": 800}
    frase = h_ev.frase_evento(e)
    assert "Feria" in frase and "sábado 14 de noviembre" in frase and "09:00 a 18:00" in frase and "800 metros" in frase


def test_itinerario_de_2_a_4_sitios_empezando_por_el_mas_cercano(conn):
    it = h_it.armar_itinerario(conn, *PLAZA_14)
    assert 2 <= len(it.sitios) <= 4
    assert it.sitios[0]["nombre"] == "Plaza 14 de Septiembre"


def test_mensaje_compartir_la_ubicacion_solo_si_se_pidio():
    s = {"nombre": "Catedral", "latitud": -17.3935, "longitud": -66.1570}
    sin = h_msg.armar_mensaje_compartir([s], False, *PLAZA_14)
    con = h_msg.armar_mensaje_compartir([s], True, *PLAZA_14)
    assert sin.startswith("Hola, estoy usando Guía Cochala. Voy a Catedral: https://www.google.com/maps")
    assert "Estoy aquí" not in sin and "Estoy aquí" in con
