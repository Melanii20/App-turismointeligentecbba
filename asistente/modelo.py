"""Modelo de embeddings del asistente.

Usa el MISMO modelo con el que se indexan los sitios (texto_embedding.MODEL_NAME).
La pregunta del usuario se vectoriza tal cual, sin pasar por construir_texto():
esa función solo arma el texto de los sitios.
"""

from sentence_transformers import SentenceTransformer

from texto_embedding import MODEL_NAME

_modelo = None


def cargar():
    """Carga el modelo si todavía no está cargado (tarda unos segundos la primera vez)."""
    global _modelo
    if _modelo is None:
        _modelo = SentenceTransformer(MODEL_NAME)
    return _modelo


def esta_cargado() -> bool:
    return _modelo is not None


def vectorizar_pregunta(pregunta: str):
    """Devuelve el vector (768 números) de la pregunta."""
    return cargar().encode(pregunta)
