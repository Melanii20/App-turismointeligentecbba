"""Lectura de sitios y eventos desde la base (solo lectura).

Regla central: el asistente solo ve sitios con estado = 'verificado'.
"""

from typing import Optional

from psycopg2.extras import RealDictCursor

# Hoy según la hora de Bolivia (el servidor puede estar en otra zona horaria).
HOY_BOLIVIA = "(now() AT TIME ZONE 'America/La_Paz')::date"

COLUMNAS_SITIO = (
    "id, nombre, tipo, descripcion, relato, que_ver, direccion, latitud, longitud, fuente, "
    "horario, costo_ingreso, duracion_visita, servicios, fecha_verificacion, "
    "acceso_descripcion_sensorial, acceso_punto_referencia_entrada, acceso_tipo_piso, "
    "acceso_piso_tactil, \"acceso_señalizacion_braille\" AS acceso_senalizacion_braille, "
    "acceso_permite_perros_guia, acceso_nivel_ruido, acceso_recomendacion"
)


def _limpiar_sitio(fila: dict) -> dict:
    for clave in ("latitud", "longitud"):
        if fila.get(clave) is not None:
            fila[clave] = float(fila[clave])
    return fila


def sitios_verificados(conn) -> list:
    """(id, nombre) de todos los sitios verificados; sirve para reconocer nombres en la pregunta."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, nombre FROM sitios_turisticos WHERE estado = 'verificado' ORDER BY id")
        return cur.fetchall()


def obtener_sitio(conn, sitio_id: int) -> Optional[dict]:
    """Un sitio verificado completo, o None (un borrador es como si no existiera)."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {COLUMNAS_SITIO} FROM sitios_turisticos WHERE id = %s AND estado = 'verificado'",
            (sitio_id,),
        )
        fila = cur.fetchone()
    return _limpiar_sitio(dict(fila)) if fila else None


def sitios_por_ids(conn, ids: list) -> list:
    """Sitios verificados completos, en el mismo orden que 'ids'."""
    if not ids:
        return []
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {COLUMNAS_SITIO} FROM sitios_turisticos WHERE estado = 'verificado' AND id = ANY(%s)",
            (list(ids),),
        )
        por_id = {f["id"]: _limpiar_sitio(dict(f)) for f in cur.fetchall()}
    return [por_id[i] for i in ids if i in por_id]


def hoy(conn):
    """Fecha de hoy en Bolivia."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT {HOY_BOLIVIA}")
        return cur.fetchone()[0]


COLUMNAS_EVENTO = "id, nombre, descripcion, tipo, fecha_inicio, fecha_fin, zona, latitud, longitud, hora_inicio, hora_fin"


def eventos_entre(conn, desde, hasta) -> list:
    """Eventos que se solapan con el rango [desde, hasta], del más próximo al más lejano."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {COLUMNAS_EVENTO} FROM eventos
            WHERE fecha_inicio <= %s AND COALESCE(fecha_fin, fecha_inicio) >= %s
            ORDER BY fecha_inicio, nombre
            """,
            (hasta, desde),
        )
        filas = [dict(f) for f in cur.fetchall()]
    for f in filas:
        for clave in ("latitud", "longitud"):
            if f.get(clave) is not None:
                f[clave] = float(f[clave])
    return filas
