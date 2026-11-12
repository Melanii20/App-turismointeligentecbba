"""Herramientas buscar_en_cache y buscar_web (niveles 2 y 3 de la cascada narrativa).

Reemplazan a buscar_wikipedia. Reglas (CLAUDE.md):
  - Solo se usan para datos NARRATIVOS de saberes de Cochabamba o Bolivia (gastronomía, tradiciones, fiestas
    —qué son, no cuándo—, leyendas, danzas y música, artesanías, historia, personajes, quechua, naturaleza),
    y siempre DESPUÉS de la base verificada (nivel 1). Nunca para datos operativos (dónde, cuándo, cuánto,
    horario, precio, accesibilidad...).
  - N2 buscar_en_cache: tabla contenido_web, vigente 30 días, sin lo que se descartó en el panel.
  - N3 buscar_web: Tavily (search_depth basic, 3 resultados, country bolivia, solo DOMINIOS_CONFIABLES).
    Respaldo si no hay clave, hay error o se acabaron los créditos: Wikipedia directa.
  - Un resultado se acepta solo si score >= TAVILY_SCORE_MIN y su texto menciona el tema y Cochabamba o Bolivia.
  - Se guarda siempre la URL y se cita. Wikipedia es CC BY-SA 4.0.
  - Nunca se envía a internet la ubicación, el contacto ni datos de la persona: solo el tema de la pregunta.
"""

from typing import List, Optional
from urllib.parse import quote, urlparse

import logging

import httpx
from pydantic import BaseModel

import config
from nombres import normalizar

LIMITE_CACHE = 200          # filas de la caché que se comparan por pregunta (las más recientes)
BUSCAR_WIKI = "https://es.wikipedia.org/w/rest.php/v1/search/page"
RESUMEN_WIKI = "https://es.wikipedia.org/api/rest_v1/page/summary/"

# tema -> palabras que lo identifican (sin tildes). El orden importa: gana el primero que coincide.
TEMAS = {
    "leyenda": ("leyenda", "mito", "cuento", "duende", "llorona", "condenado", "viuda"),
    "idioma": ("quechua", "idioma", "como se dice", "cochala", "cochalo", "expresion", "palabra", "significa en quechua"),
    "gastronomia": ("comida", "plato", "bebida", "ingrediente", "ingredientes", "silpancho", "chicha", "api", "pique", "receta",
                    "gastronomia", "sopa", "postre", "desayuno", "trancapecho", "chorizo", "fritanga", "comen", "tomar"),
    "danza": ("danza", "baile", "musica", "folklor", "folklore", "morenada", "caporal", "tinku", "cueca", "canto", "instrumento"),
    "artesania": ("artesania", "textil", "vestimenta", "pollera", "tejido", "ceramica", "sombrero", "tejidos"),
    "personaje": ("personaje", "heroina", "heroinas", "coronilla", "heroe", "quien fue", "quienes fueron", "batalla"),
    "fiesta": ("fiesta", "festividad", "carnaval", "urkupina", "virgen", "significado", "origen"),
    "tradicion": ("tradicion", "costumbre", "ritual", "creencia", "celebracion"),
    "historia": ("historia", "fundacion", "epoca", "colonial", "guerra", "independencia", "fundo"),
    "naturaleza": ("naturaleza", "flora", "fauna", "geografia", "montana", "cerro", "tunari", "valle", "rio", "animales", "plantas", "paisaje"),
}
TEMAS_QUE_ACEPTAN_BOLIVIA = ("gastronomia", "danza", "idioma")     # se busca con «Bolivia» en vez de «Cochabamba»
VACIAS = {
    "cuentame", "dime", "me", "la", "el", "los", "las", "de", "del", "que", "es", "un", "una", "sobre", "y", "en", "a",
    "por", "quien", "fue", "como", "cual", "cuales", "hay", "puedes", "contar", "algo", "hablame", "se", "su", "sus", "lo",
    "al", "con", "para", "son", "era", "eran", "donde", "viene", "dice", "significa", "cochabamba", "bolivia",
    "cochabambino", "cochabambina", "cochabambinos", "cochabambinas", "tipico", "tipica", "tipicos", "tipicas",
    "dice", "dicen", "decir", "ese", "esa", "esto", "este",
}


registro = logging.getLogger("buscar_web")


class ResultadoWeb(BaseModel):
    """Salida de las herramientas de caché y web."""

    titulo: str
    texto: str
    url: str
    dominio: str
    tema: str
    licencia: str = "CC BY-SA 4.0"
    desde_cache: bool = False
    fuente: str = "tavily"            # tavily | wikipedia
    creditos_tavily: int = 0
    id_contenido: Optional[int] = None


