"""Agente de saberes: datos narrativos de la cultura de Cochabamba (cascada N1 -> N2 -> N3).

Tiene tres herramientas: buscar_en_base, buscar_en_cache y buscar_web. El ORDEN no depende del LLM:
las herramientas usan el estado de la Cascada (deps) y se niegan a saltarse un nivel.
Máximo 3 solicitudes al LLM por pregunta.
"""

from dataclasses import dataclass
from typing import Optional

from pydantic_ai import Agent, RunContext

from servicios import cascada as c
from servicios.agentes import ejecucion
from servicios.agentes.modelos import RespuestaAgente

INSTRUCCIONES = (
    "Eres la guía turística de Cochabamba (Bolivia) y respondes saberes: gastronomía, tradiciones, fiestas (qué son y su "
    "origen), mitos y leyendas, danzas y música, artesanías, historia, personajes, quechua y naturaleza. "
    "Responde en español usando SOLO el CONTEXTO. El sistema ya buscó por ti en el orden base verificada, caché y web, "
    "así que NO llames a ninguna herramienta si el CONTEXTO trae información. Solo si dice «todavía no se ha buscado» "
    "usa, en este orden, buscar_en_base, buscar_en_cache y buscar_web (la web se niega si no la antecedieron). "
    "Frases cortas para ser escuchadas, sin listas, sin emojis, máximo 4 oraciones. "
    "Cita siempre la fuente: «según la verificación de <mes año>», «según la <documento>, página <n>» o "
    "«Según <sitio> (información de internet)…». Si no hay nada relevante, di «No tengo información sobre eso». "
    "Nunca des horarios, precios, direcciones, fechas ni datos de accesibilidad. Devuelve solo el campo texto."
)


@dataclass
class DepsSaberes:
    cascada: c.Cascada


agente = Agent(output_type=RespuestaAgente, deps_type=DepsSaberes, instructions=INSTRUCCIONES, name="agente_saberes")


def _resumen(ev: c.Evidencia) -> str:
    return ev.contexto if ev.hay() else "Sin resultados."


@agente.tool
def buscar_en_base(ctx: RunContext[DepsSaberes], consulta: str) -> str:
    """Nivel 1: busca en los sitios, eventos y documentos verificados de la base."""
    return _resumen(c.evidencia_de_base(ctx.deps.cascada.en_base(consulta)))


@agente.tool
def buscar_en_cache(ctx: RunContext[DepsSaberes], consulta: str) -> str:
    """Nivel 2: busca en el contenido de internet ya guardado (vigente 30 días)."""
    try:
        encontrado = ctx.deps.cascada.en_cache(consulta)
    except c.OrdenInvalido as e:
        return f"NO PERMITIDO: {e}"
    return _resumen(c.evidencia_de_web(encontrado)) if encontrado else "Sin resultados."


@agente.tool
def buscar_web(ctx: RunContext[DepsSaberes], consulta: str) -> str:
    """Nivel 3: busca en internet (Tavily o Wikipedia). Solo si la base y la caché no alcanzaron."""
    try:
        intento = ctx.deps.cascada.en_web(consulta)
    except c.OrdenInvalido as e:
        return f"NO PERMITIDO: {e}"
    return _resumen(c.evidencia_de_web(intento.resultado)) if intento.resultado else "Sin resultados."


def redactar(cascada: c.Cascada, evidencia: c.Evidencia, modelo=None) -> ejecucion.Ejecucion:
    prompt = (
        f"PREGUNTA: {ejecucion.limpiar_pregunta(cascada.pregunta)}\n\nCONTEXTO ({evidencia.nivel}):\n{evidencia.contexto}"
        if evidencia.hay()
        else f"PREGUNTA: {ejecucion.limpiar_pregunta(cascada.pregunta)}\n\nCONTEXTO: (todavía no se ha buscado)"
    )
    return ejecucion.ejecutar(agente, prompt, solicitudes_max=3, deps=DepsSaberes(cascada), modelo=modelo)
