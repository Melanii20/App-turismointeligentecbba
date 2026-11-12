"""Aplicación FastAPI del panel de administración.

Rutas actuales:
  /        redirige a /sitios (requiere sesión)
  /sitios  lista de sitios turísticos (requiere sesión)
  /sitios/nuevo  formulario para crear un sitio (entra como borrador)
  /sitios/{id}/editar  formulario para editar un sitio (vuelve a borrador)
  /sitios/{id}/verificar  verifica un sitio si sus datos de accesibilidad están completos (POST)
  /eventos  lista de eventos del calendario (requiere sesión)
  /eventos/nuevo  formulario para crear un evento
  /eventos/{id}/editar  formulario para editar un evento
  /eventos/{id}/eliminar  elimina un evento (POST)
  /login   formulario de inicio de sesión
  /logout  cierra la sesión (POST)
  /salud   comprueba la conexión a la base
"""

import os
from contextlib import asynccontextmanager
from datetime import date, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from auth import (
    NoAutenticado,
    hashear_password,
    requerir_usuario,
    usuario_actual,
    verificar_password,
)
import embeddings
import rutas_contenido_web
import rutas_documentos
from db import conectar

BASE_DIR = Path(__file__).parent

# Clave para firmar la cookie de sesión. Viene de panel/.env (no se sube a git).
CLAVE_SESION = os.environ.get("PANEL_SECRET")
if not CLAVE_SESION:
    raise RuntimeError("Falta la variable de entorno PANEL_SECRET (ver panel/.env.example)")

# Hash de relleno: se compara contra él cuando el email no existe, para que
# responder a un email inexistente tarde lo mismo que a uno existente.
HASH_RELLENO = hashear_password("relleno-no-es-una-contraseña-real")

