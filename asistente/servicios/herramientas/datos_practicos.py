"""Herramienta datos_practicos: horario, costo, duración y servicios de un sitio (solo SQL, sin LLM)."""

from typing import Optional

from pydantic import BaseModel

# campo pedido -> (columna, palabras que lo piden, cómo se dice)
CAMPOS = {
    "horario": ("horario", ("horario", "a que hora", "hora de apertura", "cuando abre", "cuando cierra", "abierto", "abre", "cierra")),
    "costo": ("costo_ingreso", ("cuanto cuesta", "costo", "precio", "cuanto cobran", "gratis", "cuesta")),
    "duracion": ("duracion_visita", ("cuanto tiempo", "cuanto dura", "duracion", "cuanto me toma")),
    "servicios": ("servicios", ("servicios", "bano", "banos", "tiendas", "guias")),
}
DICHO = {
    "horario": "El horario registrado es: {v}",
    "costo": "El costo de ingreso registrado es: {v}",
    "duracion": "La duración de la visita es de {v}",
    "servicios": "Los servicios registrados son: {v}",
}
ETIQUETA = {"horario": "el horario", "costo": "el costo de ingreso", "duracion": "la duración de la visita", "servicios": "los servicios"}


class DatoPractico(BaseModel):
    campo: str
    valor: Optional[str] = None


def campos_pedidos(pregunta_normalizada: str) -> list:
    """Campos por los que pregunta la persona; si no se distingue ninguno, todos."""
    t = f" {pregunta_normalizada} "
    pedidos = [c for c, (_, claves) in CAMPOS.items() if any(f" {k} " in t or k in t for k in claves)]
    return pedidos or list(CAMPOS)


def datos_practicos(sitio: dict, campos: list) -> list:
    """Valores registrados de los campos pedidos; valor None = 'no registrado' (nunca se inventa)."""
    return [DatoPractico(campo=c, valor=sitio.get(CAMPOS[c][0])) for c in campos]


def frases(sitio: dict, resultados: list) -> list:
    """Frases listas para leer. Lo que no está registrado se dice con honestidad."""
    salida = []
    for r in resultados:
        if r.valor:
            texto = DICHO[r.campo].format(v=str(r.valor).strip().rstrip("."))
            salida.append(texto + ".")
        else:
            salida.append(f"Todavía no tengo registrado {ETIQUETA[r.campo]} de {sitio['nombre']}.")
    return salida
