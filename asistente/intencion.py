"""Detecta si una pregunta es sobre cómo llegar o cómo acceder a un lugar.

Regla de CLAUDE.md: acceso_recomendacion y acceso_punto_referencia_entrada NO se
vectorizan y solo se entregan cuando la pregunta es sobre cómo llegar o acceder.
Se usan reglas simples y transparentes (palabras clave), fáciles de explicar y de probar.
"""

import unicodedata

# Fragmentos que indican una pregunta sobre llegar o acceder (ya sin tildes ni mayúsculas).
PALABRAS_LLEGADA = (
    "como llego",
    "como llegar",
    "como se llega",
    "como puedo llegar",
    "como voy",
    "como ir",
    "como entro",
    "como entrar",
    "como ingreso",
    "como ingresar",
    "como acceder",
    "como accedo",
    "como se accede",
    "donde queda",
    "donde esta",
    "donde se ubica",
    "donde es la entrada",
    "la entrada",
    "entrada",
    "acceso",
    "llegar",
    "ubicacion",
    "direccion",
)


def _normalizar(texto: str) -> str:
    """Minúsculas y sin tildes: 'Cómo LLEGO' -> 'como llego'."""
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")


def pregunta_sobre_llegada(pregunta: str) -> bool:
    """True si la pregunta parece ser sobre cómo llegar o cómo acceder al lugar."""
    normalizada = _normalizar(pregunta)
    return any(palabra in normalizada for palabra in PALABRAS_LLEGADA)


# Qué dato de accesibilidad pregunta la persona. Se compara el INICIO de cada palabra de la
# pregunta (así "ruido", "ruidoso" y "ruidosa" coinciden con "ruid", pero "episodio" no es "piso").
# El orden de esta tabla es el orden en que se responden los datos.
PREFIJOS_POR_TEMA = {
    "sensorial": ("ambiente", "olor", "sonido", "escuch", "textur", "sensacion", "siente", "sentir", "huele"),
    "piso": ("piso", "suelo", "empedrad", "escalon", "desnivel", "resbal", "terreno", "gradas"),
    "tactil": ("tactil", "podotactil"),
    "braille": ("braille",),
    "perros": ("perro", "lazarill", "mascota"),
    "ruido": ("ruid", "silenci", "tranquil", "bullici", "bulla", "escandal"),
}


def temas_de_la_pregunta(pregunta: str) -> list:
    """Datos de accesibilidad por los que se pregunta (puede ser ninguno o varios).

    Sirve para responder primero lo que la persona quiere saber. Ejemplo:
    '¿Es ruidoso La Cancha?' -> ['ruido'].
    """
    letras = "".join(c if c.isalnum() else " " for c in _normalizar(pregunta))
    palabras = letras.split()
    return [
        tema
        for tema, prefijos in PREFIJOS_POR_TEMA.items()
        if any(palabra.startswith(prefijo) for palabra in palabras for prefijo in prefijos)
    ]
