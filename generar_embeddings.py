"""
Genera embeddings para los sitios turísticos que aún no los tienen
y los guarda directamente en la base de datos (columna 'embedding').

Requisitos:
    pip install psycopg2-binary pgvector sentence-transformers

Uso:
    python generar_embeddings.py
"""

import os
import sys
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

# --- Configuración de conexión (ajusta si cambiaste algo) ---
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": 5432,
    "dbname": "turismo_db",
    "user": "postgres",
    "password": "tesis2026",
}

# MODEL_NAME y construir_texto() viven en texto_embedding.py, compartidos con el panel.
from texto_embedding import COLUMNAS_TEXTO, MODEL_NAME, construir_texto


def main():
    print(f"Cargando modelo de embeddings ({MODEL_NAME})...")
    modelo = SentenceTransformer(MODEL_NAME)

    conn = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)
    cur = conn.cursor()

    # Con --todos se recalculan TODOS los embeddings (necesario si cambió construir_texto()).
    solo_faltantes = "--todos" not in sys.argv
    columnas_sql = ", ".join(f'"{c}"' for c in COLUMNAS_TEXTO)
    cur.execute(f"""
        SELECT id, {columnas_sql}
        FROM sitios_turisticos
        {"WHERE embedding IS NULL" if solo_faltantes else ""}
    """)
    columnas = [desc[0] for desc in cur.description]
    filas = cur.fetchall()

    print(f"Sitios pendientes de vectorizar: {len(filas)}")

    for fila in filas:
        sitio = dict(zip(columnas, fila))
        texto = construir_texto(sitio)
        vector = modelo.encode(texto).tolist()

        cur.execute(
            "UPDATE sitios_turisticos SET embedding = %s WHERE id = %s",
            (vector, sitio["id"]),
        )
        print(f"  -> vectorizado id={sitio['id']}")

    conn.commit()
    cur.close()
    conn.close()
    print("Listo. Todos los sitios pendientes fueron vectorizados.")


if __name__ == "__main__":
    main()
