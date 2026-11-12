"""Tres llamadas REALES de humo a Gemini (una por agente). Gastan cuota: se ejecutan a mano, no en la suite.

    docker compose run --rm backend python -m pytest /app/pruebas/humo_agentes.py -q -p no:cacheprovider

Comprueban que la clave y el modelo del .env funcionan con Pydantic AI y que la salida viene tipada.
Si Gemini responde «503 alta demanda» o 429, la prueba se marca como omitida (no es un fallo del código).
No imprimen claves.
"""

import pytest

import modelo
from db import conectar
from servicios import cascada
from servicios.agentes import agente_clasificador, agente_saberes, agente_sitios, proveedor
from servicios.herramientas.buscar_web import IntentoWeb

pytestmark = pytest.mark.humo


def _exige_llm(ej):
    if ej.salida is None and ej.motivo_sin_llm in ("error_api", "limite_cuota_429", "tiempo_agotado"):
        pytest.skip(f"Gemini no respondió ahora ({ej.motivo_sin_llm}); reintenta en unos minutos")
    assert ej.salida is not None, f"sin salida: {ej.motivo_sin_llm}"


def test_humo_1_clasificador():
    assert proveedor.disponible(), "falta LLM_PROVEEDOR=google, LLM_MODELO o la clave en el .env"
    ej = agente_clasificador.clasificar("Me da curiosidad lo que comen los cochabambinos")
    _exige_llm(ej)
    assert ej.salida.intencion == "saberes" and ej.salida.eje_dato == "narrativo"


def test_humo_2_sitios():
    ej = agente_sitios.redactar(
        "Cuéntame de la Catedral",
        "SITIO: Catedral Metropolitana (iglesia)\nDescripción: Iglesia de piedra con eco suave y olor a incienso.\nVerificado en: noviembre de 2026",
    )
    _exige_llm(ej)
    assert len(ej.salida.texto) > 20 and "verificaci" in ej.salida.texto.lower()


def test_humo_3_saberes():
    conn = conectar()
    try:
        cas = cascada.Cascada(conn, "leyenda de la piedra que canta", modelo.vectorizar_pregunta("leyenda de la piedra que canta"),
                              modelo.vectorizar_pregunta, [], "leyenda", True, lambda *a, **k: IntentoWeb())
        ev = cas.ejecutar()
        assert ev.nivel == "documento"
        ej = agente_saberes.redactar(cas, ev)
    finally:
        conn.close()
    _exige_llm(ej)
    assert len(ej.salida.texto) > 20
    assert cas.creditos_tavily == 0
