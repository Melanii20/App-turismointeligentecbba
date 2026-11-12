import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:flutter_application_1/cliente_asistente.dart';
import 'package:flutter_application_1/estado_asistente.dart';
import 'package:flutter_application_1/main.dart';
import 'package:flutter_application_1/servicios/acciones.dart';
import 'package:flutter_application_1/servicios/ajustes.dart';
import 'package:flutter_application_1/servicios/cliente_consulta.dart';
import 'package:flutter_application_1/servicios/efectos.dart';
import 'package:flutter_application_1/servicios/eventos_hoy.dart';
import 'package:flutter_application_1/servicios/ubicacion.dart';
import 'package:flutter_application_1/widgets/tarjeta_hoy.dart';

import 'widget_test.dart' show VozFalsa, avanzar, escribirYEnviar, telefono;

class ClienteConAcciones implements ClienteAsistente {
  ClienteConAcciones(this.respuesta);
  final RespuestaAsistente respuesta;
  @override
  Future<RespuestaAsistente> preguntar(String pregunta) async => respuesta;
}

class EventosFalsos implements ServicioEventos {
  EventosFalsos(this.lista);
  final List<EventoHoy> lista;
  @override
  Future<List<EventoHoy>> hoy() async => lista;
}

class AccionesFalsas implements EjecutorAcciones {
  final List<String> hechas = [];
  @override
  Future<void> abrirNavegacion(double latitud, double longitud, String nombre) async =>
      hechas.add('nav:$nombre');
  @override
  Future<void> compartir(String texto, {String? numeroContacto}) async =>
      hechas.add('compartir:$texto');
}

class EfectosGrabados implements Efectos {
  final List<String> eventos = [];
  @override
  void alCambiarEstado(EstadoAsistente estado) => eventos.add('estado:${estado.name}');
  @override
  void respuestaLista() => eventos.add('respuesta');
  @override
  void error() => eventos.add('error');
  @override
  void abriendoNavegacion() => eventos.add('abriendo');
}

const _navegacion = AccionAsistente(
  tipo: 'abrir_navegacion',
  latitud: -17.39,
  longitud: -66.15,
  nombre: 'Catedral',
);

Widget _app({
  required ClienteAsistente cliente,
  required VozFalsa voz,
  List<EventoHoy> eventos = const [],
  AccionesFalsas? acciones,
  EfectosGrabados? efectos,
  Ajustes? ajustes,
}) => AplicacionAsistente(
  cliente: cliente,
  voz: voz,
  eventos: EventosFalsos(eventos),
  acciones: acciones ?? AccionesFalsas(),
  efectos: efectos ?? EfectosGrabados(),
  ajustes: ajustes ?? Ajustes.enMemoria(),
);

