"""Nodos 1 y 2 del grafo: normalizar el texto y decidir la intención con reglas.

Las reglas se revisan en el orden de la tabla de CLAUDE.md y gana la primera que coincide.
Son funciones puras (no usan la base ni internet), así que se pueden probar con un conjunto
fijo de preguntas (pruebas/preguntas_router.json).
"""

import re
from typing import Optional

from nombres import normalizar, sitios_mencionados

INTENCIONES = (
    "confirmacion", "mas_informacion", "ayuda", "compartir", "como_llegar", "itinerario", "eventos",
    "datos_practicos", "cercania", "saberes", "informacion", "fuera_de_alcance", "no_clara",
)

SI = {"si", "dale", "claro", "ya", "bueno", "ok", "okay", "vamos", "por favor", "si por favor", "sii", "listo", "de acuerdo", "si quiero", "claro que si"}
NO = {"no", "mejor no", "no gracias", "no quiero", "nada", "cancela", "cancelar", "ahora no"}

MAS_INFO = ("cuentame mas", "quiero saber mas", "dime mas", "mas informacion", "cuentame algo mas", "hay mas", "sabes mas", "algo mas sobre")
AYUDA = ("que puedes hacer", "que puedo preguntar", "que sabes", "ayuda", "como funciona", "para que sirves", "que haces")
COMPARTIR = ("avisa a", "avisale", "avisar a", "envia a", "enviale", "envia mi", "comparte", "compartir", "mi familia", "mi familiar", "mi mama", "mi papa", "donde estoy", "dile donde", "mandale")
VERBOS_IR = ("como llego", "como llegar", "como se llega", "como puedo llegar", "como voy", "como ir", "como puedo ir", "llevame", "quiero ir", "guiame", "me llevas", "vamos a", "quiero llegar", "como entro", "como se entra")
DONDE = ("donde queda", "donde esta", "donde se ubica", "donde es ", "ubicacion de", "la entrada", "por donde se entra", "donde queda la entrada")
ITINERARIO = ("que puedo visitar", "arma un recorrido", "armame un recorrido", "plan para hoy", "itinerario", "recorrido", "que puedo hacer hoy", "ruta turistica", "que visitar", "que conocer")
EVENTOS = ("feria", "fiesta", "festividad", "feriado", "evento", "hoy hay", "este fin de semana", "fin de semana", "que hay hoy", "que hay manana", "festival", "celebracion", "calendario", "carnaval", "entrada folklorica", "cuando es", "cuando son", "cuando se celebra", "cuando se hace", "cuando empieza", "cuando termina")
ORIGEN = ("de donde viene", "origen", "significado", "por que se celebra", "que significa", "como surgio", "como nacio")
PRACTICOS = ("horario", "a que hora", "hora de apertura", "cuando abre", "cuando cierra", "abierto", "cuanto cuesta", "costo", "precio", "cuanto cobran", "entrada cuesta", "cuanto tiempo", "cuanto dura", "duracion", "banos", "bano", "servicios", "baranda")
CERCANIA = ("cerca de mi", "cerca", "por aqui", "alrededor", "cercano", "cercanos", "mas proximo")
# Saberes: gastronomía, tradiciones y costumbres, fiestas (qué son y su origen), mitos y leyendas, danzas y música,
# artesanías y vestimenta, historia de Cochabamba, personajes históricos, quechua y naturaleza.
SABERES = (
    "leyenda", "mito", "tradicion", "tradiciones", "costumbre", "costumbres", "comida tipica", "plato tipico",
    "plato", "platos", "bebida", "bebidas", "ingrediente", "ingredientes", "gastronomia", "silpancho", "chicha",
    "pique macho", "trancapecho", "danza", "baile tipico", "musica tipica", "folklor", "folklore", "artesania",
    "artesanias", "textil", "textiles", "vestimenta", "pollera", "quechua", "cochala", "cochalo", "expresiones cochalas",
    "historia de cochabamba", "historia de la ciudad", "personaje historico", "personajes historicos", "heroina",
    "heroinas", "coronilla", "de donde viene la fiesta", "flora", "fauna", "geografia de cochabamba",
)
INFORMACION = (
    "cuentame", "cuenta me", "cuentame de", "historia", "que es", "como es", "que se escucha", "que se siente",
    "informacion", "hablame", "describeme", "descripcion", "piso", "tactil", "braille", "ruido", "ruidoso",
    "tranquilo", "silencioso", "perro", "lazarillo", "accesible", "accesibilidad", "recomienda", "recomiendas",
    "lugar", "lugares", "sitio", "sitios", "museo", "iglesia", "plaza", "catedral", "parque", "mercado", "teatro",
    "mirador", "laguna", "que ver", "que hay en", "sobre", "ambiente", "olor", "textura", "escalon", "gradas",
)
AJENOS = ("politica", "elecciones", "presidente", "futbol", "partido", "bolsa", "dolar", "bitcoin", "criptomoneda", "clima", "pronostico", "receta", "chiste", "horoscopo", "loteria", "impuestos", "medicina", "pastilla")
LUGARES_GENERICOS = ("museo", "iglesia", "plaza", "catedral", "parque", "mercado", "templo", "convento", "palacio", "teatro", "mirador", "laguna", "cristo", "basilica", "monumento", "estadio", "casona", "teleferico", "cementerio")

