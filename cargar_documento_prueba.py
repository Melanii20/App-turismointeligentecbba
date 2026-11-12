"""Carga y VERIFICA el documento FICTICIO "Guía de prueba de Cochabamba (FICTICIO)" para ver el RAG funcionando.

Es un dato de prueba inventado (igual que datos_prueba.sql). Se borra con borrar_datos_prueba.sql.
Usa las mismas funciones del panel (extraer, fragmentar, embeddings), así que se ejecuta en la imagen del panel:

  docker compose run --rm panel python /app/cargar_documento_prueba.py
"""

import sys
from pathlib import Path

sys.path.insert(0, "/app/panel")
sys.path.insert(0, "/app")

import documentos          # noqa: E402
from db import conectar    # noqa: E402

TITULO = "Guía de prueba de Cochabamba (FICTICIO)"
ARCHIVO = Path("/app/datos_prueba_docs/guia_prueba_cochabamba_FICTICIO.txt")
PERMISO = "DATO DE PRUEBA (ficticio, borrar antes de usar datos reales)"

contenido = ARCHIVO.read_bytes()
paginas = documentos.extraer_paginas(ARCHIVO.name, contenido)
fragmentos = documentos.fragmentar(paginas)
vectores = documentos.calcular_embeddings(fragmentos)

conn = conectar()
with conn.cursor() as cur:
    cur.execute("SELECT id FROM documentos WHERE titulo = %s", (TITULO,))
    if cur.fetchone():
        print("El documento de prueba ya está cargado. No se hace nada.")
        sys.exit(0)
    cur.execute("SELECT id FROM usuarios ORDER BY id LIMIT 1")
    usuario = cur.fetchone()[0]
    cur.execute(
        """
        INSERT INTO documentos (titulo, institucion_autor, tipo, tema, archivo, anio, permiso_uso, estado,
                                subido_por, verificado_por, fecha_verificacion)
        VALUES (%s, 'DATO DE PRUEBA', 'guia', 'leyendas', %s, 2026, %s, 'verificado', %s, %s, now()) RETURNING id
        """,
        (TITULO, ARCHIVO.name, PERMISO, usuario, usuario),
    )
    doc_id = cur.fetchone()[0]
    documentos.guardar_fragmentos(cur, doc_id, fragmentos, vectores)
conn.commit()
print(f"Documento {doc_id} cargado y verificado con {len(fragmentos)} fragmentos (páginas: {sorted({f['pagina'] for f in fragmentos})}).")
