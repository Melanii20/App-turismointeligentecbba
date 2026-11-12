"""Parte B y E: sección «Documentos» y «Contenido traído de internet» del panel.

Se ejecuta en la imagen del panel (necesita jinja2, pypdf, python-docx):

  docker compose run --rm panel python -m pytest /app/pruebas/test_panel_documentos.py -q
"""

import io
import os
import sys

os.environ.setdefault("PANEL_SECRET", "prueba")
import pytest  # noqa: E402

pytest.importorskip("jinja2")      # estas pruebas son del panel: en la imagen del backend se omiten
pytest.importorskip("pypdf")
pytest.importorskip("itsdangerous")
pytest.importorskip("bcrypt")

sys.path.insert(0, "/app/panel")      # solo después de comprobar que estamos en la imagen del panel
from fastapi.testclient import TestClient  # noqa: E402

import documentos  # noqa: E402
import main  # noqa: E402
from auth import requerir_usuario  # noqa: E402
from db import conectar  # noqa: E402

PREFIJO = "ZZ PRUEBA PANEL"


def pdf_con_texto(texto: str) -> bytes:
    """Un PDF válido de una página con texto (con tabla xref calculada)."""
    NL = b"\n"
    flujo = f"BT /F1 12 Tf 72 720 Td ({texto}) Tj ET".encode("latin-1")
    objetos = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(flujo)).encode() + b">>" + NL + b"stream" + NL + flujo + NL + b"endstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    salida, posiciones = bytearray(b"%PDF-1.4" + NL), []
    for n, o in enumerate(objetos, 1):
        posiciones.append(len(salida))
        salida += str(n).encode() + b" 0 obj" + NL + o + NL + b"endobj" + NL
    xref = len(salida)
    salida += b"xref" + NL + b"0 " + str(len(objetos) + 1).encode() + NL + b"0000000000 65535 f " + NL
    for pos in posiciones:
        salida += ("%010d 00000 n " % pos).encode() + NL
    salida += b"trailer" + NL + b"<</Size " + str(len(objetos) + 1).encode() + b"/Root 1 0 R>>" + NL
    salida += b"startxref" + NL + str(xref).encode() + NL + b"%%EOF"
    return bytes(salida)


def pdf_imagen() -> bytes:
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=200, height=200)        # una página sin texto = un PDF escaneado
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


@pytest.fixture(scope="module")
def cliente():
    with conectar() as c, c.cursor() as cur:
        cur.execute("SELECT id FROM usuarios ORDER BY id LIMIT 1")
        uid = cur.fetchone()[0]
    usuario = {"id": uid, "nombre": "Prueba", "rol": "administrador"}
    main.usuario_actual = lambda request: usuario
    main.app.dependency_overrides[requerir_usuario] = lambda: usuario
    with TestClient(main.app, follow_redirects=False) as c:
        yield c
    main.app.dependency_overrides.clear()
    con = conectar()
    with con.cursor() as cur:
        cur.execute("DELETE FROM documentos WHERE titulo LIKE %s", (PREFIJO + "%",))
        cur.execute("DELETE FROM contenido_web WHERE titulo LIKE %s", (PREFIJO + "%",))
    con.commit()
    con.close()


def subir(cliente, titulo, archivo=("a.txt", b"Hola. Texto de prueba suficientemente largo para el documento de prueba."), **extra):
    datos = {"titulo": titulo, "tipo": "guia", "tema": "leyendas", "permiso_uso": "Autorización de prueba", **extra}
    files = {"archivo": archivo} if archivo else {}
    return cliente.post("/documentos/nuevo", data=datos, files=files)


def estado_de(titulo):
    con = conectar()
    with con.cursor() as cur:
        cur.execute("SELECT id, estado, verificado_por, fecha_verificacion, "
                    "(SELECT count(*) FROM fragmentos_documento WHERE documento_id = d.id) FROM documentos d WHERE titulo = %s", (titulo,))
        f = cur.fetchone()
    con.close()
    return f


