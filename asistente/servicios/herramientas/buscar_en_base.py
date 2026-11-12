"""Herramienta buscar_en_base (nivel 1 de la cascada narrativa).

Consulta, ordenado por similitud con UMBRAL y MARGEN:
  - sitios VERIFICADOS (descripcion, relato, que_ver),
  - eventos (descripcion),
  - fragmentos de documentos VERIFICADOS.
Cada resultado dice su origen: sitio, evento o documento (con su página).

Regla (CLAUDE.md): los documentos NUNCA responden sobre accesibilidad, horarios, precios, direcciones
ni fechas. Esas preguntas son «operativas» y salen solo de los campos verificados de sitios y eventos
(las herramientas buscar_sitios, datos_practicos, eventos...). Esta herramienta es solo para lo narrativo.
"""

from datetime import datetime
from typing import Callable, List, Optional

from pydantic import BaseModel, Field

import config
from servicios.herramientas import buscar_sitios as h_sitios

DIAS_EVENTOS_PASADOS = 365       # un evento que terminó hace más de un año ya no se busca
MAX_CACHE_EVENTOS = 500
_cache_eventos: dict = {}        # (id, texto) -> vector; los eventos son pocos y casi no cambian


class Hallazgo(BaseModel):
    origen: str                                  # "sitio" | "evento" | "documento"
    id: int
    titulo: str
    texto: str
    similitud: Optional[float] = None
    pagina: Optional[int] = None
    documento_titulo: Optional[str] = None
    fecha_verificacion: Optional[datetime] = None
    por_nombre: bool = False


class ResultadoBase(BaseModel):
    hallazgos: List[Hallazgo] = Field(default_factory=list)
    similitud_maxima: Optional[float] = None
    sitios: list = Field(default_factory=list)   # sitios completos (para las plantillas existentes)
    por_nombre: bool = False

    def suficiente(self) -> bool:
        return bool(self.hallazgos)

    def hay_documentos(self) -> bool:
        return any(h.origen == "documento" for h in self.hallazgos)


def _texto_narrativo(sitio: dict) -> str:
    partes = [sitio.get("descripcion"), sitio.get("relato"), sitio.get("que_ver")]
    return " ".join(p.strip() for p in partes if p and p.strip())


def _coseno(a, b) -> float:
    import numpy as np

    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return float(a @ b / ((np.linalg.norm(a) * np.linalg.norm(b)) or 1.0))


def _eventos(conn, vector, vectorizar: Optional[Callable]) -> List[Hallazgo]:
    """Eventos parecidos a la pregunta. Se vectorizan al vuelo (son pocos), sin cambiar el esquema."""
    if vector is None or vectorizar is None:
        return []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, nombre, tipo, zona, descripcion FROM eventos WHERE descripcion IS NOT NULL AND descripcion <> '' "
            "AND COALESCE(fecha_fin, fecha_inicio) >= (now() AT TIME ZONE 'America/La_Paz')::date - %s",
            (DIAS_EVENTOS_PASADOS,),
        )
        filas = cur.fetchall()
    resultado = []
    for id_, nombre, tipo, zona, descripcion in filas:
        texto = f"{nombre}. {tipo or ''}. {zona or ''}. {descripcion}"
        clave = (id_, texto)
        if clave not in _cache_eventos:
            if len(_cache_eventos) >= MAX_CACHE_EVENTOS:
                _cache_eventos.clear()                      # la memoria no crece sin límite
            _cache_eventos[clave] = vectorizar(texto)
        resultado.append(Hallazgo(
            origen="evento", id=id_, titulo=nombre, texto=descripcion.strip(),
            similitud=round(_coseno(vector, _cache_eventos[clave]), 4),
        ))
    return resultado


def _documentos(conn, vector, top_k: int) -> List[Hallazgo]:
    """Fragmentos de documentos verificados, los más parecidos primero."""
    if vector is None:
        return []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT f.id, d.titulo, f.pagina, f.texto, 1 - (f.embedding <=> %s) AS similitud, d.fecha_verificacion
            FROM fragmentos_documento f JOIN documentos d ON d.id = f.documento_id
            WHERE d.estado = 'verificado' AND f.embedding IS NOT NULL
            ORDER BY f.embedding <=> %s LIMIT %s
            """,
            (vector, vector, top_k),
        )
        filas = cur.fetchall()
    return [
        Hallazgo(
            origen="documento", id=f[0], titulo=f[1], documento_titulo=f[1], pagina=f[2], texto=f[3],
            similitud=round(float(f[4]), 4), fecha_verificacion=f[5],
        )
        for f in filas
    ]


def buscar_en_base(
    conn, pregunta: str, vector, ids_nombrados: Optional[list] = None, vectorizar: Optional[Callable] = None,
    umbral: Optional[float] = None, margen: Optional[float] = None, top_k: Optional[int] = None,
    incluir_documentos: bool = True,
) -> ResultadoBase:
    """Nivel 1: sitios verificados + eventos + documentos verificados, ordenados por similitud."""
    umbral = config.UMBRAL if umbral is None else umbral
    margen = config.MARGEN if margen is None else margen
    top_k = config.TOP_K if top_k is None else top_k

    rs = h_sitios.buscar_sitios(conn, pregunta, vector, ids_nombrados=ids_nombrados, umbral=umbral, margen=margen, top_k=top_k)
    candidatos: List[Hallazgo] = []
    for s in rs.sitios:
        candidatos.append(Hallazgo(
            origen="sitio", id=s["id"], titulo=s["nombre"], texto=_texto_narrativo(s),
            similitud=s.get("similitud"), fecha_verificacion=s.get("fecha_verificacion"), por_nombre=rs.por_nombre,
        ))

    # Un sitio nombrado ya responde la pregunta: no se mezclan otros orígenes.
    if not rs.por_nombre:
        extras = [h for h in _eventos(conn, vector, vectorizar) if (h.similitud or 0) >= umbral]
        if incluir_documentos:
            extras += [h for h in _documentos(conn, vector, top_k * 2) if (h.similitud or 0) >= max(umbral, config.UMBRAL_DOCUMENTOS)]
        candidatos += extras
        if candidatos:
            mejor = max(h.similitud or 0 for h in candidatos)
            candidatos = [h for h in candidatos if (h.similitud or 0) >= mejor - margen]
        candidatos.sort(key=lambda h: h.similitud or 0, reverse=True)
        candidatos = candidatos[:top_k]

    ids_sitios = {h.id for h in candidatos if h.origen == "sitio"}
    maximo = max((h.similitud for h in candidatos if h.similitud is not None), default=rs.similitud_maxima)
    return ResultadoBase(
        hallazgos=candidatos,
        similitud_maxima=maximo if maximo is not None else rs.similitud_maxima,
        sitios=[s for s in rs.sitios if s["id"] in ids_sitios],
        por_nombre=rs.por_nombre,
    )


def mejor_alternativa(conn, vector) -> Optional[str]:
    """Nombre del sitio verificado más parecido a la pregunta (aunque no llegue al umbral).
    Sirve para el nivel 4: «No tengo información sobre eso, pero puedo contarte de…»."""
    with conn.cursor() as cur:
        if vector is not None:
            cur.execute(
                "SELECT nombre FROM sitios_turisticos WHERE estado = 'verificado' AND embedding IS NOT NULL "
                "ORDER BY embedding <=> %s LIMIT 1", (vector,),
            )
        else:
            cur.execute("SELECT nombre FROM sitios_turisticos WHERE estado = 'verificado' ORDER BY id LIMIT 1")
        f = cur.fetchone()
    return f[0] if f else None