void main() {
  group('ClienteConsulta (contrato de /api/consulta)', () {
    test('envía el contexto, entiende acciones y fuente, y guarda el contexto nuevo', () async {
      final cuerpos = <Map<String, dynamic>>[];
      final cliente = ClienteConsulta(
        urlBase: 'http://prueba',
        cliente: MockClient((peticion) async {
          expect(peticion.url.path, '/api/consulta');
          cuerpos.add(jsonDecode(peticion.body) as Map<String, dynamic>);
          return http.Response.bytes(
            utf8.encode(
              jsonEncode({
                'respuesta': 'Catedral. Te abro la navegación.',
                'intencion': 'como_llegar',
                'uso_llm': false,
                'fuente': 'base_verificada',
                'fuentes': [
                  {'nombre': 'Verificado el 12/10/2026', 'url': null},
                ],
                'sitio_id': 17,
                'acciones': [
                  {'tipo': 'abrir_navegacion', 'latitud': -17.39, 'longitud': -66.15, 'nombre': 'Catedral'},
                ],
                'escuchar_despues': true,
                'contexto': {
                  'turnos': [
                    {'pregunta': 'a', 'respuesta': 'b'},
                  ],
                  'ultimo_sitio_id': 17,
                  'accion_pendiente': {'tipo': 'abrir_navegacion'},
                },
              }),
            ),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }),
      );

      final r1 = await cliente.preguntar('¿Cómo llego a la Catedral?');
      expect(r1.texto, contains('Te abro la navegación'));
      expect(r1.fuente, 'Verificado el 12/10/2026');
      expect(r1.acciones.single.tipo, 'abrir_navegacion');
      expect(r1.acciones.single.nombre, 'Catedral');
      expect(r1.escucharDespues, isTrue);

      await cliente.preguntar('sí');
      expect(cuerpos.first['canal'], 'app');
      expect(cuerpos.first['contexto']['ultimo_sitio_id'], isNull);
      expect(cuerpos.first.containsKey('latitud'), isFalse); // sin autorización, no se envía ubicación
      // La segunda pregunta devuelve el contexto que dio el servidor.
      expect(cuerpos.last['contexto']['ultimo_sitio_id'], 17);
      expect(cuerpos.last['contexto']['accion_pendiente'], {'tipo': 'abrir_navegacion'});
    });

    test('la fuente de Wikipedia se muestra como «Fuente: Wikipedia»', () async {
      final cliente = ClienteConsulta(
        urlBase: 'http://prueba',
        cliente: MockClient(
          (_) async => http.Response.bytes(
            utf8.encode(
              jsonEncode({
                'respuesta': 'Según Wikipedia, algo.',
                'fuente': 'wikipedia',
                'fuentes': [{'nombre': 'Wikipedia: X', 'url': 'https://es.wikipedia.org/wiki/X'}],
                'acciones': [],
                'escuchar_despues': false,
                'contexto': {'turnos': [], 'ultimo_sitio_id': null, 'accion_pendiente': null},
              }),
            ),
            200,
          ),
        ),
      );
      expect((await cliente.preguntar('leyenda')).fuente, 'Fuente: Wikipedia');
    });

    test('un error 429 da un mensaje claro', () async {
      final cliente = ClienteConsulta(
        urlBase: 'http://prueba',
        cliente: MockClient((_) async => http.Response('{}', 429)),
      );
      expect(
        cliente.preguntar('hola'),
        throwsA(isA<ErrorAsistente>().having((e) => e.mensaje, 'mensaje', contains('muchas preguntas'))),
      );
    });

    test('con la ubicación autorizada se envía solo en la consulta', () async {
      Map<String, dynamic>? cuerpo;
      final cliente = ClienteConsulta(
        urlBase: 'http://prueba',
        ubicacion: _UbicacionFija(),
        cliente: MockClient((p) async {
          cuerpo = jsonDecode(p.body) as Map<String, dynamic>;
          return http.Response(
            jsonEncode({'respuesta': 'ok', 'fuente': 'sistema', 'fuentes': [], 'acciones': [], 'contexto': {}}),
            200,
          );
        }),
      );
      await cliente.preguntar('¿qué hay cerca?');
      expect(cuerpo!['latitud'], -17.39);
      expect(cuerpo!['longitud'], -66.15);
    });
  });

  group('Ajustes', () {
    test('el contacto de confianza guarda solo dígitos', () {
      final a = Ajustes.enMemoria()..contacto = '+591 7000-0000';
      expect(a.contacto, '59170000000');
    });
    test('valores por defecto: voz normal, sonidos y vibración sí, ubicación no', () {
      final a = Ajustes.enMemoria();
      expect(a.velocidad, VelocidadVoz.normal);
      expect(a.sonidos && a.vibracion && a.anunciarEventos, isTrue);
      expect(a.usarUbicacion, isFalse);
    });
  });

  group('Tarjeta «Hoy»', () {
    final evento = const EventoHoy(
      nombre: 'Feria del Api',
      texto: 'Feria del Api, hoy en Plaza Colón.',
      distanciaM: 800,
    );

    testWidgets('muestra el evento más cercano y la guía lo anuncia al abrir', (tester) async {
      telefono(tester);
      final voz = VozFalsa();
      await tester.pumpWidget(_app(cliente: ClienteConAcciones(const RespuestaAsistente(texto: 'x', hayInformacion: true, sitios: [])), voz: voz, eventos: [evento]));
      await avanzar(tester);
      expect(find.textContaining('Hoy cerca de ti · Feria del Api · a 800 m'), findsOneWidget);
      expect(voz.leidos.single, startsWith('Hoy hay: Feria del Api'));
    });

    testWidgets('si se desactiva en Ajustes, no lo anuncia pero la tarjeta sigue', (tester) async {
      telefono(tester);
      final voz = VozFalsa();
      await tester.pumpWidget(_app(
        cliente: ClienteConAcciones(const RespuestaAsistente(texto: 'x', hayInformacion: true, sitios: [])),
        voz: voz,
        eventos: [evento],
        ajustes: Ajustes.enMemoria()..anunciarEventos = false,
      ));
      await avanzar(tester);
      expect(voz.leidos, isEmpty);
      expect(find.textContaining('Feria del Api'), findsOneWidget);
    });

    testWidgets('sin eventos no aparece', (tester) async {
      telefono(tester);
      await tester.pumpWidget(_app(cliente: ClienteConAcciones(const RespuestaAsistente(texto: 'x', hayInformacion: true, sitios: [])), voz: VozFalsa()));
      await avanzar(tester);
      expect(find.textContaining('Escuchar eventos de hoy'), findsNothing);
      expect(find.byIcon(Icons.event), findsNothing);
    });

    testWidgets('al tocarla, la guía lee los eventos de hoy y mide al menos 48 dp', (tester) async {
      telefono(tester);
      final voz = VozFalsa();
      await tester.pumpWidget(_app(
        cliente: ClienteConAcciones(const RespuestaAsistente(texto: 'x', hayInformacion: true, sitios: [])),
        voz: voz,
        eventos: [evento],
        ajustes: Ajustes.enMemoria()..anunciarEventos = false,
      ));
      await avanzar(tester);
      final caja = tester.getSize(find.byType(TarjetaHoy));
      expect(caja.height, greaterThanOrEqualTo(48));
      await tester.tap(find.byIcon(Icons.event));
      await avanzar(tester);
      expect(voz.leidos.single, startsWith('Eventos de hoy: Feria del Api'));
    });
  });

  group('Acciones decididas por el asistente', () {
    testWidgets('la navegación se abre sola al terminar de hablar', (tester) async {
      telefono(tester);
      final voz = VozFalsa();
      final acciones = AccionesFalsas();
      final efectos = EfectosGrabados();
      await tester.pumpWidget(_app(
        cliente: ClienteConAcciones(const RespuestaAsistente(
          texto: 'Catedral. Te abro la navegación.', hayInformacion: true, sitios: [], acciones: [_navegacion],
        )),
        voz: voz, acciones: acciones, efectos: efectos,
      ));
      await escribirYEnviar(tester, '¿Cómo llego a la Catedral?');
      voz.empezarAHablar();
      await avanzar(tester);
      expect(acciones.hechas, isEmpty, reason: 'todavía está hablando');

      voz.terminarDeHablar();
      await tester.pump();
      expect(find.text('Abriendo navegación…'), findsOneWidget); // el estado se comunica por texto
      await tester.pump(const Duration(seconds: 1));
      expect(acciones.hechas, ['nav:Catedral']);
      expect(efectos.eventos, contains('abriendo')); // y por vibración
      await avanzar(tester);
      expect(find.text('Abriendo navegación…'), findsNothing);
    });

    testWidgets('«Detener» mientras habla cancela la navegación anunciada', (tester) async {
      telefono(tester);
      final voz = VozFalsa();
      final acciones = AccionesFalsas();
      await tester.pumpWidget(_app(
        cliente: ClienteConAcciones(const RespuestaAsistente(
          texto: 'Te abro la navegación.', hayInformacion: true, sitios: [], acciones: [_navegacion],
        )),
        voz: voz, acciones: acciones,
      ));
      await escribirYEnviar(tester, '¿Cómo llego a la Catedral?');
      voz.empezarAHablar();
      await avanzar(tester);
      await tester.tap(find.byKey(const Key('boton-hablar'))); // ahora es «Detener»
      await avanzar(tester);
      voz.terminarDeHablar(); // el motor de voz avisa que se cortó
      await tester.pump(const Duration(seconds: 2));
      expect(acciones.hechas, isEmpty);
    });

    testWidgets('compartir deja el mensaje listo (nunca lo envía)', (tester) async {
      telefono(tester);
      final voz = VozFalsa();
      final acciones = AccionesFalsas();
      await tester.pumpWidget(_app(
        cliente: ClienteConAcciones(const RespuestaAsistente(
          texto: 'Te dejo el mensaje listo para enviar.', hayInformacion: true, sitios: [],
          acciones: [AccionAsistente(tipo: 'compartir', texto: 'Hola, estoy usando Guía Cochala.')],
        )),
        voz: voz, acciones: acciones,
      ));
      await escribirYEnviar(tester, 'Avisa a mi familia');
      voz.empezarAHablar();
      voz.terminarDeHablar();
      await tester.pump(const Duration(seconds: 1));
      expect(acciones.hechas, ['compartir:Hola, estoy usando Guía Cochala.']);
    });

    testWidgets('escuchar_despues abre el micrófono solo para oír el «sí»', (tester) async {
      telefono(tester);
      final voz = VozFalsa();
      await tester.pumpWidget(_app(
        cliente: ClienteConAcciones(const RespuestaAsistente(
          texto: 'Catedral. ¿Quieres que te lleve?', hayInformacion: true, sitios: [], escucharDespues: true,
        )),
        voz: voz,
      ));
      await escribirYEnviar(tester, '¿Dónde queda la Catedral?');
      voz.empezarAHablar();
      voz.terminarDeHablar();
      await avanzar(tester);
      expect(find.text(EstadoAsistente.escuchando.etiqueta), findsOneWidget);
    });
  });

  group('Estados: sonido y vibración', () {
    testWidgets('cada cambio de estado avisa a los efectos; un error suena distinto', (tester) async {
      telefono(tester);
      final efectos = EfectosGrabados();
      final voz = VozFalsa();
      await tester.pumpWidget(_app(
        cliente: ClienteConAcciones(const RespuestaAsistente(texto: 'Listo.', hayInformacion: true, sitios: [])),
        voz: voz, efectos: efectos,
      ));
      await escribirYEnviar(tester, 'hola asistente');
      expect(efectos.eventos, containsAllInOrder(['estado:pensando', 'respuesta']));

      // Si no se entiende nada al hablar: texto de error + efecto de error.
      await tester.tap(find.byKey(const Key('boton-hablar')));
      await avanzar(tester);
      voz.silencio();
      await avanzar(tester);
      expect(find.textContaining('No te entendí, intenta de nuevo'), findsOneWidget);
      expect(efectos.eventos, contains('error'));
    });
  });
}

class _UbicacionFija implements ServicioUbicacion {
  @override
  Future<({double latitud, double longitud})?> actual() async => (latitud: -17.39, longitud: -66.15);
  @override
  Future<bool> pedirPermiso() async => true;
}
