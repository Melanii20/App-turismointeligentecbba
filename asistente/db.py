"""Conexión a la base de datos del asistente.

Los datos de conexión se leen de variables de entorno. Los valores por defecto son los
de desarrollo local (CLAUDE.md). Cuando la base esté en la nube, solo se cambian las
variables (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSLMODE), no el código.
"""

import os

import psycopg2
from pgvector.psycopg2 import register_vector


def _configuracion() -> dict:
    config = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", "5432")),
        "dbname": os.environ.get("DB_NAME", "turismo_db"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", "tesis2026"),
    }
    if os.environ.get("DB_SSLMODE"):
        config["sslmode"] = os.environ["DB_SSLMODE"]
    return config


def conectar():
    """Abre una conexión nueva. Quien la use debe cerrarla (conn.close())."""
    conn = psycopg2.connect(**_configuracion())
    register_vector(conn)
    return conn
