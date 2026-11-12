"""Pruebas de decidir_accion: una por cada fila de la tabla del nodo 7 de CLAUDE.md."""

from servicios.herramientas.decidir_accion import decidir_accion

CRISTO = {"nombre": "Cristo de la Concordia", "latitud": -17.3839, "longitud": -66.1342}
SIN_COORDENADAS = {"nombre": "Lugar sin ubicación", "latitud": None, "longitud": None}


def test_llevame_abre_la_navegacion_directo():
    d = decidir_accion("como_llegar", CRISTO, {}, quiere_ir=True)
    assert d.acciones and d.acciones[0]["tipo"] == "abrir_navegacion"
    assert d.acciones[0]["nombre"] == "Cristo de la Concordia"
    assert d.frase_final == "Te abro la navegación."
    assert d.accion_pendiente is None and not d.escuchar_despues


def test_donde_queda_pregunta_si_quiere_que_lo_lleve():
    d = decidir_accion("como_llegar", CRISTO, {}, quiere_ir=False)
    assert d.acciones == []
    assert d.accion_pendiente["tipo"] == "abrir_navegacion"
    assert d.escuchar_despues is True
    assert d.frase_final == "¿Quieres que te lleve?"


def test_cercania_itinerario_y_eventos_dejan_pendiente_el_primero_con_coordenadas():
    for intencion in ("cercania", "itinerario", "eventos"):
        d = decidir_accion(intencion, {"candidatos": [SIN_COORDENADAS, CRISTO]}, {})
        assert d.accion_pendiente["nombre"] == "Cristo de la Concordia", intencion
        assert d.escuchar_despues and d.frase_final.startswith("¿Quieres que te lleve a")


def test_confirmacion_si_ejecuta_la_accion_pendiente():
    pendiente = {"tipo": "abrir_navegacion", "latitud": -17.38, "longitud": -66.13, "nombre": "Cristo"}
    d = decidir_accion("confirmacion", None, {"accion_pendiente": pendiente}, respuesta_si_no="si")
    assert d.acciones == [pendiente]
    assert d.frase_final == "Listo, te abro la navegación."
    assert d.accion_pendiente is None


def test_confirmacion_no_borra_la_accion_pendiente():
    pendiente = {"tipo": "abrir_navegacion", "latitud": 1, "longitud": 1, "nombre": "X"}
    d = decidir_accion("confirmacion", None, {"accion_pendiente": pendiente}, respuesta_si_no="no")
    assert d.acciones == [] and d.accion_pendiente is None and d.frase_final == "Está bien."


def test_confirmacion_si_sin_pendiente_no_hace_nada():
    d = decidir_accion("confirmacion", None, {}, respuesta_si_no="si")
    assert d.acciones == []


def test_compartir_prepara_el_mensaje_sin_enviarlo():
    d = decidir_accion("compartir", {"texto": "Hola"}, {})
    assert d.acciones == [{"tipo": "compartir", "texto": "Hola"}]
    assert d.frase_final == "Te dejo el mensaje listo para enviar."


def test_sitio_sin_coordenadas_no_tiene_accion():
    d = decidir_accion("como_llegar", SIN_COORDENADAS, {}, quiere_ir=True)
    assert d.acciones == [] and d.accion_pendiente is None and d.frase_final == ""


def test_informacion_cultura_y_datos_practicos_no_tienen_accion():
    for intencion in ("informacion", "saberes", "datos_practicos", "ayuda"):
        d = decidir_accion(intencion, CRISTO, {})
        assert d.acciones == [] and d.accion_pendiente is None and d.frase_final == "", intencion