@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Al arrancar, carga el modelo de embeddings una sola vez."""
    embeddings.cargar_modelo()
    yield


app = FastAPI(title="Panel de administración", lifespan=ciclo_de_vida)
app.add_middleware(
    SessionMiddleware,
    secret_key=CLAVE_SESION,
    max_age=8 * 60 * 60,  # la sesión dura 8 horas
    same_site="lax",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
plantillas = Jinja2Templates(directory=BASE_DIR / "templates")


def url_estatico(ruta: str) -> str:
    """URL de un archivo de /static con su fecha de modificación como versión.
    Así, cuando cambia un CSS o un JS, el navegador descarga el nuevo en vez de
    usar el que tenía guardado en caché."""
    try:
        version = int((BASE_DIR / "static" / ruta).stat().st_mtime)
    except OSError:
        version = 0
    return f"/static/{ruta}?v={version}"


plantillas.env.globals["estatico"] = url_estatico


def pagina(request: Request, nombre: str, contexto: dict, status_code: int = 200):
    """Renderiza una plantilla agregando siempre el usuario de la sesión."""
    contexto = {"usuario": usuario_actual(request), **contexto}
    return plantillas.TemplateResponse(request, nombre, contexto, status_code=status_code)


@app.exception_handler(NoAutenticado)
def redirigir_a_login(request: Request, exc: NoAutenticado):
    return RedirectResponse("/login", status_code=303)


app.include_router(rutas_documentos.crear_router(pagina))
app.include_router(rutas_contenido_web.crear_router(pagina))


@app.get("/")
def inicio(usuario: dict = Depends(requerir_usuario)):
    return RedirectResponse("/sitios", status_code=303)


LIMITES_TEXTO = {
    "nombre": ("El nombre", 200),
    "tipo": ("El tipo", 50),
    "direccion": ("La dirección", 255),
    "fuente": ("La fuente", 255),
    "acceso_tipo_piso": ("El tipo de piso", 50),
    "horario": ("El horario", 150),
    "costo_ingreso": ("El costo de ingreso", 100),
    "duracion_visita": ("La duración de la visita", 50),
}
NIVELES_RUIDO = ("bajo", "medio", "alto")
# Valor del formulario -> valor en la base. "Sin verificar" se guarda como NULL.
OPCIONES_BOOLEANAS = {"si": True, "no": False}


def a_texto(valor: str):
    """Texto limpio, o None si quedó vacío (así se guarda NULL, no una cadena vacía)."""
    return valor.strip() or None


def a_decimal(texto: str, minimo: int, maximo: int, nombre: str, campo: str, errores: dict):
    texto = texto.strip().replace(",", ".")
    if not texto:
        return None
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        errores[campo] = f"{nombre} debe ser un número, por ejemplo -17.393800."
        return None
    if not numero.is_finite() or not (minimo <= numero <= maximo):
        errores[campo] = f"{nombre} debe estar entre {minimo} y {maximo}."
        return None
    return numero


def validar_sitio(form: dict):
    """Valida el formulario. Devuelve (datos listos para la base, errores por campo)."""
    errores = {}
    datos = {}

    for campo, (etiqueta, maximo) in LIMITES_TEXTO.items():
        datos[campo] = a_texto(form[campo])
        if len(form[campo].strip()) > maximo:
            errores[campo] = f"{etiqueta} no puede pasar de {maximo} caracteres."

    for campo, etiqueta in (("nombre", "El nombre"), ("tipo", "El tipo"), ("descripcion", "La descripción")):
        if not form[campo].strip():
            errores[campo] = f"{etiqueta} es obligatorio."
    datos["descripcion"] = a_texto(form["descripcion"])
    # Capa general (la escribe la administradora; opcional, nunca se genera sola).
    for campo in ("relato", "que_ver", "servicios"):
        datos[campo] = a_texto(form[campo])

    datos["latitud"] = a_decimal(form["latitud"], -90, 90, "La latitud", "latitud", errores)
    datos["longitud"] = a_decimal(form["longitud"], -180, 180, "La longitud", "longitud", errores)

    # Campos de accesibilidad: solo lo que la administradora escribe o elige.
    # Lo que queda en blanco o "Sin verificar" se guarda como NULL, nunca como un valor supuesto.
    datos["acceso_descripcion_sensorial"] = a_texto(form["acceso_descripcion_sensorial"])
    datos["acceso_punto_referencia_entrada"] = a_texto(form["acceso_punto_referencia_entrada"])
    datos["acceso_recomendacion"] = a_texto(form["acceso_recomendacion"])
    datos["acceso_piso_tactil"] = OPCIONES_BOOLEANAS.get(form["acceso_piso_tactil"])
    datos["acceso_señalizacion_braille"] = OPCIONES_BOOLEANAS.get(form["acceso_senalizacion_braille"])
    datos["acceso_permite_perros_guia"] = OPCIONES_BOOLEANAS.get(form["acceso_permite_perros_guia"])

    ruido = form["acceso_nivel_ruido"].strip()
    if ruido and ruido not in NIVELES_RUIDO:
        errores["acceso_nivel_ruido"] = "Elige bajo, medio, alto o 'Sin verificar'."
    datos["acceso_nivel_ruido"] = ruido if ruido in NIVELES_RUIDO else None

    return datos, errores


def tipos_existentes():
    """Tipos ya usados, para sugerirlos en el campo 'Tipo' (no se inventa ninguno)."""
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT tipo FROM sitios_turisticos ORDER BY tipo")
            return [f[0] for f in cur.fetchall()]
    finally:
        conn.close()


CAMPOS_FORMULARIO = (
    "nombre", "tipo", "descripcion", "direccion", "latitud", "longitud", "fuente",
    "acceso_descripcion_sensorial", "acceso_punto_referencia_entrada", "acceso_tipo_piso",
    "acceso_piso_tactil", "acceso_senalizacion_braille", "acceso_permite_perros_guia",
    "acceso_nivel_ruido", "acceso_recomendacion",
    "relato", "que_ver", "horario", "costo_ingreso", "duracion_visita", "servicios",
)


def datos_verificacion(sitio_id: int):
    """Quién verificó el sitio y cuándo (trazabilidad), o None si no está verificado."""
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.nombre, s.fecha_verificacion
                FROM sitios_turisticos s
                LEFT JOIN usuarios u ON u.id = s.verificado_por
                WHERE s.id = %s AND s.estado = 'verificado'
                """,
                (sitio_id,),
            )
            fila = cur.fetchone()
    finally:
        conn.close()
    if fila is None:
        return None
    return {"nombre": fila[0], "fecha": fila[1].strftime("%d/%m/%Y %H:%M") if fila[1] else None}


