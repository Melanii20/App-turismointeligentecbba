"""Ejecuta las filas AUTOMATIZABLES de docs/guia_pruebas.md (secciones 1 a 8, 12 y 14) contra /api/consulta.

Guarda el contexto entre turnos e imprime PASA, FALLA (con el motivo), NO EJECUTABLE o MANUAL por cada fila.
Escribe el resultado en docs/resultado_probar_guia.md.

Cómo se ejecuta (desde C:\\tesis):

    docker compose run --rm backend python pruebas/probar_guia.py

Usa el backend en el mismo proceso (TestClient), con la configuración real del .env: si hay clave de Gemini
se hacen llamadas reales (las filas del clasificador la necesitan); si hay clave de Tavily, también se gastan
créditos. Nunca imprime claves ni las guarda.

Las filas que necesitan la app, el teléfono o el panel (5.3, 5.4, 6.4, 6.5, 7.3, 9, 10, 11, 12.3, 13, 15) son
PRUEBAS MANUALES y aquí solo se listan.

Las filas que nombran a «Cristo de la Concordia», «La Cancha» o «Convento de Santa Teresa» exigen que esos sitios
estén VERIFICADOS. Si siguen en borrador (sus datos acceso_* no se pueden inventar), la fila queda «NO EJECUTABLE» y
se corre además una variante equivalente con un sitio de prueba ya verificado (fila «b»).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
for ruta in (RAIZ / "asistente", RAIZ):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))
os.chdir(RAIZ / "asistente")
# El límite de 20 consultas por minuto se prueba aparte (12.4); en el resto se sube para no estorbar.
os.environ["LIMITE_CONSULTAS"] = "1000/minute"

from fastapi.testclient import TestClient  # noqa: E402

import config  # noqa: E402
from db import conectar  # noqa: E402

PLAZA = (-17.3935, -66.1570)
RESULTADOS = []        # (id, pregunta o acción, estado, detalle)


def registrar(fila, que, estado, detalle=""):
    RESULTADOS.append((fila, que, estado, detalle))
    print(f"[{estado:<13}] {fila:<5} {que[:70]}" + (f"  -> {detalle}" if detalle and estado != "PASA" else ""))


class Sesion:
    """Una conversación: guarda el contexto entre turnos, como hace la app."""

    def __init__(self, cliente):
        self.cliente, self.contexto = cliente, {"turnos": [], "ultimo_sitio_id": None, "accion_pendiente": None}

    def preguntar(self, texto, ubicacion=None, reintentos=0):
        cuerpo = {"pregunta": texto, "canal": "app", "contexto": self.contexto}
        if ubicacion:
            cuerpo["latitud"], cuerpo["longitud"] = ubicacion
        for intento in range(reintentos + 1):
            r = self.cliente.post("/api/consulta", json=cuerpo)
            if r.status_code != 200:
                raise AssertionError(f"HTTP {r.status_code}: {r.text[:200]}")
            datos = r.json()
            if reintentos and not datos["uso_llm"] and intento < reintentos:
                time.sleep(6)                    # la cuota gratuita de Gemini es por minuto: se reintenta
                continue
            break
        self.contexto = datos["contexto"]
        # La acción pendiente viaja dentro de «contexto» (contrato de la API); los créditos de Tavily, el eje del dato
        # y el motivo sin LLM no se devuelven a la app: se leen de la fila de métricas que acaba de guardar esta consulta.
        datos["accion_pendiente"] = datos["contexto"].get("accion_pendiente")
        f = sql("SELECT eje_dato, creditos_tavily, motivo_sin_llm FROM metricas_consulta ORDER BY id DESC LIMIT 1")
        datos["eje_dato"], datos["creditos_tavily"], datos["motivo_sin_llm"] = f[0] if f else (None, 0, None)
        return datos


def fila(id_, que, comprobacion, preguntas, ubicacion=None, reintentos=0, cliente=None):
    """Ejecuta una fila. 'preguntas' es la lista de turnos; 'comprobacion(respuestas)' devuelve None si PASA o el motivo."""
    try:
        s = Sesion(cliente)
        respuestas = [s.preguntar(p, ubicacion, reintentos) for p in preguntas]
        motivo = comprobacion(*respuestas)
    except AssertionError as e:
        registrar(id_, que, "FALLA", str(e))
        return
    except Exception as e:                        # un error inesperado también es un fallo, con su mensaje
        registrar(id_, que, "FALLA", f"{type(e).__name__}: {str(e)[:200]}")
        return
    registrar(id_, que, "PASA" if motivo is None else "FALLA", motivo or "")


def sql(consulta, parametros=None):
    con = conectar()
    try:
        with con.cursor() as cur:
            cur.execute(consulta, parametros)
            filas = cur.fetchall() if cur.description else []
        con.commit()
        return filas
    finally:
        con.close()


def esta_verificado(nombre):
    f = sql("SELECT estado FROM sitios_turisticos WHERE nombre = %s", (nombre,))
    return bool(f) and f[0][0] == "verificado"


def fila_con_sitio(id_, que, sitio, comprobacion, preguntas, variante=None, **kw):
    """Fila que nombra un sitio de la guía: si está en borrador, NO EJECUTABLE + variante con un sitio verificado."""
    if esta_verificado(sitio):
        fila(id_, que, comprobacion, preguntas, **kw)
        return
    registrar(id_, que, "NO EJECUTABLE", f"«{sitio}» está en borrador (no se pueden inventar sus datos acceso_*)")
    if variante:
        fila(id_ + "b", variante[0], comprobacion, variante[1], **kw)


def requiere(condicion, texto):
    assert condicion, texto


def ejecutar():
    from main import app
    con_llm = bool(config.LLM_API_KEY) and config.LLM_PROVEEDOR in ("google", "gemini")
    con_tavily = bool(config.TAVILY_API_KEY)
    print(f"Gemini configurado: {con_llm} | Tavily configurado: {con_tavily} | Wikipedia (contacto): {bool(config.WIKIPEDIA_CONTACTO)}\n")

    with TestClient(app) as cliente:
        # ---------------- 1. Orquestador ----------------
        def c11(r):
            requiere(r["intencion"] == "ayuda" and r["uso_llm"] is False and "Por ejemplo" in r["respuesta"], f"intencion={r['intencion']} uso_llm={r['uso_llm']}")
        fila("1.1", "¿Qué puedes hacer?", c11, ["¿Qué puedes hacer?"], cliente=cliente)

        def c12(r):
            requiere(r["intencion"] == "fuera_de_alcance" and r["uso_llm"] is False, f"intencion={r['intencion']}")
        fila("1.2", "¿Quién ganó el partido de ayer?", c12, ["¿Quién ganó el partido de ayer?"], cliente=cliente)

        def c13(r):
            requiere(r["respuesta"] == "¿A qué lugar te refieres?", r["respuesta"])
        fila("1.3", "¿Qué horario tiene? (sin sitio)", c13, ["¿Qué horario tiene?"], cliente=cliente)

        def c14(r):
            requiere(r["nivel_fuente"] not in ("web", "cache_web") and r["creditos_tavily"] == 0 and "No tengo" in r["respuesta"], f"nivel={r['nivel_fuente']} | {r['respuesta'][:100]}")
            requiere(r["eje_dato"] == "operativo", f"eje={r['eje_dato']}")
        fila("1.4", "¿Cuánto cuesta un silpancho?", c14, ["¿Cuánto cuesta un silpancho?"], cliente=cliente)

        def c15(r):
            requiere("No tengo ese dato verificado" in r["respuesta"] or "En mi base verificada tengo" in r["respuesta"], f"parte operativa ausente: {r['respuesta'][:160]}")
            requiere(r["acciones"] == [] and r["accion_pendiente"] is None, "una compuesta no debe dejar acciones")
            requiere(r["nivel_fuente"] in ("web", "cache_web", "base", "documento", "ninguna"), r["nivel_fuente"])
        fila("1.5", "¿Qué es la chicha y dónde la puedo probar?", c15, ["¿Qué es la chicha y dónde la puedo probar?"], cliente=cliente)

        # ---------------- 2. Clasificador ----------------
        def c21(r):
            requiere(r["intencion"] == "saberes" and r["uso_llm"] is True, f"intencion={r['intencion']} uso_llm={r['uso_llm']} motivo={r.get('motivo_sin_llm')}")
        fila("2.1", "Me da curiosidad lo que comen los cochabambinos", c21, ["Me da curiosidad lo que comen los cochabambinos"], reintentos=2, cliente=cliente)

        def c22(r):
            requiere(r["intencion"] in ("itinerario", "cercania") and r["uso_llm"] is True, f"intencion={r['intencion']} uso_llm={r['uso_llm']}")
        fila("2.2", "Quiero conocer algo bonito para pasear", c22, ["Quiero conocer algo bonito para pasear"], ubicacion=PLAZA, reintentos=2, cliente=cliente)

        # ---------------- 3. Agente de sitios ----------------
        def c31(r):
            requiere(r["nivel_fuente"] == "base" and "verificaci" in r["respuesta"].lower(), f"nivel={r['nivel_fuente']} | {r['respuesta'][:120]}")
        fila_con_sitio("3.1", "Cuéntame del Cristo de la Concordia", "Cristo de la Concordia", c31, ["Cuéntame del Cristo de la Concordia"],
                       variante=("Cuéntame de la Catedral Metropolitana", ["Cuéntame de la Catedral Metropolitana"]), cliente=cliente)

        def c32(r):
            requiere(r["eje_dato"] == "operativo" and r["nivel_fuente"] != "web", "debe ser operativo y sin web")
            requiere("piso táctil" in r["respuesta"].lower() or "no tengo" in r["respuesta"].lower(), r["respuesta"][:120])
        fila_con_sitio("3.2", "¿El Cristo tiene piso táctil?", "Cristo de la Concordia", c32, ["¿El Cristo tiene piso táctil?"],
                       variante=("¿La Catedral Metropolitana tiene piso táctil?", ["¿La Catedral Metropolitana tiene piso táctil?"]), cliente=cliente)

        def c33(r):
            requiere(r["eje_dato"] == "operativo" and ("ruido" in r["respuesta"].lower() or "ruidos" in r["respuesta"].lower() or "no tengo" in r["respuesta"].lower() or "silencio" in r["respuesta"].lower() or "tranquil" in r["respuesta"].lower()), r["respuesta"][:140])
        fila_con_sitio("3.3", "¿La Cancha es ruidosa?", "La Cancha", c33, ["¿La Cancha es ruidosa?"],
                       variante=("¿El Mercado 25 de Mayo es ruidoso?", ["¿El Mercado 25 de Mayo es ruidoso?"]), cliente=cliente)

        def c34(r):
            bajos = {f[0] for f in sql("SELECT nombre FROM sitios_turisticos WHERE estado = 'verificado' AND acceso_nivel_ruido = 'bajo'")}
            altos = {f[0] for f in sql("SELECT nombre FROM sitios_turisticos WHERE estado = 'verificado' AND acceso_nivel_ruido <> 'bajo'")}
            requiere(any(n in r["respuesta"] for n in bajos) and not any(n in r["respuesta"] for n in altos), f"sitios devueltos no son todos de ruido bajo: {r['respuesta'][:160]}")
        fila("3.4", "Busco un lugar tranquilo", c34, ["Busco un lugar tranquilo"], cliente=cliente)

        def c35(r):
            requiere(r["respuesta"].startswith("No tengo información sobre Museo del Louvre") and "Puedo contarte de" in r["respuesta"] and "mejor encaja" not in r["respuesta"], r["respuesta"][:160])
            requiere(r["nivel_fuente"] == "ninguna", r["nivel_fuente"])
        fila("3.5", "Cuéntame del Museo del Louvre", c35, ["Cuéntame del Museo del Louvre"], cliente=cliente)

        # ---------------- 4. Agente de saberes ----------------
        def c41(r):
            requiere(r["nivel_fuente"] == "documento" and r["creditos_tavily"] == 0, f"nivel={r['nivel_fuente']} créditos={r['creditos_tavily']}")
            requiere("Guía de prueba de Cochabamba (FICTICIO)" in r["respuesta"] and "página" in r["respuesta"], "falta título o página en la cita")
        fila("4.1", "Cuéntame la leyenda de la piedra que canta", c41, ["Cuéntame la leyenda de la piedra que canta"], cliente=cliente)

        # La caché de «silpancho» se limpia para que 4.2 sea de verdad la primera vez (son páginas de internet guardadas, se recrean solas).
        borradas = sql("DELETE FROM contenido_web WHERE lower(titulo || ' ' || texto) LIKE '%silpancho%' RETURNING id")
        print(f"      (se limpió la caché web de «silpancho»: {len(borradas)} filas)")

        def c42(r):
            requiere(r["nivel_fuente"] == "web" and "información de internet" in r["respuesta"], f"nivel={r['nivel_fuente']} | {r['respuesta'][:140]}")
            if con_tavily:
                requiere(r["creditos_tavily"] == 1, f"créditos={r['creditos_tavily']}")
        if con_tavily:
            fila("4.2", "¿Qué es el silpancho? (primera vez)", c42, ["¿Qué es el silpancho?"], cliente=cliente)
        else:
            registrar("4.2", "¿Qué es el silpancho? (primera vez)", "NO EJECUTABLE", "falta TAVILY_API_KEY: no se puede verificar «1 crédito»")
            fila("4.2b", "¿Qué es el silpancho? (Wikipedia directa, sin Tavily)", c42, ["¿Qué es el silpancho?"], cliente=cliente)

        def c43(r):
            requiere(r["nivel_fuente"] == "cache_web" and r["creditos_tavily"] == 0, f"nivel={r['nivel_fuente']} créditos={r['creditos_tavily']}")
        fila("4.3", "¿Qué es el silpancho? (segunda vez)", c43, ["¿Qué es el silpancho?"], cliente=cliente)

        def c44(r):
            requiere(r["intencion"] == "saberes" and r["nivel_fuente"] in ("web", "cache_web", "documento", "base"), f"intencion={r['intencion']} nivel={r['nivel_fuente']} | {r['respuesta'][:120]}")
            requiere("Según" in r["respuesta"] or "según" in r["respuesta"], "la respuesta no cita su fuente")
        fila("4.4", "¿De dónde viene la fiesta de Urkupiña?", c44, ["¿De dónde viene la fiesta de Urkupiña?"], cliente=cliente)

        def c45(r):
            requiere(r["intencion"] == "eventos" and r["nivel_fuente"] in ("base", "ninguna") and r["fuente"] != "wikipedia", f"intencion={r['intencion']} nivel={r['nivel_fuente']}")
            requiere(r["creditos_tavily"] == 0, "no debe gastar créditos")
        fila("4.5", "¿Cuándo es Urkupiña?", c45, ["¿Cuándo es Urkupiña?"], cliente=cliente)

        def c46(r):
            requiere(r["intencion"] == "saberes", f"intencion={r['intencion']}")
            requiere("información de internet" in r["respuesta"] or "según" in r["respuesta"].lower() or r["respuesta"].startswith("No tengo información"), r["respuesta"][:140])
        fila("4.6", "¿Cómo se dice gracias en quechua?", c46, ["¿Cómo se dice gracias en quechua?"], cliente=cliente)

        def c47(r1, r2):
            requiere(r1["nivel_fuente"] == "base" and r1["respuesta"].endswith("¿Quieres saber más?") and r1["escuchar_despues"] is True, f"primer turno: nivel={r1['nivel_fuente']}")
            requiere(r1["accion_pendiente"] and r1["accion_pendiente"]["tipo"] == "mas_informacion", "falta la acción pendiente")
            requiere(r2["nivel_fuente"] in ("web", "cache_web"), f"segundo turno: nivel={r2['nivel_fuente']} | {r2['respuesta'][:120]}")
        if esta_verificado("Cristo de la Concordia"):
            fila("4.7", "Cuéntame la historia del Cristo → sí", c47, ["Cuéntame la historia del Cristo de la Concordia", "sí"], cliente=cliente)
        else:
            registrar("4.7", "Cuéntame la historia del Cristo → sí", "NO EJECUTABLE", "«Cristo de la Concordia» está en borrador")
            fila("4.7b", "Cuéntame la historia de la Catedral Metropolitana → sí", c47,
                 ["Cuéntame la historia de la Catedral Metropolitana", "sí"], cliente=cliente)

        # 4.8: prueba automática (pytest) de que la web no se abre antes que la base
        r = subprocess.run([sys.executable, "-m", "pytest", str(RAIZ / "pruebas" / "test_agentes.py"), "-q", "-k", "antes_de_la_base or despues_de_base", "-p", "no:cacheprovider"],
                           capture_output=True, text=True)
        registrar("4.8", "agente_saberes no puede usar la web antes de la base", "PASA" if r.returncode == 0 else "FALLA", r.stdout[-300:])

        # ---------------- 5. Eventos ----------------
        def c51(r):
            requiere(r["intencion"] == "eventos" and r["fuente"] in ("base_verificada", "sistema") and r["uso_llm"] is False, f"intencion={r['intencion']}")
            requiere("Eventos" in r["respuesta"] or "No tengo eventos registrados" in r["respuesta"], r["respuesta"][:120])
        fila("5.1", "¿Qué hay hoy?", c51, ["¿Qué hay hoy?"], ubicacion=PLAZA, cliente=cliente)
        hoy = cliente.get("/api/eventos/hoy", params={"latitud": PLAZA[0], "longitud": PLAZA[1]})
        registrar("5.1b", "GET /api/eventos/hoy", "PASA" if hoy.status_code == 200 and "eventos" in hoy.json() else "FALLA", f"HTTP {hoy.status_code}")

        def c52(r):
            requiere(r["intencion"] == "eventos" and r["uso_llm"] is False, f"intencion={r['intencion']}")
        fila("5.2", "¿Qué fiestas hay este fin de semana?", c52, ["¿Qué fiestas hay este fin de semana?"], cliente=cliente)
        registrar("5.3", "Abrir la app (tarjeta Hoy)", "MANUAL", "necesita la app")
        registrar("5.4", "Tocar «Escuchar eventos de hoy»", "MANUAL", "necesita la app")

        # ---------------- 6. Movilidad ----------------
        def c61(r):
            requiere(r["intencion"] == "como_llegar" and r["acciones"] and r["acciones"][0]["tipo"] == "abrir_navegacion", f"acciones={r['acciones']}")
            requiere(r["respuesta"].endswith("Te abro la navegación.") and r["uso_llm"] is False, r["respuesta"][-80:])
        fila_con_sitio("6.1", "¿Cómo llego a La Cancha?", "La Cancha", c61, ["¿Cómo llego a La Cancha?"],
                       variante=("¿Cómo llego a la Catedral Metropolitana?", ["¿Cómo llego a la Catedral Metropolitana?"]), ubicacion=PLAZA, cliente=cliente)

        def c62(r1, r2):
            requiere(r1["respuesta"].endswith("¿Quieres que te lleve?") and r1["escuchar_despues"] and r1["acciones"] == [], "debe ofrecer y escuchar")
            requiere(r2["acciones"] and r2["acciones"][0]["tipo"] == "abrir_navegacion", f"con «sí» debía abrir: {r2['acciones']}")
        fila_con_sitio("6.2", "¿Dónde queda el Convento de Santa Teresa? → sí", "Convento de Santa Teresa", c62,
                       ["¿Dónde queda el Convento de Santa Teresa?", "sí"],
                       variante=("¿Dónde queda la Iglesia de San Francisco? → sí", ["¿Dónde queda la Iglesia de San Francisco?", "sí"]), cliente=cliente)

        def c63(r1, r2):
            requiere(r2["respuesta"] == "Está bien." and r2["acciones"] == [] and r2["accion_pendiente"] is None, r2["respuesta"])
        fila_con_sitio("6.3", "¿Dónde queda el Convento? → no", "Convento de Santa Teresa", c63,
                       ["¿Dónde queda el Convento de Santa Teresa?", "no"],
                       variante=("¿Dónde queda la Iglesia de San Francisco? → no", ["¿Dónde queda la Iglesia de San Francisco?", "no"]), cliente=cliente)
        registrar("6.4", "¿Cómo llego al Cristo? → Detener", "MANUAL", "necesita la app (el botón Detener)")
        registrar("6.5", "Sin apps de mapas en el emulador", "MANUAL", "necesita el emulador")

        # ---------------- 7. Compartir e itinerario ----------------
        def c71(r):
            requiere(r["acciones"] and r["acciones"][0]["tipo"] == "compartir", f"acciones={r['acciones']}")
            requiere("Estoy aquí" not in r["acciones"][0]["texto"], "no debe incluir la ubicación si no la pidió")
        fila_con_sitio("7.1", "Avisa a mi familia que voy a La Cancha", "La Cancha", c71, ["Avisa a mi familia que voy a La Cancha"],
                       variante=("Avisa a mi familia que voy a la Catedral Metropolitana", ["Avisa a mi familia que voy a la Catedral Metropolitana"]), cliente=cliente)

        def c72(r):
            requiere(r["acciones"] and "Estoy aquí" in r["acciones"][0]["texto"], f"acciones={r['acciones']}")
        fila("7.2", "Dile a mi familia dónde estoy", c72, ["Dile a mi familia dónde estoy"], ubicacion=PLAZA, cliente=cliente)
        registrar("7.3", "Contacto de confianza en Ajustes", "MANUAL", "necesita la app")

        def c74(r):
            requiere(r["intencion"] == "itinerario" and r["uso_llm"] is False and "¿Quieres que te lleve a" in r["respuesta"], r["respuesta"][-120:])
            requiere(r["accion_pendiente"] and r["escuchar_despues"], "debe ofrecer llevar al primero")
        fila("7.4", "Arma un recorrido para hoy", c74, ["Arma un recorrido para hoy"], ubicacion=PLAZA, cliente=cliente)

        # ---------------- 8. Datos prácticos ----------------
        def c81(r):
            requiere(r["intencion"] == "datos_practicos" and r["uso_llm"] is False and r["nivel_fuente"] == "base", f"intencion={r['intencion']}")
            requiere("horario" in r["respuesta"].lower() or "hora" in r["respuesta"].lower() or "registrado" in r["respuesta"].lower(), r["respuesta"][:140])
        fila_con_sitio("8.1", "¿A qué hora abre el Convento de Santa Teresa?", "Convento de Santa Teresa", c81, ["¿A qué hora abre el Convento de Santa Teresa?"],
                       variante=("¿A qué hora abre la Catedral Metropolitana?", ["¿A qué hora abre la Catedral Metropolitana?"]), cliente=cliente)

        def c82(r1, r2):
            requiere(r2["sitio_id"] == r1["sitio_id"] and r2["intencion"] == "datos_practicos", f"el segundo turno no usó el sitio del contexto (sitio {r1['sitio_id']} -> {r2['sitio_id']})")
        fila_con_sitio("8.2", "¿Cuánto cuesta entrar al Cristo? → ¿y cuánto tiempo se necesita?", "Cristo de la Concordia", c82,
                       ["¿Cuánto cuesta entrar al Cristo?", "¿y cuánto tiempo se necesita?"],
                       variante=("¿Cuánto cuesta entrar a la Catedral Metropolitana? → ¿y cuánto tiempo?", ["¿Cuánto cuesta entrar a la Catedral Metropolitana?", "¿y cuánto tiempo se necesita?"]), cliente=cliente)

        # ---------------- 12. Fallos y respaldos ----------------
        # 12.1: clave de Gemini incorrecta -> plantillas, la app no se cae
        clave_real = config.LLM_API_KEY
        config.LLM_API_KEY = "clave-incorrecta-de-prueba"
        config.LLM_PROVEEDOR = "google"
        config.LLM_MODELO = config.LLM_MODELO or "gemini-2.0-flash"

        def c121(r):
            requiere(r["uso_llm"] is False and r["motivo_sin_llm"], f"uso_llm={r['uso_llm']}")
            requiere("verificaci" in r["respuesta"].lower() and r["nivel_fuente"] == "base", r["respuesta"][:140])
        fila("12.1", "GOOGLE_API_KEY incorrecta", c121, ["Cuéntame de la Catedral Metropolitana"], cliente=cliente)
        config.LLM_API_KEY = clave_real

        # 12.2: sin TAVILY_API_KEY -> Wikipedia directa (si hay contacto) o «No tengo información»
        clave_tavily = config.TAVILY_API_KEY
        config.TAVILY_API_KEY = ""
        sql("DELETE FROM contenido_web WHERE lower(titulo || ' ' || texto) LIKE '%tinku%'")

        def c122(r):
            requiere(r["creditos_tavily"] == 0, "no debe gastar Tavily")
            if config.WIKIPEDIA_CONTACTO:
                requiere(r["nivel_fuente"] in ("web", "ninguna"), r["nivel_fuente"])
            else:
                requiere(r["respuesta"].startswith("No tengo información"), r["respuesta"][:100])
        fila("12.2", "Sin TAVILY_API_KEY", c122, ["¿Qué es el tinku, la danza?"], cliente=cliente)
        config.TAVILY_API_KEY = clave_tavily
        registrar("12.3", "Apagar el backend con la app abierta", "MANUAL", "necesita la app")

    # 12.4: límite de consultas, en un proceso aparte con el límite real del .env (20 por minuto)
    codigo = (
        "import sys, os; sys.path[:0] = ['/app/asistente', '/app']; os.chdir('/app/asistente');"
        "from fastapi.testclient import TestClient; from main import app;"
        "c = TestClient(app); r = [c.post('/api/consulta', json={'pregunta': '¿Qué puedes hacer?'}).status_code for _ in range(25)];"
        "print(r)"
    )
    entorno = {k: v for k, v in os.environ.items() if k != "LIMITE_CONSULTAS"}
    entorno.pop("LIMITE_CONSULTAS", None)
    p = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, env=entorno)
    try:
        codigos = eval(p.stdout.strip().splitlines()[-1])
        ok = codigos[:20] == [200] * 20 and all(c == 429 for c in codigos[20:])
        registrar("12.4", "25 preguntas en un minuto", "PASA" if ok else "FALLA", f"códigos: {codigos}")
    except Exception:
        registrar("12.4", "25 preguntas en un minuto", "FALLA", p.stdout[-200:] + p.stderr[-200:])

    # ---------------- 14. Privacidad y métricas ----------------
    columnas = {f[0] for f in sql("SELECT column_name FROM information_schema.columns WHERE table_name = 'metricas_consulta'")}
    ultimas = sql("SELECT intencion, nivel_fuente, uso_llm, creditos_tavily, tiempo_ms FROM metricas_consulta ORDER BY id DESC LIMIT 10")
    prohibidas = {"pregunta", "texto", "ubicacion", "latitud", "longitud", "contacto", "chat_id", "respuesta"}
    ok = bool(ultimas) and not (columnas & prohibidas) and all(f[1] is not None for f in ultimas)
    registrar("14.1", "SELECT * FROM metricas_consulta ... LIMIT 10", "PASA" if ok else "FALLA", f"columnas: {sorted(columnas)}")
    r = subprocess.run([sys.executable, "-m", "pytest", str(RAIZ / "pruebas" / "test_agentes.py"), "-q", "-k", "ubicacion_ni_datos", "-p", "no:cacheprovider"], capture_output=True, text=True)
    registrar("14.2", "No se envía ubicación ni contacto a Gemini/Tavily", "PASA" if r.returncode == 0 else "FALLA", "prueba automática test_nunca_se_envia_la_ubicacion_ni_datos_personales_al_llm")
    por_nivel = sql("SELECT nivel_fuente, count(*) FROM metricas_consulta GROUP BY 1 ORDER BY 2 DESC")
    registrar("14.3", "SELECT nivel_fuente, count(*) ... GROUP BY 1", "PASA" if por_nivel else "FALLA", str(por_nivel))

    # ---------------- Manuales (guía 9, 10, 11, 13, 15) ----------------
    for id_, que in (("9", "Documentos (panel)"), ("10", "Contenido traído de internet (panel)"), ("11", "Panel de sitios y eventos"),
                     ("13", "App: accesibilidad y sentidos (teléfono real)"), ("15", "Opcionales: aviso diario y Telegram")):
        registrar(id_, que, "MANUAL", "necesita el panel, la app o el teléfono")

    resumen()


def resumen():
    cuenta = {}
    for _, _, estado, _ in RESULTADOS:
        cuenta[estado] = cuenta.get(estado, 0) + 1
    print("\nResumen:", ", ".join(f"{k}: {v}" for k, v in sorted(cuenta.items())))
    salida = RAIZ / "docs" / "resultado_probar_guia.md"
    lineas = ["# Resultado de pruebas/probar_guia.py", "", f"Resumen: {', '.join(f'{k}: {v}' for k, v in sorted(cuenta.items()))}", "",
              "| Fila | Pregunta o acción | Resultado | Motivo |", "|---|---|---|---|"]
    for id_, que, estado, detalle in RESULTADOS:
        lineas.append(f"| {id_} | {que} | {estado} | {detalle.replace('|', '/').replace(chr(10), ' ')[:200]} |")
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Guardado en {salida}")
    sys.exit(1 if cuenta.get("FALLA") else 0)


if __name__ == "__main__":
    ejecutar()