# ---------- extracción y fragmentos ----------
def test_fragmentos_de_800_con_solapamiento_y_sin_cortar_palabras():
    parrafos = "\n\n".join(f"Párrafo número {i}. " + ("palabra " * 40).strip() + "." for i in range(12))
    frags = documentos.fragmentar([(1, parrafos)])
    assert len(frags) > 2 and all(len(f["texto"]) <= 1000 for f in frags)
    assert all(f["pagina"] == 1 for f in frags) and [f["numero"] for f in frags] == list(range(1, len(frags) + 1))
    # solapamiento: el comienzo de cada fragmento repite el final del anterior
    for a, b in zip(frags, frags[1:]):
        assert b["texto"][:40].strip().split()[0] in a["texto"]


def test_un_parrafo_enorme_se_parte():
    frags = documentos.fragmentar([(3, "Una oración larga. " * 300)])
    assert len(frags) > 3 and all(len(f["texto"]) <= 1000 for f in frags) and frags[0]["pagina"] == 3


def test_pdf_con_texto_da_paginas():
    paginas = documentos.extraer_paginas("guia.pdf", pdf_con_texto("Leyenda de la piedra que canta en Cochabamba, texto largo de prueba."))
    assert paginas[0][0] == 1 and "piedra" in paginas[0][1]


def test_pdf_imagen_se_rechaza_con_mensaje_claro():
    with pytest.raises(documentos.ErrorDocumento, match="es una imagen; súbelo con texto"):
        documentos.extraer_paginas("escaneado.pdf", pdf_imagen())


def test_docx_y_txt():
    from docx import Document

    d = Document()
    d.add_paragraph("Primer párrafo del documento Word de prueba.")
    d.add_paragraph("Segundo párrafo con más texto de prueba.")
    buf = io.BytesIO()
    d.save(buf)
    assert "Segundo" in documentos.extraer_paginas("a.docx", buf.getvalue())[0][1]
    paginas = documentos.extraer_paginas("a.txt", "Página uno\fPágina dos".encode("utf-8"))
    assert [p[0] for p in paginas] == [1, 2]


def test_extension_no_permitida():
    with pytest.raises(documentos.ErrorDocumento):
        documentos.extraer_paginas("virus.exe", b"x")


# ---------- panel ----------
def test_subir_sin_permiso_de_uso_no_deja_guardar(cliente):
    r = cliente.post("/documentos/nuevo", data={"titulo": PREFIJO + " sin permiso", "tipo": "guia", "permiso_uso": ""},
                     files={"archivo": ("a.txt", b"texto de prueba " * 10)})
    assert r.status_code == 400 and "permiso o licencia" in r.text
    assert estado_de(PREFIJO + " sin permiso") is None


def test_subir_pdf_imagen_muestra_el_aviso(cliente):
    r = subir(cliente, PREFIJO + " imagen", ("esc.pdf", pdf_imagen()))
    assert r.status_code == 400 and "es una imagen; súbelo con texto" in r.text
    assert estado_de(PREFIJO + " imagen") is None


