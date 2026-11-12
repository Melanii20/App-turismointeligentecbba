import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_application_1/avatar_asistente.dart';
import 'package:flutter_application_1/cliente_asistente.dart';
import 'package:flutter_application_1/estado_asistente.dart';
import 'package:flutter_application_1/main.dart';
import 'package:flutter_application_1/servicio_voz.dart';
import 'package:flutter_application_1/widgets/avatar_abuela.dart';

const respuestaFalsa = 'La Cancha. El nivel de ruido habitual es alto.';

/// Cliente falso: responde sin red, para probar solo la pantalla.
class ClienteFalso implements ClienteAsistente {
  ClienteFalso({this.falla = false});
  final bool falla;
  final List<String> preguntas = [];

  /// Si se asigna, la respuesta espera a que la prueba lo complete (para ver el estado "pensando").
  Completer<void>? espera;

  @override
  Future<RespuestaAsistente> preguntar(String pregunta) async {
    preguntas.add(pregunta);
    if (espera != null) await espera!.future;
    if (falla) {
      throw const ErrorAsistente(
        'No pude conectarme con el asistente. Revisa tu conexión.',
      );
    }
    return const RespuestaAsistente(
      texto: respuestaFalsa,
      hayInformacion: true,
      sitios: ['La Cancha'],
    );
  }
}

/// Voz falsa: no usa micrófono ni altavoz. Permite "decir" cosas desde la prueba.
class VozFalsa implements ServicioVoz {
  VozFalsa({this.permiteMicrofono = true});
  final bool permiteMicrofono;
  final List<String> leidos = [];
  void Function(String, bool)? _alResultado;
  VoidCallback? _alTerminarEscucha;
  VoidCallback? _alEmpezarHabla;
  VoidCallback? _alTerminarHabla;
  int veceCalladas = 0;

  @override
  Future<bool> iniciarEscucha({
    required void Function(String, bool) alResultado,
    required VoidCallback alTerminar,
  }) async {
    if (!permiteMicrofono) return false;
    _alResultado = alResultado;
    _alTerminarEscucha = alTerminar;
    return true;
  }

  void decir(String texto, {bool esFinal = true}) =>
      _alResultado?.call(texto, esFinal);
  void silencio() => _alTerminarEscucha?.call();
  void empezarAHablar() => _alEmpezarHabla?.call();
  void terminarDeHablar() => _alTerminarHabla?.call();

  @override
  Future<void> detenerEscucha() async {}

  @override
  Future<void> hablar(
    String texto, {
    required VoidCallback alEmpezar,
    required VoidCallback alTerminar,
  }) async {
    leidos.add(texto);
    _alEmpezarHabla = alEmpezar;
    _alTerminarHabla = alTerminar;
  }

  @override
  Future<void> callar() async {
    veceCalladas++;
  }
}

Widget app(ClienteFalso cliente, VozFalsa voz) =>
    AplicacionAsistente(cliente: cliente, voz: voz);

/// Avanza el tiempo un poco. No se usa pumpAndSettle porque el personaje se anima sin parar.
Future<void> avanzar(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
}

Future<void> escribirYEnviar(WidgetTester tester, String texto) async {
  await tester.tap(find.byKey(const Key('boton-escribir')));
  await avanzar(tester);
  await tester.enterText(find.byType(EditableText), texto);
  await tester.tap(find.text('Enviar'));
  await avanzar(tester);
}