def formulario_sitio(
    request: Request, valores: dict, errores: dict, status_code: int = 200,
    sitio_id: int = None, estado: str = None, resumen: str = None,
):
    """Muestra el formulario. Con sitio_id es edición; sin él, es un sitio nuevo.
    'resumen' reemplaza el texto del aviso de errores (se usa al verificar)."""
    editando = sitio_id is not None
    return pagina(
        request,
        "sitio_form.html",
        {
            "titulo": "Editar sitio" if editando else "Nuevo sitio",
            "v": valores,
            "errores": errores,
            "resumen": resumen,
            "tipos": tipos_existentes(),
            "accion": f"/sitios/{sitio_id}/editar" if editando else "/sitios/nuevo",
            "boton": "Guardar cambios" if editando else "Guardar como borrador",
            "es_nuevo": not editando,
            "sitio_id": sitio_id,
            "estado": estado,
            # Los mismos requisitos que exige verificar_sitio(); el nombre usa el del campo del formulario (sin ñ).
            "requisitos": [(c.replace("ñ", "n"), etiqueta) for c, etiqueta in REQUISITOS_VERIFICACION],
            "verificacion": datos_verificacion(sitio_id) if editando and estado == "verificado" else None,
        },
        status_code=status_code,
    )


def a_opcion(valor):
    """Valor de la base -> valor del formulario (True='si', False='no', NULL='')."""
    return "" if valor is None else ("si" if valor else "no")


