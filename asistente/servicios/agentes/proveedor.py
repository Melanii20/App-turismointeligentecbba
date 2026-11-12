"""Proveedor del modelo: Gemini mediante Pydantic AI (LLM_PROVEEDOR=google).

Se usa GoogleModel con GoogleProvider(api_key=...) de la documentación actual de Pydantic AI
(el prefijo de texto equivalente es «google:<modelo>»; «google-gla:» es el nombre antiguo).
La clave sale de GOOGLE_API_KEY (o LLM_API_KEY) del .env y nunca se escribe en el código ni en registros.
"""

from typing import Optional

import config


def disponible() -> bool:
    """True si hay proveedor Google/Gemini, modelo y clave configurados."""
    return config.LLM_PROVEEDOR in ("google", "gemini") and bool(config.LLM_MODELO) and bool(config.LLM_API_KEY)


def motivo_no_disponible() -> str:
    if config.LLM_PROVEEDOR not in ("google", "gemini"):
        return "sin_proveedor"
    return "sin_clave" if not config.LLM_API_KEY else "sin_modelo"


def modelo():
    """El modelo de Gemini, o None si falta algo de la configuración."""
    if not disponible():
        return None
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider

    return GoogleModel(config.LLM_MODELO, provider=GoogleProvider(api_key=config.LLM_API_KEY))
