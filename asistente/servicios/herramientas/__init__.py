"""Registro central de herramientas del asistente: nombre -> función.

Cada herramienta está en su archivo, con type hints y docstring en español. No dependen de FastAPI
ni de variables globales (reciben la conexión a la base como parámetro), así que en el futuro se
pueden exponer por MCP sin reescribirlas.

Nota: aquí se importan los MÓDULOS (no las funciones con su mismo nombre), para que
`from servicios.herramientas import buscar_sitios` siga devolviendo el módulo.
"""

from servicios.herramientas import (
    armar_itinerario as _armar_itinerario,
    armar_mensaje_compartir as _armar_mensaje_compartir,
    buscar_sitios as _buscar_sitios,
    buscar_en_base as _buscar_en_base,
    buscar_web as _buscar_web,
    como_llegar as _como_llegar,
    datos_practicos as _datos_practicos,
    decidir_accion as _decidir_accion,
    eventos as _eventos,
    generar_respuesta as _generar_respuesta,
    sitios_cercanos as _sitios_cercanos,
)

REGISTRO = {
    "buscar_sitios": _buscar_sitios.buscar_sitios,
    "sitios_cercanos": _sitios_cercanos.sitios_cercanos,
    "datos_practicos": _datos_practicos.datos_practicos,
    "como_llegar": _como_llegar.como_llegar,
    "eventos_por_fecha": _eventos.eventos_por_fecha,
    "eventos_de_hoy": _eventos.eventos_de_hoy,
    "armar_itinerario": _armar_itinerario.armar_itinerario,
    "armar_mensaje_compartir": _armar_mensaje_compartir.armar_mensaje_compartir,
    "buscar_en_base": _buscar_en_base.buscar_en_base,
    "buscar_en_cache": _buscar_web.buscar_en_cache,
    "buscar_web": _buscar_web.buscar_web,
    "decidir_accion": _decidir_accion.decidir_accion,
    "generar_respuesta": _generar_respuesta.generar_respuesta_sitios,
}
