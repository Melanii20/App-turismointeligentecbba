"""Sección «Contenido traído de internet» del panel (parte E).

Lista lo que el asistente guardó en la caché web (tabla contenido_web). La administradora puede:
  - «Convertir en documento»: crea un documento tipo web_revisado en BORRADOR, con su URL de origen y el
    permiso «Licencia del sitio de origen: …». Al verificarlo, entra al nivel 1 de la cascada.
  - «Descartar»: el contenido no se vuelve a usar desde la caché.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

import documentos
from auth import requerir_usuario
from db import conectar

ESTADOS = ("pendiente", "convertido", "descartado")
# tema de la caché web -> tema de documentos
TEMA_DOCUMENTO = {
    "leyenda": "leyendas", "tradicion": "tradiciones", "fiesta": "fiestas", "gastronomia": "gastronomia",
    "danza": "danzas_musica", "artesania": "artesanias", "historia": "historia", "personaje": "personajes",
    "idioma": "idioma", "naturaleza": "naturaleza",
}


def crear_router(pagina):
    router = APIRouter()

    @router.get("/contenido-web")
    def lista(request: Request, estado: str = None, usuario: dict = Depends(requerir_usuario)):
        mensaje = request.session.pop("mensaje", None)
        filtro = estado if estado in ESTADOS else None
        conn = conectar()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT estado_revision, count(*) FROM contenido_web GROUP BY estado_revision")
                por_estado = dict(cur.fetchall())
                cur.execute(
                    """
                    SELECT id, titulo, COALESCE(dominio, ''), url, tema, obtenido_en, estado_revision, licencia
                    FROM contenido_web WHERE (%(f)s::text IS NULL OR estado_revision = %(f)s) ORDER BY obtenido_en DESC
                    """,
                    {"f": filtro},
                )
                filas = [
                    {"id": f[0], "titulo": f[1], "dominio": f[2], "url": f[3], "tema": f[4], "fecha": f[5],
                     "estado_revision": f[6], "licencia": f[7]}
                    for f in cur.fetchall()
                ]
        finally:
            conn.close()
        conteos = {e: por_estado.get(e, 0) for e in ESTADOS}
        conteos["total"] = sum(por_estado.values())
        return pagina(request, "contenido_web.html", {
            "titulo": "Contenido traído de internet", "filas": filas, "mensaje": mensaje, "conteos": conteos, "filtro": filtro,
        })

    @router.post("/contenido-web/{contenido_id}/convertir")
    def convertir(contenido_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
        conn = conectar()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT titulo, texto, url, tema, licencia, estado_revision FROM contenido_web WHERE id = %s FOR UPDATE",
                    (contenido_id,),
                )
                f = cur.fetchone()
                if not f:
                    return pagina(request, "no_encontrado.html", {"titulo": "Contenido no encontrado"}, status_code=404)
                titulo, texto, url, tema, licencia, estado = f
                if estado == "convertido":
                    request.session["mensaje"] = f"«{titulo}» ya se había convertido en documento."
                    return RedirectResponse("/contenido-web", status_code=303)
                fragmentos = documentos.fragmentar([(None, texto)])
                vectores = documentos.calcular_embeddings(fragmentos)
                permiso = f"Licencia del sitio de origen: {licencia or 'ver la página de origen'} ({url})"
                cur.execute(
                    """
                    INSERT INTO documentos (titulo, institucion_autor, tipo, tema, url_origen, permiso_uso, estado, subido_por)
                    VALUES (%s, %s, 'web_revisado', %s, %s, %s, 'borrador', %s) RETURNING id
                    """,
                    (titulo[:255], "Internet", TEMA_DOCUMENTO.get(tema), url, permiso, usuario["id"]),
                )
                doc_id = cur.fetchone()[0]
                documentos.guardar_fragmentos(cur, doc_id, fragmentos, vectores)
                cur.execute("UPDATE contenido_web SET estado_revision = 'convertido' WHERE id = %s", (contenido_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        request.session["mensaje"] = f"«{titulo}» se convirtió en un documento en borrador. Revísalo y verifícalo."
        return RedirectResponse(f"/documentos/{doc_id}", status_code=303)

    @router.post("/contenido-web/{contenido_id}/descartar")
    def descartar(contenido_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
        conn = conectar()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE contenido_web SET estado_revision = 'descartado' WHERE id = %s RETURNING titulo", (contenido_id,))
                f = cur.fetchone()
            conn.commit()
        finally:
            conn.close()
        if not f:
            return pagina(request, "no_encontrado.html", {"titulo": "Contenido no encontrado"}, status_code=404)
        request.session["mensaje"] = f"«{f[0]}» descartado: el asistente ya no lo usa."
        return RedirectResponse("/contenido-web", status_code=303)

    return router