/// Pone la pantalla del tamaño de un teléfono común (360 x 740 dp).
void telefono(WidgetTester tester) {
  tester.view.devicePixelRatio = 3;
  tester.view.physicalSize = const Size(360 * 3, 740 * 3);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets('escribir: la respuesta queda por escrito en la tarjeta', (
    tester,
  ) async {
    telefono(tester);
    await tester.pumpWidget(app(ClienteFalso(), VozFalsa()));
    expect(
      find.text('¡Hola, viajero! ¿Qué descubriremos hoy?'),
      findsOneWidget,
    );

    await escribirYEnviar(tester, '¿Es ruidoso La Cancha?');
    expect(find.text(respuestaFalsa), findsOneWidget);
  });

  testWidgets(
    'el personaje pasa por los 4 estados: reposo, pensando, hablando y reposo',
    (tester) async {
      telefono(tester);
      final voz = VozFalsa();
      final cliente = ClienteFalso()..espera = Completer<void>();
      await tester.pumpWidget(app(cliente, voz));
      expect(find.text(EstadoAsistente.reposo.etiqueta), findsOneWidget);

      await escribirYEnviar(tester, 'hola asistente');
      expect(find.text(EstadoAsistente.pensando.etiqueta), findsOneWidget);
      expect(
        find.text('Preguntaste: hola asistente'),
        findsOneWidget,
        reason: 'mientras piensa se ve qué pregunta responde',
      );

      cliente.espera!.complete();
      await tester.pump();
      expect(voz.leidos, [respuestaFalsa]);
      expect(
        find.text(EstadoAsistente.hablando.etiqueta),
        findsNothing,
        reason: '"hablando" empieza cuando la voz suena, no cuando llega el texto',
      );
      expect(find.text(respuestaFalsa), findsOneWidget, reason: 'el texto ya se ve');

      voz.empezarAHablar();
      await tester.pump();
      expect(find.text(EstadoAsistente.hablando.etiqueta), findsOneWidget);

      voz.terminarDeHablar();
      await tester.pump();
      expect(find.text(EstadoAsistente.reposo.etiqueta), findsOneWidget);
    },
  );

  testWidgets('Detener: mientras el asistente habla, el botón central calla la voz', (
    tester,
  ) async {
    telefono(tester);
    final voz = VozFalsa();
    await tester.pumpWidget(app(ClienteFalso(), voz));
    await escribirYEnviar(tester, 'hola asistente');
    voz.empezarAHablar();
    await tester.pump();
    expect(find.text(EstadoAsistente.hablando.etiqueta), findsOneWidget);
    expect(find.text('Detener'), findsOneWidget);

    final antes = voz.veceCalladas;
    await tester.tap(find.byKey(const Key('boton-hablar')));
    await avanzar(tester);
    expect(voz.veceCalladas, greaterThan(antes));
    expect(find.text(EstadoAsistente.reposo.etiqueta), findsOneWidget);
    expect(find.text('Hablar'), findsOneWidget);
  });

  testWidgets('Repetir: vuelve a leer la última respuesta (y pasa otra vez a "hablando")', (
    tester,
  ) async {
    telefono(tester);
    final voz = VozFalsa();
    await tester.pumpWidget(app(ClienteFalso(), voz));
    await escribirYEnviar(tester, 'hola asistente');
    voz.empezarAHablar();
    voz.terminarDeHablar();
    await tester.pump();
    expect(voz.leidos, [respuestaFalsa]);

    await tester.tap(find.byKey(const Key('boton-repetir')));
    await avanzar(tester);
    expect(voz.leidos, [respuestaFalsa, respuestaFalsa]);
    voz.empezarAHablar();
    await tester.pump();
    expect(find.text(EstadoAsistente.hablando.etiqueta), findsOneWidget);
  });

  testWidgets('Repetir funciona aunque la voz esté desactivada en Ajustes (es una orden explícita)', (
    tester,
  ) async {
    telefono(tester);
    final voz = VozFalsa();
    await tester.pumpWidget(
      MediaQuery(
        data: const MediaQueryData(accessibleNavigation: true),
        child: app(ClienteFalso(), voz),
      ),
    );
    await escribirYEnviar(tester, 'hola asistente');
    expect(voz.leidos, isEmpty);
    await tester.tap(find.byKey(const Key('boton-repetir')));
    await avanzar(tester);
    expect(voz.leidos, [respuestaFalsa]);
  });

  testWidgets('si pasan más de 20 segundos sin respuesta: vuelve al reposo, avisa y lo dice', (
    tester,
  ) async {
    telefono(tester);
    final voz = VozFalsa();
    final cliente = ClienteFalso()..espera = Completer<void>(); // nunca responde
    await tester.pumpWidget(app(cliente, voz));
    await escribirYEnviar(tester, 'hola asistente');
    expect(find.text(EstadoAsistente.pensando.etiqueta), findsOneWidget);

    await tester.pump(const Duration(seconds: 19));
    expect(find.text(EstadoAsistente.pensando.etiqueta), findsOneWidget);

    await tester.pump(const Duration(seconds: 2));
    await tester.pump();
    const aviso = 'No se pudo obtener la respuesta. Intenta de nuevo.';
    expect(find.text(aviso), findsOneWidget);
    expect(find.text(EstadoAsistente.pensando.etiqueta), findsNothing);
    expect(voz.leidos, [aviso]);
  });

  test('la boca acompaña al estado: 0 sonrisa, 1 reposo, 2 "mmm", 3 habla automática', () {
    expect(AvatarControl.bocaPorEstado, {0: 10, 1: 0, 2: 11, 3: 12});
    expect(
      [for (final e in EstadoAsistente.values) e.numero],
      [0, 1, 2, 3],
      reason: 'el número de cada estado coincide con "estado" del archivo Rive',
    );
  });

  testWidgets(
    'hablar: pasa a "escuchando", muestra lo entendido y lo envía solo',
    (tester) async {
      telefono(tester);
      final cliente = ClienteFalso();
      final voz = VozFalsa();
      await tester.pumpWidget(app(cliente, voz));

      await tester.tap(find.byKey(const Key('boton-hablar')));
      await avanzar(tester);
      expect(find.text(EstadoAsistente.escuchando.etiqueta), findsOneWidget);
      expect(find.text('Detener'), findsOneWidget);
      expect(find.text('Habla ahora…'), findsOneWidget);

      voz.decir('¿cómo llego a', esFinal: false);
      await tester.pump();
      expect(
        find.text('¿cómo llego a'),
        findsOneWidget,
        reason: 'se ve lo que se va entendiendo',
      );
      expect(cliente.preguntas, isEmpty);

      voz.decir('¿cómo llego a La Cancha?');
      await avanzar(tester);
      expect(cliente.preguntas, ['¿cómo llego a La Cancha?']);
      expect(find.text(respuestaFalsa), findsOneWidget);
    },
  );

  testWidgets(
    'hablar: si se calla sin terminar de entender, envía lo que haya entendido',
    (tester) async {
      telefono(tester);
      final cliente = ClienteFalso();
      final voz = VozFalsa();
      await tester.pumpWidget(app(cliente, voz));
      await tester.tap(find.byKey(const Key('boton-hablar')));
      await avanzar(tester);
      voz.decir('ruido en el mercado', esFinal: false);
      voz.silencio();
      await avanzar(tester);
      expect(cliente.preguntas, ['ruido en el mercado']);
    },
  );

  testWidgets('sin permiso de micrófono: lo dice por escrito y no se rompe', (
    tester,
  ) async {
    telefono(tester);
    await tester.pumpWidget(
      app(ClienteFalso(), VozFalsa(permiteMicrofono: false)),
    );
    await tester.tap(find.byKey(const Key('boton-hablar')));
    await avanzar(tester);
    expect(find.textContaining('No pude usar el micrófono'), findsOneWidget);
    expect(find.text(EstadoAsistente.reposo.etiqueta), findsOneWidget);
  });

  testWidgets(
    'voz desactivada en Ajustes: la respuesta solo se escribe y no se lee',
    (tester) async {
      telefono(tester);
      final voz = VozFalsa();
      await tester.pumpWidget(app(ClienteFalso(), voz));
      await tester.tap(find.byKey(const Key('boton-ajustes')));
      await avanzar(tester);
      expect(find.byKey(const Key('boton-historial')), findsOneWidget);
      // Ahora Ajustes tiene varios interruptores; el de la voz es el primero.
      await tester.tap(find.byType(Switch).first);
      await avanzar(tester);
      // Cierra la hoja de Ajustes (ahora es más alta, así que no queda barrera donde tocar).
      Navigator.of(tester.element(find.byType(Switch).first)).pop();
      await avanzar(tester);

      await escribirYEnviar(tester, 'hola asistente');
      expect(voz.leidos, isEmpty);
      expect(find.text(respuestaFalsa), findsOneWidget);
      expect(find.text(EstadoAsistente.reposo.etiqueta), findsOneWidget);
    },
  );

  testWidgets('con lector de pantalla activado la voz propia empieza apagada', (
    tester,
  ) async {
    telefono(tester);
    final voz = VozFalsa();
    await tester.pumpWidget(
      MediaQuery(
        data: const MediaQueryData(accessibleNavigation: true),
        child: app(ClienteFalso(), voz),
      ),
    );
    await escribirYEnviar(tester, 'hola asistente');
    expect(voz.leidos, isEmpty);
    expect(find.text(respuestaFalsa), findsOneWidget);
  });

  testWidgets('si falla la conexión, lo dice con un mensaje claro', (
    tester,
  ) async {
    telefono(tester);
    await tester.pumpWidget(app(ClienteFalso(falla: true), VozFalsa()));
    await escribirYEnviar(tester, 'hola asistente');
    expect(find.textContaining('No pude conectarme'), findsOneWidget);
  });

  testWidgets(
    'escribir: una pregunta casi vacía no se envía y se explica por qué',
    (tester) async {
      telefono(tester);
      final cliente = ClienteFalso();
      await tester.pumpWidget(app(cliente, VozFalsa()));
      await escribirYEnviar(tester, ' a ');
      expect(cliente.preguntas, isEmpty);
      expect(find.text('Escribe al menos 2 letras.'), findsOneWidget);
    },
  );

  testWidgets('Historial: muestra toda la conversación', (tester) async {
    telefono(tester);
    await tester.pumpWidget(app(ClienteFalso(), VozFalsa()));
    await escribirYEnviar(tester, '¿Es ruidoso La Cancha?');
    await tester.tap(find.byKey(const Key('boton-ajustes')));
    await avanzar(tester);
    await tester.tap(find.byKey(const Key('boton-historial')));
    await avanzar(tester);
    expect(find.text('Historial de la conversación'), findsOneWidget);
    expect(find.text('¿Es ruidoso La Cancha?'), findsOneWidget);
    expect(find.text(respuestaFalsa), findsWidgets);
    expect(find.textContaining('¡Hola, viajero!'), findsWidgets);
  });

  testWidgets('Ayuda: abre las instrucciones de uso', (tester) async {
    telefono(tester);
    await tester.pumpWidget(app(ClienteFalso(), VozFalsa()));
    await tester.tap(find.byKey(const Key('boton-ayuda')));
    await avanzar(tester);
    expect(find.textContaining('Hablar: toca el micrófono'), findsOneWidget);
  });

  group('accesibilidad', () {
    const botones = {
      'boton-repetir': ('Repetir', 'Repetir la última respuesta'),
      'boton-hablar': ('Hablar', 'Hablar con la guía'),
      'boton-escribir': ('Escribir', 'Escribir una pregunta'),
    };

    testWidgets(
      'cada botón tiene nombre, su nombre contiene el texto visible y mide al menos 48 dp',
      (tester) async {
        telefono(tester);
        final asegurar = tester.ensureSemantics();
        await tester.pumpWidget(app(ClienteFalso(), VozFalsa()));
        for (final e in botones.entries) {
          final (visible, accesible) = e.value;
          expect(
            find.text(visible),
            findsOneWidget,
            reason: 'el botón muestra "$visible"',
          );
          final nodo = tester.getSemantics(find.byKey(Key(e.key)));
          expect(nodo.label, accesible);
          expect(
            nodo.label.contains(visible),
            isTrue,
            reason: 'el nombre accesible debe incluir el texto visible',
          );
          final tam = tester.getSize(find.byKey(Key(e.key)));
          expect(
            tam.width >= 48 && tam.height >= 48,
            isTrue,
            reason: '${e.key} mide $tam',
          );
        }
        // Ayuda y Ajustes están en la barra de arriba, con nombre propio para TalkBack.
        for (final (clave, nombre) in [
          ('boton-ayuda', 'Ayuda'),
          ('boton-ajustes', 'Ajustes'),
        ]) {
          final tam = tester.getSize(find.byKey(Key(clave)));
          expect(
            tam.width >= 48 && tam.height >= 48,
            isTrue,
            reason: '$clave mide $tam',
          );
          final nodo = tester.getSemantics(find.byKey(Key(clave)));
          expect(
            '${nodo.label} ${nodo.tooltip}',
            contains(nombre),
            reason: 'TalkBack debe poder leer "$nombre"',
          );
        }
        await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
        await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
        asegurar.dispose();
      },
    );

    for (final brillo in [Brightness.light, Brightness.dark]) {
      testWidgets(
        'los textos tienen contraste suficiente en modo ${brillo.name}',
        (tester) async {
          telefono(tester);
          tester.platformDispatcher.platformBrightnessTestValue = brillo;
          addTearDown(
            tester.platformDispatcher.clearPlatformBrightnessTestValue,
          );
          final asegurar = tester.ensureSemantics();
          await tester.pumpWidget(app(ClienteFalso(), VozFalsa()));
          await avanzar(tester);
          await expectLater(tester, meetsGuideline(textContrastGuideline));
          asegurar.dispose();
        },
      );
    }

    testWidgets('el personaje es decorativo: TalkBack lo ignora', (
      tester,
    ) async {
      telefono(tester);
      final asegurar = tester.ensureSemantics();
      await tester.pumpWidget(app(ClienteFalso(), VozFalsa()));
      expect(
        find.descendant(
          of: find.byType(AvatarAsistente),
          matching: find.byType(ExcludeSemantics),
        ),
        findsWidgets,
      );
      expect(
        find.bySemanticsLabel(RegExp('personaje|imagen', caseSensitive: false)),
        findsNothing,
      );
      asegurar.dispose();
    });

    testWidgets(
      'la respuesta nueva se anuncia a TalkBack como región viva, diciendo quién habla',
      (tester) async {
        telefono(tester);
        final asegurar = tester.ensureSemantics();
        await tester.pumpWidget(app(ClienteFalso(), VozFalsa()));
        await escribirYEnviar(tester, 'hola asistente');
        final nodo = tester.getSemantics(
          find.bySemanticsLabel(RegExp('^Guía: La Cancha')),
        );
        expect(nodo.label, 'Guía: $respuestaFalsa');
        expect(nodo.flagsCollection.isLiveRegion, isTrue);
        asegurar.dispose();
      },
    );

    testWidgets(
      'el orden de lectura es: título, globo, estado, Hablar, Escribir, Repetir',
      (tester) async {
        telefono(tester);
        final asegurar = tester.ensureSemantics();
        await tester.pumpWidget(app(ClienteFalso(), VozFalsa()));
        await avanzar(tester);
        final etiquetas = [
          'Tu guía de Cochabamba',
          '¡Hola, viajero!',
          'En espera',
          'Hablar con la guía',
          'Escribir una pregunta',
          'Repetir la última respuesta',
        ];
        final orden = <int>[];
        for (final e in etiquetas) {
          final nodo = tester.getSemantics(find.bySemanticsLabel(RegExp(e)));
          orden.add(nodo.sortKey is OrdinalSortKey
              ? (nodo.sortKey! as OrdinalSortKey).order.toInt()
              : -1);
        }
        expect(orden, [0, 1, 2, 3, 4, 5]);
        asegurar.dispose();
      },
    );

    testWidgets('con "quitar animaciones" nada se mueve', (tester) async {
      telefono(tester);
      await tester.pumpWidget(
        MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: app(ClienteFalso(), VozFalsa()),
        ),
      );
      await tester.pump(const Duration(seconds: 1));
      expect(tester.hasRunningAnimations, isFalse);
    });

    for (final escala in [1.5, 2.0]) {
      testWidgets(
        'con letra al ${(escala * 100).round()}% no se desborda la pantalla',
        (tester) async {
          telefono(tester);
          await tester.pumpWidget(
            MediaQuery(
              data: MediaQueryData(textScaler: TextScaler.linear(escala)),
              child: app(ClienteFalso(), VozFalsa()),
            ),
          );
          await avanzar(tester);
          expect(tester.takeException(), isNull);
          await tester.tap(find.byKey(const Key('boton-escribir')));
          await avanzar(tester);
          expect(tester.takeException(), isNull);
        },
      );
    }
  });
}