def detectar_tema(texto_normalizado: str) -> Optional[str]:
    """Tema de saberes de la pregunta, o None si no es un tema reconocido."""
    tokens = texto_normalizado.split()
    marco = f" {texto_normalizado} "
    for tema, claves in TEMAS.items():
        for c in claves:
            if " " in c:
                if f" {c} " in marco:
                    return tema
            elif any(t == c or (len(c) >= 5 and t.startswith(c)) for t in tokens):
                return tema
    return None


def palabras_clave(texto_normalizado: str) -> List[str]:
    """Palabras importantes de la pregunta (sin las vacías), para armar la búsqueda y comprobar relevancia."""
    return [p for p in texto_normalizado.split() if p not in VACIAS and len(p) > 2]


def nombre_de_dominio(dominio: str) -> str:
    """Nombre legible para citar: es.wikipedia.org -> Wikipedia."""
    d = (dominio or "").lower()
    return "Wikipedia" if d.endswith("wikipedia.org") else d.removeprefix("www.")


def _relevante(titulo: str, texto: str, consulta_norm: str) -> bool:
    """El texto menciona el tema de la pregunta y Cochabamba o Bolivia."""
    contenido = normalizar(f"{titulo} {texto}")
    if "cochabamba" not in contenido and "bolivia" not in contenido:
        return False
    claves = palabras_clave(consulta_norm)
    return not claves or any(c in contenido for c in claves)


# ---------------------------------------------------------------------------------------------
# N2 · caché
# ---------------------------------------------------------------------------------------------
def buscar_en_cache(conn, consulta: str, tema: str) -> Optional[ResultadoWeb]:
    """Nivel 2: contenido de internet ya guardado (vigente CACHE_WEB_DIAS días y no descartado)."""
    claves = palabras_clave(normalizar(consulta))
    if not claves:
        return None
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, fuente, titulo, texto, url, tema, licencia, COALESCE(dominio, ''), estado_revision FROM contenido_web
            WHERE obtenido_en > now() - make_interval(days => %s) AND estado_revision <> 'descartado'
              AND tema = %s
            ORDER BY obtenido_en DESC
            LIMIT %s
            """,
            (config.CACHE_WEB_DIAS, tema, LIMITE_CACHE),
        )
        filas = cur.fetchall()
    mejor, puntos_mejor = None, 0
    for f in filas:
        contenido = normalizar(f"{f[2]} {f[3]}")
        puntos = sum(1 for c in claves if c in contenido)
        # Debe coincidir casi todo lo que se pregunta (75 %): un «gracias en quechua» no se contesta con la página del Tinku.
        if puntos >= max(1, -(-3 * len(claves) // 4)) and puntos > puntos_mejor:
            mejor, puntos_mejor = f, puntos
    if not mejor:
        return None
    return ResultadoWeb(
        id_contenido=mejor[0], fuente=mejor[1], titulo=mejor[2], texto=mejor[3], url=mejor[4], tema=mejor[5],
        licencia=mejor[6], dominio=mejor[7] or urlparse(mejor[4]).netloc, desde_cache=True,
    )


# ---------------------------------------------------------------------------------------------
# N3 · web
# ---------------------------------------------------------------------------------------------
def _cliente_tavily():
    """Cliente de Tavily. Se separa en una función para poder simularlo en las pruebas."""
    from tavily import TavilyClient

    return TavilyClient(api_key=config.TAVILY_API_KEY)


def _consulta_web(consulta: str, tema: str) -> str:
    """Tema + palabras de la pregunta + «Cochabamba» (o «Bolivia» para gastronomía, danzas e idioma)."""
    lugar = "Bolivia" if tema in TEMAS_QUE_ACEPTAN_BOLIVIA else "Cochabamba"
    palabras = palabras_clave(normalizar(consulta))
    if tema not in palabras:
        palabras.insert(0, tema)
    return " ".join(palabras + [lugar])


def _guardar(conn, fuente: str, r: ResultadoWeb) -> bool:
    """Guarda en contenido_web. Devuelve False si esa página ya fue descartada en el panel."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT estado_revision FROM contenido_web WHERE fuente = %s AND titulo = %s", (fuente, r.titulo))
            antes = cur.fetchone()
            if antes and antes[0] == "descartado":
                return False
            cur.execute(
                """
                INSERT INTO contenido_web (fuente, tema, titulo, url, texto, licencia, dominio)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fuente, titulo) DO UPDATE
                  SET tema = EXCLUDED.tema, url = EXCLUDED.url, texto = EXCLUDED.texto,
                      dominio = EXCLUDED.dominio, obtenido_en = now()
                RETURNING id
                """,
                (fuente, r.tema, r.titulo, r.url, r.texto, r.licencia, r.dominio),
            )
            r.id_contenido = cur.fetchone()[0]
        conn.commit()
    except Exception as error:
        conn.rollback()
        registro.warning("no se pudo guardar en contenido_web: %s: %s", type(error).__name__, str(error)[:200])
        return False
    return True


