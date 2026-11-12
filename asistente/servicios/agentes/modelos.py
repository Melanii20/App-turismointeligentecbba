"""Modelos de entrada y salida (Pydantic) de los agentes."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Clasificacion(BaseModel):
    """Salida del agente clasificador."""

    intencion: Literal[
        "ayuda", "compartir", "como_llegar", "itinerario", "eventos", "datos_practicos",
        "cercania", "saberes", "informacion", "fuera_de_alcance",
    ]
    eje_dato: Literal["operativo", "narrativo"]
    sitio: Optional[str] = None


class RespuestaAgente(BaseModel):
    """Salida común de los agentes que redactan. El código corrige nivel_fuente y fuentes con lo que
    realmente se recuperó: el LLM solo aporta el texto."""

    texto: str = Field(description="Respuesta para ser escuchada, máximo 4 oraciones, sin listas ni emojis.")
    nivel_fuente: Literal["base", "documento", "cache_web", "web", "ninguna"] = "ninguna"
    fuentes: List[dict] = Field(default_factory=list)
    uso_herramientas: List[str] = Field(default_factory=list)
