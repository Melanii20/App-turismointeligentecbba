"""Herramienta buscar_sitios: RAG semántico + filtros SQL exactos, siempre con estado = 'verificado'."""

from typing import Optional

from pydantic import BaseModel, Field

import config
from nombres import normalizar, sitios_mencionados
from servicios.herramientas import datos


class Filtros(BaseModel):
    """Filtros exactos que se detectan en la pregunta (además de la búsqueda por significado)."""

    ruido_bajo: bool = False
    piso_tactil: bool = False
    perros_guia: bool = False
    tipo: Optional[str] = None

    def hay_accesibilidad(self) -> bool:
        return self.ruido_bajo or self.piso_tactil or self.perros_guia

    def hay_alguno(self) -> bool:
        return self.hay_accesibilidad() or self.tipo is not None


class ResultadoBusqueda(BaseModel):
    sitios: list = Field(default_factory=list)       # sitios verificados completos (con 'similitud')
    similitud_maxima: Optional[float] = None
    por_nombre: bool = False                          # True si la pregunta nombraba el sitio
    filtros: Filtros = Field(default_factory=Filtros)


TIPOS = ("museo", "iglesia", "plaza", "mercado", "parque", "teatro", "mirador", "laguna", "catedral", "casona", "paseo")


def detectar_filtros(pregunta_normalizada: str) -> Filtros:
    """Filtros que pide la pregunta. 'tranquilo / sin ruido' -> ruido bajo, 'piso táctil', 'perro guía', tipo."""
    t = f" {pregunta_normalizada} "
    palabras = pregunta_normalizada.split()
    tipo = next((x for x in TIPOS if x in palabras or (x + "s") in palabras), None)
    return Filtros(
        ruido_bajo=any(f in t for f in (" tranquil", " sin ruido", " silencios", " poco ruido", " poca bulla", " sin bulla")),
        piso_tactil=("piso tactil" in t or " podotactil" in t or " tactil" in t),
        perros_guia=(" perro" in t or " lazarill" in t),
        tipo=tipo,
    )


def buscar_sitios(
    conn, pregunta: str, vector, filtros: Optional[Filtros] = None, ids_nombrados: Optional[list] = None,
    umbral: float = None, margen: float = None, top_k: int = None,
) -> ResultadoBusqueda:
    """Sitios verificados que responden la pregunta.

    1) Si la pregunta nombra uno o más sitios verificados, se devuelven esos.
    2) Si no, búsqueda por significado (coseno) con filtros SQL exactos; con umbral y margen.
       Si hay un filtro de accesibilidad (piso táctil, ruido bajo, perro guía), el filtro es el criterio
       principal: los sitios con ese dato en NULL ("sin información") no entran nunca.
    """
    umbral = config.UMBRAL if umbral is None else umbral
    margen = config.MARGEN if margen is None else margen
    top_k = config.TOP_K if top_k is None else top_k
    filtros = filtros or detectar_filtros(normalizar(pregunta))

    if ids_nombrados is None:
        ids_nombrados = sitios_mencionados(pregunta, datos.sitios_verificados(conn))
    if ids_nombrados:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, 1 - (embedding <=> %s) FROM sitios_turisticos "
                "WHERE estado = 'verificado' AND id = ANY(%s)",
                (vector, ids_nombrados),
            )
            sim = {f[0]: (float(f[1]) if f[1] is not None else None) for f in cur.fetchall()}
        sitios = datos.sitios_por_ids(conn, [i for i in ids_nombrados if i in sim][:top_k])
        for s in sitios:
            s["similitud"] = sim.get(s["id"])
            s["coincidencia"] = "nombre"
        return ResultadoBusqueda(
            sitios=sitios, por_nombre=True, filtros=filtros,
            similitud_maxima=max((s["similitud"] for s in sitios if s["similitud"] is not None), default=None),
        )

    condiciones = ["estado = 'verificado'", "embedding IS NOT NULL"]
    parametros = []
    if filtros.ruido_bajo:
        condiciones.append("acceso_nivel_ruido = 'bajo'")
    if filtros.piso_tactil:
        condiciones.append("acceso_piso_tactil = true")
    if filtros.perros_guia:
        condiciones.append("acceso_permite_perros_guia = true")
    if filtros.tipo:
        condiciones.append("(tipo ILIKE %s OR nombre ILIKE %s)")
        parametros += [f"%{filtros.tipo}%", f"%{filtros.tipo}%"]
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT id, 1 - (embedding <=> %s) AS similitud FROM sitios_turisticos
            WHERE {' AND '.join(condiciones)}
            ORDER BY embedding <=> %s LIMIT %s
            """,
            [vector, *parametros, vector, top_k],
        )
        filas = [(f[0], float(f[1])) for f in cur.fetchall()]

    if not filas:
        return ResultadoBusqueda(filtros=filtros)
    mejor = filas[0][1]
    if filtros.hay_accesibilidad():
        elegidas = filas                                   # el filtro exacto manda
    else:
        elegidas = [(i, s) for i, s in filas if s >= umbral and s >= mejor - margen]
    sitios = datos.sitios_por_ids(conn, [i for i, _ in elegidas])
    sim = dict(elegidas)
    for s in sitios:
        s["similitud"] = round(sim[s["id"]], 4)
        s["coincidencia"] = "significado"
    return ResultadoBusqueda(sitios=sitios, similitud_maxima=round(mejor, 4), filtros=filtros)
