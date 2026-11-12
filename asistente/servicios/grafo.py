"""Grafo de decisión del asistente: un nodo = una función explícita (sin LangGraph).

El diagrama está en docs/grafo_asistente.mmd y debe mantenerse igual a este código.

  1 normalizar -> 2 router por reglas (2b agente_clasificador si ninguna coincide) -> 3 intención y eje
  -> 4 resolver sitio -> herramienta -> 5 umbral -> cascada narrativa N1 a N4 -> 6 redactar
  -> 7 decidir acción -> 8 respuesta (contrato JSON)

Regla de dos ejes (CLAUDE.md):
  - dato OPERATIVO (dónde, cuándo, cuánto, horario, precio, cómo llego, accesibilidad): SOLO la base
    verificada. Si no está: «No tengo ese dato verificado». Nunca documentos ni web.
  - dato NARRATIVO (saberes, o la historia de un sitio o evento de Cochabamba): cascada
    N1 base + documentos -> N2 caché web -> N3 web -> N4 «No tengo información sobre eso, pero puedo contarte de…».
"""

import re
from typing import Callable, Optional

import config
from intencion import pregunta_sobre_llegada, temas_de_la_pregunta
from nombres import normalizar, sitios_mencionados
from servicios import cascada as casc
from servicios import router_reglas
from servicios.agentes import agente_clasificador, agente_saberes, agente_sitios
from servicios.herramientas import (
    armar_itinerario as h_itinerario,
    armar_mensaje_compartir as h_compartir,
    buscar_en_base as h_base,
    buscar_sitios as h_buscar,
    buscar_web as h_web,
    como_llegar as h_llegar,
    datos,
    datos_practicos as h_practicos,
    decidir_accion as h_accion,
    eventos as h_eventos,
    generar_respuesta as h_generar,
    sitios_cercanos as h_cercanos,
)

SIN_INFORMACION = "No tengo información sobre eso."
SIN_DATO_VERIFICADO = "No tengo ese dato verificado."
ACLARAR_SITIO = "¿A qué lugar te refieres?"
ACLARAR_MAS = "¿Sobre qué quieres saber más?"
NO_ENTENDI = "No te entendí bien. ¿Puedes decirlo de otra forma?"
FUERA_DE_ALCANCE = "Solo puedo ayudarte con turismo en Cochabamba: sitios, eventos, cultura y cómo llegar."
SABER_MAS = "¿Quieres saber más?"
SIN_MAS = "No encontré más información sobre eso en las fuentes que uso."
AYUDA = (
    "Puedes preguntarme por los sitios turísticos de Cochabamba, sus eventos y su cultura. "
    "Por ejemplo: ¿Qué hay hoy? Cuéntame del Cristo. ¿Cómo llego a La Cancha? "
    "También puedes decirme: arma un recorrido, o avisa a mi familia."
)
PALABRAS_RELATO = ("historia", "leyenda", "mito", "tradicion", "relato", "origen")
_SEPARADOR_COMPUESTA = re.compile(
    r"\s+y\s+(?=¿?(?:d[oó]nde|cu[aá]ndo|cu[aá]nto|a qu[eé] hora|c[oó]mo llego|c[oó]mo llegar|c[oó]mo se llega))", re.IGNORECASE
)


def _turnos_nuevos(contexto: dict, pregunta: str, respuesta: str) -> list:
    turnos = list(contexto.get("turnos") or [])[-config.MAX_TURNOS:]
    turnos.append({"pregunta": pregunta[: config.LARGO_MAX_PREGUNTA], "respuesta": respuesta[:600]})
    return turnos[-config.MAX_TURNOS:]


def _fuentes_base(sitios: list) -> list:
    fuentes = []
    for s in sitios:
        v = s.get("fecha_verificacion")
        if v:
            fuentes.append({"nombre": f"Verificado el {v.strftime('%d/%m/%Y')}", "url": None})
    return fuentes[:1] if len(sitios) == 1 else fuentes


