"""Evaluación del RAG con Ragas (fidelidad y relevancia). PREPARADO, NO EJECUTADO todavía.

Qué hace: para cada pregunta de un CSV, ejecuta el grafo del asistente, toma la respuesta y el
contexto (los textos verificados de los sitios) y calcula con Ragas:
  - faithfulness: ¿la respuesta se apoya solo en el contexto? (no inventa)
  - answer_relevancy: ¿la respuesta contesta la pregunta?

Ragas usa un LLM como juez, así que necesita una clave (LLM_API_KEY en el .env). No se ejecuta
solo; cuando tengas más sitios verificados y la clave:

  1) Instala Ragas dentro del contenedor (una sola vez, o agrégalo al Dockerfile):
       docker run -it --rm -v C:\tesis:/app -v tesis-modelos:/root/.cache/huggingface --env-file C:\tesis\.env ^
         -e DB_HOST=host.docker.internal -e PYTHONPATH=/app/asistente:/app -w /app tesis-asistente ^
         sh -c "pip install ragas datasets langchain-openai && python evaluar_ragas.py preguntas_prueba.csv"
  2) El CSV tiene la columna `pregunta` (como preguntas_prueba.example.csv).

Compara la plantilla contra el LLM cambiando LLM_PROVEEDOR en el .env y guardando cada resultado.
"""

import csv
import sys

sys.path.insert(0, "asistente")

import modelo  # noqa: E402
from db import conectar  # noqa: E402
from servicios import grafo  # noqa: E402
from servicios.herramientas import datos  # noqa: E402
from servicios.herramientas.generar_respuesta import _contexto_llm  # noqa: E402


def recolectar(ruta_csv: str) -> dict:
    filas = {"question": [], "answer": [], "contexts": []}
    conn = conectar()
    try:
        with open(ruta_csv, encoding="utf-8", newline="") as f:
            for fila in csv.DictReader(f):
                pregunta = fila["pregunta"].strip()
                r = grafo.procesar(conn, pregunta, {}, vectorizar=modelo.vectorizar_pregunta)
                contexto = datos.obtener_sitio(conn, r["sitio_id"]) if r["sitio_id"] else None
                filas["question"].append(pregunta)
                filas["answer"].append(r["respuesta"])
                filas["contexts"].append([_contexto_llm([contexto])] if contexto else [""])
    finally:
        conn.close()
    return filas


def main() -> None:
    ruta = sys.argv[1] if len(sys.argv) > 1 else "preguntas_prueba.csv"
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, faithfulness

    resultado = evaluate(Dataset.from_dict(recolectar(ruta)), metrics=[faithfulness, answer_relevancy])
    print(resultado)


if __name__ == "__main__":
    main()