def test_flujo_completo_borrador_verificar_editar_eliminar(cliente):
    titulo = PREFIJO + " flujo"
    texto = ("Esta es una leyenda ficticia de prueba. " * 40).encode()
    r = subir(cliente, titulo, ("flujo.txt", texto))
    assert r.status_code == 303
    doc_id, estado, verificador, fecha, n = estado_de(titulo)
    assert estado == "borrador" and verificador is None and n >= 1                    # entra en borrador, con fragmentos
    assert "Fragmento 1" in cliente.get(f"/documentos/{doc_id}").text                 # vista previa

    assert cliente.post(f"/documentos/{doc_id}/verificar").status_code == 303
    _, estado, verificador, fecha, _ = estado_de(titulo)
    assert estado == "verificado" and verificador is not None and fecha is not None

    # editar o reemplazar el archivo -> vuelve a borrador y se regeneran los fragmentos
    r = cliente.post(f"/documentos/{doc_id}/editar", data={"titulo": titulo, "tipo": "guia", "permiso_uso": "Otro permiso"},
                     files={"archivo": ("nuevo.txt", ("Otro texto totalmente distinto. " * 100).encode())})
    assert r.status_code == 303
    _, estado, verificador, fecha, n2 = estado_de(titulo)
    assert estado == "borrador" and verificador is None and fecha is None and n2 >= 1

    # eliminar pide confirmación y borra los fragmentos en cascada
    assert "No, volver" in cliente.get(f"/documentos/{doc_id}/eliminar").text
    cliente.post(f"/documentos/{doc_id}/eliminar", data={})
    assert estado_de(titulo) is not None                                              # sin confirmar no se borra
    cliente.post(f"/documentos/{doc_id}/eliminar", data={"confirmar": "si"})
    assert estado_de(titulo) is None
    con = conectar()
    with con.cursor() as cur:
        cur.execute("SELECT count(*) FROM fragmentos_documento WHERE documento_id = %s", (doc_id,))
        assert cur.fetchone()[0] == 0
    con.close()


def test_la_lista_y_la_navegacion_incluyen_documentos(cliente):
    r = cliente.get("/documentos")
    assert r.status_code == 200 and "Subir documento" in r.text and 'href="/documentos"' in r.text


# ---------- contenido traído de internet (parte E) ----------
def _contenido(titulo="PRUEBA PANEL silpancho"):
    con = conectar()
    with con.cursor() as cur:
        cur.execute(
            "INSERT INTO contenido_web (fuente, tema, titulo, url, texto, dominio) VALUES "
            "('tavily','gastronomia',%s,'https://es.wikipedia.org/wiki/Silpancho','El silpancho es típico de Cochabamba.','es.wikipedia.org') RETURNING id",
            (PREFIJO + " " + titulo,),
        )
        i = cur.fetchone()[0]
    con.commit()
    con.close()
    return i


def test_lista_de_contenido_web_con_dominio_url_tema_fecha_y_estado(cliente):
    i = _contenido("lista")
    r = cliente.get("/contenido-web")
    assert r.status_code == 200 and "es.wikipedia.org" in r.text and "gastronomia" in r.text and "pendiente" in r.text
    assert "https://es.wikipedia.org/wiki/Silpancho" in r.text and "Convertir en documento" in r.text and f"/contenido-web/{i}/descartar" in r.text


def test_convertir_en_documento_crea_borrador_con_permiso_y_marca_convertido(cliente):
    i = _contenido("convertir")
    r = cliente.post(f"/contenido-web/{i}/convertir")
    assert r.status_code == 303
    con = conectar()
    with con.cursor() as cur:
        cur.execute("SELECT estado_revision FROM contenido_web WHERE id = %s", (i,))
        assert cur.fetchone()[0] == "convertido"
        cur.execute("SELECT tipo, estado, url_origen, permiso_uso, archivo FROM documentos WHERE titulo = %s", (PREFIJO + " convertir",))
        tipo, estado, url, permiso, archivo = cur.fetchone()
        cur.execute("SELECT count(*) FROM fragmentos_documento f JOIN documentos d ON d.id = f.documento_id WHERE d.titulo = %s", (PREFIJO + " convertir",))
        assert cur.fetchone()[0] >= 1
    con.close()
    assert tipo == "web_revisado" and estado == "borrador" and url == "https://es.wikipedia.org/wiki/Silpancho" and archivo is None
    assert permiso.startswith("Licencia del sitio de origen:") and "CC BY-SA 4.0" in permiso
    # convertir otra vez no duplica
    assert cliente.post(f"/contenido-web/{i}/convertir").status_code == 303


def test_descartar_marca_el_contenido(cliente):
    i = _contenido("descartar")
    assert cliente.post(f"/contenido-web/{i}/descartar").status_code == 303
    con = conectar()
    with con.cursor() as cur:
        cur.execute("SELECT estado_revision FROM contenido_web WHERE id = %s", (i,))
        assert cur.fetchone()[0] == "descartado"
    con.close()
