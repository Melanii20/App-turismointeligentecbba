"""Ejecución común de los agentes: límites de uso, tiempo máximo y motivo cuando no se usó el LLM."""

import logging
import re
from typing import Any, Optional

from pydantic import BaseModel

import config
from servicios.agentes import proveedor


registro = logging.getLogger("agentes")


class Ejecucion(BaseModel):
    """Resultado de intentar usar un agente. Si salida es None, el grafo usa la plantilla."""

    salida: Any = None
    motivo_sin_llm: Optional[str] = None
    solicitudes: int = 0


def limpiar_pregunta(texto: str) -> str:
    """Quita correos y números largos (teléfonos) antes de enviar la pregunta a un servicio externo."""
    texto = re.sub(r"\S+@\S+", "[dato personal]", texto)
    return re.sub(r"\+?\d[\d\s\-]{6,}\d", "[dato personal]", texto)


def motivo_de_error(error: Exception) -> str:
    nombre = type(error).__name__
    texto = str(error)
    if "429" in texto or "RESOURCE_EXHAUSTED" in texto or "quota" in texto.lower():
        return "limite_cuota_429"
    if nombre in ("TimeoutError", "ReadTimeout", "ConnectTimeout") or "timeout" in nombre.lower() or "timed out" in texto.lower():
        return "tiempo_agotado"
    if nombre == "UsageLimitExceeded":
        return "limite_solicitudes"
    if nombre in ("UnexpectedModelBehavior", "ValidationError"):
        return "salida_invalida"
    return "error_api"


def ejecutar(agente, prompt: str, solicitudes_max: int, deps=None, modelo=None) -> Ejecucion:
    """Una ejecución de 'agente' con límite de solicitudes y de tiempo (AGENTE_TIMEOUT_S).

    'modelo' permite poner un TestModel o FunctionModel en las pruebas (no gasta cuota).
    Nunca lanza: ante cualquier fallo devuelve salida=None y el motivo.
    """
    from pydantic_ai import UsageLimits

    try:
        elegido = modelo or proveedor.modelo()           # crear el modelo también puede fallar (clave o modelo mal puestos)
        if elegido is None:
            return Ejecucion(motivo_sin_llm=proveedor.motivo_no_disponible())
        resultado = agente.run_sync(
            prompt, model=elegido, deps=deps, usage_limits=UsageLimits(request_limit=solicitudes_max),
            timeout=config.AGENTE_TIMEOUT_S,
        )
        return Ejecucion(salida=resultado.output, solicitudes=resultado.usage.requests)
    except Exception as error:
        motivo = motivo_de_error(error)
        detalle = str(error).replace(config.LLM_API_KEY, "***") if config.LLM_API_KEY else str(error)
        registro.warning("agente %s sin LLM (%s): %s: %s", getattr(agente, "name", "?"), motivo, type(error).__name__, detalle[:300])
        return Ejecucion(motivo_sin_llm=motivo)