def _por_tavily(conn, consulta: str, tema: str) -> tuple:
    """(resultado o None, funciono). 'funciono' es False si no hay clave, falló la API o no hay créditos."""
    if not config.TAVILY_API_KEY:
        return None, False
    try:
        # include_domains con include_domains_mode="restrict": solo busca en los dominios de confianza.
        respuesta = _cliente_tavily().search(
            query=_consulta_web(consulta, tema), search_depth="basic", max_results=3, country="bolivia",
            include_answer=False, include_domains=list(config.DOMINIOS_CONFIABLES),
            include_domains_mode="restrict", timeout=config.WIKIPEDIA_TIMEOUT_S * 2,
        )
    except Exception:
        return None, False
    consulta_norm = normalizar(consulta)
    for item in (respuesta or {}).get("results", []):
        texto, titulo, url = (item.get("content") or "").strip(), (item.get("title") or "").strip(), item.get("url") or ""
        if not (texto and titulo and url):
            continue
        try:
            puntaje = float(item.get("score") or 0)
        except (TypeError, ValueError):
            continue                     # un puntaje ilegible se descarta, no rompe la búsqueda
        if puntaje < config.TAVILY_SCORE_MIN or not _relevante(titulo, texto, consulta_norm):
            continue
        r = ResultadoWeb(titulo=titulo, texto=texto, url=url, dominio=urlparse(url).netloc, tema=tema,
                         fuente="tavily", creditos_tavily=1)
        if _guardar(conn, "tavily", r):
            return r, True
    return None, True


def _pedir_json(url: str, params: Optional[dict] = None) -> Optional[dict]:
    """Una llamada a Wikipedia. Se separa en una función para poder simularla en las pruebas."""
    if not config.USER_AGENT:        # sin contacto configurado, Wikimedia rechaza la petición (403)
        return None
    try:
        r = httpx.get(url, params=params, headers={"User-Agent": config.USER_AGENT},
                      timeout=config.WIKIPEDIA_TIMEOUT_S, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _por_wikipedia(conn, consulta: str, tema: str) -> Optional[ResultadoWeb]:
    consulta_norm = normalizar(consulta)
    encontrados = _pedir_json(BUSCAR_WIKI, {"q": _consulta_web(consulta, tema), "limit": 3})
    for pagina in (encontrados or {}).get("pages", []):
        titulo = pagina.get("title")
        if not titulo:
            continue
        resumen = _pedir_json(RESUMEN_WIKI + quote(titulo.replace(" ", "_"), safe=""))
        texto = (resumen or {}).get("extract")
        if not texto or not _relevante(titulo, texto, consulta_norm):
            continue
        url = ((resumen.get("content_urls") or {}).get("desktop") or {}).get("page") or (
            "https://es.wikipedia.org/wiki/" + quote(titulo.replace(" ", "_"))
        )
        r = ResultadoWeb(titulo=titulo, texto=texto, url=url, dominio="es.wikipedia.org", tema=tema, fuente="wikipedia")
        if _guardar(conn, "wikipedia", r):
            return r
    return None


class IntentoWeb(BaseModel):
    """Qué pasó en el nivel 3: el resultado (si lo hay) y cuántos créditos de Tavily se gastaron."""

    resultado: Optional[ResultadoWeb] = None
    creditos_tavily: int = 0


def buscar_web(conn, consulta: str, tema: str) -> IntentoWeb:
    """Nivel 3: Tavily y, si no se puede usar (sin clave, error o sin créditos), Wikipedia directa."""
    if tema not in TEMAS:
        return IntentoWeb()
    resultado, tavily_funciono = _por_tavily(conn, consulta, tema)
    if resultado:
        return IntentoWeb(resultado=resultado, creditos_tavily=1)
    creditos = 1 if tavily_funciono else 0         # si Tavily respondió, el crédito ya se gastó
    # Sin clave, con error o sin resultado útil: Wikipedia directa (solo si es un dominio de confianza).
    if not tavily_funciono or "es.wikipedia.org" in config.DOMINIOS_CONFIABLES:
        return IntentoWeb(resultado=_por_wikipedia(conn, consulta, tema), creditos_tavily=creditos)
    return IntentoWeb(creditos_tavily=creditos)