def _fuente_de(nivel: str, dominio: str = "") -> str:
    """Valor del campo `fuente` del contrato: base_verificada, wikipedia, web o sistema."""
    if nivel in ("base", "documento"):
        return "base_verificada"
    if nivel in ("cache_web", "web"):
        return "wikipedia" if dominio.endswith("wikipedia.org") else "web"
    return "sistema"


def procesar(
    conn,
    pregunta: str,
    contexto: Optional[dict] = None,
    latitud: Optional[float] = None,
    longitud: Optional[float] = None,
    vectorizar: Optional[Callable] = None,
    web: Callable = h_web.buscar_web,
) -> dict:
    """Recorre el grafo y devuelve el contrato JSON de /api/consulta (más campos internos de métricas)."""
    pregunta = " ".join(pregunta.split())[: config.LARGO_MAX_PREGUNTA]
    contexto = dict(contexto or {})
    verificados = datos.sitios_verificados(conn)                        # (id, nombre)

    # 1-2. Normalizar y router por reglas
    clasif = router_reglas.clasificar(pregunta, verificados, contexto)
    t = clasif["texto"]
    ids_nombrados = clasif["sitios_ids"]
    intencion = clasif["intencion"]
    uso_llm, motivo = False, None

    # 2b. agente_clasificador (Gemini), solo si ninguna regla coincidió
    if intencion is None:
        ej = agente_clasificador.clasificar(pregunta)
        if ej.salida is not None:
            uso_llm, intencion = True, ej.salida.intencion
            if ej.salida.sitio and not ids_nombrados:
                ids_nombrados = sitios_mencionados(str(ej.salida.sitio), verificados)
        else:
            # Sin LLM (o con error) no se puede clasificar: se prueba el RAG, que responde si no hay nada.
            intencion = "no_clara" if ej.motivo_sin_llm == "salida_invalida" else "informacion"
            motivo = ej.motivo_sin_llm

    resultado = _despachar(conn, intencion, pregunta, t, contexto, ids_nombrados, latitud, longitud, vectorizar, web, verificados)
    resultado["uso_llm"] = resultado.get("uso_llm", False) or uso_llm
    if resultado["uso_llm"]:
        resultado["motivo_sin_llm"] = None
    elif not resultado.get("motivo_sin_llm"):
        resultado["motivo_sin_llm"] = motivo or "regla_sin_llm"
    resultado["intencion"] = intencion
    resultado["eje_dato"] = resultado.get("eje_dato") or router_reglas.eje_dato(t, intencion)
    resultado["turnos"] = _turnos_nuevos(contexto, pregunta, resultado["respuesta"])
    return resultado


