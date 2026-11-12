"""
Prueba la búsqueda semántica sobre los sitios turísticos (sin LLM todavía).
Escribes una pregunta y muestra los sitios más parecidos con su puntaje.

Uso:
    python probar_busqueda.py
    (escribe 'salir' para terminar)
"""

import os
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": 5432,
    "dbname": "turismo_db",
    "user": "postgres",
    "password": "tesis2026",
}

# Debe ser EXACTAMENTE el mismo modelo usado en generar_embeddings.py
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"

# Puntaje mínimo para considerar que un resultado es relevante.
# Es un valor inicial: lo vamos a calibrar con las pruebas.
UMBRAL = 0.40

TOP_K = 3


def buscar(cur, modelo, pregunta):
    vector = modelo.encode(pregunta)  # arreglo numpy, pgvector lo entiende directo
    cur.execute(
        """
        SELECT id, nombre, 1 - (embedding <=> %s) AS similitud
        FROM sitios_turisticos
        WHERE embedding IS NOT NULL
          AND estado = 'verificado'  -- el asistente solo ve sitios verificados
        ORDER BY embedding <=> %s
        LIMIT %s
        """,
        (vector, vector, TOP_K),
    )
    return cur.fetchall()


def main():
    print(f"Cargando modelo ({MODEL_NAME})...")
    modelo = SentenceTransformer(MODEL_NAME)

    conn = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)
    cur = conn.cursor()

    print("\nListo. Escribe una pregunta (o 'salir').\n")
    while True:
        pregunta = input("Pregunta: ").strip()
        if not pregunta:
            continue
        if pregunta.lower() == "salir":
            break

        resultados = buscar(cur, modelo, pregunta)
        for id_, nombre, similitud in resultados:
            marca = "RELEVANTE" if similitud >= UMBRAL else "bajo umbral"
            print(f"  {similitud:.3f}  [{marca}]  {nombre} (id={id_})")

        if not resultados or resultados[0][2] < UMBRAL:
            print("  -> El asistente respondería: 'No tengo información sobre eso.'")
        print()

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
