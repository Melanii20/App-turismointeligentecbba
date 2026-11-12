"""
Ayuda a elegir UMBRAL y MARGEN de la búsqueda semántica (solo lectura: no modifica la base).

Necesita un archivo CSV con preguntas de prueba que TÚ escribes, con dos columnas:
    pregunta,sitio_esperado
    "¿Qué historia tiene el Cristo de la Concordia?",Cristo de la Concordia
    "¿Cómo está el clima hoy?",
- sitio_esperado: nombre EXACTO del sitio que debería responder la pregunta.
- Si la pregunta está fuera de alcance (el asistente debería decir "No tengo
  información"), deja sitio_esperado vacío.

Por defecto solo mira los sitios verificados, igual que el asistente.

Cómo se interpretan los parámetros (confirmar que coincide con tu diseño):
- UMBRAL: similitud mínima para considerar relevante un sitio.
- MARGEN: solo se devuelven los sitios cuya similitud está a menos de MARGEN de la mejor.
- TOP_K: máximo de sitios devueltos.

Uso (desde C:\\tesis, en PowerShell):
    docker run -it --rm -v C:\\tesis:/app -v tesis-modelos:/root/.cache/huggingface -e DB_HOST=host.docker.internal tesis-python python calibrar_umbral.py
    (opcional) python calibrar_umbral.py mi_archivo.csv
    (opcional, solo para practicar) python calibrar_umbral.py preguntas_prueba.example.csv --incluir-borradores
"""

import csv
import os
import sys

import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

from texto_embedding import MODEL_NAME

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": 5432,
    "dbname": "turismo_db",
    "user": "postgres",
    "password": "tesis2026",
}

TOP_K = 3
UMBRALES = [round(0.30 + 0.05 * i, 2) for i in range(0, 11)]  # 0.30 a 0.80
MARGENES = [0.05, 0.10, 0.15, 0.20]

MIN_POSITIVAS = 10
MIN_NEGATIVAS = 5
MIN_SITIOS = 10


def leer_preguntas(ruta):
    with open(ruta, newline="", encoding="utf-8-sig") as archivo:
        filas = [
            (f["pregunta"].strip(), (f.get("sitio_esperado") or "").strip())
            for f in csv.DictReader(archivo)
            if (f.get("pregunta") or "").strip()
        ]
    return filas


def similitudes(cur, modelo, pregunta, solo_verificados):
    """Todos los sitios con su similitud, de mayor a menor."""
    vector = modelo.encode(pregunta)
    filtro = "AND estado = 'verificado'" if solo_verificados else ""
    cur.execute(
        f"""
        SELECT nombre, 1 - (embedding <=> %s) AS similitud
        FROM sitios_turisticos
        WHERE embedding IS NOT NULL {filtro}
        ORDER BY embedding <=> %s
        """,
        (vector, vector),
    )
    return [(nombre, float(sim)) for nombre, sim in cur.fetchall()]