def _despachar(conn, intencion, pregunta, t, contexto, ids_nombrados, latitud, longitud, vectorizar, web, verificados) -> dict:
    ultimo = contexto.get("ultimo_sitio_id")

    def salida(
        respuesta, fuente="sistema", fuentes=None, sitio_id=ultimo, decision=None, uso_llm=False, sim=None,
        nivel=None, creditos=0, motivo=None, eje=None,
    ):
        d = decision or h_accion.Decision()
        texto = " ".join(x for x in (respuesta, d.frase_final) if x)
        return {
            "respuesta": texto, "uso_llm": uso_llm, "fuente": fuente, "fuentes": fuentes or [],
            "sitio_id": sitio_id, "acciones": d.acciones, "escuchar_despues": d.escuchar_despues,
            "accion_pendiente": d.accion_pendiente, "ultimo_sitio_id": sitio_id, "similitud_maxima": sim,
            "nivel_fuente": nivel or ("base" if fuente == "base_verificada" else "ninguna"),
            "creditos_tavily": creditos, "motivo_sin_llm": motivo, "eje_dato": eje,
        }

    def sitio_resuelto():
        """Nodo 4: el sitio nombrado; si no, el último del contexto; si no, None."""
        for i in ids_nombrados[:1] + ([ultimo] if ultimo else []):
            s = datos.obtener_sitio(conn, i)
            if s:
                return s
        return None

    def vector_de(texto):
        return vectorizar(texto) if vectorizar else None

    def sin_informacion(vector):
        """Nivel 4: no hay nada; se ofrece una alternativa de la base."""
        alternativa = h_base.mejor_alternativa(conn, vector)
        return f"No tengo información sobre eso, pero puedo contarte de {alternativa}." if alternativa else SIN_INFORMACION

    def asegurar_cita(texto, ev):
        """El texto SIEMPRE lleva su fuente, aunque el LLM la haya omitido."""
        if ev.nivel in ("cache_web", "web"):
            if "información de internet" not in texto:
                texto = f"{ev.cita}, {texto[0].lower()}{texto[1:]}"
        elif "según" not in texto.lower() and ev.cita:
            texto = f"{texto} {ev.cita[0].upper()}{ev.cita[1:]}."
        return " ".join(texto.split())

    def redactar_saberes(cas, ev):
        """(texto, uso_llm, motivo): agente_saberes redacta; si no se puede, plantilla que lee y cita."""
        ej = agente_saberes.redactar(cas, ev)
        if ej.salida is not None and ej.salida.texto.strip():
            return asegurar_cita(ej.salida.texto, ev), True, None
        hallazgos = cas.base.hallazgos if cas.base else None
        return asegurar_cita(casc.plantilla(ev, hallazgos), ev), False, ej.motivo_sin_llm or "salida_vacia"

    def oferta_saber_mas(ev, tema, consulta, sitio_id):
        """C6: respuesta corta salida del nivel 1 -> «¿Quieres saber más?» y espera un «sí»."""
        if ev.nivel in ("base", "documento") and ev.es_corta() and tema:
            return h_accion.Decision(
                accion_pendiente={"tipo": "mas_informacion", "tema": tema, "nivel_siguiente": "cache_web",
                                  "consulta": consulta, "sitio_id": sitio_id},
                escuchar_despues=True, frase_final=SABER_MAS,
            )
        return None

    def respuesta_de_evidencia(cas, ev, consulta, oferta=False, sitio_id=None):
        texto, uso, motivo = redactar_saberes(cas, ev)
        d = oferta_saber_mas(ev, cas.tema, consulta, sitio_id) if oferta else None
        return salida(
            texto, _fuente_de(ev.nivel, ev.dominio), ev.fuentes, ev.sitio_id or sitio_id or ultimo, d, uso,
            ev.similitud_maxima, nivel=ev.nivel, creditos=cas.creditos_tavily, motivo=motivo, eje="narrativo",
        )

    def cascada_nueva(consulta, t_consulta, ids, intencion_):
        tema = h_web.detectar_tema(t_consulta)
        if tema is None and intencion_ == "saberes":
            tema = "tradicion"
        elif tema is None and ids:
            tema = "historia"                   # la historia o leyenda de un sitio de Cochabamba
        permitida = tema is not None and not router_reglas.menciona_lugar_desconocido(t_consulta, ids)
        return casc.Cascada(conn, consulta, vector_de(consulta), vectorizar, ids, tema, permitida, web)

    # ----- sin herramienta -----
    if intencion == "ayuda":
        return salida(AYUDA)
    if intencion == "fuera_de_alcance":
        return salida(FUERA_DE_ALCANCE)
    if intencion == "no_clara":
        return salida(NO_ENTENDI)

    # ----- C6: «¿Quieres saber más?» baja al siguiente nivel, solo para la parte narrativa -----
    def mas_informacion(pend):
        consulta = (pend or {}).get("consulta")
        if not consulta:
            turnos = contexto.get("turnos") or []
            consulta = turnos[-1].get("pregunta") if turnos else None
        if not consulta:
            return salida(ACLARAR_MAS)
        t2 = normalizar(consulta)
        ids = sitios_mencionados(consulta, verificados) or ([pend["sitio_id"]] if (pend or {}).get("sitio_id") else [])
        cas = cascada_nueva(consulta, t2, ids, "saberes")
        if (pend or {}).get("tema"):
            cas.tema, cas.web_permitida = pend["tema"], True
        cas.omitir_base()                       # el nivel 1 ya se mostró
        ev = cas.ejecutar()
        if not ev.hay():
            return salida(SIN_MAS, creditos=cas.creditos_tavily, eje="narrativo")
        return respuesta_de_evidencia(cas, ev, consulta, sitio_id=ids[0] if ids else None)

    if intencion == "confirmacion":
        pend = contexto.get("accion_pendiente") or {}
        if pend.get("tipo") == "mas_informacion":
            return mas_informacion(pend) if router_reglas.respuesta_si_no(t) == "si" else salida("Está bien.")
        d = h_accion.decidir_accion("confirmacion", None, contexto, respuesta_si_no=router_reglas.respuesta_si_no(t))
        return salida("", decision=d)
    if intencion == "mas_informacion":
        pend = contexto.get("accion_pendiente") or {}
        return mas_informacion(pend if pend.get("tipo") == "mas_informacion" else None)

    # ----- A1: lugar con nombre propio que no está en la base (nunca "lo que mejor encaja") -----
    if intencion in ("informacion", "como_llegar", "datos_practicos", "saberes"):
        lp = router_reglas.lugar_no_registrado(pregunta, ids_nombrados)
        if lp:
            if not lp["de_cochabamba"]:
                return salida(
                    f"No tengo información sobre {lp['lugar']}. "
                    f"Puedo contarte de {lp['articulo']} {lp['tipo_plural']} de Cochabamba que tengo "
                    f"registrad{'as' if lp['articulo'] == 'las' else 'os'}."
                )
            if intencion in ("como_llegar", "datos_practicos") or router_reglas.eje_dato(t, intencion) == "operativo":
                return salida(f"No tengo datos verificados de {lp['lugar']}.", eje="operativo")
            # Es de Cochabamba pero no está en la base: la parte narrativa sigue la cascada desde el nivel 2.
            cas = cascada_nueva(pregunta, t, [], "informacion")
            cas.tema = cas.tema or "historia"
            cas.web_permitida = True
            cas.omitir_base()
            ev = cas.ejecutar()
            if ev.hay():
                r = respuesta_de_evidencia(cas, ev, pregunta)
                r["respuesta"] += f" No tengo datos verificados de {lp['lugar']}."
                return r
            return salida(f"No tengo información sobre {lp['lugar']}. No tengo datos verificados de ese lugar.",
                          creditos=cas.creditos_tavily, eje="narrativo")

    # ----- compartir -----
    if intencion == "compartir":
        s = sitio_resuelto()
        con_ubicacion = "donde estoy" in t or "mi ubicacion" in t
        if con_ubicacion and latitud is None:
            return salida("No tengo tu ubicación. Activa la ubicación del teléfono y vuelve a pedirlo.")
        texto = h_compartir.armar_mensaje_compartir([s] if s else [], con_ubicacion, latitud, longitud)
        d = h_accion.decidir_accion("compartir", {"texto": texto}, contexto)
        return salida("", decision=d, sitio_id=s["id"] if s else ultimo)

    # ----- eventos (solo SQL) -----
    if intencion == "eventos":
        desde, hasta, etiqueta = h_eventos.rango_de_la_pregunta(t, datos.hoy(conn))
        eventos = h_eventos.eventos_por_fecha(conn, desde, hasta, latitud, longitud)
        if not eventos:
            return salida(f"No tengo eventos registrados {etiqueta}.")
        frases = [f"Eventos {etiqueta}:"] + [h_eventos.frase_evento(e) for e in eventos[:3]]
        d = h_accion.decidir_accion("eventos", {"candidatos": eventos}, contexto)
        return salida(" ".join(frases), decision=d, fuente="base_verificada")

    # ----- itinerario -----
    if intencion == "itinerario":
        it = h_itinerario.armar_itinerario(conn, latitud, longitud)
        d = h_accion.decidir_accion("itinerario", {"candidatos": it.sitios}, contexto)
        return salida(" ".join(h_itinerario.frases(it)), decision=d, fuente="base_verificada" if it.sitios else "sistema")

    # ----- cercanía -----
    if intencion == "cercania":
        if latitud is None or longitud is None:
            return salida("Para decirte qué hay cerca necesito tu ubicación. Activa la ubicación y vuelve a preguntar.")
        cerca = h_cercanos.sitios_cercanos(conn, latitud, longitud, limite=3)
        if not cerca:
            return salida(f"No tengo sitios verificados a menos de {str(config.RADIO_CERCA_KM).replace('.', ',')} kilómetros de ti.")
        frases = ["Cerca de ti hay:"] + [f"{s['nombre']}, {h_llegar.geo.decir_distancia(s['distancia_m'])}." for s in cerca]
        d = h_accion.decidir_accion("cercania", {"candidatos": cerca}, contexto)
        return salida(" ".join(frases), decision=d, fuente="base_verificada", sitio_id=cerca[0]["id"])

    # ----- datos prácticos / cómo llegar (operativos: requieren sitio, nodo 4) -----
    if intencion in ("datos_practicos", "como_llegar"):
        s = sitio_resuelto()
        if not s:
            # Un plato, una bebida o una fiesta no son sitios: de eso no hay precio ni horario verificado.
            if router_reglas.contiene(t, router_reglas.SABERES):
                return salida(f"{SIN_DATO_VERIFICADO} Solo doy precios, horarios y direcciones de la base verificada.", eje="operativo")
            return salida(ACLARAR_SITIO, eje="operativo")
        fuentes = _fuentes_base([s])
        if intencion == "datos_practicos":
            frases = h_practicos.frases(s, h_practicos.datos_practicos(s, h_practicos.campos_pedidos(t)))
            return salida(" ".join([f"{s['nombre']}."] + frases), "base_verificada", fuentes, s["id"], eje="operativo")
        r = h_llegar.como_llegar(s, latitud, longitud)
        d = h_accion.decidir_accion(
            "como_llegar", {"nombre": r.nombre, "latitud": r.latitud, "longitud": r.longitud}, contexto,
            quiere_ir=router_reglas.quiere_ir(t),
        )
        return salida(" ".join(h_llegar.frases(r)), "base_verificada", fuentes, s["id"], d, eje="operativo")

    # ----- informacion y saberes -----
    eje = router_reglas.eje_dato(t, intencion)

    # Dato OPERATIVO de un sitio (accesibilidad, ruido, piso...): solo sitios verificados, sin documentos ni web.
    if intencion == "informacion" and eje == "operativo":
        res = h_buscar.buscar_sitios(conn, pregunta, vector_de(pregunta), ids_nombrados=ids_nombrados)
        if not res.sitios:
            return salida(SIN_DATO_VERIFICADO, sim=res.similitud_maxima, eje="operativo")
        texto, uso, motivo = h_generar.generar_respuesta_sitios(
            pregunta, res.sitios, temas_de_la_pregunta(pregunta),
            sobre_llegada=pregunta_sobre_llegada(pregunta) and len(res.sitios) == 1 and res.por_nombre,
            pide_relato=any(p in t.split() for p in PALABRAS_RELATO),
        )
        unico = res.sitios[0]["id"] if len(res.sitios) == 1 else ultimo
        return salida(texto, "base_verificada", _fuentes_base(res.sitios), unico, uso_llm=uso, sim=res.similitud_maxima,
                      nivel="base", motivo=motivo, eje="operativo")

    def narrativo(intencion_, consulta, t_consulta, ids):
        """Dato narrativo: cascada N1 (base + documentos) -> N2 (caché) -> N3 (web) -> N4."""
        cas = cascada_nueva(consulta, t_consulta, ids, intencion_)
        base = cas.en_base()
        if base.suficiente():
            top = base.hallazgos[0]
            ev = casc.evidencia_de_base(base)
            if intencion_ == "saberes":
                return respuesta_de_evidencia(cas, ev, consulta, oferta=True)
            if top.origen == "sitio":            # sitio nombrado o parecido: respuesta completa de sitio
                llegada = pregunta_sobre_llegada(consulta) and len(base.sitios) == 1 and base.por_nombre
                texto, uso, motivo = h_generar.generar_respuesta_sitios(
                    consulta, base.sitios, temas_de_la_pregunta(consulta), sobre_llegada=llegada,
                    pide_relato=any(p in t_consulta.split() for p in PALABRAS_RELATO),
                )
                unico = base.sitios[0]["id"] if len(base.sitios) == 1 else ultimo
                d = None if llegada else oferta_saber_mas(ev, cas.tema, consulta, unico)
                return salida(texto, "base_verificada", _fuentes_base(base.sitios), unico, d, uso, base.similitud_maxima,
                              nivel="base", motivo=motivo, eje="narrativo")
            # documento o evento
            ej = agente_sitios.redactar(consulta, ev.contexto)
            if ej.salida is not None and ej.salida.texto.strip():
                texto, uso, motivo = asegurar_cita(ej.salida.texto, ev), True, None
            else:
                texto, uso, motivo = asegurar_cita(casc.plantilla(ev, base.hallazgos), ev), False, ej.motivo_sin_llm or "salida_vacia"
            return salida(texto, "base_verificada", ev.fuentes, ultimo, oferta_saber_mas(ev, cas.tema, consulta, None), uso,
                          ev.similitud_maxima, nivel=ev.nivel, motivo=motivo, eje="narrativo")
        # N1 no alcanzó: N2 caché y N3 web (solo si es un tema de saberes de Cochabamba o Bolivia)
        ev = cas.ejecutar()
        if ev.hay():
            return respuesta_de_evidencia(cas, ev, consulta)
        return salida(sin_informacion(vector_de(consulta)), sim=base.similitud_maxima, creditos=cas.creditos_tavily, eje="narrativo")

    def operativa(parte_operativa, parte_narrativa):
        """Segunda parte de una pregunta compuesta: solo sitios verificados; si no hay, lo dice."""
        t_op = normalizar(parte_operativa)
        ids = sitios_mencionados(parte_operativa, verificados)
        s = datos.obtener_sitio(conn, ids[0]) if ids else None
        if s:
            if router_reglas.quiere_ir(t_op) or "donde" in t_op.split():
                return " ".join(h_llegar.frases(h_llegar.como_llegar(s, latitud, longitud)))
            return " ".join(h_practicos.frases(s, h_practicos.datos_practicos(s, h_practicos.campos_pedidos(t_op))))
        if vectorizar:
            res = h_buscar.buscar_sitios(conn, parte_narrativa, vectorizar(parte_narrativa), ids_nombrados=[])
            if res.sitios:
                return f"En mi base verificada tengo relacionado con eso: {', '.join(x['nombre'] for x in res.sitios[:2])}."
        return f"{SIN_DATO_VERIFICADO} No hay un lugar registrado para eso en mi base."

    # ----- C5: pregunta compuesta, parte narrativa + parte operativa (máximo 2 partes) -----
    if router_reglas.dividir_compuesta(t):
        partes = _SEPARADOR_COMPUESTA.split(pregunta, maxsplit=1)
        if len(partes) == 2:
            parte_n = partes[0].strip(" ¿?")
            r = narrativo(intencion, parte_n, normalizar(parte_n), sitios_mencionados(parte_n, verificados))
            oferta = (r["accion_pendiente"] or {}).get("tipo") == "mas_informacion"
            cuerpo = r["respuesta"][: -len(SABER_MAS)].rstrip() if oferta and r["respuesta"].endswith(SABER_MAS) else r["respuesta"]
            r["respuesta"] = f"{cuerpo} {operativa(partes[1], parte_n)}".strip()
            if oferta:
                r["respuesta"] += f" {SABER_MAS}"           # la pregunta va al final y se conserva la acción pendiente
            else:
                r["accion_pendiente"], r["escuchar_despues"] = None, False
            return r

    return narrativo(intencion, pregunta, t, ids_nombrados)
