"""Cascada de fuentes para los datos NARRATIVOS (regla de dos ejes de CLAUDE.md).

  N1  base verificada: sitios (descripcion, relato, que_ver), eventos y documentos verificados
  N2  caché web (contenido_web vigente 30 días)
  N3  web: Tavily y, como respaldo, Wikipedia directa
  N4  «No tengo información sobre eso, pero puedo contarte de…» con una alternativa de la base

El orden N1 -> N2 -> N3 se impone AQUÍ, en el código, no en las instrucciones al LLM: la clase Cascada
lleva el estado y se niega (OrdenInvalido) a consultar la web si antes no se consultaron la base y la
caché sin encontrar lo suficiente. Los datos operativos (dónde, cuándo, cuánto, horario, accesibilidad...)
nunca pasan por aquí: salen solo de la base verificada.
"""

from typing import Callable, List, Optional

from pydantic import BaseModel, Field

import config
from servicios.herramientas import buscar_en_base as h_base
from servicios.herramientas import buscar_web as h_web
from servicios.herramientas.generar_respuesta import fecha_verificacion_texto

NIVELES = ("base", "documento", "cache_web", "web", "ninguna")


class OrdenInvalido(Exception):
    """Se intentó saltar un nivel de la cascada (por ejemplo, ir a la web sin mirar antes la base)."""


class Evidencia(BaseModel):
    """Lo que encontró la cascada y con qué nivel, listo para redactar o para la plantilla."""

    nivel: str = "ninguna"
    contexto: str = ""                                    # texto que se le entrega al LLM
    cita: str = ""                                        # «según la verificación de octubre de 2026», etc.
    fuentes: List[dict] = Field(default_factory=list)
    n_fragmentos: int = 0
    caracteres: int = 0
    sitio_id: Optional[int] = None
    similitud_maxima: Optional[float] = None
    titulo: str = ""
    dominio: str = ""
    sitios: list = Field(default_factory=list)            # sitios completos (para las plantillas de sitios)

    def hay(self) -> bool:
        return self.nivel != "ninguna"

    def es_corta(self) -> bool:
        """Para «¿Quieres saber más?»: menos de 2 fragmentos o menos de 300 caracteres."""
        return self.n_fragmentos < 2 or self.caracteres < 300


def cita_hallazgo(h: h_base.Hallazgo) -> str:
    if h.origen == "documento":
        return f"según la {h.documento_titulo}" + (f", página {h.pagina}" if h.pagina else "")
    if h.origen == "evento":
        return "según el calendario de eventos registrado"
    v = fecha_verificacion_texto({"fecha_verificacion": h.fecha_verificacion}) if h.fecha_verificacion else None
    return f"según la verificación de {v}" if v else "según la base verificada"


def evidencia_de_base(res: h_base.ResultadoBase) -> Evidencia:
    if not res.hallazgos:
        return Evidencia(similitud_maxima=res.similitud_maxima)
    citas, fuentes, bloques = [], [], []
    for h in res.hallazgos:
        c = cita_hallazgo(h)
        if c not in citas:
            citas.append(c)
            if h.origen == "documento":
                fuentes.append({"nombre": c[0].upper() + c[1:], "url": None})
            elif h.fecha_verificacion:
                fuentes.append({"nombre": f"Verificado el {h.fecha_verificacion.strftime('%d/%m/%Y')}", "url": None})
        etiqueta = {"sitio": "SITIO", "evento": "EVENTO", "documento": "DOCUMENTO"}[h.origen]
        extra = f", página {h.pagina}" if h.pagina else ""
        bloques.append(f"{etiqueta}: {h.titulo}{extra} ({c})\n{h.texto}")
    mejor = res.hallazgos[0]
    return Evidencia(
        nivel="documento" if mejor.origen == "documento" else "base",
        contexto="\n\n".join(bloques), cita=" y ".join(citas[:2]), fuentes=fuentes[:2],
        n_fragmentos=len(res.hallazgos), caracteres=sum(len(h.texto) for h in res.hallazgos),
        sitio_id=res.sitios[0]["id"] if len(res.sitios) == 1 else None,
        similitud_maxima=res.similitud_maxima, titulo=mejor.titulo, sitios=res.sitios,
    )


def evidencia_de_web(r: h_web.ResultadoWeb) -> Evidencia:
    nombre = h_web.nombre_de_dominio(r.dominio)
    return Evidencia(
        nivel="cache_web" if r.desde_cache else "web",
        contexto=f"PÁGINA: {r.titulo} ({nombre}, información de internet)\n{r.texto}",
        cita=f"Según {nombre} (información de internet)",
        fuentes=[{"nombre": f"{nombre}: {r.titulo}" + (f" ({r.licencia})" if r.licencia else ""), "url": r.url}],
        n_fragmentos=1, caracteres=len(r.texto), titulo=r.titulo, dominio=r.dominio,
    )