def cargar_sitio(sitio_id: int):
    """Lee un sitio y lo devuelve como (valores del formulario, estado), o (None, None)."""
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT nombre, tipo, descripcion, direccion, latitud, longitud, fuente,
                       acceso_descripcion_sensorial, acceso_punto_referencia_entrada,
                       acceso_tipo_piso, acceso_piso_tactil, acceso_señalizacion_braille,
                       acceso_permite_perros_guia, acceso_nivel_ruido, acceso_recomendacion,
                       estado, relato, que_ver, horario, costo_ingreso, duracion_visita, servicios
                FROM sitios_turisticos WHERE id = %s
                """,
                (sitio_id,),
            )
            f = cur.fetchone()
    finally:
        conn.close()
    if f is None:
        return None, None

    texto = lambda x: "" if x is None else str(x)
    valores = {
        "nombre": f[0], "tipo": f[1], "descripcion": f[2], "direccion": texto(f[3]),
        "latitud": texto(f[4]), "longitud": texto(f[5]), "fuente": texto(f[6]),
        "acceso_descripcion_sensorial": texto(f[7]),
        "acceso_punto_referencia_entrada": texto(f[8]),
        "acceso_tipo_piso": texto(f[9]),
        "acceso_piso_tactil": a_opcion(f[10]),
        "acceso_senalizacion_braille": a_opcion(f[11]),
        "acceso_permite_perros_guia": a_opcion(f[12]),
        "acceso_nivel_ruido": texto(f[13]),
        "acceso_recomendacion": texto(f[14]),
        "relato": texto(f[16]), "que_ver": texto(f[17]), "horario": texto(f[18]),
        "costo_ingreso": texto(f[19]), "duracion_visita": texto(f[20]), "servicios": texto(f[21]),
    }
    return valores, f[15]


@app.get("/sitios/nuevo")
def formulario_nuevo(request: Request, usuario: dict = Depends(requerir_usuario)):
    return formulario_sitio(request, {}, {})


@app.post("/sitios/nuevo")
async def crear_sitio(request: Request, usuario: dict = Depends(requerir_usuario)):
    enviado = await request.form()
    form = {campo: str(enviado.get(campo, "")) for campo in CAMPOS_FORMULARIO}

    datos, errores = validar_sitio(form)
    if errores:
        return formulario_sitio(request, form, errores, status_code=400)

    datos["embedding"] = embeddings.calcular_embedding(datos)

    conn = conectar()
    try:
        with conn.cursor() as cur:
            # estado = 'borrador' siempre; los acceso_* van explícitos (NULL si no se verificó),
            # para que la base no rellene sus valores por defecto.
            cur.execute(
                """
                INSERT INTO sitios_turisticos (
                    nombre, tipo, descripcion, latitud, longitud, direccion, fuente,
                    acceso_descripcion_sensorial, acceso_punto_referencia_entrada,
                    acceso_tipo_piso, acceso_piso_tactil, acceso_señalizacion_braille,
                    acceso_permite_perros_guia, acceso_nivel_ruido, acceso_recomendacion,
                    relato, que_ver, horario, costo_ingreso, duracion_visita, servicios,
                    estado, embedding
                ) VALUES (
                    %(nombre)s, %(tipo)s, %(descripcion)s, %(latitud)s, %(longitud)s,
                    %(direccion)s, %(fuente)s,
                    %(acceso_descripcion_sensorial)s, %(acceso_punto_referencia_entrada)s,
                    %(acceso_tipo_piso)s, %(acceso_piso_tactil)s, %(acceso_señalizacion_braille)s,
                    %(acceso_permite_perros_guia)s, %(acceso_nivel_ruido)s, %(acceso_recomendacion)s,
                    %(relato)s, %(que_ver)s, %(horario)s, %(costo_ingreso)s,
                    %(duracion_visita)s, %(servicios)s,
                    'borrador', %(embedding)s
                )
                """,
                datos,
            )
        conn.commit()
    finally:
        conn.close()

    request.session["mensaje"] = f"Sitio «{datos['nombre']}» creado como borrador."
    return RedirectResponse("/sitios", status_code=303)


@app.get("/sitios/{sitio_id}/editar")
def formulario_editar(sitio_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
    valores, estado = cargar_sitio(sitio_id)
    if valores is None:
        return pagina(request, "no_encontrado.html", {"titulo": "Sitio no encontrado"}, status_code=404)
    return formulario_sitio(request, valores, {}, sitio_id=sitio_id, estado=estado)


@app.post("/sitios/{sitio_id}/editar")
async def guardar_edicion(sitio_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
    enviado = await request.form()
    form = {campo: str(enviado.get(campo, "")) for campo in CAMPOS_FORMULARIO}

    _, estado_anterior = cargar_sitio(sitio_id)
    if estado_anterior is None:
        return pagina(request, "no_encontrado.html", {"titulo": "Sitio no encontrado"}, status_code=404)

    datos, errores = validar_sitio(form)
    if errores:
        return formulario_sitio(
            request, form, errores, status_code=400, sitio_id=sitio_id, estado=estado_anterior
        )

    datos["id"] = sitio_id
    datos["embedding"] = embeddings.calcular_embedding(datos)

    conn = conectar()
    try:
        with conn.cursor() as cur:
            # Cualquier edición deja el sitio en 'borrador' y limpia la verificación:
            # lo que cambió ya no fue verificado. Hay que verificarlo de nuevo.
            cur.execute(
                """
                UPDATE sitios_turisticos SET
                    nombre = %(nombre)s, tipo = %(tipo)s, descripcion = %(descripcion)s,
                    latitud = %(latitud)s, longitud = %(longitud)s,
                    direccion = %(direccion)s, fuente = %(fuente)s,
                    acceso_descripcion_sensorial = %(acceso_descripcion_sensorial)s,
                    acceso_punto_referencia_entrada = %(acceso_punto_referencia_entrada)s,
                    acceso_tipo_piso = %(acceso_tipo_piso)s,
                    acceso_piso_tactil = %(acceso_piso_tactil)s,
                    acceso_señalizacion_braille = %(acceso_señalizacion_braille)s,
                    acceso_permite_perros_guia = %(acceso_permite_perros_guia)s,
                    acceso_nivel_ruido = %(acceso_nivel_ruido)s,
                    acceso_recomendacion = %(acceso_recomendacion)s,
                    relato = %(relato)s, que_ver = %(que_ver)s, horario = %(horario)s,
                    costo_ingreso = %(costo_ingreso)s, duracion_visita = %(duracion_visita)s,
                    servicios = %(servicios)s,
                    estado ='borrador', verificado_por = NULL, fecha_verificacion = NULL,
                    embedding = %(embedding)s, actualizado_en = now()
                WHERE id = %(id)s
                """,
                datos,
            )
        conn.commit()
    finally:
        conn.close()

    mensaje = f"Sitio «{datos['nombre']}» actualizado."
    if estado_anterior == "verificado":
        mensaje += " Estaba verificado, así que volvió a borrador y hay que verificarlo de nuevo."
    request.session["mensaje"] = mensaje
    return RedirectResponse("/sitios", status_code=303)


# Datos de accesibilidad que deben estar registrados de forma explícita para poder verificar.
# (campo, etiqueta, ¿es booleano?). acceso_recomendacion es opcional.
REQUISITOS_VERIFICACION = (
    ("acceso_descripcion_sensorial", "Descripción sensorial"),
    ("acceso_punto_referencia_entrada", "Punto de referencia de la entrada"),
    ("acceso_tipo_piso", "Tipo de piso"),
    ("acceso_piso_tactil", "Piso táctil (elige Sí o No)"),
    ("acceso_señalizacion_braille", "Señalización en braille (elige Sí o No)"),
    ("acceso_permite_perros_guia", "Perros guía (elige Sí o No)"),
    ("acceso_nivel_ruido", "Nivel de ruido"),
)


@app.post("/sitios/{sitio_id}/verificar")
def verificar_sitio(sitio_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
    """Marca el sitio como verificado, con quién lo verificó y cuándo.
    Verifica lo que está GUARDADO en la base, no lo que haya en pantalla sin guardar."""
    columnas = ", ".join(c for c, _ in REQUISITOS_VERIFICACION)
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT nombre, estado, embedding IS NOT NULL, {columnas} "
                "FROM sitios_turisticos WHERE id = %s FOR UPDATE",
                (sitio_id,),
            )
            fila = cur.fetchone()
            if fila is None:
                return pagina(request, "no_encontrado.html", {"titulo": "Sitio no encontrado"}, status_code=404)
            nombre, estado, tiene_embedding = fila[0], fila[1], fila[2]

            if estado == "verificado":
                request.session["mensaje"] = f"El sitio «{nombre}» ya estaba verificado."
                return RedirectResponse("/sitios", status_code=303)

            # La clave es el nombre del campo del formulario (sin ñ), para que el enlace
            # del aviso de errores lleve al campo correcto.
            errores = {
                campo.replace("ñ", "n"): f"Falta registrar: {etiqueta}."
                for (campo, etiqueta), valor in zip(REQUISITOS_VERIFICACION, fila[3:])
                if valor is None or (isinstance(valor, str) and not valor.strip())
            }
            if not tiene_embedding:
                errores["nombre"] = "El sitio no tiene embedding. Guarda el sitio de nuevo para generarlo."

            if not errores:
                cur.execute(
                    """
                    UPDATE sitios_turisticos
                    SET estado = 'verificado', verificado_por = %s, fecha_verificacion = now()
                    WHERE id = %s
                    """,
                    (usuario["id"], sitio_id),
                )
        if not errores:
            conn.commit()
    finally:
        conn.close()

    if errores:
        valores, estado = cargar_sitio(sitio_id)
        return formulario_sitio(
            request, valores, errores, status_code=400, sitio_id=sitio_id, estado=estado,
            resumen=f"No se puede verificar todavía. Faltan {len(errores)} dato{'s' if len(errores) > 1 else ''}:",
        )

    request.session["mensaje"] = f"Sitio «{nombre}» verificado. Ya es visible para el asistente."
    return RedirectResponse("/sitios", status_code=303)


@app.get("/sitios")
def lista_sitios(
    request: Request,
    estado: str = None,
    q: str = None,
    usuario: dict = Depends(requerir_usuario),
):
    """Lista de sitios. Filtros opcionales por URL: ?estado=borrador|verificado y ?q=texto."""
    mensaje = request.session.pop("mensaje", None)

    filtro = estado if estado in ("borrador", "verificado") else None  # cualquier otro valor se ignora
    q = (q or "").strip()[:100]
    # En LIKE, % y _ son comodines: se escapan para buscar el texto tal cual lo escribió el usuario.
    patron = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

    conn = conectar()
    try:
        with conn.cursor() as cur:
            # Los totales no dependen de los filtros: sirven de resumen de todo el catálogo.
            cur.execute("SELECT estado, count(*) FROM sitios_turisticos GROUP BY estado")
            por_estado = dict(cur.fetchall())

            # Todos los valores van como parámetros (%(nombre)s), nunca pegados al SQL.
            cur.execute(
                """
                SELECT id, nombre, tipo, estado FROM sitios_turisticos
                WHERE (%(filtro)s::text IS NULL OR estado = %(filtro)s)
                  AND (%(q)s = '' OR nombre ILIKE %(patron)s)
                ORDER BY nombre
                """,
                {"filtro": filtro, "q": q, "patron": patron},
            )
            sitios = [
                {"id": f[0], "nombre": f[1], "tipo": f[2], "estado": f[3]}
                for f in cur.fetchall()
            ]
    finally:
        conn.close()

    conteos = {
        "total": sum(por_estado.values()),
        "verificado": por_estado.get("verificado", 0),
        "borrador": por_estado.get("borrador", 0),
    }

    def enlace(nuevo_estado):
        """Enlace a la lista con el estado elegido, conservando la búsqueda."""
        parametros = {}
        if nuevo_estado:
            parametros["estado"] = nuevo_estado
        if q:
            parametros["q"] = q
        return "/sitios" + ("?" + urlencode(parametros) if parametros else "")

    return pagina(
        request,
        "sitios.html",
        {
            "titulo": "Sitios turísticos",
            "sitios": sitios,
            "mensaje": mensaje,
            "conteos": conteos,
            "filtro": filtro,
            "q": q,
            "enlaces": {"todos": enlace(None), "verificado": enlace("verificado"), "borrador": enlace("borrador")},
        },
    )


# ---------------------------------------------------------------------------
# Eventos del calendario (ferias, festividades, feriados). Sin IA: solo fecha y zona.
# La tabla `eventos` ya existía; no cambia el esquema. Cualquier administradora con sesión
# puede crear, editar y eliminar eventos.
# ---------------------------------------------------------------------------
TIPOS_EVENTO = ("feria", "festividad", "feriado")
LIMITES_EVENTO = {
    "nombre": ("El nombre", 200),
    "tipo": ("El tipo", 50),
    "zona": ("La zona", 150),
}
CAMPOS_EVENTO = (
    "nombre", "tipo", "descripcion", "fecha_inicio", "fecha_fin", "zona",
    "hora_inicio", "hora_fin", "latitud", "longitud",
)
FILTROS_EVENTO = ("proximos", "pasados", "todos")
# "Hoy" según la hora de Bolivia (el servidor puede estar en otra zona horaria).
HOY_BOLIVIA = "(now() AT TIME ZONE 'America/La_Paz')::date"


def a_fecha(texto: str, campo: str, etiqueta: str, errores: dict, obligatoria: bool = False):
    """Texto 'AAAA-MM-DD' (lo que envía <input type="date">) -> date, o None si está vacío o es inválido."""
    texto = texto.strip()
    if not texto:
        if obligatoria:
            errores[campo] = f"{etiqueta} es obligatoria."
        return None
    try:
        fecha = date.fromisoformat(texto)
    except ValueError:
        errores[campo] = f"{etiqueta} no es una fecha válida."
        return None
    if not (1900 <= fecha.year <= 2100):
        errores[campo] = f"{etiqueta} debe estar entre los años 1900 y 2100."
        return None
    return fecha


def a_hora(texto: str, campo: str, etiqueta: str, errores: dict):
    """Texto 'HH:MM' (lo que envía <input type="time">) -> time, o None si está vacío o es inválido."""
    texto = texto.strip()
    if not texto:
        return None
    try:
        return time.fromisoformat(texto)
    except ValueError:
        errores[campo] = f"{etiqueta} no es una hora válida (ejemplo: 18:30)."
        return None


def validar_evento(form: dict):
    """Valida el formulario de un evento. Devuelve (datos listos para la base, errores por campo)."""
    errores = {}
    datos = {}

    for campo, (etiqueta, maximo) in LIMITES_EVENTO.items():
        datos[campo] = a_texto(form[campo])
        if len(form[campo].strip()) > maximo:
            errores[campo] = f"{etiqueta} no puede pasar de {maximo} caracteres."
    if not form["nombre"].strip():
        errores["nombre"] = "El nombre es obligatorio."
    datos["descripcion"] = a_texto(form["descripcion"])

    datos["fecha_inicio"] = a_fecha(form["fecha_inicio"], "fecha_inicio", "La fecha de inicio", errores, obligatoria=True)
    datos["fecha_fin"] = a_fecha(form["fecha_fin"], "fecha_fin", "La fecha de fin", errores)
    if datos["fecha_inicio"] and datos["fecha_fin"] and datos["fecha_fin"] < datos["fecha_inicio"]:
        errores["fecha_fin"] = "La fecha de fin no puede ser anterior a la de inicio."

    datos["hora_inicio"] = a_hora(form["hora_inicio"], "hora_inicio", "La hora de inicio", errores)
    datos["hora_fin"] = a_hora(form["hora_fin"], "hora_fin", "La hora de fin", errores)
    datos["latitud"] = a_decimal(form["latitud"], -90, 90, "La latitud", "latitud", errores)
    datos["longitud"] = a_decimal(form["longitud"], -180, 180, "La longitud", "longitud", errores)
    if (datos["latitud"] is None) != (datos["longitud"] is None) and "latitud" not in errores and "longitud" not in errores:
        errores["latitud"] = "Escribe la latitud y la longitud juntas, o deja las dos en blanco."

    return datos, errores


def formulario_evento(request: Request, valores: dict, errores: dict, status_code: int = 200, evento_id: int = None):
    """Muestra el formulario de eventos. Con evento_id es edición; sin él, es un evento nuevo."""
    editando = evento_id is not None
    tipo_actual = valores.get("tipo", "")
    # Si el evento tiene un tipo fuera de la lista, se conserva como opción para no perderlo al guardar.
    tipos = list(TIPOS_EVENTO) + ([tipo_actual] if tipo_actual and tipo_actual not in TIPOS_EVENTO else [])
    return pagina(
        request,
        "evento_form.html",
        {
            "titulo": "Editar evento" if editando else "Nuevo evento",
            "v": valores,
            "errores": errores,
            "tipos": tipos,
            "accion": f"/eventos/{evento_id}/editar" if editando else "/eventos/nuevo",
            "boton": "Guardar cambios" if editando else "Guardar evento",
            "evento_id": evento_id,
        },
        status_code=status_code,
    )


def cargar_evento(evento_id: int):
    """Lee un evento y lo devuelve como valores del formulario, o None si no existe."""
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT nombre, tipo, descripcion, fecha_inicio, fecha_fin, zona, "
                "to_char(hora_inicio, 'HH24:MI'), to_char(hora_fin, 'HH24:MI'), latitud, longitud "
                "FROM eventos WHERE id = %s",
                (evento_id,),
            )
            f = cur.fetchone()
    finally:
        conn.close()
    if f is None:
        return None
    texto = lambda x: "" if x is None else str(x)
    return {
        "nombre": f[0], "tipo": texto(f[1]), "descripcion": texto(f[2]),
        "fecha_inicio": texto(f[3]), "fecha_fin": texto(f[4]), "zona": texto(f[5]),
        "hora_inicio": texto(f[6]), "hora_fin": texto(f[7]),
        "latitud": texto(f[8]), "longitud": texto(f[9]),
    }


@app.get("/eventos")
def lista_eventos(request: Request, cuando: str = None, usuario: dict = Depends(requerir_usuario)):
    """Lista de eventos. Filtro por URL: ?cuando=proximos|pasados|todos (por defecto, los próximos)."""
    mensaje = request.session.pop("mensaje", None)
    filtro = cuando if cuando in FILTROS_EVENTO else "proximos"

    conn = conectar()
    try:
        with conn.cursor() as cur:
            # Un evento es "próximo" si todavía no terminó (hoy cuenta). Sin fecha de fin, dura un día.
            cur.execute(
                f"""
                SELECT count(*),
                       count(*) FILTER (WHERE COALESCE(fecha_fin, fecha_inicio) >= {HOY_BOLIVIA}),
                       count(*) FILTER (WHERE COALESCE(fecha_fin, fecha_inicio) < {HOY_BOLIVIA})
                FROM eventos
                """
            )
            total, proximos, pasados = cur.fetchone()

            cur.execute(
                f"""
                SELECT id, nombre, tipo, fecha_inicio, fecha_fin, zona,
                       COALESCE(fecha_fin, fecha_inicio) < {HOY_BOLIVIA} AS paso
                FROM eventos
                WHERE %(filtro)s = 'todos'
                   OR (%(filtro)s = 'proximos' AND COALESCE(fecha_fin, fecha_inicio) >= {HOY_BOLIVIA})
                   OR (%(filtro)s = 'pasados'  AND COALESCE(fecha_fin, fecha_inicio) <  {HOY_BOLIVIA})
                ORDER BY CASE WHEN %(filtro)s = 'pasados' THEN NULL ELSE fecha_inicio END ASC,
                         fecha_inicio DESC, nombre
                """,
                {"filtro": filtro},
            )
            filas = cur.fetchall()
    finally:
        conn.close()

    def dia(fecha):
        return fecha.strftime("%d/%m/%Y")

    eventos = [
        {
            "id": f[0], "nombre": f[1], "tipo": f[2] or "",
            "fechas": dia(f[3]) if not f[4] or f[4] == f[3] else f"{dia(f[3])} al {dia(f[4])}",
            "zona": f[5] or "", "paso": f[6],
        }
        for f in filas
    ]
    return pagina(
        request,
        "eventos.html",
        {
            "titulo": "Eventos",
            "eventos": eventos,
            "mensaje": mensaje,
            "filtro": filtro,
            "conteos": {"todos": total, "proximos": proximos, "pasados": pasados},
        },
    )


@app.get("/eventos/nuevo")
def formulario_evento_nuevo(request: Request, usuario: dict = Depends(requerir_usuario)):
    return formulario_evento(request, {}, {})


@app.post("/eventos/nuevo")
async def crear_evento(request: Request, usuario: dict = Depends(requerir_usuario)):
    enviado = await request.form()
    form = {campo: str(enviado.get(campo, "")) for campo in CAMPOS_EVENTO}

    datos, errores = validar_evento(form)
    if errores:
        return formulario_evento(request, form, errores, status_code=400)

    datos["creado_por"] = usuario["id"]
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO eventos (nombre, descripcion, tipo, fecha_inicio, fecha_fin, zona, creado_por,
                                     hora_inicio, hora_fin, latitud, longitud)
                VALUES (%(nombre)s, %(descripcion)s, %(tipo)s, %(fecha_inicio)s, %(fecha_fin)s, %(zona)s, %(creado_por)s,
                        %(hora_inicio)s, %(hora_fin)s, %(latitud)s, %(longitud)s)
                """,
                datos,
            )
        conn.commit()
    finally:
        conn.close()

    request.session["mensaje"] = f"Evento «{datos['nombre']}» creado."
    return RedirectResponse("/eventos?cuando=todos", status_code=303)


