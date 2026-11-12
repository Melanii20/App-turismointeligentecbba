import 'dart:convert';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'package:workmanager/workmanager.dart';

import '../config.dart';

/// Aviso diario de eventos (prioridad baja, desactivado por defecto).
///
/// Una vez al día (a las 8:00) una tarea de fondo consulta GET /api/eventos/hoy y, si hay eventos,
/// muestra una notificación local: «Hoy en Cochabamba: (evento) en (zona)». No usa Firebase ni
/// cuentas, y el servidor no guarda nada. Al tocar la notificación, la app se abre y la guía
/// anuncia los eventos de hoy (si «Anunciar los eventos» está activo).
abstract class ServicioAviso {
  /// Activa el aviso. Devuelve false si no se pudo (por ejemplo, sin permiso de notificaciones).
  Future<bool> activar();
  Future<void> desactivar();
}

class AvisoNulo implements ServicioAviso {
  const AvisoNulo();
  @override
  Future<bool> activar() async => false;
  @override
  Future<void> desactivar() async {}
}

const _nombreTarea = 'aviso-diario-eventos';
const _canal = AndroidNotificationDetails(
  'eventos_hoy',
  'Eventos de hoy',
  channelDescription: 'Aviso diario con los eventos de Cochabamba',
  importance: Importance.defaultImportance,
);

/// Función que ejecuta Workmanager en segundo plano. Debe ser de nivel superior.
@pragma('vm:entry-point')
void despachadorDeTareas() {
  Workmanager().executeTask((tarea, datos) async {
    try {
      final r = await http
          .get(Uri.parse('$urlApi/api/eventos/hoy'))
          .timeout(const Duration(seconds: 15));
      if (r.statusCode != 200) return true;
      final eventos =
          (jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>)['eventos'] as List? ?? const [];
      if (eventos.isEmpty) return true;
      final primero = eventos.first as Map<String, dynamic>;
      final zona = (primero['zona'] as String?) ?? '';
      final texto = 'Hoy en Cochabamba: ${primero['nombre']}${zona.isEmpty ? '' : ' en $zona'}';

      final plugin = FlutterLocalNotificationsPlugin();
      await plugin.initialize(
        const InitializationSettings(
          android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        ),
      );
      await plugin.show(
        1,
        'Guía Cochala',
        eventos.length > 1 ? '$texto y ${eventos.length - 1} más' : texto,
        const NotificationDetails(android: _canal),
      );
    } catch (_) {
      // Sin red o sin servidor: no hay aviso hoy. La tarea se vuelve a intentar mañana.
    }
    return true;
  });
}

class AvisoDiarioReal implements ServicioAviso {
  @override
  Future<bool> activar() async {
    try {
      final plugin = FlutterLocalNotificationsPlugin();
      await plugin.initialize(
        const InitializationSettings(
          android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        ),
      );
      // Android 13+ pide permiso de notificaciones.
      final android = plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
      final permitido = await android?.requestNotificationsPermission() ?? true;
      if (!permitido) return false;

      await Workmanager().initialize(despachadorDeTareas);
      final ahora = DateTime.now();
      var proxima = DateTime(ahora.year, ahora.month, ahora.day, 8);
      if (!proxima.isAfter(ahora)) proxima = proxima.add(const Duration(days: 1));
      await Workmanager().registerPeriodicTask(
        _nombreTarea,
        _nombreTarea,
        frequency: const Duration(hours: 24),
        initialDelay: proxima.difference(ahora),
        existingWorkPolicy: ExistingPeriodicWorkPolicy.update,
        constraints: Constraints(networkType: NetworkType.connected),
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<void> desactivar() async {
    try {
      await Workmanager().cancelByUniqueName(_nombreTarea);
    } catch (_) {}
  }
}
