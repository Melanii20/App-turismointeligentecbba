"""Detecta si una pregunta menciona por su nombre a un sitio.

La búsqueda semántica no encuentra bien las preguntas por nombre ("¿Cómo llego a La Cancha?"),
porque el nombre no forma parte del texto que se vectoriza. Esta búsqueda por nombre
complementa a la semántica (enfoque híbrido). Son reglas simples y fáciles de explicar:

  R1. El nombre completo aparece en la pregunta ("la cancha", "cristo de la concordia").
  R2. Nombre de 2 o más palabras: aparecen todas sus palabras importantes, en cualquier orden
      ("convento santa teresa", sin el "de").
  R3. Nombre de 2 o más palabras: aparece una palabra que identifica a UN solo sitio
      ("el cristo", "teresa"). Se ignoran las palabras genéricas ("convento", "museo", "plaza"...)
      y las que se repiten en varios nombres, para no confundir sitios distintos.

Solo se consideran sitios verificados: quien llama a esta función pasa solo esos.
"""

import unicodedata
from collections import Counter

# Palabras que no ayudan a identificar un sitio.
PALABRAS_VACIAS = {"la", "el", "los", "las", "de", "del", "y", "e", "en", "a", "al", "un", "una", "unos", "unas"}

# Palabras comunes de lugares: sirven en R1/R2 (dentro del nombre completo) pero no solas en R3.
PALABRAS_GENERICAS = {
    "convento", "museo", "plaza", "iglesia", "catedral", "mercado", "parque", "templo", "cerro",
    "monumento", "teleferico", "casa", "palacio", "capilla", "santuario", "centro", "calle",
    "avenida", "puente", "basilica", "cementerio", "estadio", "teatro", "mirador", "ciudad",
    "lago", "laguna", "rio", "fortaleza", "hotel", "restaurante", "santa", "santo", "san",
}

LARGO_MINIMO_R3 = 4


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y sin signos: '¿Cómo llego a La Cancha?' -> 'como llego a la cancha'."""
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    letras = "".join(c if c.isalnum() else " " for c in sin_tildes)
    return " ".join(letras.split())


def palabras_importantes(nombre_normalizado: str) -> list:
    return [p for p in nombre_normalizado.split() if p not in PALABRAS_VACIAS]


def sitios_mencionados(pregunta: str, sitios: list) -> list:
    """Ids de los sitios cuyo nombre se menciona en la pregunta.

    'sitios' es una lista de (id, nombre) de sitios verificados.
    """
    texto = normalizar(pregunta)
    palabras_pregunta = set(texto.split())
    texto_con_bordes = f" {texto} "

    nombres = [(id_, normalizar(nombre)) for id_, nombre in sitios]
    # En cuántos nombres aparece cada palabra importante.
    frecuencia = Counter(p for _, n in nombres for p in set(palabras_importantes(n)))

    encontrados = []
    for id_, nombre in nombres:
        if not nombre:
            continue
        importantes = palabras_importantes(nombre)

        # R1: el nombre completo, como palabras completas.
        if f" {nombre} " in texto_con_bordes:
            encontrados.append(id_)
            continue

        # R2 y R3 solo para nombres de 2 o más palabras importantes (así "La Cancha" no se
        # confunde con "una cancha de fútbol").
        if len(importantes) < 2:
            continue
        if all(p in palabras_pregunta for p in importantes):
            encontrados.append(id_)
            continue
        if any(
            p in palabras_pregunta
            and frecuencia[p] == 1
            and len(p) >= LARGO_MINIMO_R3
            and p not in PALABRAS_GENERICAS
            for p in importantes
        ):
            encontrados.append(id_)
    return encontrados
