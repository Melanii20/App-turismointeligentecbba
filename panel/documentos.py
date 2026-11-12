"""Documentos de turismo para el RAG: leer el archivo, partirlo en fragmentos y calcular sus embeddings.

Pasos:
  1. extraer_paginas(): texto del PDF (con número de página), DOCX o TXT. Un PDF sin texto (imagen)
     se rechaza: no hay OCR a propósito.
  2. fragmentar(): trozos de unos 800 caracteres con 150 de solapamiento, respetando párrafos.
  3. calcular_embeddings(): el MISMO modelo de los sitios (embeddings.py).

Reglas (CLAUDE.md): un documento nunca llena campos acceso_*, ni responde sobre accesibilidad,
horarios, precios, direcciones o fechas. Eso lo decide el asistente, no este módulo; aquí solo se
guarda el texto narrativo.
"""

import io
import re
from typing import List, Optional, Tuple

TAMANO_FRAGMENTO = 800
SOLAPAMIENTO = 150
EXTENSIONES = (".pdf", ".docx", ".txt")
TAMANO_MAXIMO_BYTES = 15 * 1024 * 1024
MINIMO_CARACTERES_PDF = 40       # menos que esto en todo el PDF = es una imagen escaneada


class ErrorDocumento(ValueError):
    """Error que se le muestra a la persona (en español)."""


def _limpiar(texto: str) -> str:
    texto = texto.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def extraer_paginas(nombre_archivo: str, contenido: bytes) -> List[Tuple[Optional[int], str]]:
    """Lista de (página o None, texto). Lanza ErrorDocumento si no se puede leer o no tiene texto."""
    nombre = nombre_archivo.lower()
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise ErrorDocumento("El archivo pesa más de 15 MB. Sube una versión más liviana.")
    if nombre.endswith(".pdf"):
        return _paginas_pdf(contenido)
    if nombre.endswith(".docx"):
        return _paginas_docx(contenido)
    if nombre.endswith(".txt"):
        return _paginas_txt(contenido)
    raise ErrorDocumento("Solo se aceptan archivos PDF, DOCX o TXT.")


def _paginas_pdf(contenido: bytes):
    from pypdf import PdfReader

    try:
        lector = PdfReader(io.BytesIO(contenido))
        paginas = [(i + 1, _limpiar(p.extract_text() or "")) for i, p in enumerate(lector.pages)]
    except Exception:
        raise ErrorDocumento("No se pudo leer el PDF. Comprueba que no esté dañado ni protegido con contraseña.")
    paginas = [(n, t) for n, t in paginas if t]
    if sum(len(t) for _, t in paginas) < MINIMO_CARACTERES_PDF:
        raise ErrorDocumento("Este PDF es una imagen; súbelo con texto.")
    return paginas


def _paginas_docx(contenido: bytes):
    from docx import Document

    try:
        doc = Document(io.BytesIO(contenido))
    except Exception:
        raise ErrorDocumento("No se pudo leer el DOCX. Comprueba que sea un documento de Word válido.")
    texto = _limpiar("\n\n".join(p.text for p in doc.paragraphs if p.text.strip()))
    if not texto:
        raise ErrorDocumento("El documento no tiene texto.")
    return [(None, texto)]        # Word no guarda páginas fijas: sin número de página


def _paginas_txt(contenido: bytes):
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = contenido.decode("latin-1")
    # Un salto de página (\f) separa páginas; si no hay, todo es la página 1.
    trozos = [_limpiar(t) for t in texto.split("\f")]
    paginas = [(i + 1, t) for i, t in enumerate(trozos) if t]
    if not paginas:
        raise ErrorDocumento("El archivo no tiene texto.")
    return paginas


def _partir_largo(texto: str, tamano: int) -> List[str]:
    """Parte un párrafo más largo que 'tamano' por oraciones y, si hace falta, por palabras."""
    piezas, actual = [], ""
    for oracion in re.split(r"(?<=[.!?…])\s+", texto):
        if len(oracion) > tamano:
            if actual:
                piezas.append(actual)
                actual = ""
            palabras, corte = oracion.split(), ""
            for p in palabras:
                if len(corte) + len(p) + 1 > tamano and corte:
                    piezas.append(corte)
                    corte = ""
                corte = f"{corte} {p}".strip()
            actual = corte
        elif len(actual) + len(oracion) + 1 > tamano and actual:
            piezas.append(actual)
            actual = oracion
        else:
            actual = f"{actual} {oracion}".strip()
    if actual:
        piezas.append(actual)
    return piezas


def _cola_con_palabras_completas(texto: str, largo: int) -> str:
    """Los últimos 'largo' caracteres, empezando en una palabra completa."""
    if len(texto) <= largo:
        return texto
    cola = texto[-largo:]
    espacio = cola.find(" ")
    return cola[espacio + 1:] if espacio != -1 else cola


def fragmentar_pagina(texto: str, tamano: int = TAMANO_FRAGMENTO, solape: int = SOLAPAMIENTO) -> List[str]:
    """Fragmentos de ~'tamano' caracteres con 'solape' de solapamiento, sin cortar párrafos si caben."""
    parrafos: List[str] = []
    for p in re.split(r"\n\s*\n|\n", texto):
        p = " ".join(p.split())
        if not p:
            continue
        parrafos.extend(_partir_largo(p, tamano) if len(p) > tamano else [p])

    fragmentos, actual = [], ""
    for p in parrafos:
        if actual and len(actual) + len(p) + 1 > tamano:
            fragmentos.append(actual)
            actual = f"{_cola_con_palabras_completas(actual, solape)} {p}".strip()
        else:
            actual = f"{actual} {p}".strip()
    if actual and (not fragmentos or actual != fragmentos[-1]):
        fragmentos.append(actual)
    return fragmentos


def fragmentar(paginas: List[Tuple[Optional[int], str]]) -> List[dict]:
    """[{'numero', 'pagina', 'texto'}] para todo el documento (el solapamiento no cruza páginas)."""
    resultado = []
    for pagina, texto in paginas:
        for f in fragmentar_pagina(texto):
            resultado.append({"numero": len(resultado) + 1, "pagina": pagina, "texto": f})
    return resultado


def calcular_embeddings(fragmentos: List[dict]) -> List[list]:
    """Vectores (768) de los fragmentos, con el mismo modelo que los sitios."""
    import embeddings

    if not fragmentos:
        return []
    vectores = embeddings.cargar_modelo().encode([f["texto"] for f in fragmentos], batch_size=16)
    return [v.tolist() for v in vectores]


def guardar_fragmentos(cur, documento_id: int, fragmentos: List[dict], vectores: List[list]) -> None:
    """Reemplaza todos los fragmentos del documento por los nuevos."""
    cur.execute("DELETE FROM fragmentos_documento WHERE documento_id = %s", (documento_id,))
    for f, v in zip(fragmentos, vectores):
        cur.execute(
            "INSERT INTO fragmentos_documento (documento_id, numero, pagina, texto, embedding) "
            "VALUES (%s, %s, %s, %s, %s)",
            (documento_id, f["numero"], f["pagina"], f["texto"], v),
        )
