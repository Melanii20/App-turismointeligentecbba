import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/services.dart';

import '../estado_asistente.dart';
import 'ajustes.dart';

/// Sonidos y vibración que acompañan a cada estado (para quien no ve el avatar).
/// Es una interfaz para poder probar la pantalla sin sonido ni vibración.
abstract class Efectos {
  /// Se llama cada vez que cambia el estado (desde _cambiarEstado).
  void alCambiarEstado(EstadoAsistente estado);

  /// Llegó una respuesta (vibración media).
  void respuestaLista();

  /// Error o "no te entendí": dos tonos bajos y doble vibración.
  void error();

  /// Antes de abrir la app de navegación: una vibración.
  void abriendoNavegacion();
}

/// Efectos que no hacen nada (pruebas).
class EfectosNulos implements Efectos {
  const EfectosNulos();
  @override
  void alCambiarEstado(EstadoAsistente estado) {}
  @override
  void respuestaLista() {}
  @override
  void error() {}
  @override
  void abriendoNavegacion() {}
}

/// Efectos reales. Los sonidos son cortos (< 0,5 s) y están en assets/sonidos/.
/// Respetan los ajustes "Sonidos" y "Vibración".
class EfectosReales implements Efectos {
  EfectosReales(this._ajustes);

  final Ajustes _ajustes;
  AudioPlayer? _reproductor;

  Future<void> _sonar(String archivo) async {
    if (!_ajustes.sonidos) return;
    try {
      final r = _reproductor ??= AudioPlayer();
      await r.stop();
      await r.play(AssetSource('sonidos/$archivo'));
    } catch (_) {
      // Sin sonido la app sigue igual: el estado también se comunica por texto y vibración.
    }
  }

  Future<void> _vibrar({bool doble = false, bool suave = false}) async {
    if (!_ajustes.vibracion) return;
    try {
      suave ? await HapticFeedback.lightImpact() : await HapticFeedback.mediumImpact();
      if (doble) {
        await Future<void>.delayed(const Duration(milliseconds: 140));
        await HapticFeedback.mediumImpact();
      }
    } catch (_) {}
  }

  @override
  void alCambiarEstado(EstadoAsistente estado) {
    switch (estado) {
      case EstadoAsistente.escuchando:
        _sonar('escuchar.wav');
        _vibrar(suave: true);
      case EstadoAsistente.pensando:
        _sonar('procesar.wav');
      case EstadoAsistente.reposo:
      case EstadoAsistente.hablando:
        break;
    }
  }

  @override
  void respuestaLista() => _vibrar();

  @override
  void error() {
    _sonar('error.wav');
    _vibrar(doble: true);
  }

  @override
  void abriendoNavegacion() => _vibrar();
}
