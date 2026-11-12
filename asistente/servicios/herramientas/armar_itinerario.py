"""Herramienta armar_itinerario: 2 a 4 sitios verificados en orden de recorrido + eventos de hoy."""

from typing import Optional

from pydantic import BaseModel, Field

from servicios import geo
from servicios.herramientas import datos, eventos as herr_eventos
from servicios.herramientas.sitios_cercanos import sitios_cercanos


class Itinerario(BaseModel):
    sitios: list = Field(default_factory=list)
    eventos_hoy: list = Field(default_factory=list)
    horas: float = 3


def armar_itinerario(
    conn, latitud: Optional[float] = None, longitud: Optional[float] = None, horas: float = 3
) -> Itinerario:
    """Con ubicación: los sitios más cercanos (el más cercano primero) y luego cada uno al más próximo del anterior.
    Sin ubicación: los primeros sitios verificados con coordenadas, en orden de nombre.
    La cantidad (2 a 4) depende de las horas disponibles: unas 45 min por sitio, o la duración registrada."""
    maximo = max(2, min(4, int(horas * 60 // 45)))
    if latitud is not None and longitud is not None:
        candidatos = sitios_cercanos(conn, latitud, longitud, radio_km=5, limite=8)
        if not candidatos:
            candidatos = []
    else:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM sitios_turisticos WHERE estado = 'verificado' "
                "AND latitud IS NOT NULL AND longitud IS NOT NULL ORDER BY nombre LIMIT 8"
            )
            candidatos = datos.sitios_por_ids(conn, [f[0] for f in cur.fetchall()])

    ruta = []
    if candidatos:
        ruta.append(candidatos.pop(0))
        while candidatos and len(ruta) < maximo:
            ult = ruta[-1]
            candidatos.sort(key=lambda s: geo.distancia_m(ult["latitud"], ult["longitud"], s["latitud"], s["longitud"]))
            ruta.append(candidatos.pop(0))
    return Itinerario(
        sitios=ruta, eventos_hoy=herr_eventos.eventos_de_hoy(conn, latitud, longitud), horas=horas
    )


def frases(it: Itinerario) -> list:
    if not it.sitios:
        return ["Todavía no tengo sitios verificados cerca para armar un recorrido."]
    salida = [f"Te propongo {len(it.sitios)} lugares, en este orden."]
    for i, s in enumerate(it.sitios, 1):
        extra = f" Visita de {s['duracion_visita']}." if s.get("duracion_visita") else ""
        salida.append(f"{i}. {s['nombre']}.{extra}")
    if it.eventos_hoy:
        salida.append("Además, hoy hay: " + " ".join(herr_eventos.frase_evento(e) for e in it.eventos_hoy[:2]))
    return salida
