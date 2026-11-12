"""Búsqueda semántica sobre los sitios VERIFICADOS.

Regla central del proyecto: el asistente solo ve sitios con estado = 'verificado'.
Los borradores nunca salen de aquí, ni en la búsqueda ni en las consultas por id.
"""

import nombres

# Columnas que se leen de cada sitio (no se lee verificado_por, ni el embedding, ni fechas internas).
COLUMNAS = """
    id, nombre, tipo, descripcion, direccion, latitud, longitud, fuente,
    acceso_descripcion_sensorial, acceso_tipo_piso, acceso_piso_tactil,
    acceso_señalizacion_braille, acceso_permite_perros_guia, acceso_nivel_ruido,
    acceso_punto_referencia_entrada, acceso_recomendacion
"""


def _a_sitio(fila, incluir_llegada: bool, similitud: float = None, coincidencia: str = None) -> dict:
    """Convierte una fila de la base en el diccionario público del sitio.

    Los datos de accesibilidad se entregan tal cual están en la base. Un valor null
    significa 'sin verificar' (nunca se rellena ni se supone).
    """
    (id_, nombre, tipo, descripcion, direccion, latitud, longitud, fuente,
     sensorial, piso, tactil, braille, perros, ruido, referencia, recomendacion) = fila

    sitio = {
        "id": id_,
        "nombre": nombre,
        "tipo": tipo,
        "descripcion": descripcion,
        "direccion": direccion,
        "latitud": float(latitud) if latitud is not None else None,
        "longitud": float(longitud) if longitud is not None else None,
        "fuente": fuente,
        "accesibilidad": {
            "descripcion_sensorial": sensorial,
            "tipo_piso": piso,
            "piso_tactil": tactil,
            "senalizacion_braille": braille,
            "permite_perros_guia": perros,
            "nivel_ruido": ruido,
        },
    }
    if similitud is not None:
        sitio["similitud"] = round(similitud, 4)
    if coincidencia is not None:
        # "nombre": la pregunta menciona el nombre del sitio. "significado": lo halló la búsqueda semántica.
        sitio["coincidencia"] = coincidencia
    if incluir_llegada:
        sitio["como_llegar"] = {
            "punto_referencia_entrada": referencia,
            "recomendacion": recomendacion,
        }
    return sitio


def buscar(conn, vector, umbral: float, margen: float, top_k: int, incluir_llegada: bool) -> list:
    """Sitios verificados más parecidos al vector de la pregunta.

    Se piden los top_k más cercanos y luego se quedan solo los que:
      - tienen similitud >= umbral, y
      - están a menos de 'margen' de la mejor similitud.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {COLUMNAS}, 1 - (embedding <=> %s) AS similitud
            FROM sitios_turisticos
            WHERE estado = 'verificado' AND embedding IS NOT NULL
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (vector, vector, top_k),
        )
        filas = cur.fetchall()

    if not filas:
        return []

    mejor = float(filas[0][-1])
    resultado = []
    for fila in filas:
        similitud = float(fila[-1])
        if similitud >= umbral and similitud >= mejor - margen:
            resultado.append(_a_sitio(fila[:-1], incluir_llegada, similitud, "significado"))
    return resultado


def buscar_por_nombre(conn, pregunta: str, vector, top_k: int, incluir_llegada: bool) -> list:
    """Sitios VERIFICADOS cuyo nombre se menciona en la pregunta (ver nombres.py).

    Como la persona nombró el lugar, se devuelve aunque la similitud semántica sea baja.
    La similitud se informa igualmente, solo como dato.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id, nombre FROM sitios_turisticos WHERE estado = 'verificado'")
        verificados = cur.fetchall()

    ids = nombres.sitios_mencionados(pregunta, verificados)
    if not ids:
        return []

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {COLUMNAS}, 1 - (embedding <=> %s) AS similitud
            FROM sitios_turisticos
            WHERE estado = 'verificado' AND id = ANY(%s)
            ORDER BY similitud DESC NULLS LAST
            LIMIT %s
            """,
            (vector, ids, top_k),
        )
        filas = cur.fetchall()

    return [
        _a_sitio(f[:-1], incluir_llegada, float(f[-1]) if f[-1] is not None else None, "nombre")
        for f in filas
    ]


def listar(conn) -> list:
    """Todos los sitios verificados, en forma resumida (para listas y mapas)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, nombre, tipo, latitud, longitud
            FROM sitios_turisticos
            WHERE estado = 'verificado'
            ORDER BY nombre
            """
        )
        return [
            {
                "id": f[0],
                "nombre": f[1],
                "tipo": f[2],
                "latitud": float(f[3]) if f[3] is not None else None,
                "longitud": float(f[4]) if f[4] is not None else None,
            }
            for f in cur.fetchall()
        ]


def obtener(conn, sitio_id: int):
    """Un sitio verificado completo, incluida la información de cómo llegar; o None.

    Un sitio en borrador devuelve None, igual que uno que no existe.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {COLUMNAS} FROM sitios_turisticos WHERE id = %s AND estado = 'verificado'",
            (sitio_id,),
        )
        fila = cur.fetchone()
    return _a_sitio(fila, incluir_llegada=True) if fila else None
