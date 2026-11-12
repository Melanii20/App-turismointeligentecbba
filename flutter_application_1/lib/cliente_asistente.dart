import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'config.dart';

/// Lo que devuelve la API del asistente para una pregunta.
class RespuestaAsistente {
  const RespuestaAsistente({
    required this.texto,
    required this.hayInformacion,
    required this.sitios,
    this.fuente,
    this.acciones = const [],
    this.escucharDespues = false,
  });

  final String texto;
  final bool hayInformacion;
  final List<String> sitios; // nombres de los sitios usados para responder

  /// Línea corta de la fuente: «Fuente: Wikipedia» o «Verificado el 12/10/2026». Null si no hay.
  final String? fuente;

  /// Acciones que decidió el asistente; la app las ejecuta sola al terminar de hablar.
  final List<AccionAsistente> acciones;

  /// Si la app debe abrir el micrófono al terminar de hablar (esperando un «sí» o un «no»).
  final bool escucharDespues;
}

/// Una acción decidida por el asistente: abrir la navegación o dejar un mensaje listo para enviar.
class AccionAsistente {
  const AccionAsistente({
    required this.tipo,
    this.latitud,
    this.longitud,
    this.nombre,
    this.texto,
    this.numeroContacto,
  });

  factory AccionAsistente.desdeJson(Map<String, dynamic> j) => AccionAsistente(
    tipo: j['tipo'] as String,
    latitud: (j['latitud'] as num?)?.toDouble(),
    longitud: (j['longitud'] as num?)?.toDouble(),
    nombre: j['nombre'] as String?,
    texto: j['texto'] as String?,
    numeroContacto: j['numero_contacto'] as String?,
  );

  final String tipo; // abrir_navegacion | compartir
  final double? latitud;
  final double? longitud;
  final String? nombre;
  final String? texto;
  final String? numeroContacto;
}

/// Error con un mensaje listo para mostrar a la persona.
class ErrorAsistente implements Exception {
  const ErrorAsistente(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}

/// Contrato del cliente. Existe para poder probar la pantalla sin red.
abstract class ClienteAsistente {
  Future<RespuestaAsistente> preguntar(String pregunta);
}

/// Cliente real: habla con la API FastAPI de la carpeta asistente/.
class ClienteHttp implements ClienteAsistente {
  ClienteHttp({http.Client? cliente, this.urlBase = urlApi})
    : _cliente = cliente ?? http.Client();

  final http.Client _cliente;
  final String urlBase;

  @override
  Future<RespuestaAsistente> preguntar(String pregunta) async {
    final http.Response respuesta;
    try {
      respuesta = await _cliente
          .post(
            Uri.parse('$urlBase/preguntar'),
            headers: {'Content-Type': 'application/json; charset=utf-8'},
            body: jsonEncode({'pregunta': pregunta}),
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

    final datos =
        jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>;
    final sitios = (datos['sitios'] as List? ?? const [])
        .map((s) => (s as Map<String, dynamic>)['nombre'] as String)
        .toList();
    return RespuestaAsistente(
      texto: datos['respuesta'] as String,
      hayInformacion: datos['hay_informacion'] as bool,
      sitios: sitios,
    );
  }
}
