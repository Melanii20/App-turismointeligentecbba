"""Lógica compartida para construir el texto que se vectoriza.

La usan generar_embeddings.py y el panel de administración, para que los dos
generen exactamente el mismo texto (y por lo tanto el mismo embedding).
No importa librerías pesadas: solo define el modelo y arma el texto.
"""

# Modelo de embeddings multilingüe, gratuito y local (no necesita API key).
# Se debe usar SIEMPRE el mismo modelo para indexar y para consultar.
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"

# Columnas que construir_texto() necesita leer de la tabla sitios_turisticos.
COLUMNAS_TEXTO = (
    "nombre", "tipo", "descripcion", "relato", "que_ver", "acceso_descripcion_sensorial",
    "acceso_tipo_piso", "acceso_piso_tactil", "acceso_señalizacion_braille",
    "acceso_permite_perros_guia", "acceso_nivel_ruido",
)


def _hay(valor) -> bool:
    """True si el dato existe. Para texto, que no esté vacío; para sí/no, que no sea NULL
    (False también es un dato registrado)."""
    if valor is None:
        return False
    return bool(valor.strip()) if isinstance(valor, str) else True


def construir_texto(sitio: dict) -> str:
    """Une los textos del sitio y frases de accesibilidad en un solo texto, para que la
    búsqueda semántica encuentre el sitio tanto por su historia como por su acceso.

    Se vectorizan: nombre, tipo, descripción, relato, qué ver y descripción sensorial, más
    frases de los datos de accesibilidad. La frase solo se genera si el dato existe; un
    dato NULL ("sin información") no genera nada. No se vectorizan la recomendación, la
    referencia de la entrada, el horario, el costo, la duración, los servicios ni la dirección.
    """
    partes = []
    for campo in ("nombre", "tipo", "descripcion", "relato", "que_ver", "acceso_descripcion_sensorial"):
        valor = sitio.get(campo)
        if _hay(valor):
            partes.append(valor.strip())

    if _hay(sitio.get("acceso_tipo_piso")):
        partes.append(f"El piso del lugar es {sitio['acceso_tipo_piso']}.")

    tactil = sitio.get("acceso_piso_tactil")
    if tactil is not None:
        partes.append(
            "Cuenta con piso táctil para orientación de personas ciegas."
            if tactil else "No cuenta con piso táctil."
        )
    braille = sitio.get("acceso_señalizacion_braille")
    if braille is not None:
        partes.append("Tiene señalización en braille." if braille else "No tiene señalización en braille.")
    perros = sitio.get("acceso_permite_perros_guia")
    if perros is not None:
        partes.append(
            "Se permite el ingreso de perros guía." if perros else "No se permite el ingreso de perros guía."
        )
    if _hay(sitio.get("acceso_nivel_ruido")):
        partes.append(f"El nivel de ruido habitual del lugar es {sitio['acceso_nivel_ruido']}.")

    return " ".join(partes)