class Cascada:
    """Estado de la cascada narrativa de UNA pregunta. Es el 'deps' del agente de saberes."""

    def __init__(
        self, conn, pregunta: str, vector, vectorizar: Optional[Callable] = None, ids_nombrados: Optional[list] = None,
        tema: Optional[str] = None, web_permitida: bool = True, fn_web: Optional[Callable] = None,
    ):
        self.conn, self.pregunta, self.vector, self.vectorizar = conn, pregunta, vector, vectorizar
        self.ids_nombrados = ids_nombrados or []
        self.tema, self.web_permitida = tema, web_permitida
        self.fn_web = fn_web or h_web.buscar_web           # se puede simular en las pruebas
        self.base_consultada = self.cache_consultada = self.web_consultada = False
        self.base: Optional[h_base.ResultadoBase] = None
        self.cache: Optional[h_web.ResultadoWeb] = None
        self.web: Optional[h_web.IntentoWeb] = None
        self.herramientas_usadas: List[str] = []
        self.creditos_tavily = 0

    # --- niveles ---
    def omitir_base(self) -> None:
        """«Cuéntame más»: el nivel 1 ya se mostró, se sigue con el siguiente."""
        self.base_consultada, self.base = True, h_base.ResultadoBase()

    def en_base(self, consulta: Optional[str] = None) -> h_base.ResultadoBase:
        if not self.base_consultada:
            vector = self.vector
            if consulta and consulta != self.pregunta and self.vectorizar:
                vector = self.vectorizar(consulta)
            self.base = h_base.buscar_en_base(
                self.conn, consulta or self.pregunta, vector, ids_nombrados=self.ids_nombrados, vectorizar=self.vectorizar
            )
            self.base_consultada = True
            self.herramientas_usadas.append("buscar_en_base")
        return self.base

    def en_cache(self, consulta: Optional[str] = None) -> Optional[h_web.ResultadoWeb]:
        if not self.base_consultada:
            raise OrdenInvalido("Primero hay que consultar buscar_en_base.")
        if not self.cache_consultada:
            if not self.base.suficiente() and self.tema:
                self.cache = h_web.buscar_en_cache(self.conn, consulta or self.pregunta, self.tema)
            self.cache_consultada = True
            self.herramientas_usadas.append("buscar_en_cache")
        return self.cache

    def en_web(self, consulta: Optional[str] = None) -> h_web.IntentoWeb:
        if not (self.base_consultada and self.cache_consultada):
            raise OrdenInvalido("La web solo se puede usar después de buscar_en_base y buscar_en_cache sin resultado suficiente.")
        if self.base.suficiente() or self.cache is not None:
            raise OrdenInvalido("Ya hay información suficiente en un nivel anterior: no se usa la web.")
        if not (self.web_permitida and self.tema):
            raise OrdenInvalido("Esta pregunta no es un tema de saberes de Cochabamba o Bolivia: no se consulta la web.")
        if not self.web_consultada:
            self.web = self.fn_web(self.conn, consulta or self.pregunta, self.tema)
            self.web_consultada = True
            self.creditos_tavily += self.web.creditos_tavily
            self.herramientas_usadas.append("buscar_web")
        return self.web

    # --- resultado ---
    def evidencia(self) -> Evidencia:
        """La evidencia del nivel más profundo que dio resultado."""
        if self.web and self.web.resultado:
            return evidencia_de_web(self.web.resultado)
        if self.cache:
            return evidencia_de_web(self.cache)
        if self.base and self.base.suficiente():
            return evidencia_de_base(self.base)
        return Evidencia(similitud_maxima=self.base.similitud_maxima if self.base else None)

    def ejecutar(self) -> Evidencia:
        """Recorre N1 -> N2 -> N3 en orden y devuelve lo que encontró (nivel 'ninguna' = ir al N4)."""
        self.en_base()
        self.en_cache()
        try:
            self.en_web()
        except OrdenInvalido:
            pass
        return self.evidencia()


# ---------------------------------------------------------------------------------------------
# Plantillas (sin LLM): leen el fragmento o la descripción citando la fuente.
# ---------------------------------------------------------------------------------------------
def _oraciones(texto: str, cuantas: int = 2, maximo: int = 420) -> str:
    texto = " ".join(texto.split())
    if texto[:1].islower() and ". " in texto:        # el fragmento empieza a mitad de una oración (solapamiento)
        texto = texto.split(". ", 1)[1]
    partes = [p.strip() for p in texto.replace("…", "...").split(". ") if p.strip()]
    corto = ". ".join(partes[:cuantas])
    if len(corto) > maximo:
        corto = corto[:maximo].rsplit(" ", 1)[0]
    return corto if corto.endswith((".", "!", "?")) else corto + "."


def plantilla(ev: Evidencia, hallazgos: Optional[List[h_base.Hallazgo]] = None) -> str:
    """Texto para voz con las dos primeras oraciones de lo encontrado y su fuente."""
    if ev.nivel in ("cache_web", "web"):
        cuerpo = ev.contexto.split("\n", 1)[1] if "\n" in ev.contexto else ev.contexto
        resumen = _oraciones(cuerpo)
        return f"{ev.cita}, {resumen[0].lower()}{resumen[1:]}"
    if ev.nivel in ("base", "documento") and hallazgos:
        h = hallazgos[0]
        return f"{_oraciones(h.texto)} {ev.cita[0].upper()}{ev.cita[1:]}."
    return ""
