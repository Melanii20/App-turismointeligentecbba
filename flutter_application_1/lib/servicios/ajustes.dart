import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Velocidad de la voz del asistente. TalkBack suele usarse rápido, por eso hay tres opciones.
enum VelocidadVoz {
  lenta('Lenta', 0.35),
  normal('Normal', 0.5),
  rapida('Rápida', 0.7);

  const VelocidadVoz(this.etiqueta, this.valor);
  final String etiqueta;

  /// Valor que entiende flutter_tts (0 a 1).
  final double valor;
}

/// Ajustes de la persona. Se guardan SOLO en el teléfono (shared_preferences): nada de esto
/// (ni el contacto de confianza) se envía al servidor.
class Ajustes extends ChangeNotifier {
  Ajustes._(this._prefs);

  /// Ajustes que no se guardan (para pruebas o si el almacenamiento falla).
  Ajustes.enMemoria() : _prefs = null;

  final SharedPreferences? _prefs;

  VelocidadVoz _velocidad = VelocidadVoz.normal;
  bool _anunciarEventos = true;
  bool _sonidos = true;
  bool _vibracion = true;
  bool _usarUbicacion = false;
  bool _avisoDiario = false;
  String _contacto = '';

  VelocidadVoz get velocidad => _velocidad;
  bool get anunciarEventos => _anunciarEventos;
  bool get sonidos => _sonidos;
  bool get vibracion => _vibracion;

  /// Si la persona aceptó compartir su ubicación. Solo se usa en la consulta que la necesita.
  bool get usarUbicacion => _usarUbicacion;

  /// Aviso diario de eventos (notificación local a las 8:00). Desactivado por defecto.
  bool get avisoDiario => _avisoDiario;

  /// Número del contacto de confianza (con código de país, solo dígitos). Vacío = sin contacto.
  String get contacto => _contacto;

  /// Lee los ajustes guardados. Si no se pueden leer, usa los valores por defecto.
  static Future<Ajustes> cargar() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final a = Ajustes._(prefs);
      final nombre = prefs.getString('velocidad_voz');
      a._velocidad = VelocidadVoz.values.firstWhere(
        (v) => v.name == nombre,
        orElse: () => VelocidadVoz.normal,
      );
      a._anunciarEventos = prefs.getBool('anunciar_eventos') ?? true;
      a._sonidos = prefs.getBool('sonidos') ?? true;
      a._vibracion = prefs.getBool('vibracion') ?? true;
      a._usarUbicacion = prefs.getBool('usar_ubicacion') ?? false;
      a._avisoDiario = prefs.getBool('aviso_diario') ?? false;
      a._contacto = prefs.getString('contacto_confianza') ?? '';
      return a;
    } catch (_) {
      return Ajustes.enMemoria();
    }
  }

  void _guardar(String clave, Object valor) {
    notifyListeners();
    final prefs = _prefs;
    if (prefs == null) return;
    try {
      if (valor is bool) {
        prefs.setBool(clave, valor);
      } else if (valor is String) {
        prefs.setString(clave, valor);
      }
    } catch (_) {}
  }

  set velocidad(VelocidadVoz v) {
    _velocidad = v;
    _guardar('velocidad_voz', v.name);
  }

  set anunciarEventos(bool v) {
    _anunciarEventos = v;
    _guardar('anunciar_eventos', v);
  }

  set sonidos(bool v) {
    _sonidos = v;
    _guardar('sonidos', v);
  }

  set vibracion(bool v) {
    _vibracion = v;
    _guardar('vibracion', v);
  }

  set usarUbicacion(bool v) {
    _usarUbicacion = v;
    _guardar('usar_ubicacion', v);
  }

  set avisoDiario(bool v) {
    _avisoDiario = v;
    _guardar('aviso_diario', v);
  }

  /// Guarda solo dígitos (quita espacios, guiones y el signo +), listo para wa.me.
  set contacto(String v) {
    _contacto = v.replaceAll(RegExp(r'[^0-9]'), '');
    _guardar('contacto_confianza', _contacto);
  }
}
