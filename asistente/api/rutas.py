"""Rutas de la API para la app móvil y el bot (contrato de CLAUDE.md).

  POST /api/consulta       pregunta -> respuesta + acciones + contexto
  GET  /api/eventos/hoy    eventos vigentes hoy (el más cercano primero si hay ubicación)
  GET  /api/estado         comprobación de que el servidor responde

Privacidad: no se guardan preguntas, conversaciones ni ubicaciones. Solo se guarda una fila de
métricas sin datos personales (tabla metricas_consulta).
"""

import time
from typing import Optional

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

import config
import modelo
from db import conectar
from servicios import grafo
from servicios.herramientas import eventos as h_eventos

limitador = Limiter(key_func=get_remote_address)
router = APIRouter()


class Contexto(BaseModel):
    turnos: list = Field(default_factory=list)
    ultimo_sitio_id: Optional[int] = None
    accion_pendiente: Optional[dict] = None

    @field_validator("turnos")
    @classmethod
    def _maximo_de_turnos(cls, v):
        return v[-config.MAX_TURNOS:]            # historial de máximo 6 turnos


class ConsultaIn(BaseModel):
    pregunta: str = Field(min_length=1, max_length=config.LARGO_MAX_PREGUNTA)
    canal: str = Field(default="app", pattern="^(app|telegram)$")
    contexto: Contexto = Field(default_factory=Contexto)
    latitud: Optional[float] = Field(default=None, ge=-90, le=90)
    longitud: Optional[float] = Field(default=None, ge=-180, le=180)


def registrar_metrica(conn, canal: str, r: dict, tiempo_ms: int) -> None:
    """Una fila sin datos personales: sin texto de la pregunta, sin ubicación, sin identificador."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO metricas_consulta (canal, intencion, uso_llm, fuente, sitio_id, similitud_maxima, tiempo_ms, "
                "nivel_fuente, eje_dato, creditos_tavily, motivo_sin_llm) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (canal, r["intencion"], r["uso_llm"], r["fuente"], r.get("sitio_id"), r.get("similitud_maxima"), tiempo_ms,
                 r.get("nivel_fuente"), r.get("eje_dato"), r.get("creditos_tavily", 0), r.get("motivo_sin_llm")),
            )
        conn.commit()
    except Exception:
        conn.rollback()                           # las métricas nunca deben romper una respuesta


def responder(conn, datos: ConsultaIn, vectorizar=None, web=None) -> dict:
    """Ejecuta el grafo y arma el contrato JSON de salida."""
    inicio = time.monotonic()
    extra = {"web": web} if web else {}
    r = grafo.procesar(
        conn, datos.pregunta, datos.contexto.model_dump(), datos.latitud, datos.longitud,
        vectorizar=vectorizar or modelo.vectorizar_pregunta, **extra,
    )
    registrar_metrica(conn, datos.canal, r, int(round((time.monotonic() - inicio) * 1000)))
    return {
        "respuesta": r["respuesta"],
        "intencion": r["intencion"],
        "uso_llm": r["uso_llm"],
        "fuente": r["fuente"],
        "nivel_fuente": r["nivel_fuente"],
        "fuentes": r["fuentes"],
        "sitio_id": r["sitio_id"],
        "acciones": r["acciones"],
        "escuchar_despues": r["escuchar_despues"],
        "contexto": {
            "turnos": r["turnos"],
            "ultimo_sitio_id": r["ultimo_sitio_id"],
            "accion_pendiente": r["accion_pendiente"],
        },
    }


@router.post("/api/consulta")
@limitador.limit(config.LIMITE_CONSULTAS)
def consulta(request: Request, datos: ConsultaIn):
    conn = conectar()
    try:
        return responder(conn, datos)
    finally:
        conn.close()


def _evento_json(e: dict) -> dict:
    return {
        "id": e["id"], "nombre": e["nombre"], "tipo": e.get("tipo"), "zona": e.get("zona"),
        "descripcion": e.get("descripcion"),
        "fecha_inicio": e["fecha_inicio"].isoformat(),
        "fecha_fin": e["fecha_fin"].isoformat() if e.get("fecha_fin") else None,
        "hora_inicio": e["hora_inicio"].strftime("%H:%M") if e.get("hora_inicio") else None,
        "hora_fin": e["hora_fin"].strftime("%H:%M") if e.get("hora_fin") else None,
        "latitud": e.get("latitud"), "longitud": e.get("longitud"),
        "distancia_m": e.get("distancia_m"),
        "texto": h_eventos.frase_evento(e),
    }


@router.get("/api/eventos/hoy")
@limitador.limit(config.LIMITE_CONSULTAS)
def eventos_hoy(
    request: Request,
    latitud: Optional[float] = Query(default=None, ge=-90, le=90),
    longitud: Optional[float] = Query(default=None, ge=-180, le=180),
):
    """Eventos vigentes hoy. Si hay ubicación y el evento tiene coordenadas dentro de RADIO_EVENTO_KM,
    el más cercano va primero, con su distancia. La ubicación no se guarda."""
    conn = conectar()
    try:
        eventos = h_eventos.eventos_de_hoy(conn, latitud, longitud)
    finally:
        conn.close()
    return {"eventos": [_evento_json(e) for e in eventos]}


@router.get("/api/estado")
def estado():
    """Comprobación del servidor. Indica con true/false qué está configurado; nunca muestra claves."""
    try:
        conectar().close()
        base = True
    except Exception:
        base = False
    return {
        "estado": "ok",
        "modelo_cargado": modelo.esta_cargado(),
        "base_de_datos": base,
        "gemini": bool(config.LLM_API_KEY) and config.LLM_PROVEEDOR in ("google", "gemini") and bool(config.LLM_MODELO),
        "tavily": bool(config.TAVILY_API_KEY),
        "wikipedia": bool(config.WIKIPEDIA_CONTACTO),
    }
