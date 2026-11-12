"""Herramientas eventos_por_fecha y eventos_de_hoy (solo SQL, sin LLM).

Los eventos se leen de la tabla `eventos`; Wikipedia nunca se usa para eventos ni para sus fechas.
"""

from datetime import date, timedelta
from typing import Optional

import config
from servicios import geo
from servicios.herramientas import datos

DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def decir_fecha(f: date) -> str:
    return f"{DIAS[f.weekday()]} {f.day} de {MESES[f.month - 1]}"


def rango_de_la_pregunta(pregunta_normalizada: str, hoy: date) -> tuple:
    """(desde, hasta, etiqueta) según palabras como 'hoy', 'mañana', 'fin de semana'. Por defecto, 30 días."""
    t = pregunta_normalizada
    if "pasado manana" in t:
        d = hoy + timedelta(days=2)
        return d, d, "pasado mañana"
    if "manana" in t:
        d = hoy + timedelta(days=1)
        return d, d, "mañana"
    if "fin de semana" in t:
        sabado = hoy + timedelta(days=(5 - hoy.weekday()) % 7) if hoy.weekday() < 5 else hoy - timedelta(days=hoy.weekday() - 5)
        return sabado, sabado + timedelta(days=1), "este fin de semana"
    if "esta semana" in t or "semana" in t:
        return hoy, hoy + timedelta(days=6 - hoy.weekday()), "esta semana"
    if "este mes" in t or "mes" in t.split():
        siguiente = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1)
        return hoy, siguiente - timedelta(days=1), "este mes"
    if "hoy" in t:
        return hoy, hoy, "hoy"
    return hoy, hoy + timedelta(days=30), "en los próximos 30 días"


def _con_distancia(eventos: list, latitud: Optional[float], longitud: Optional[float]) -> list:
    """Agrega 'distancia_m' y pone primero el más cercano dentro de RADIO_EVENTO_KM."""
    for e in eventos:
        e["distancia_m"] = None
        if latitud is not None and longitud is not None and e.get("latitud") is not None:
            e["distancia_m"] = round(geo.distancia_m(latitud, longitud, e["latitud"], e["longitud"]))
    radio = config.RADIO_EVENTO_KM * 1000
    cerca = sorted((e for e in eventos if e["distancia_m"] is not None and e["distancia_m"] <= radio), key=lambda e: e["distancia_m"])
    resto = [e for e in eventos if e not in cerca]
    return cerca + resto


def eventos_por_fecha(conn, desde: date, hasta: date, latitud: Optional[float] = None, longitud: Optional[float] = None) -> list:
    """Eventos del rango. Con ubicación, el más cercano (dentro del radio) va primero."""
    return _con_distancia(datos.eventos_entre(conn, desde, hasta), latitud, longitud)


def eventos_de_hoy(conn, latitud: Optional[float] = None, longitud: Optional[float] = None) -> list:
    """Eventos vigentes hoy (hora de Bolivia). Con ubicación, el más cercano va primero."""
    h = datos.hoy(conn)
    return eventos_por_fecha(conn, h, h, latitud, longitud)


def frase_evento(e: dict) -> str:
    """Una frase para leer: nombre, fechas, hora, zona y distancia."""
    ini, fin = e["fecha_inicio"], e.get("fecha_fin")
    cuando = decir_fecha(ini) if not fin or fin == ini else f"del {decir_fecha(ini)} al {decir_fecha(fin)}"
    partes = [f"{e['nombre']}, {cuando}"]
    if e.get("hora_inicio"):
        hora = e["hora_inicio"].strftime("%H:%M")
        if e.get("hora_fin"):
            hora += " a " + e["hora_fin"].strftime("%H:%M")
        partes.append(f"a las {hora}" if not e.get("hora_fin") else f"de {hora}")
    if e.get("zona"):
        partes.append(f"en {e['zona']}")
    if e.get("distancia_m") is not None:
        partes.append(geo.decir_distancia(e["distancia_m"]))
    return " ".join(partes) + "."
