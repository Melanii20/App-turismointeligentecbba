import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../cliente_asistente.dart';
import '../config.dart';
import 'ubicacion.dart';

/// Cliente de POST /api/consulta (el contrato de CLAUDE.md).
///
/// Mantiene en memoria el contexto de la conversación (últimos turnos, último sitio y acción
/// pendiente) y lo devuelve en cada pregunta; el servidor no guarda nada. La ubicación se envía
/// solo si la persona la autorizó en Ajustes, y solo en la consulta.
class ClienteConsulta implements ClienteAsistente {
  ClienteConsulta({
    http.Client? cliente,
    this.urlBase = urlApi,
    this.ubicacion = const UbicacionNula(),
  }) : _cliente = cliente ?? http.Client();

  final http.Client _cliente;
  final String urlBase;
  final ServicioUbicacion ubicacion;

  List<dynamic> _turnos = [];
  int? _ultimoSitioId;
  Map<String, dynamic>? _accionPendiente;

  @override
  Future<RespuestaAsistente> preguntar(String pregunta) async {
    final donde = await ubicacion.actual();
    final cuerpo = <String, dynamic>{
      'pregunta': pregunta,
      'canal': 'app',
      'contexto': {
        'turnos': _turnos,
        'ultimo_sitio_id': _ultimoSitioId,
        'accion_pendiente': _accionPendiente,
      },
      if (donde != null) 'latitud': donde.latitud,
      if (donde != null) 'longitud': donde.longitud,
    };

    final http.Response respuesta;
    try {
      respuesta = await _cliente
          .post(
            Uri.parse('$urlBase/api/consulta'),
            headers: {'Content-Type': 'application/json; charset=utf-8'},
            body: jsonEncode(cuerpo),
          )
          .timeout(esperaMaxima);
    } on TimeoutException {
      throw const ErrorAsistente(
        'El asistente tardó demasiado en responder. Intenta de nuevo.',
      );
    } catch (_) {
      throw const ErrorAsistente(
        'No pude conectarme con el asistente. Revisa tu conexión.',
      );
    }

    if (respuesta.statusCode == 429) {
      throw const ErrorAsistente(
        'Hiciste muchas preguntas seguidas. Espera un momento.',
      );
    }
    if (respuesta.statusCode != 200) {
      throw const ErrorAsistente(
        'El asistente tuvo un problema. Intenta de nuevo.',
      );
    }

    final d = jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>;
    final contexto = d['contexto'] as Map<String, dynamic>? ?? const {};
    _turnos = contexto['turnos'] as List? ?? const [];
    _ultimoSitioId = contexto['ultimo_sitio_id'] as int?;
    _accionPendiente = contexto['accion_pendiente'] as Map<String, dynamic>?;

    final fuentes = d['fuentes'] as List? ?? const [];
    final fuente = _lineaDeFuente(d['fuente'] as String?, fuentes);
    final texto = d['respuesta'] as String;
    return RespuestaAsistente(
      texto: texto,
      hayInformacion: d['fuente'] != 'sistema',
      sitios: const [],
      fuente: fuente,
      acciones: (d['acciones'] as List? ?? const [])
          .map((a) => AccionAsistente.desdeJson(a as Map<String, dynamic>))
          .toList(),
      escucharDespues: d['escuchar_despues'] as bool? ?? false,
    );
  }

  /// «Fuente: Wikipedia» o «Verificado el 12/10/2026»; nada si la respuesta es del sistema.
  static String? _lineaDeFuente(String? fuente, List<dynamic> fuentes) {
    if (fuente == 'wikipedia') return 'Fuente: Wikipedia';
    if (fuente == 'base_verificada' && fuentes.isNotEmpty) {
      final nombre = (fuentes.first as Map<String, dynamic>)['nombre'] as String?;
      if (nombre != null && nombre.isNotEmpty) return nombre;
    }
    return null;
  }
}
