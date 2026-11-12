"""API pública y de solo lectura del asistente turístico.

Rutas:
  POST /preguntar    una pregunta -> sitios verificados relacionados (+ texto de respuesta)
  GET  /sitios       lista resumida de sitios verificados
  GET  /sitios/{id}  un sitio verificado completo, con la información de cómo llegar
  GET  /salud        comprobación de que la API, la base y el modelo responden

Solo lectura: no hay login ni escritura, y los sitios en borrador nunca aparecen.
Esta API es distinta del panel de administración (carpeta panel/).
"""

import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import busqueda
import config
import generador
import modelo
from db import conectar
from intencion import pregunta_sobre_llegada, temas_de_la_pregunta


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Al arrancar, carga el modelo una sola vez para que la primera pregunta no tarde."""
    modelo.cargar()
    yield


app = FastAPI(title="API del asistente turístico", lifespan=ciclo_de_vida)

# API de la app móvil (contrato de CLAUDE.md): /api/consulta, /api/eventos/hoy, /api/estado.
# Límite de consultas por IP con slowapi.
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

from api.rutas import limitador, router as router_api  # noqa: E402

app.state.limiter = limitador
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(router_api)

# Permite que la versión web de la app (por ejemplo, probando en Chrome) lea la API.
# Es una API pública de solo lectura y sin cookies, por eso se aceptan todos los orígenes.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


# ---------- Límite de peticiones por dirección (protección básica) ----------
_visitas = defaultdict(deque)


def limitar_peticiones(request: Request):
    """Máximo config.LIMITE_PETICIONES_POR_MINUTO por minuto desde una misma dirección.
    Es una protección sencilla en memoria; detrás de un túnel o proxy, la dirección
    puede ser la del proxy."""
    ip = request.client.host if request.client else "desconocida"
    ahora = time.monotonic()
    cola = _visitas[ip]
    while cola and ahora - cola[0] > 60:
        cola.popleft()
    if len(cola) >= config.LIMITE_PETICIONES_POR_MINUTO:
        raise HTTPException(status_code=429, detail="Demasiadas preguntas seguidas. Espera un momento.")
    cola.append(ahora)


class Pregunta(BaseModel):
    pregunta: str = Field(min_length=2, max_length=config.LARGO_MAX_PREGUNTA)


@app.post("/preguntar", dependencies=[Depends(limitar_peticiones)])
def preguntar(datos: Pregunta):
    """Busca entre los sitios VERIFICADOS los que mejor responden la pregunta."""
    pregunta = datos.pregunta.strip()
    if len(pregunta) < 2:
        raise HTTPException(status_code=422, detail="La pregunta está vacía.")

    # Solo si la pregunta es sobre cómo llegar o acceder se entrega esa información.
    sobre_llegada = pregunta_sobre_llegada(pregunta)
    temas = temas_de_la_pregunta(pregunta)
    vector = modelo.vectorizar_pregunta(pregunta)

    conn = conectar()
    try:
        # 1) Si la pregunta nombra un sitio verificado, se responde sobre ese sitio.
        sitios = busqueda.buscar_por_nombre(
            conn, pregunta, vector, config.TOP_K, incluir_llegada=sobre_llegada
        )
        # 2) Si no, búsqueda por significado, con umbral y margen.
        if not sitios:
            sitios = busqueda.buscar(
                conn, vector, config.UMBRAL, config.MARGEN, config.TOP_K, incluir_llegada=sobre_llegada
            )
    finally:
        conn.close()

    return {
        "respuesta": generador.generar(pregunta, sitios, temas, sobre_llegada),
        "hay_informacion": bool(sitios),
        "sobre_llegada": sobre_llegada,
        "temas": temas,
        "generador": generador.GENERADOR,
        "sitios": sitios,
    }


@app.get("/sitios", dependencies=[Depends(limitar_peticiones)])
def lista_de_sitios():
    conn = conectar()
    try:
        return {"sitios": busqueda.listar(conn)}
    finally:
        conn.close()


@app.get("/sitios/{sitio_id}", dependencies=[Depends(limitar_peticiones)])
def un_sitio(sitio_id: int):
    conn = conectar()
    try:
        sitio = busqueda.obtener(conn, sitio_id)
    finally:
        conn.close()
    if sitio is None:
        raise HTTPException(status_code=404, detail="Ese sitio no existe o todavía no está verificado.")
    return sitio


@app.get("/salud")
def salud():
    """Comprueba la base de datos y el modelo."""
    try:
        conn = conectar()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM sitios_turisticos WHERE estado = 'verificado'")
                verificados = cur.fetchone()[0]
        finally:
            conn.close()
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"No se pudo consultar la base: {error}")
    return {
        "base_de_datos": "ok",
        "sitios_verificados": verificados,
        "modelo_cargado": modelo.esta_cargado(),
        "umbral": config.UMBRAL,
        "margen": config.MARGEN,
        "top_k": config.TOP_K,
    }