# Tipos de lugar que, seguidos de un nombre propio ("Museo del Louvre", "Torre Eiffel"), nombran un sitio concreto.
TIPOS_NOMBRADOS = (
    "museo", "iglesia", "plaza", "parque", "teatro", "catedral", "palacio", "basílica", "basilica", "estadio",
    "templo", "convento", "mercado", "torre", "mirador", "castillo", "puente", "monumento", "cementerio",
    "casona", "laguna", "santuario", "capilla", "teleférico", "teleferico",
)
_PATRON_LUGAR = re.compile(
    r"\b(?i:(" + "|".join(TIPOS_NOMBRADOS) + r"))\s+"
    r"((?:(?:de la|de los|de las|del|de|la|el)\s+)?[A-ZÁÉÍÓÚÑÜ][\w'\-]*"
    r"(?:\s+(?:(?:de la|de los|de las|del|de|y)\s+)?[A-ZÁÉÍÓÚÑÜ][\w'\-]*)*)"
)
GENERO_FEMENINO = ("iglesia", "plaza", "catedral", "basilica", "torre", "casona", "laguna", "capilla")

# Verbos que muestran que la persona QUIERE ir (cambian la acción: abrir navegación directo).
QUIERE_IR = VERBOS_IR


def _contiene(texto: str, frases) -> bool:
    """True si alguna frase aparece como palabras completas dentro del texto normalizado."""
    marco = f" {texto} "
    # La frase debe empezar en el inicio de una palabra ("feria" también encuentra "ferias").
    return any(f" {f.strip()}" in marco for f in frases)


contiene = _contiene      # nombre público para el grafo


def quiere_ir(texto_normalizado: str) -> bool:
    return _contiene(texto_normalizado, QUIERE_IR)


def respuesta_si_no(texto_normalizado: str) -> Optional[str]:
    """'si' o 'no' si el texto entero es una confirmación corta; si no, None."""
    t = texto_normalizado
    if len(t.split()) > 4:
        return None
    if t in SI or (t.startswith("si ") and len(t.split()) <= 3):
        return "si"
    if t in NO or t.startswith("no "):
        return "no"
    return None


def menciona_lugar_desconocido(texto_normalizado: str, nombres_ids: list) -> bool:
    """True si la pregunta habla de un tipo de lugar ('museo', 'iglesia'...) y no hay ningún sitio
    verificado nombrado: puede ser un sitio que no está en la base. En ese caso NUNCA se usa Wikipedia."""
    return not nombres_ids and any(p in texto_normalizado.split() for p in LUGARES_GENERICOS)


def clasificar(pregunta: str, sitios: list, contexto: Optional[dict] = None) -> dict:
    """Devuelve {'intencion', 'texto', 'sitios_ids', 'por_reglas'}.

    'sitios' es la lista (id, nombre) de sitios verificados. 'intencion' puede ser None cuando
    ninguna regla coincide: el grafo decide entonces si usa el clasificador (2b) o el respaldo.
    """
    contexto = contexto or {}
    t = normalizar(pregunta)
    ids = sitios_mencionados(pregunta, sitios)
    resultado = {"texto": t, "sitios_ids": ids, "por_reglas": True}

    def r(intencion):
        resultado["intencion"] = intencion
        return resultado

    if contexto.get("accion_pendiente") and respuesta_si_no(t):
        return r("confirmacion")
    if _contiene(t, MAS_INFO):
        return r("mas_informacion")
    if _contiene(t, AYUDA):
        return r("ayuda")
    if _contiene(t, COMPARTIR):
        return r("compartir")
    # "la entrada" sola es de cómo llegar, pero "¿cuánto cuesta la entrada?" es un dato práctico.
    if _contiene(t, VERBOS_IR) or (_contiene(t, DONDE) and not _contiene(t, PRACTICOS) and not _contiene(t, ("entrada folklorica",))):
        return r("como_llegar")
    if _contiene(t, ITINERARIO):
        return r("itinerario")
    if _contiene(t, EVENTOS) and not _contiene(t, ORIGEN):
        return r("eventos")
    if _contiene(t, PRACTICOS):
        return r("datos_practicos")
    if _contiene(t, CERCANIA):
        return r("cercania")
    # Si nombra un sitio, siempre es 'informacion', aunque diga "leyenda".
    if ids:
        return r("informacion")
    if _contiene(t, SABERES) or _contiene(t, ORIGEN):
        # Un tipo de lugar sin sitio reconocido puede ser un sitio fuera de la base: no es saberes.
        return r("informacion" if menciona_lugar_desconocido(t, ids) else "saberes")
    if _contiene(t, AJENOS):
        return r("fuera_de_alcance")
    if _contiene(t, INFORMACION):
        return r("informacion")
    resultado["intencion"] = None
    resultado["por_reglas"] = False
    return resultado


