"""Prueba automática del router por reglas con pruebas/preguntas_router.json.

Da el porcentaje de acierto y exige que haya al menos 5 preguntas por intención.
"""

import json
from collections import Counter
from pathlib import Path

from servicios import router_reglas

DATOS = json.loads((Path(__file__).parent / "preguntas_router.json").read_text(encoding="utf-8"))
SITIOS = [tuple(s) for s in DATOS["sitios_verificados"]]
CASOS = DATOS["casos"]


def _clasificar(caso):
    contexto = {"accion_pendiente": {"tipo": "abrir_navegacion"}} if caso.get("con_pendiente") else {}
    return router_reglas.clasificar(caso["pregunta"], SITIOS, contexto)["intencion"]


def test_hay_al_menos_5_preguntas_por_intencion():
    cuenta = Counter(c["intencion"] for c in CASOS)
    esperadas = [i for i in router_reglas.INTENCIONES if i != "no_clara"]
    faltan = {i: cuenta[i] for i in esperadas if cuenta[i] < 5}
    assert not faltan, f"Intenciones con menos de 5 preguntas: {faltan}"


def test_porcentaje_de_acierto_del_router():
    fallos = [(c["pregunta"], c["intencion"], _clasificar(c)) for c in CASOS if _clasificar(c) != c["intencion"]]
    acierto = 100 * (len(CASOS) - len(fallos)) / len(CASOS)
    print(f"\nAcierto del router: {acierto:.1f}% ({len(CASOS) - len(fallos)}/{len(CASOS)})")
    for pregunta, esperada, obtenida in fallos:
        print(f"  FALLA: {pregunta!r} esperaba {esperada}, dio {obtenida}")
    assert acierto >= 95, f"Acierto {acierto:.1f}% (menor a 95%)"


def test_confirmacion_solo_con_accion_pendiente():
    assert router_reglas.clasificar("sí", SITIOS, {})["intencion"] != "confirmacion"


def test_si_nombra_un_sitio_va_a_informacion_aunque_diga_leyenda():
    r = router_reglas.clasificar("Cuéntame la leyenda de la Casona Santiváñez", SITIOS, {})
    assert r["intencion"] == "informacion" and r["sitios_ids"] == [27]


def test_pregunta_sin_regla_queda_sin_intencion():
    assert router_reglas.clasificar("zzz qqq", SITIOS, {})["intencion"] is None
