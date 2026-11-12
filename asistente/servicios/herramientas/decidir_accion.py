"""Herramienta decidir_accion (nodo 7 del grafo): el asistente decide qué acción tomar.

Son reglas en el código, no el LLM, para que sea predecible y se pueda probar. No hay botones de
acción en la app: la app solo ejecuta lo que esta función decide, al terminar de hablar.
"""

from typing import Optional

from pydantic import BaseModel, Field


class Decision(BaseModel):
    acciones: list = Field(default_factory=list)
    accion_pendiente: Optional[dict] = None
    escuchar_despues: bool = False
    frase_final: str = ""


def _navegacion(latitud, longitud, nombre) -> dict:
    return {"tipo": "abrir_navegacion", "latitud": latitud, "longitud": longitud, "nombre": nombre}


def _con_coordenadas(item: dict) -> bool:
    return item.get("latitud") is not None and item.get("longitud") is not None


def decidir_accion(
    intencion: str, resultado: Optional[dict], contexto: Optional[dict], quiere_ir: bool = False,
    respuesta_si_no: Optional[str] = None,
) -> Decision:
    """Reglas de la tabla del nodo 7 de CLAUDE.md.

    resultado, según la intención:
      como_llegar -> {"nombre", "latitud", "longitud"}
      cercania / itinerario / eventos -> {"candidatos": [ {"nombre","latitud","longitud"}, ... ]} (el primero es el elegido)
      compartir -> {"texto": "...", "numero_contacto": opcional}
    """
    contexto = contexto or {}
    resultado = resultado or {}

    if intencion == "confirmacion":
        pendiente = contexto.get("accion_pendiente")
        if respuesta_si_no == "si" and pendiente:
            return Decision(acciones=[pendiente], frase_final="Listo, te abro la navegación.")
        return Decision(frase_final="Está bien.")           # "no": se borra la acción pendiente

    if intencion == "compartir" and resultado.get("texto"):
        accion = {"tipo": "compartir", "texto": resultado["texto"]}
        if resultado.get("numero_contacto"):
            accion["numero_contacto"] = resultado["numero_contacto"]
        return Decision(acciones=[accion], frase_final="Te dejo el mensaje listo para enviar.")

    if intencion == "como_llegar":
        if not _con_coordenadas(resultado):
            return Decision()                                # da la dirección; "No tengo la ubicación exacta" lo dice la herramienta
        nav = _navegacion(resultado["latitud"], resultado["longitud"], resultado["nombre"])
        if quiere_ir:
            return Decision(acciones=[nav], frase_final="Te abro la navegación.")
        return Decision(accion_pendiente=nav, escuchar_despues=True, frase_final="¿Quieres que te lleve?")

    if intencion in ("cercania", "itinerario", "eventos"):
        for c in resultado.get("candidatos", []):
            if _con_coordenadas(c):
                return Decision(
                    accion_pendiente=_navegacion(c["latitud"], c["longitud"], c["nombre"]),
                    escuchar_despues=True,
                    frase_final=f"¿Quieres que te lleve a {c['nombre']}?",
                )
    return Decision()
