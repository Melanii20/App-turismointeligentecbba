"""Herramienta generar_respuesta (nodo 6): redacta el texto para voz.

Con Gemini configurado, el agente de sitios redacta usando SOLO el contexto entregado. Sin LLM, o si falla o tarda
más de 15 s, se usa una plantilla con el texto recuperado (dos primeras oraciones + fuente).
Los datos de accesibilidad nunca salen de aquí inventados: vienen de la base o no se mencionan.
"""

from datetime import datetime
from typing import Optional

import config
import generador

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")

def fecha_verificacion_texto(sitio: dict) -> Optional[str]:
    f = sitio.get("fecha_verificacion")
    if isinstance(f, datetime):
        return f"{MESES[f.month - 1]} de {f.year}"
    return None


def a_forma_plantilla(s: dict) -> dict:
    """Adapta un sitio al formato que usa el generador de plantillas (generador.py)."""
    return {
        "id": s["id"], "nombre": s["nombre"], "descripcion": s.get("descripcion"),
        "direccion": s.get("direccion"),
        # Bajo el UMBRAL nunca se presenta como "lo que mejor encaja" (solo entra por un filtro exacto).
        "coincidencia": s.get("coincidencia") if (s.get("similitud") or 0) >= config.UMBRAL else "filtro",
        "accesibilidad": {
            "descripcion_sensorial": s.get("acceso_descripcion_sensorial"),
            "tipo_piso": s.get("acceso_tipo_piso"),
            "piso_tactil": s.get("acceso_piso_tactil"),
            "senalizacion_braille": s.get("acceso_senalizacion_braille"),
            "permite_perros_guia": s.get("acceso_permite_perros_guia"),
            "nivel_ruido": s.get("acceso_nivel_ruido"),
        },
        "como_llegar": {
            "punto_referencia_entrada": s.get("acceso_punto_referencia_entrada"),
            "recomendacion": s.get("acceso_recomendacion"),
        },
    }


def _plantilla_sitios(pregunta: str, sitios: list, temas: list, sobre_llegada: bool, pide_relato: bool) -> str:
    if pide_relato and len(sitios) == 1 and sitios[0].get("relato"):
        # Si preguntan por la historia o la leyenda y el administrador la registró, se cuenta tal cual.
        texto = f"{sitios[0]['nombre']}. " + generador._recortar(sitios[0]["relato"], 420)
    else:
        texto = generador.generar(pregunta, [a_forma_plantilla(s) for s in sitios], temas, sobre_llegada)
    fechas = {fecha_verificacion_texto(s) for s in sitios if fecha_verificacion_texto(s)}
    if len(fechas) == 1:
        texto += f" Según la verificación de {fechas.pop()}."
    return " ".join(texto.split())


def _contexto_llm(sitios: list) -> str:
    bloques = []
    for s in sitios:
        lineas = [f"SITIO: {s['nombre']} ({s.get('tipo') or 'sin tipo'})"]
        for etiqueta, clave in (
            ("Descripción", "descripcion"), ("Historia", "relato"), ("Qué ver", "que_ver"),
            ("Ambiente", "acceso_descripcion_sensorial"), ("Piso", "acceso_tipo_piso"),
            ("Nivel de ruido", "acceso_nivel_ruido"), ("Horario", "horario"), ("Costo", "costo_ingreso"),
        ):
            if s.get(clave):
                lineas.append(f"{etiqueta}: {s[clave]}")
        for etiqueta, clave in (
            ("Piso táctil", "acceso_piso_tactil"), ("Señalización en braille", "acceso_senalizacion_braille"),
            ("Perros guía permitidos", "acceso_permite_perros_guia"),
        ):
            if s.get(clave) is not None:
                lineas.append(f"{etiqueta}: {'sí' if s[clave] else 'no'}")
        v = fecha_verificacion_texto(s)
        if v:
            lineas.append(f"Verificado en: {v}")
        bloques.append("\n".join(lineas))
    return "\n\n".join(bloques)


def generar_respuesta_sitios(
    pregunta: str, sitios: list, temas: list, sobre_llegada: bool = False, pide_relato: bool = False, modelo=None
) -> tuple:
    """(texto, uso_llm, motivo_sin_llm) para respuestas basadas en sitios verificados.

    El agente de sitios (Gemini) redacta con los datos verificados; si no hay LLM, falla, da error 429 o
    tarda más de 15 s, se usa la plantilla (que lee la descripción citando la verificación).
    Lo de «cómo llegar» siempre va tal cual, sin LLM.
    """
    from servicios.agentes import agente_sitios

    plantilla = _plantilla_sitios(pregunta, sitios, temas, sobre_llegada, pide_relato)
    if sobre_llegada:
        return plantilla, False, "dato_fijo_sin_llm"
    ejecucion = agente_sitios.redactar(pregunta, _contexto_llm(sitios), modelo=modelo)
    if ejecucion.salida is not None and ejecucion.salida.texto.strip():
        redactado = ejecucion.salida.texto
        if "verificaci" not in redactado.lower() and fecha_verificacion_texto(sitios[0]):
            redactado += f" Según la verificación de {fecha_verificacion_texto(sitios[0])}."
        return " ".join(redactado.split()), True, None
    return plantilla, False, ejecucion.motivo_sin_llm or "salida_vacia"
