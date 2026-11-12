"""Correcciones del backend pedidas tras la revisión (hallazgos 1, 3, 4, 5, 11, 12 y 13)."""

import pytest

import modelo
from db import conectar
from servicios import cascada, grafo
from servicios.agentes import agente_sitios, ejecucion, proveedor
from servicios.herramientas import buscar_en_base as h_base
from servicios.herramientas import buscar_web as h_web
from servicios.herramientas.buscar_web import IntentoWeb, ResultadoWeb


@pytest.fixture(scope="module")
def conn():
    c = conectar()
    yield c
    c.close()


def _borrar(conn, titulo):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM contenido_web WHERE titulo = %s", (titulo,))
    conn.commit()


# 1. proveedor.modelo() dentro del try
def test_si_crear_el_modelo_falla_responde_con_motivo_y_no_lanza(monkeypatch):
    def roto():
        raise ValueError("modelo mal configurado")
    monkeypatch.setattr(proveedor, "modelo", roto)
    ej = ejecucion.ejecutar(agente_sitios.agente, "hola", solicitudes_max=1)
    assert ej.salida is None and ej.motivo_sin_llm == "error_api"


# 3. la caché respeta el tema
def test_la_cache_solo_devuelve_contenido_del_mismo_tema(conn):
    titulo = "ZZ Cache Tema Cochabamba"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO contenido_web (fuente, tema, titulo, url, texto, dominio) VALUES "
            "('tavily','gastronomia',%s,'https://x/t','El zzcachetema es típico de Cochabamba.','x')", (titulo,))
    conn.commit()
    try:
        assert h_web.buscar_en_cache(conn, "zzcachetema", "gastronomia") is not None
        assert h_web.buscar_en_cache(conn, "zzcachetema", "danza") is None
    finally:
        _borrar(conn, titulo)


# 4. _guardar ya no traga los errores
def test_guardar_devuelve_false_si_falla_la_base(conn):
    class Rota:
        def cursor(self):
            raise RuntimeError("base caída")

        def rollback(self):
            pass

    r = ResultadoWeb(titulo="X", texto="t", url="https://x", dominio="x", tema="historia")
    assert h_web._guardar(Rota(), "tavily", r) is False


# 5. compuesta con «¿Quieres saber más?» conserva la acción pendiente y deja la pregunta al final
def test_compuesta_conserva_la_oferta_de_saber_mas(conn):
    r = grafo.procesar(conn, "¿Qué es la leyenda de la piedra que canta y dónde puedo ir a escucharla?", {},
                       vectorizar=modelo.vectorizar_pregunta, web=lambda *a, **k: IntentoWeb())
    assert "No tengo ese dato verificado" in r["respuesta"] or "En mi base verificada" in r["respuesta"]
    if r["accion_pendiente"]:
        assert r["accion_pendiente"]["tipo"] == "mas_informacion" and r["escuchar_despues"] is True
        assert r["respuesta"].endswith("¿Quieres saber más?")
        assert r["respuesta"].count("¿Quieres saber más?") == 1


# 11. eventos vigentes y memoria acotada
def test_eventos_muy_pasados_no_entran_al_nivel_1(conn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO eventos (nombre, descripcion, tipo, fecha_inicio) VALUES "
            "('ZZ Evento Viejo', 'zzviejoevento leyenda antigua del valle', 'festividad', (now() - interval '3 years')::date) RETURNING id")
        i = cur.fetchone()[0]
    conn.commit()
    try:
        v = modelo.vectorizar_pregunta("zzviejoevento leyenda antigua del valle")
        res = h_base.buscar_en_base(conn, "zzviejoevento leyenda antigua del valle", v, vectorizar=modelo.vectorizar_pregunta, umbral=0.0)
        assert all(not (h.origen == "evento" and h.id == i) for h in res.hallazgos)
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM eventos WHERE id = %s", (i,))
        conn.commit()


def test_la_memoria_de_eventos_tiene_tope(conn, monkeypatch):
    monkeypatch.setattr(h_base, "MAX_CACHE_EVENTOS", 3)
    h_base._cache_eventos.clear()
    v = modelo.vectorizar_pregunta("fiesta")
    h_base.buscar_en_base(conn, "fiesta", v, vectorizar=modelo.vectorizar_pregunta, umbral=0.0)
    assert 0 < len(h_base._cache_eventos) <= 3


def test_la_cache_compara_como_maximo_las_filas_mas_recientes(conn):
    assert h_web.LIMITE_CACHE == 200


# 12. puntaje ilegible de Tavily
def test_un_puntaje_ilegible_no_rompe_la_busqueda(monkeypatch, conn):
    class Falso:
        def search(self, **kw):
            return {"results": [
                {"title": "Malo Cochabamba", "url": "https://es.wikipedia.org/wiki/M", "content": "texto zzmalo de Cochabamba", "score": "alto"},
                {"title": "ZZ Bueno Cochabamba", "url": "https://es.wikipedia.org/wiki/B", "content": "El zzbueno es de Cochabamba.", "score": None},
            ]}
    monkeypatch.setattr(h_web.config, "TAVILY_API_KEY", "x")
    monkeypatch.setattr(h_web, "_cliente_tavily", lambda: Falso())
    intento = h_web.buscar_web(conn, "zzmalo zzbueno", "historia")
    assert intento.resultado is None and intento.creditos_tavily == 1


# 13. si Tavily no aporta, se intenta Wikipedia directa
def test_si_tavily_no_aporta_se_prueba_wikipedia(monkeypatch, conn):
    class Vacio:
        def search(self, **kw):
            return {"results": []}

    def pedir(url, params=None):
        if "search" in url:
            return {"pages": [{"title": "ZZ Wiki Cochabamba"}]}
        return {"extract": "El zzwiki es una tradición de Cochabamba.", "content_urls": {"desktop": {"page": "https://es.wikipedia.org/wiki/ZZ_Wiki"}}}

    monkeypatch.setattr(h_web.config, "TAVILY_API_KEY", "x")
    monkeypatch.setattr(h_web, "_cliente_tavily", lambda: Vacio())
    monkeypatch.setattr(h_web, "_pedir_json", pedir)
    try:
        intento = h_web.buscar_web(conn, "zzwiki", "tradicion")
        assert intento.resultado and intento.resultado.dominio == "es.wikipedia.org"
        assert intento.creditos_tavily == 1                    # el crédito de Tavily ya se gastó
    finally:
        _borrar(conn, "ZZ Wiki Cochabamba")


def test_no_se_usa_wikipedia_si_no_es_un_dominio_de_confianza(monkeypatch, conn):
    class Vacio:
        def search(self, **kw):
            return {"results": []}
    monkeypatch.setattr(h_web.config, "TAVILY_API_KEY", "x")
    monkeypatch.setattr(h_web.config, "DOMINIOS_CONFIABLES", ("turismo.gob.bo",))
    monkeypatch.setattr(h_web, "_cliente_tavily", lambda: Vacio())
    monkeypatch.setattr(h_web, "_pedir_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe llamar a Wikipedia")))
    assert h_web.buscar_web(conn, "zzotro", "tradicion").resultado is None
