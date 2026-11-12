"""Sección «Documentos» del panel: subir, ver fragmentos, verificar, editar y eliminar.

Un documento entra como borrador. Solo cuando una persona lo verifica, sus fragmentos entran al RAG
(nivel 1 de la cascada narrativa). Editar o reemplazar el archivo lo devuelve a borrador.
"""

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from starlette.datastructures import UploadFile

import documentos
from auth import requerir_usuario
from db import conectar

CARPETA = Path(__file__).resolve().parent.parent / "documentos_subidos"
TIPOS = ("manual", "guia", "folleto", "libro", "web_revisado", "otro")
TEMAS = ("general", "gastronomia", "tradiciones", "fiestas", "leyendas", "danzas_musica", "artesanias", "historia",
         "personajes", "idioma", "naturaleza")
ESTADOS = ("borrador", "verificado")
CAMPOS = ("titulo", "institucion_autor", "tipo", "tema", "anio", "permiso_uso", "url_origen")
LIMITES = {"titulo": ("El título", 255), "institucion_autor": ("La institución o autor", 255), "url_origen": ("La URL de origen", 2000)}


def _nombre_seguro(nombre: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(nombre).name)[:120]
    return base or "documento"


def validar(form: dict, hay_archivo: bool, archivo_obligatorio: bool) -> tuple:
    """(datos limpios, errores). La clave de cada error es el nombre del campo."""
    errores, datos = {}, {}
    for campo in CAMPOS:
        datos[campo] = (form.get(campo) or "").strip() or None
    if not datos["titulo"]:
        errores["titulo"] = "El título es obligatorio."
    if not datos["permiso_uso"]:
        errores["permiso_uso"] = (
            "Escribe con qué permiso o licencia se usa este documento (por ejemplo: «autorización de la institución» "
            "o «licencia CC BY 4.0»). Es obligatorio."
        )
    if datos["tipo"] not in TIPOS:
        errores["tipo"] = "Elige un tipo de documento."
    if datos["tema"] and datos["tema"] not in TEMAS:
        errores["tema"] = "Elige un tema de la lista."
    for campo, (nombre, maximo) in LIMITES.items():
        if datos[campo] and len(datos[campo]) > maximo:
            errores[campo] = f"{nombre} no puede pasar de {maximo} caracteres."
    if datos["anio"]:
        try:
            anio = int(datos["anio"])
            if not 1500 <= anio <= 2100:
                raise ValueError
            datos["anio"] = anio
        except ValueError:
            errores["anio"] = "El año debe ser un número de cuatro cifras, por ejemplo 2019."
    if archivo_obligatorio and not hay_archivo:
        errores["archivo"] = "Elige un archivo PDF, DOCX o TXT."
    return datos, errores