@app.get("/eventos/{evento_id}/editar")
def formulario_evento_editar(evento_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
    valores = cargar_evento(evento_id)
    if valores is None:
        return pagina(request, "no_encontrado.html", {"titulo": "Evento no encontrado"}, status_code=404)
    return formulario_evento(request, valores, {}, evento_id=evento_id)


@app.post("/eventos/{evento_id}/editar")
async def guardar_evento(evento_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
    if cargar_evento(evento_id) is None:
        return pagina(request, "no_encontrado.html", {"titulo": "Evento no encontrado"}, status_code=404)

    enviado = await request.form()
    form = {campo: str(enviado.get(campo, "")) for campo in CAMPOS_EVENTO}
    datos, errores = validar_evento(form)
    if errores:
        return formulario_evento(request, form, errores, status_code=400, evento_id=evento_id)

    datos["id"] = evento_id
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE eventos SET nombre = %(nombre)s, descripcion = %(descripcion)s, tipo = %(tipo)s,
                    fecha_inicio = %(fecha_inicio)s, fecha_fin = %(fecha_fin)s, zona = %(zona)s,
                    hora_inicio = %(hora_inicio)s, hora_fin = %(hora_fin)s,
                    latitud = %(latitud)s, longitud = %(longitud)s
                WHERE id = %(id)s
                """,
                datos,
            )
        conn.commit()
    finally:
        conn.close()

    request.session["mensaje"] = f"Evento «{datos['nombre']}» actualizado."
    return RedirectResponse("/eventos?cuando=todos", status_code=303)


@app.post("/eventos/{evento_id}/eliminar")
def eliminar_evento(evento_id: int, request: Request, usuario: dict = Depends(requerir_usuario)):
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM eventos WHERE id = %s RETURNING nombre", (evento_id,))
            fila = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    if fila is None:
        return pagina(request, "no_encontrado.html", {"titulo": "Evento no encontrado"}, status_code=404)
    request.session["mensaje"] = f"Evento «{fila[0]}» eliminado."
    return RedirectResponse("/eventos?cuando=todos", status_code=303)


@app.get("/login")
def formulario_login(request: Request):
    if usuario_actual(request):
        return RedirectResponse("/sitios", status_code=303)
    return pagina(request, "login.html", {"titulo": "Iniciar sesión", "error": None})


@app.post("/login")
def iniciar_sesion(request: Request, email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()

    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, nombre, rol, password_hash FROM usuarios WHERE lower(email) = %s",
                (email,),
            )
            fila = cur.fetchone()
    finally:
        conn.close()

    password_hash = fila[3] if fila else HASH_RELLENO
    correcta = verificar_password(password, password_hash)

    if not fila or not correcta:
        # Mensaje genérico: no revela si el email existe o no.
        return pagina(
            request,
            "login.html",
            {"titulo": "Iniciar sesión", "error": "Correo o contraseña incorrectos.", "email": email},
            status_code=401,
        )

    request.session.clear()
    request.session["usuario"] = {"id": fila[0], "nombre": fila[1], "rol": fila[2]}
    return RedirectResponse("/sitios", status_code=303)


@app.post("/logout")
def cerrar_sesion(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/salud")
def salud():
    """Prueba de conexión a la base. Útil para verificar que Docker llega a Postgres."""
    try:
        conn = conectar()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM sitios_turisticos")
                total = cur.fetchone()[0]
        finally:
            conn.close()
        return {
            "base_de_datos": "ok",
            "sitios": total,
            "modelo_embeddings": embeddings.modelo_cargado(),
        }
    except Exception as error:
        return JSONResponse(
            status_code=503,
            content={"base_de_datos": "error", "detalle": str(error)},
        )
