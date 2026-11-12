"""Cálculos de distancia y enlaces de mapa (todo gratis, sin APIs de pago)."""

import math
from typing import Optional


def distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en línea recta entre dos puntos, en metros (fórmula haversine)."""
    radio = 6371000.0
    f1, f2 = math.radians(lat1), math.radians(lat2)
    df = f2 - f1
    dl = math.radians(lon2 - lon1)
    a = math.sin(df / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2
    return 2 * radio * math.asin(math.sqrt(a))


def decir_distancia(metros: Optional[float]) -> str:
    """'a 320 metros' / 'a 1,4 kilómetros', pensado para leerse en voz alta."""
    if metros is None:
        return ""
    if metros < 100:
        return "a menos de cien metros"
    if metros < 1000:
        return f"a unos {int(round(metros, -1))} metros"
    return "a " + f"{metros / 1000:.1f}".replace(".", ",") + " kilómetros"


def enlace_mapa(latitud: float, longitud: float) -> str:
    """Enlace gratuito de Google Maps (sin clave) a un punto."""
    return f"https://www.google.com/maps/search/?api=1&query={latitud},{longitud}"
