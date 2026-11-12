"""Configuración común de las pruebas. Se ejecutan dentro de Docker (ver pruebas/README.md)."""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
for ruta in (RAIZ / "asistente", RAIZ):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def sin_llm_real(monkeypatch, request):
    """Las pruebas NUNCA gastan cuota de Gemini ni créditos de Tavily, aunque el .env tenga claves.
    Solo las pruebas marcadas @pytest.mark.humo (llamadas reales de humo) pueden usarlas."""
    if request.node.get_closest_marker("humo"):
        return
    try:
        from servicios.agentes import proveedor
        from servicios.herramientas import buscar_web
    except ImportError:          # las pruebas del panel corren en otra imagen, sin los agentes
        return

    monkeypatch.setattr(proveedor, "modelo", lambda: None)
    monkeypatch.setattr(buscar_web.config, "TAVILY_API_KEY", "")
    monkeypatch.setattr(buscar_web.config, "USER_AGENT", "")


def pytest_configure(config):
    config.addinivalue_line("markers", "humo: llamada real a Gemini o Tavily (gasta cuota); se ejecuta a mano")
