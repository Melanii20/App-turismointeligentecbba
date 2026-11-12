import 'package:geolocator/geolocator.dart';

import 'ajustes.dart';

/// Ubicación de la persona. Solo se pide cuando la necesita una consulta y solo si la persona
/// la autorizó en Ajustes. No se guarda en ningún lado.
abstract class ServicioUbicacion {
  /// (latitud, longitud) o null si no hay permiso, está apagada en Ajustes o no se pudo obtener.
  Future<({double latitud, double longitud})?> actual();

  /// Pide el permiso del sistema. Devuelve true si quedó concedido.
  Future<bool> pedirPermiso();
}

class UbicacionNula implements ServicioUbicacion {
  const UbicacionNula();
  @override
  Future<({double latitud, double longitud})?> actual() async => null;
  @override
  Future<bool> pedirPermiso() async => false;
}

class UbicacionReal implements ServicioUbicacion {
  UbicacionReal(this._ajustes);
  final Ajustes _ajustes;

  @override
  Future<bool> pedirPermiso() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return false;
      var permiso = await Geolocator.checkPermission();
      if (permiso == LocationPermission.denied) {
        permiso = await Geolocator.requestPermission();
      }
      return permiso == LocationPermission.whileInUse ||
          permiso == LocationPermission.always;
    } catch (_) {
      return false;
    }
  }

  @override
  Future<({double latitud, double longitud})?> actual() async {
    if (!_ajustes.usarUbicacion) return null;
    try {
      final permiso = await Geolocator.checkPermission();
      if (permiso != LocationPermission.whileInUse &&
          permiso != LocationPermission.always) {
        return null; // nunca se pide el permiso aquí: solo desde Ajustes, con explicación
      }
      final p = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: Duration(seconds: 8),
        ),
      );
      return (latitud: p.latitude, longitud: p.longitude);
    } catch (_) {
      return null;
    }
  }
}
