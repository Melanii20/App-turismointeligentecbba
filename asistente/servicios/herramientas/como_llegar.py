"""Herramienta como_llegar: referencia de la entrada, recomendación, distancia y coordenadas.

Lee de la base lo que las apps de mapas no tienen. No llama a ninguna API de mapas.
"""

from typing import Optional

from pydantic import BaseModel

from servicios import geo


class ComoLlegar(BaseModel):
    sitio_id: int
    nombre: str
    punto_referencia_entrada: Optional[str] = None
    recomendacion: Optional[str] = None
    direccion: Optional[str] = None
    distancia_m: Optional[float] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None

    @property
    def tiene_coordenadas(self) -> bool:
        return self.latitud is not None and self.longitud is not None


def como_llegar(sitio: dict, latitud: Optional[float] = None, longitud: Optional[float] = None) -> ComoLlegar:
    """Información para llegar a un sitio. La distancia (en línea recta) solo se calcula si la persona
    envió su ubicación en esta consulta."""
    distancia = None
    if latitud is not None and longitud is not None and sitio.get("latitud") is not None:
        distancia = geo.distancia_m(latitud, longitud, sitio["latitud"], sitio["longitud"])
    return ComoLlegar(
        sitio_id=sitio["id"], nombre=sitio["nombre"],
        punto_referencia_entrada=sitio.get("acceso_punto_referencia_entrada"),
        recomendacion=sitio.get("acceso_recomendacion"),
        direccion=sitio.get("direccion"),
        distancia_m=distancia, latitud=sitio.get("latitud"), longitud=sitio.get("longitud"),
    )


def frases(r: ComoLlegar) -> list:
    """Texto para leer en voz alta, en el orden de CLAUDE.md: entrada, recomendación, distancia."""
    salida = [f"{r.nombre}."]
    if r.punto_referencia_entrada:
        salida.append("Para reconocer la entrada: " + r.punto_referencia_entrada.strip().rstrip(".") + ".")
    if r.recomendacion:
        salida.append("Recomendación: " + r.recomendacion.strip().rstrip(".") + ".")
    if r.direccion:
        salida.append(f"La dirección es {r.direccion.strip().rstrip('.')}.")
    if r.distancia_m is not None:
        salida.append(f"Estás {geo.decir_distancia(r.distancia_m)} en línea recta.")
    if not r.punto_referencia_entrada and not r.recomendacion:
        salida.append("Todavía no tengo verificado cómo reconocer la entrada.")
    if not r.tiene_coordenadas:
        salida.append("No tengo la ubicación exacta registrada.")
    return salida