def resultados(ranking, umbral, margen):
    """Nombres que devolvería el asistente con estos parámetros."""
    if not ranking:
        return []
    mejor = ranking[0][1]
    return [n for n, s in ranking if s >= umbral and s >= mejor - margen][:TOP_K]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    solo_verificados = "--incluir-borradores" not in sys.argv
    ruta = args[0] if args else "preguntas_prueba.csv"

    if not os.path.exists(ruta):
        print(f"No encuentro '{ruta}'. Crea ese archivo (ver el formato en el encabezado de este script)")
        print("o copia preguntas_prueba.example.csv como punto de partida.")
        return

    preguntas = leer_preguntas(ruta)
    if not preguntas:
        print(f"'{ruta}' no tiene preguntas.")
        return

    print(f"Cargando modelo ({MODEL_NAME})...")
    modelo = SentenceTransformer(MODEL_NAME)
    conn = psycopg2.connect(**DB_CONFIG)
    register_vector(conn)
    cur = conn.cursor()

    cur.execute(
        "SELECT count(*) FROM sitios_turisticos WHERE embedding IS NOT NULL"
        + (" AND estado = 'verificado'" if solo_verificados else "")
    )
    n_sitios = cur.fetchone()[0]
    print(f"\nSitios considerados: {n_sitios} ({'verificados' if solo_verificados else 'TODOS, incluidos borradores'})")

    cur.execute("SELECT nombre FROM sitios_turisticos")
    nombres_validos = {f[0] for f in cur.fetchall()}

    datos = []  # (pregunta, esperado, ranking)
    print("\n--- Similitud por pregunta ---")
    for pregunta, esperado in preguntas:
        if esperado and esperado not in nombres_validos:
            print(f"AVISO: el sitio esperado '{esperado}' no existe; revisa el nombre exacto.")
        ranking = similitudes(cur, modelo, pregunta, solo_verificados)
        datos.append((pregunta, esperado, ranking))
        top = ", ".join(f"{n} {s:.3f}" for n, s in ranking[:3]) or "(sin sitios)"
        tipo = f"esperado: {esperado}" if esperado else "FUERA DE ALCANCE"
        print(f"- {pregunta}\n    [{tipo}]  mejores: {top}")

    positivas = [d for d in datos if d[1]]
    negativas = [d for d in datos if not d[1]]

    if not positivas or not negativas:
        print("\nHacen falta preguntas de las dos clases (con sitio esperado y fuera de alcance) para calibrar.")
        conn.close()
        return

    # Separación directa: ¿hay un umbral que distinga lo relevante de lo irrelevante?
    sims_positivas = [
        next((s for n, s in r if n == esp), 0.0) for _, esp, r in positivas
    ]
    sims_negativas = [r[0][1] if r else 0.0 for _, _, r in negativas]
    print("\n--- Separación ---")
    print(f"Similitud más baja del sitio correcto: {min(sims_positivas):.3f}")
    print(f"Similitud más alta en preguntas fuera de alcance: {max(sims_negativas):.3f}")
    if max(sims_negativas) < min(sims_positivas):
        medio = (max(sims_negativas) + min(sims_positivas)) / 2
        print(f"Se separan limpiamente. Un UMBRAL entre ambos valores (p. ej. {medio:.2f}) sirve para estas preguntas.")
    else:
        print("Se SOLAPAN: ningún umbral separa perfecto estas preguntas. Revisa preguntas y descripciones.")

    # Tabla de combinaciones
    filas = []
    for u in UMBRALES:
        for m in MARGENES:
            aciertos = sobrantes = 0
            for _, esp, r in positivas:
                res = resultados(r, u, m)
                if esp in res:
                    aciertos += 1
                sobrantes += len([n for n in res if n != esp])
            falsos = sum(1 for _, _, r in negativas if resultados(r, u, m))
            filas.append((u, m, aciertos / len(positivas), falsos / len(negativas), sobrantes / len(positivas)))

    filas.sort(key=lambda f: (-f[2], f[3], f[4], abs(f[0] - 0.5)))
    print("\n--- Mejores combinaciones (acierto alto, sin falsos positivos, pocos sitios de más) ---")
    print("UMBRAL  MARGEN  aciertos  falsos_positivos  sitios_de_más_por_pregunta")
    for u, m, rec, fp, ext in filas[:8]:
        print(f"{u:>6.2f}  {m:>6.2f}  {rec:>7.0%}  {fp:>15.0%}  {ext:>24.2f}")

    print(f"\nPreguntas con sitio esperado: {len(positivas)} | fuera de alcance: {len(negativas)}")
    avisos = []
    if len(positivas) < MIN_POSITIVAS:
        avisos.append(f"menos de {MIN_POSITIVAS} preguntas con sitio esperado")
    if len(negativas) < MIN_NEGATIVAS:
        avisos.append(f"menos de {MIN_NEGATIVAS} preguntas fuera de alcance")
    if n_sitios < MIN_SITIOS:
        avisos.append(f"menos de {MIN_SITIOS} sitios en la búsqueda")
    if not solo_verificados:
        avisos.append("incluye borradores: solo es un ejercicio, no uses estos valores")
    if avisos:
        print("ADVERTENCIA: resultado poco confiable (" + "; ".join(avisos) + ").")
    print("Este script solo sugiere: la decisión final y el cambio de valores los haces tú.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
