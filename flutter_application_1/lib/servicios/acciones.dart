import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import 'ajustes.dart';

/// Acciones que decide el asistente (no hay botones de acción). Se ejecutan al terminar de hablar.
abstract class EjecutorAcciones {
  /// Abre una app de navegación hacia el punto.
  Future<void> abrirNavegacion(double latitud, double longitud, String nombre);

  /// Deja el mensaje listo para enviar. Nunca lo envía: la persona pulsa enviar.
  Future<void> compartir(String texto, {String? numeroContacto});
}

class AccionesNulas implements EjecutorAcciones {
  const AccionesNulas();
  @override
  Future<void> abrirNavegacion(double latitud, double longitud, String nombre) async {}
  @override
  Future<void> compartir(String texto, {String? numeroContacto}) async {}
}

/// Todo gratis y sin claves: `geo:` y la URL de Google Maps sin clave; `wa.me`, `sms:` y la hoja de
/// compartir de Android.
class AccionesReales implements EjecutorAcciones {
  AccionesReales(this._ajustes);
  final Ajustes _ajustes;

  @override
  Future<void> abrirNavegacion(double latitud, double longitud, String nombre) async {
    final etiqueta = Uri.encodeComponent(nombre);
    final geo = Uri.parse('geo:0,0?q=$latitud,$longitud($etiqueta)');
    try {
      // La primera vez, Android pregunta con qué app abrirla; la persona puede marcar "siempre".
      if (await launchUrl(geo, mode: LaunchMode.externalApplication)) return;
    } catch (_) {}
    // Respaldo: enlace gratuito de Google Maps (sin clave de API), a pie.
    final web = Uri.parse(
      'https://www.google.com/maps/dir/?api=1&destination=$latitud,$longitud&travelmode=walking',
    );
    await launchUrl(web, mode: LaunchMode.externalApplication);
  }

  @override
  Future<void> compartir(String texto, {String? numeroContacto}) async {
    final numero = (numeroContacto?.isNotEmpty ?? false)
        ? numeroContacto!
        : _ajustes.contacto;
    if (numero.isNotEmpty) {
      final texto2 = Uri.encodeComponent(texto);
      try {
        if (await launchUrl(
          Uri.parse('https://wa.me/$numero?text=$texto2'),
          mode: LaunchMode.externalApplication,
        )) {
          return;
        }
      } catch (_) {}
      try {
        if (await launchUrl(Uri.parse('sms:$numero?body=$texto2'))) return;
      } catch (_) {}
    }
    await SharePlus.instance.share(ShareParams(text: texto));
  }
}
