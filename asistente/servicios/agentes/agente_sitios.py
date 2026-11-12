"""Agente de sitios (intenciones informacion y cercania): redacta con el nivel 1 de la base.

Una sola llamada al LLM, SIN herramientas y SIN acceso a la web. El orquestador ya recuperó los sitios y
los fragmentos de documentos verificados; el agente solo los convierte en frases para ser escuchadas.
"""

from typing import List, Optional

from pydantic_ai import Agent

from servicios.agentes import ejecucion
from servicios.agentes.modelos import RespuestaAgente

INSTRUCCIONES = (
    "Eres la guía turística de Cochabamba (Bolivia) para personas que escuchan la respuesta, entre ellas personas "
    "ciegas. Responde en español usando SOLO el CONTEXTO que recibes; si algo no está, di que no lo tienes. "
    "Frases cortas para ser escuchadas, sin listas, sin emojis, máximo 4 oraciones. "
    "Menciona lo sensorial (sonidos, olores, texturas) si está en el contexto. "
    "Menciona la fuente que indica el contexto: la fecha de verificación del sitio («según la verificación de octubre "
    "de 2026») o el documento y su página («según la <título>, página <n>»). "
    "Nunca des datos de accesibilidad (piso táctil, braille, ruido, perros guía, entrada), horarios, precios, "
    "direcciones ni fechas que no estén escritos en el contexto, y nunca los saques de un documento. "
    "Devuelve solo el campo texto; los demás campos los completa el sistema."
)

agente = Agent(output_type=RespuestaAgente, instructions=INSTRUCCIONES, name="agente_sitios")


def redactar(pregunta: str, contexto: str, modelo=None) -> ejecucion.Ejecucion:
    prompt = f"PREGUNTA: {ejecucion.limpiar_pregunta(pregunta)}\n\nCONTEXTO:\n{contexto}"
    return ejecucion.ejecutar(agente, prompt, solicitudes_max=1, modelo=modelo)