def lugar_no_registrado(pregunta: str, nombres_ids: list) -> Optional[dict]:
    """Detecta un lugar con nombre propio ("Museo del Louvre") que NO es un sitio verificado.

    Solo mira el texto original (con mayúsculas) y solo si la pregunta no nombra ningún sitio de la base.
    Devuelve {'lugar', 'tipo', 'tipo_plural', 'articulo', 'de_cochabamba'} o None.
    'de_cochabamba' es True si la pregunta dice "Cochabamba"; si no, se trata como un lugar de fuera.
    """
    if nombres_ids:
        return None
    m = _PATRON_LUGAR.search(pregunta)
    if not m:
        return None
    tipo = normalizar(m.group(1))
    lugar = f"{m.group(1)} {m.group(2)}".strip()
    # Quita "de Cochabamba" del nombre: es el contexto, no parte del nombre.
    lugar = re.sub(r"\s+(?:de|en)\s+Cochabamba\b.*$", "", lugar)
    femenino = tipo in GENERO_FEMENINO
    return {
        "lugar": lugar,
        "tipo": tipo,
        "tipo_plural": tipo + ("es" if tipo.endswith(("l", "r")) else "s"),
        "articulo": "las" if femenino else "los",
        "de_cochabamba": "cochabamba" in normalizar(pregunta),
    }


# ---------------------------------------------------------------------------------------------
# Eje «tipo de dato»: operativo (solo base verificada) o narrativo (cascada N1 a N4)
# ---------------------------------------------------------------------------------------------
OPERATIVO = (
    "donde", "cuando", "cuanto", "cuantos", "horario", "hora", "horas", "precio", "precios", "cuesta", "costo", "cobran",
    "llego", "llegar", "como voy", "accesible", "accesibilidad", "piso", "tactil", "braille", "perro", "perros",
    "lazarillo", "ruido", "ruidoso", "tranquilo", "silencioso", "entrada", "abre", "cierra", "abierto", "telefono",
    "direccion", "escalon", "escalones", "gradas", "banos", "servicios",
)
INTENCIONES_OPERATIVAS = ("como_llegar", "datos_practicos", "eventos", "cercania", "itinerario", "compartir")


def eje_dato(texto_normalizado: str, intencion: str) -> str:
    """'operativo' (dónde, cuándo, cuánto, horario, precio, cómo llego, accesibilidad: solo base verificada)
    o 'narrativo' (qué es, de dónde viene, qué significa, historia, leyenda, cuéntame)."""
    if intencion in INTENCIONES_OPERATIVAS:
        return "operativo"
    if intencion == "saberes" or intencion == "mas_informacion":
        return "narrativo"
    t = texto_normalizado.replace("de donde", " ")
    if intencion in ("informacion", "no_clara") and any(
        p in t.split() or (" " in p and p in t) for p in OPERATIVO
    ):
        return "operativo"
    return "narrativo"


_PARTE_OPERATIVA = re.compile(
    r"^(?P<narrativa>.+?)\s+y\s+(?P<operativa>(?:donde|cuando|cuanto|a que hora|como llego|como llegar|como se llega)\b.*)$"
)


def dividir_compuesta(texto_normalizado: str) -> Optional[tuple]:
    """Pregunta compuesta («¿Qué es la chicha y dónde la puedo probar?») -> (parte narrativa, parte operativa).
    Máximo 2 partes. None si no es compuesta."""
    m = _PARTE_OPERATIVA.match(texto_normalizado)
    if not m:
        return None
    narrativa, operativa = m.group("narrativa").strip(), m.group("operativa").strip()
    cue = ("que es", "que son", "de donde", "que significa", "historia", "leyenda", "cuentame", "origen", "quien fue", "como se hace")
    if not any(c in narrativa for c in cue) and not _contiene(narrativa, SABERES):
        return None
    return narrativa, operativa
