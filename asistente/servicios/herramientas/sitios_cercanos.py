"""Herramienta sitios_cercanos: sitios verificados ordenados por distancia (haversine)."""

from typing import Optional

import config
from servicios import geo
from servicios.herramientas import datos


def sitios_cercanos(
    conn, latitud: float, longitud: float, radio_km: Optional[float] = None, limite: int = 5
) -> list:
    """Sitios verificados con coordenadas dentro de 'radio_km', del más cercano al más lejano.
    Cada sitio trae 'distancia_m'. No guarda la ubicación: se usa solo en esta consulta."""
    radio_km = config.RADIO_CERCA_KM if radio_km is None else radio_km
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, latitud, longitud FROM sitios_turisticos "
            "WHERE estado = 'verificado' AND latitud IS NOT NULL AND longitud IS NOT NULL"
        )
        filas = cur.fetchall()
    con_distancia = sorted(
        ((geo.distancia_m(latitud, longitud, float(la), float(lo)), i) for i, la, lo in filas),
        key=lambda x: x[0],
    )
    elegidos = [(d, i) for d, i in con_distancia if d <= radio_km * 1000][:limite]
    sitios = datos.sitios_por_ids(conn, [i for _, i in elegidos])
    distancias = {i: d for d, i in elegidos}
    for s in sitios:
        s["distancia_m"] = round(distancias[s["id"]])
    return sitios
