"""Agente clasificador (nodo 2b del grafo): solo se llama si ninguna regla coincidió.

Devuelve la intención y el tipo de dato (operativo o narrativo). Una sola solicitud al LLM.
"""

from typing import Optional

from pydantic_ai import Agent

from servicios.agentes import ejecucion
from servicios.agentes.modelos import Clasificacion

INSTRUCCIONES = (
    "Clasificas preguntas de una guía turística de Cochabamba, Bolivia. Devuelves intencion, eje_dato y sitio.\n"
    "Intenciones: ayuda (qué puede hacer la guía), compartir (avisar o enviar un mensaje a un familiar), "
    "como_llegar (ir a un lugar), itinerario (armar un recorrido o pedir un lugar para pasear), eventos (ferias, "
    "fiestas, calendario), datos_practicos (horario, costo, duración, baños), cercania (qué hay cerca), "
    "saberes (gastronomía, tradiciones, fiestas y su origen, mitos y leyendas, danzas y música, artesanías, "
    "historia, personajes, quechua, naturaleza; también lo que comen, beben, bailan, cantan, visten o celebran los "
    "cochabambinos), informacion (SOLO cuando nombra un sitio turístico concreto o pide su accesibilidad), "
    "fuera_de_alcance (política, deportes, finanzas, salud, clima, noticias y todo lo que no sea turismo y cultura "
    "de Cochabamba).\n"
    "eje_dato: operativo si pregunta dónde, cuándo, cuánto, horario, precio, cómo llego o accesibilidad; "
    "narrativo si pregunta qué es, de dónde viene, qué significa, historia o leyendas.\n"
    "sitio: el nombre del lugar si la pregunta nombra uno; si no, null. No inventes datos."
)

agente = Agent(output_type=Clasificacion, instructions=INSTRUCCIONES, name="agente_clasificador")


def clasificar(pregunta: str, modelo=None) -> ejecucion.Ejecucion:
    """Ejecucion.salida es una Clasificacion, o None si no hay LLM o falló (el grafo sigue sin él)."""
    return ejecucion.ejecutar(agente, ejecucion.limpiar_pregunta(pregunta), solicitudes_max=1, modelo=modelo)
