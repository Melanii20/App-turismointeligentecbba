import 'dart:ui' show VoidCallback;

import 'package:flutter_tts/flutter_tts.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';

import 'servicios/ajustes.dart';

/// Voz del teléfono: escuchar a la persona (voz -> texto) y leer las respuestas (texto -> voz).
/// Es una interfaz para poder probar la pantalla sin micrófono ni altavoz.
abstract class ServicioVoz {
  /// Empieza a escuchar. Devuelve false si no se pudo (sin permiso o sin reconocimiento de voz).
  /// [alResultado] se llama con el texto parcial y, al final, con el texto definitivo.
  /// [alTerminar] se llama cuando se deja de escuchar, por haber terminado de hablar o por un error.
  Future<bool> iniciarEscucha({
    required void Function(String texto, bool esFinal) alResultado,
    required VoidCallback alTerminar,
  });

  /// Termina de escuchar y entrega lo que se alcanzó a entender.
  Future<void> detenerEscucha();

  /// Lee un texto en voz alta. [alEmpezar] se llama cuando la voz realmente empieza a sonar, y
  /// [alTerminar] al acabar, al interrumpirla o si falla.
  Future<void> hablar(
    String texto, {
    required VoidCallback alEmpezar,
    required VoidCallback alTerminar,
  });

  /// Calla la voz si está hablando.
  Future<void> callar();
}

/// Implementación real con los motores del teléfono (speech_to_text y flutter_tts).
class ServicioVozReal implements ServicioVoz {
  // ignore: prefer_initializing_formals
  ServicioVozReal({Ajustes? ajustes}) : _ajustes = ajustes;

  /// Si se pasan los ajustes, la velocidad de la voz sigue la que eligió la persona.
  final Ajustes? _ajustes;

  // Se crean la primera vez que se usan, no al abrir la app, para no fallar al arrancar.
  late final SpeechToText _oido = SpeechToText();
  late final FlutterTts _boca = FlutterTts();

  bool _oidoListo = false;
  bool _bocaLista = false;
  String? _idioma;
  VoidCallback? _alTerminarEscucha;
  VoidCallback? _alEmpezarHabla;
  VoidCallback? _alTerminarHabla;

  Future<bool> _prepararOido() async {
    if (_oidoListo) return true;
    _oidoListo = await _oido.initialize(
      onStatus: (estado) {
        if (estado == 'done' || estado == 'notListening') {
          _alTerminarEscucha?.call();
        }
      },
      onError: (_) => _alTerminarEscucha?.call(),
    );
    if (_oidoListo) {
      // Se prefiere español de Bolivia; si el teléfono no lo tiene, cualquier español.
      final locales = await _oido.locales();
      final codigos = locales.map((l) => l.localeId).toList();
      _idioma = codigos.firstWhere(
        (c) => c.toLowerCase().replaceAll('-', '_') == 'es_bo',
        orElse: () => codigos.firstWhere(
          (c) => c.toLowerCase().startsWith('es'),
          orElse: () => '',
        ),
      );
      if (_idioma!.isEmpty) _idioma = null;
    }
    return _oidoListo;
  }

  Future<void> _prepararBoca() async {
    if (_bocaLista) return;
    await _boca.setLanguage('es-ES');
    await _boca.setSpeechRate(0.5);
    _boca.setStartHandler(() => _alEmpezarHabla?.call());
    _boca.setCompletionHandler(() => _alTerminarHabla?.call());
    _boca.setCancelHandler(() => _alTerminarHabla?.call());
    _boca.setErrorHandler((_) => _alTerminarHabla?.call());
    _bocaLista = true;
  }

  @override
  Future<bool> iniciarEscucha({
    required void Function(String texto, bool esFinal) alResultado,
    required VoidCallback alTerminar,
  }) async {
    try {
      if (!await _prepararOido()) return false;
      _alTerminarEscucha = alTerminar;
      await _oido.listen(
        onResult: (SpeechRecognitionResult r) =>
            alResultado(r.recognizedWords, r.finalResult),
        listenOptions: SpeechListenOptions(
          partialResults: true,
          cancelOnError: true,
          listenFor: const Duration(seconds: 30),
          pauseFor: const Duration(seconds: 3),
          localeId: _idioma,
        ),
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<void> detenerEscucha() async {
    try {
      await _oido.stop();
    } catch (_) {}
  }

  @override
  Future<void> hablar(
    String texto, {
    required VoidCallback alEmpezar,
    required VoidCallback alTerminar,
  }) async {
    await _prepararBoca();
    _alEmpezarHabla = alEmpezar;
    _alTerminarHabla = alTerminar;
    await _boca.setSpeechRate(_ajustes?.velocidad.valor ?? 0.5);
    await _boca.speak(texto);
  }

  @override
  Future<void> callar() async {
    try {
      await _boca.stop();
    } catch (_) {}
  }
}
