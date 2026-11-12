"""Cálculo de embeddings dentro del panel.

El modelo se carga una sola vez al arrancar la app (ver 'lifespan' en main.py)
y se reutiliza en cada petición. El texto se arma con construir_texto() de
texto_embedding.py, el mismo que usa generar_embeddings.py.
"""

from sentence_transformers import SentenceTransformer

from texto_embedding import MODEL_NAME, construir_texto

_modelo = None


def cargar_modelo():
    """Carga el modelo si todavía no está cargado."""
    global _modelo
    if _modelo is None:
        _modelo = SentenceTransformer(MODEL_NAME)
    return _modelo


def modelo_cargado() -> bool:
    return _modelo is not None


def calcular_embedding(sitio: dict) -> list:
    """Devuelve el vector (768 números) de un sitio.

    'sitio' debe tener las claves que usa construir_texto(): descripcion y las
    columnas acceso_* (descripcion_sensorial, tipo_piso, piso_tactil,
    señalizacion_braille, permite_perros_guia, nivel_ruido).
    """
    return cargar_modelo().encode(construir_texto(sitio)).tolist()
