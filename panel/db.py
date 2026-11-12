"""Conexión a la base de datos del panel.

Usa la misma configuración que generar_embeddings.py. El host se lee de la
variable de entorno DB_HOST (por defecto 'localhost'; desde Docker se usa
'host.docker.internal').
"""

import os
import psycopg2
from pgvector.psycopg2 import register_vector

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": 5432,
    "dbname": "turismo_db",
    "user": "postgres",
    "password": "tesis2026",
}


def conectar():
    """Abre una conexión nueva. Quien la use debe cerrarla (conn.close()).
    Registra el tipo 'vector' para poder guardar embeddings directamente."""
    conn = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)
    return conn
