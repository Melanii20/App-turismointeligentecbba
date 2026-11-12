"""Herramienta armar_mensaje_compartir: texto listo para enviar a un familiar.

Nada se envía solo: la app abre WhatsApp o la hoja de compartir con este texto y la persona pulsa enviar.
"""

from typing import Optional

from servicios import geo


def armar_mensaje_compartir(
    sitios: list, incluir_ubicacion: bool = False,
    latitud: Optional[float] = None, longitud: Optional[float] = None,
) -> str:
    """'Hola, estoy usando Guía Cochala. Voy a <sitio>: <enlace>.' (varios sitios = recorrido).
    'Estoy aquí: <enlace>' se agrega solo si la persona lo pidió y envió su ubicación."""
    if not sitios:
        texto = "Hola, estoy usando Guía Cochala."
    elif len(sitios) == 1:
        s = sitios[0]
        enlace = f": {geo.enlace_mapa(s['latitud'], s['longitud'])}" if s.get("latitud") is not None else ""
        texto = f"Hola, estoy usando Guía Cochala. Voy a {s['nombre']}{enlace}."
    else:
        lineas = []
        for s in sitios:
            enlace = f": {geo.enlace_mapa(s['latitud'], s['longitud'])}" if s.get("latitud") is not None else ""
            lineas.append(f"- {s['nombre']}{enlace}")
        texto = "Hola, estoy usando Guía Cochala. Mi recorrido de hoy:\n" + "\n".join(lineas)
    if incluir_ubicacion and latitud is not None and longitud is not None:
        texto += f"\nEstoy aquí: {geo.enlace_mapa(latitud, longitud)}"
    return texto
