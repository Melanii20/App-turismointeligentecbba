"""Parámetros de la búsqueda y de la API.

Los valores de UMBRAL, MARGEN y TOP_K son los de CLAUDE.md. Se calibraron con solo
3 sitios y 5 preguntas: hay que recalibrarlos con calibrar_umbral.py cuando haya
más sitios verificados. Todo se puede cambiar sin tocar el código con variables de
entorno (archivo .env en la raíz del proyecto, que NO se sube a git).
"""

import os


def _entero(nombre: str, defecto: int) -> int:
    return int(os.environ.get(nombre, str(defecto)))


def _decimal(nombre: str, defecto: float) -> float:
    return float(os.environ.get(nombre, str(defecto)))


# ---------- Búsqueda ----------
# Similitud mínima (0 a 1) para considerar que un sitio responde la pregunta.
UMBRAL = _decimal("UMBRAL", 0.50)
# Solo se devuelven los sitios cuya similitud está a menos de MARGEN de la mejor.
MARGEN = _decimal("MARGEN", 0.10)
# Los fragmentos de documentos son textos largos y se parecen entre sí (cualquier «leyenda» se parece a otra):
# se exige más similitud. Recalibrar con documentos reales.
UMBRAL_DOCUMENTOS = _decimal("UMBRAL_DOCUMENTOS", 0.60)
# Máximo de sitios que se devuelven por pregunta.
TOP_K = _entero("TOP_K", 3)

# Radios de cercanía, en kilómetros.
RADIO_CERCA_KM = _decimal("RADIO_CERCA_KM", 1.5)    # sitios
RADIO_EVENTO_KM = _decimal("RADIO_EVENTO_KM", 3)    # eventos

# ---------- Protección de costos ----------
# Peticiones por minuto desde una misma dirección (la API antigua /preguntar).
LIMITE_PETICIONES_POR_MINUTO = _entero("LIMITE_PETICIONES_POR_MINUTO", 30)
# Límite de /api/consulta, con la sintaxis de slowapi.
LIMITE_CONSULTAS = os.environ.get("LIMITE_CONSULTAS", "20/minute")
LARGO_MAX_PREGUNTA = 300
MAX_TURNOS = 6

# ---------- LLM (opcional) ----------
# Si no hay clave, el sistema funciona igual con las plantillas de respaldo.
# LLM_PROVEEDOR: "ninguno" | "anthropic" | "openai" (cualquier servicio compatible con la API de OpenAI).
LLM_PROVEEDOR = os.environ.get("LLM_PROVEEDOR", "ninguno").strip().lower()
LLM_MODELO = os.environ.get("LLM_MODELO", "").strip()
# La clave de Gemini se lee de GOOGLE_API_KEY; si no existe, de LLM_API_KEY (nunca se muestra ni se registra).
LLM_API_KEY = (os.environ.get("GOOGLE_API_KEY") or os.environ.get("LLM_API_KEY") or "").strip()
# Solo para el proveedor "openai": dirección base del servicio (por ejemplo, el de otro proveedor).
LLM_URL_BASE = os.environ.get("LLM_URL_BASE", "https://api.openai.com/v1").strip().rstrip("/")
LLM_TIMEOUT_S = _decimal("LLM_TIMEOUT_S", 15)

# ---------- Wikipedia (solo temas culturales, siempre después del RAG) ----------
TEMAS_WIKIPEDIA = tuple(
    t.strip()
    for t in os.environ.get(
        "TEMAS_WIKIPEDIA", "leyenda,tradicion,fiesta,comida,danza,musica,historia,personaje"
    ).split(",")
    if t.strip()
)
WIKIPEDIA_TIMEOUT_S = _decimal("WIKIPEDIA_TIMEOUT_S", 5)
CACHE_WEB_DIAS = _entero("CACHE_WEB_DIAS", 30)
# Wikimedia exige que el User-Agent traiga un contacto (correo o página del proyecto); sin él
# responde 403. Pon el tuyo en WIKIPEDIA_CONTACTO (en el .env). Sin contacto, Wikipedia no se
# consulta y el asistente responde "No tengo información sobre eso" para esos temas.
WIKIPEDIA_CONTACTO = os.environ.get("WIKIPEDIA_CONTACTO", "").strip()
USER_AGENT = (
    f"GuiaCochala/1.0 (proyecto de grado UNIFRANZ; {WIKIPEDIA_CONTACTO})" if WIKIPEDIA_CONTACTO else ""
)

# ---------- Telegram (opcional) ----------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()

# ---------- Búsqueda web con Tavily (solo narrativo de saberes, después de base y caché) ----------
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "").strip()
TAVILY_SCORE_MIN = _decimal("TAVILY_SCORE_MIN", 0.5)
# Dominios en los que Tavily puede buscar (modo restrict). Empieza solo con Wikipedia en español;
# la estudiante agregará sitios oficiales en el .env, separados por comas.
DOMINIOS_CONFIABLES = tuple(
    d.strip() for d in os.environ.get("DOMINIOS_CONFIABLES", "es.wikipedia.org").split(",") if d.strip()
)
# Tiempo máximo de cada llamada a los agentes de Gemini (segundos).
AGENTE_TIMEOUT_S = _decimal("AGENTE_TIMEOUT_S", 15)
