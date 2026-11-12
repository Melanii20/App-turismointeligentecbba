"""Generador de respuestas del asistente.

Hoy hay un solo generador, "plantilla": arma la respuesta SOLO con los datos verificados de la
base, con frases cortas pensadas para leerse en voz alta. No usa inteligencia artificial, así que
no puede inventar nada: si un dato es null (sin verificar), no se menciona como si existiera.

El generador se elige con la variable de entorno GENERADOR. Más adelante se podrá agregar otro
(por ejemplo, un modelo de lenguaje local) sin cambiar el resto de la API.
"""

import os

GENERADORES_DISPONIBLES = ("plantilla",)
GENERADOR = os.environ.get("GENERADOR", "plantilla")
if GENERADOR not in GENERADORES_DISPONIBLES:
    raise ValueError(
        f"GENERADOR='{GENERADOR}' no existe todavía. Opciones disponibles: {', '.join(GENERADORES_DISPONIBLES)}"
    )

SIN_INFORMACION = "No tengo información sobre eso."
ORDINALES = ("Primero", "Segundo", "Tercero", "Cuarto", "Quinto")

# Para decir qué dato falta cuando se pregunta por algo que todavía no está verificado.
ETIQUETAS = {
    "sensorial": "ambiente",
    "piso": "piso",
    "tactil": "piso táctil",
    "braille": "señalización en braille",
    "perros": "ingreso de perros guía",
    "ruido": "nivel de ruido",
}
# Orden en que se cuentan los datos cuando no se pregunta por uno en particular.
ORDEN_GENERAL = ("sensorial", "piso", "tactil", "braille", "perros", "ruido")


# ---------- Utilidades de texto ----------
def _limpiar(texto: str) -> str:
    return " ".join(str(texto).split())


def _con_punto(texto: str) -> str:
    texto = _limpiar(texto)
    if not texto:
        return texto
    return texto if texto[-1] in ".!?…" else texto + "."


def _recortar(texto: str, maximo: int) -> str:
    """Recorta sin partir palabras, preferiblemente al final de una oración."""
    texto = _limpiar(texto)
    if len(texto) <= maximo:
        return texto
    corte = texto.rfind(". ", 0, maximo)
    if corte >= 80:
        return texto[: corte + 1]
    corte = texto.rfind(" ", 0, maximo)
    return texto[:corte].rstrip(",;:") + "…"


def _primera_oracion(texto: str, maximo: int = 240) -> str:
    texto = _limpiar(texto)
    corte = texto.find(". ")
    if corte != -1:
        texto = texto[: corte + 1]
    return _recortar(texto, maximo)


# ---------- Datos de accesibilidad -> frases ----------
def _dato(sitio: dict, tema: str):
    """Frase del dato pedido, o None si el dato no está verificado (null)."""
    acc = sitio.get("accesibilidad") or {}
    if tema == "sensorial":
        return _con_punto(_recortar(acc["descripcion_sensorial"], 320)) if acc.get("descripcion_sensorial") else None
    if tema == "piso":
        return f"El piso es {_limpiar(acc['tipo_piso'])}." if acc.get("tipo_piso") else None
    if tema == "ruido":
        return f"El nivel de ruido habitual es {_limpiar(acc['nivel_ruido'])}." if acc.get("nivel_ruido") else None
    textos_si_no = {
        "tactil": ("Tiene piso táctil.", "No tiene piso táctil.", "piso_tactil"),
        "braille": ("Tiene señalización en braille.", "No tiene señalización en braille.", "senalizacion_braille"),
        "perros": (
            "Se permite el ingreso de perros guía.",
            "No se permite el ingreso de perros guía.",
            "permite_perros_guia",
        ),
    }
    if tema in textos_si_no:
        si, no, clave = textos_si_no[tema]
        valor = acc.get(clave)
        if valor is None:
            return None
        return si if valor else no
    return None


def _frases_llegada(sitio: dict) -> list:
    """Cómo llegar y cómo reconocer la entrada, tal cual están verificados."""
    frases = []
    if sitio.get("direccion"):
        frases.append(f"La dirección es {_limpiar(sitio['direccion'])}.")
    llegar = sitio.get("como_llegar") or {}
    if llegar.get("punto_referencia_entrada"):
        frases.append("Para reconocer la entrada: " + _con_punto(llegar["punto_referencia_entrada"]))
    if llegar.get("recomendacion"):
        frases.append("Recomendación: " + _con_punto(llegar["recomendacion"]))
    return frases


def _un_sitio(sitio: dict, temas: list, sobre_llegada: bool) -> list:
    """Frases sobre un solo sitio, en el orden en que conviene escucharlas."""
    nombre = _limpiar(sitio["nombre"])
    frases = []
    pedidos = [t for t in ORDEN_GENERAL if t in temas]

    if sobre_llegada:
        frases.append(_con_punto(nombre))
        llegada = _frases_llegada(sitio)
        frases += llegada or ["Todavía no tengo verificado cómo llegar."]
        for tema in ("piso", "ruido"):
            if tema not in pedidos:
                pedidos.append(tema)
    elif pedidos:
        frases.append(_con_punto(nombre))
    else:
        frases.append(_con_punto(nombre))
        if sitio.get("descripcion"):
            frases.append(_con_punto(_primera_oracion(sitio["descripcion"])))
        pedidos = list(ORDEN_GENERAL)

    for tema in pedidos:
        dato = _dato(sitio, tema)
        if dato:
            frases.append(dato)
        elif tema in temas:
            # Se preguntó por algo que no está verificado: se dice, no se supone.
            frases.append(f"Todavía no tengo verificado el dato de {ETIQUETAS[tema]}.")
    return frases


def _varios_sitios(sitios: list, temas: list, sobre_llegada: bool) -> list:
    """Respuesta breve cuando hay varios sitios: una línea por sitio."""
    frases = [f"Encontré {len(sitios)} sitios que pueden servirte."]
    for i, sitio in enumerate(sitios):
        nombre = _limpiar(sitio["nombre"])
        ordinal = ORDINALES[i] if i < len(ORDINALES) else f"Sitio {i + 1}"
        partes = [f"{ordinal}, {nombre}."]
        pedidos = [t for t in ORDEN_GENERAL if t in temas]
        if sobre_llegada:
            partes += _frases_llegada(sitio)[:1]  # solo la dirección, si existe
        elif pedidos:
            for tema in pedidos:
                dato = _dato(sitio, tema)
                partes.append(dato or f"Todavía no tengo verificado el dato de {ETIQUETAS[tema]}.")
        elif sitio.get("descripcion"):
            partes.append(_con_punto(_primera_oracion(sitio["descripcion"], 160)))
        frases.append(" ".join(partes))
    return frases


def generar(pregunta: str, sitios: list, temas: list, sobre_llegada: bool) -> str:
    """Texto de la respuesta, listo para mostrarse y leerse en voz alta."""
    if not sitios:
        return SIN_INFORMACION

    if len(sitios) == 1:
        sitio = sitios[0]
        frases = _un_sitio(sitio, temas, sobre_llegada)
        # Si lo halló el significado y no el nombre, se dice con honestidad que es una sugerencia.
        if sitio.get("coincidencia") == "significado":
            frases.insert(0, "Lo que mejor encaja con tu pregunta es:")
    else:
        frases = _varios_sitios(sitios, temas, sobre_llegada)

    return " ".join(frases)