def crear_router(pagina):
    router = APIRouter()

    def formulario(request, valores, errores, status_code=200, documento_id=None, estado=None):
        return pagina(
            request, "documento_form.html",
            {
                "titulo": "Editar documento" if documento_id else "Subir documento",
                "v": valores, "errores": errores, "tipos": TIPOS, "temas": TEMAS,
                "documento_id": documento_id, "estado": estado,
                "accion": f"/documentos/{documento_id}/editar" if documento_id else "/documentos/nuevo",
                "boton": "Guardar cambios" if documento_id else "Subir y procesar",
            },
            status_code=status_code,
        )

    async def leer_formulario(request: Request):
        form = await request.form()
        valores = {c: form.get(c) for c in CAMPOS}
        archivo = form.get("archivo")
        subido = archivo if isinstance(archivo, UploadFile) and archivo.filename else None
        contenido = await subido.read() if subido else None
        return valores, subido, contenido

    def procesar_archivo(nombre: str, contenido: bytes):
        """(fragmentos, vectores). Lanza ErrorDocumento con un mensaje claro."""
        paginas = documentos.extraer_paginas(nombre, contenido)
        fragmentos = documentos.fragmentar(paginas)
        if not fragmentos:
            raise documentos.ErrorDocumento("No se encontró texto en el archivo.")
        return fragmentos, documentos.calcular_embeddings(fragmentos)

    # ---------------- lista ----------------
    @router.get("/documentos")
    def lista(request: Request, estado: str = None, usuario: dict = Depends(requerir_usuario)):
        mensaje = request.session.pop("mensaje", None)
        filtro = estado if estado in ESTADOS else None
        conn = conectar()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT estado, count(*) FROM documentos GROUP BY estado")
                por_estado = dict(cur.fetchall())
                cur.execute(
                    """
                    SELECT d.id, d.titulo, d.tipo, d.tema, d.estado, d.anio,
                           (SELECT count(*) FROM fragmentos_documento f WHERE f.documento_id = d.id)
                    FROM documentos d WHERE (%(f)s::text IS NULL OR d.estado = %(f)s) ORDER BY d.titulo
                    """,
                    {"f": filtro},
                )
                filas = [
                    {"id": f[0], "titulo": f[1], "tipo": f[2], "tema": f[3], "estado": f[4], "anio": f[5], "fragmentos": f[6]}
                    for f in cur.fetchall()
                ]
        finally:
            conn.close()
        conteos = {"total": sum(por_estado.values()), "verificado": por_estado.get("verificado", 0), "borrador": por_estado.get("borrador", 0)}
        return pagina(request, "documentos.html", {
            "titulo": "Documentos", "documentos": filas, "mensaje": mensaje, "conteos": conteos, "filtro": filtro,
        })

    # ---------------- crear ----------------
    @router.get("/documentos/nuevo")
    def nuevo(request: Request, usuario: dict = Depends(requerir_usuario)):
        return formulario(request, {"tipo": "guia"}, {})

    @router.post("/documentos/nuevo")
    async def crear(request: Request, usuario: dict = Depends(requerir_usuario)):
        valores, subido, contenido = await leer_formulario(request)
        datos, errores = validar(valores, subido is not None, archivo_obligatorio=True)
        fragmentos = vectores = None
        if "archivo" not in errores and subido is not None:
            try:
                fragmentos, vectores = procesar_archivo(subido.filename, contenido)
            except documentos.ErrorDocumento as e:
                errores["archivo"] = str(e)
        if errores:
            return formulario(request, valores, errores, status_code=400)

        conn = conectar()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documentos (titulo, institucion_autor, tipo, tema, anio, permiso_uso, url_origen,
                                            estado, subido_por)
                    VALUES (%(titulo)s, %(institucion_autor)s, %(tipo)s, %(tema)s, %(anio)s, %(permiso_uso)s,
                            %(url_origen)s, 'borrador', %(usuario)s) RETURNING id
                    """,
                    {**datos, "usuario": usuario["id"]},
                )
                doc_id = cur.fetchone()[0]
                CARPETA.mkdir(exist_ok=True)
                ruta = f"{doc_id}_{_nombre_seguro(subido.filename)}"
                (CARPETA / ruta).write_bytes(contenido)
                cur.execute("UPDATE documentos SET archivo = %s WHERE id = %s", (ruta, doc_id))
                documentos.guardar_fragmentos(cur, doc_id, fragmentos, vectores)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        request.session["mensaje"] = (
            f"Documento «{datos['titulo']}» subido con {len(fragmentos)} fragmentos. Está en borrador: revísalo y verifícalo."
        )
        return RedirectResponse(f"/documentos/{doc_id}", status_code=303)

    # ---------------- detalle / vista previa ----------------
    def cargar(doc_id: int):
        conn = conectar()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, titulo, institucion_autor, tipo, tema, archivo, url_origen, anio, permiso_uso, estado, "
                    "fecha_verificacion FROM documentos WHERE id = %s", (doc_id,),
                )
                f = cur.fetchone()
                if not f:
                    return None, []
                cur.execute(
                    "SELECT numero, pagina, texto FROM fragmentos_documento WHERE documento_id = %s ORDER BY numero",
                    (doc_id,),
                )
                frags = [{"numero": r[0], "pagina": r[1], "texto": r[2]} for r in cur.fetchall()]
        finally:
            conn.close()
        clave = ("id", "titulo", "institucion_autor", "tipo", "tema", "archivo", "url_origen", "anio", "permiso_uso", "estado", "fecha_verificacion")
        return dict(zip(clave, f)), frags

    @router.get("/documentos/{doc_id}")
    def detalle(doc_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
        mensaje = request.session.pop("mensaje", None)
        error = request.session.pop("error", None)
        doc, frags = cargar(doc_id)
        if not doc:
            return pagina(request, "no_encontrado.html", {"titulo": "Documento no encontrado"}, status_code=404)
        return pagina(request, "documento_detalle.html", {
            "titulo": doc["titulo"], "doc": doc, "fragmentos": frags, "mensaje": mensaje, "error": error,
        })

    # ---------------- verificar ----------------
    @router.post("/documentos/{doc_id}/verificar")
    def verificar(doc_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
        conn = conectar()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT titulo, estado, permiso_uso, (SELECT count(*) FROM fragmentos_documento WHERE documento_id = %s) "
                    "FROM documentos WHERE id = %s FOR UPDATE", (doc_id, doc_id),
                )
                f = cur.fetchone()
                if not f:
                    return pagina(request, "no_encontrado.html", {"titulo": "Documento no encontrado"}, status_code=404)
                titulo, estado, permiso, n = f
                if estado == "verificado":
                    request.session["mensaje"] = f"El documento «{titulo}» ya estaba verificado."
                elif not (permiso or "").strip() or n == 0:
                    request.session["error"] = "No se puede verificar: falta el permiso de uso o no tiene fragmentos."
                else:
                    cur.execute(
                        "UPDATE documentos SET estado = 'verificado', verificado_por = %s, fecha_verificacion = now() WHERE id = %s",
                        (usuario["id"], doc_id),
                    )
                    request.session["mensaje"] = f"Documento «{titulo}» verificado. Ya lo usa el asistente."
            conn.commit()
        finally:
            conn.close()
        return RedirectResponse(f"/documentos/{doc_id}", status_code=303)

    # ---------------- editar / reemplazar ----------------
    @router.get("/documentos/{doc_id}/editar")
    def editar_form(doc_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
        doc, _ = cargar(doc_id)
        if not doc:
            return pagina(request, "no_encontrado.html", {"titulo": "Documento no encontrado"}, status_code=404)
        valores = {c: ("" if doc[c] is None else doc[c]) for c in CAMPOS}
        return formulario(request, valores, {}, documento_id=doc_id, estado=doc["estado"])

    @router.post("/documentos/{doc_id}/editar")
    async def editar(doc_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
        doc, _ = cargar(doc_id)
        if not doc:
            return pagina(request, "no_encontrado.html", {"titulo": "Documento no encontrado"}, status_code=404)
        valores, subido, contenido = await leer_formulario(request)
        datos, errores = validar(valores, subido is not None, archivo_obligatorio=False)
        fragmentos = vectores = None
        if subido is not None and "archivo" not in errores:
            try:
                fragmentos, vectores = procesar_archivo(subido.filename, contenido)
            except documentos.ErrorDocumento as e:
                errores["archivo"] = str(e)
        if errores:
            return formulario(request, valores, errores, status_code=400, documento_id=doc_id, estado=doc["estado"])

        conn = conectar()
        try:
            with conn.cursor() as cur:
                # Cualquier edición devuelve el documento a borrador: hay que volver a verificarlo.
                cur.execute(
                    """
                    UPDATE documentos SET titulo=%(titulo)s, institucion_autor=%(institucion_autor)s, tipo=%(tipo)s,
                        tema=%(tema)s, anio=%(anio)s, permiso_uso=%(permiso_uso)s, url_origen=%(url_origen)s,
                        estado='borrador', verificado_por=NULL, fecha_verificacion=NULL WHERE id=%(id)s
                    """,
                    {**datos, "id": doc_id},
                )
                if subido is not None:
                    CARPETA.mkdir(exist_ok=True)
                    ruta = f"{doc_id}_{_nombre_seguro(subido.filename)}"
                    (CARPETA / ruta).write_bytes(contenido)
                    cur.execute("UPDATE documentos SET archivo = %s WHERE id = %s", (ruta, doc_id))
                    documentos.guardar_fragmentos(cur, doc_id, fragmentos, vectores)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        extra = f" Se regeneraron {len(fragmentos)} fragmentos." if fragmentos else ""
        request.session["mensaje"] = f"Documento «{datos['titulo']}» guardado.{extra} Volvió a borrador: verifícalo de nuevo."
        return RedirectResponse(f"/documentos/{doc_id}", status_code=303)

    # ---------------- eliminar (con confirmación) ----------------
    @router.get("/documentos/{doc_id}/eliminar")
    def eliminar_confirmar(doc_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
        doc, frags = cargar(doc_id)
        if not doc:
            return pagina(request, "no_encontrado.html", {"titulo": "Documento no encontrado"}, status_code=404)
        return pagina(request, "documento_eliminar.html", {"titulo": "Eliminar documento", "doc": doc, "n": len(frags)})

    @router.post("/documentos/{doc_id}/eliminar")
    async def eliminar(doc_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
        form = await request.form()
        if form.get("confirmar") != "si":
            return RedirectResponse(f"/documentos/{doc_id}/eliminar", status_code=303)
        conn = conectar()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM documentos WHERE id = %s RETURNING titulo, archivo", (doc_id,))
                fila = cur.fetchone()          # los fragmentos se borran en cascada
            conn.commit()
        finally:
            conn.close()
        if not fila:
            return pagina(request, "no_encontrado.html", {"titulo": "Documento no encontrado"}, status_code=404)
        if fila[1]:
            try:
                (CARPETA / fila[1]).unlink(missing_ok=True)
            except OSError:
                pass
        request.session["mensaje"] = f"Documento «{fila[0]}» eliminado, con todos sus fragmentos."
        return RedirectResponse("/documentos", status_code=303)

    return router
