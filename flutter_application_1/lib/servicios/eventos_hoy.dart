import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';
import 'ubicacion.dart';

/// Un evento vigente hoy, tal como lo entrega GET /api/eventos/hoy.
class EventoHoy {
  const EventoHoy({required this.nombre, required this.texto, this.distanciaM});

  final String nombre;

  /// Frase lista para leer: nombre, fechas, hora, zona y distancia.
  final String texto;
  final int? distanciaM;

  factory EventoHoy.desdeJson(Map<String, dynamic> j) => EventoHoy(
    nombre: j['nombre'] as String,
    texto: j['texto'] as String? ?? j['nombre'] as String,
    distanciaM: (j['distancia_m'] as num?)?.round(),
  );

  /// Título corto de la tarjeta: «Hoy cerca de ti · Feria X · a 800 m» o «Hoy · Feria X».
  String titulo({required bool cerca}) {
    final d = distanciaM;
    final lejania = d == null
        ? ''
        : d < 1000
        ? ' · a $d m'
        : ' · a ${(d / 1000).toStringAsFixed(1).replaceAll('.', ',')} km';
    return '${cerca && d != null ? 'Hoy cerca de ti' : 'Hoy'} · $nombre$lejania';
  }
}

/// Eventos de hoy. Interfaz para poder probar la pantalla sin red.
abstract class ServicioEventos {
  Future<List<EventoHoy>> hoy();
}

class EventosNulos implements ServicioEventos {
  const EventosNulos();
  @override
  Future<List<EventoHoy>> hoy() async => const [];
}

class EventosHttp implements ServicioEventos {
  EventosHttp({
    required this.ubicacion,
    http.Client? cliente,
    this.urlBase = urlApi,
  }) : _cliente = cliente ?? http.Client();

  final ServicioUbicacion ubicacion;
  final http.Client _cliente;
  final String urlBase;

  @override
  Future<List<EventoHoy>> hoy() async {
    try {
      final donde = await ubicacion.actual();
      final uri = Uri.parse('$urlBase/api/eventos/hoy').replace(
        queryParameters: donde == null
            ? null
            : {
                'latitud': donde.latitud.toStringAsFixed(5),
                'longitud': donde.longitud.toStringAsFixed(5),
              },
      );
      final r = await _cliente.get(uri).timeout(const Duration(seconds: 8));
      if (r.statusCode != 200) return const [];
      final datos = jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
      return (datos['eventos'] as List? ?? const [])
          .map((e) => EventoHoy.desdeJson(e as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return const []; // sin red o sin servidor: la tarjeta simplemente no aparece
    }
  }
}
