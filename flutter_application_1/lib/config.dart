/// Dirección de la API del asistente.
///
/// Por defecto apunta a 10.0.2.2:8000: desde el emulador de Android, esa dirección es tu PC
/// (el backend del docker-compose, puerto 8000). En un celular real conectado por USB funciona
/// `adb reverse tcp:8000 tcp:8000` con `--dart-define=API_URL=http://localhost:8000`. Para otra dirección:
///   flutter run --dart-define=API_URL=http://192.168.1.10:8000
const String urlApi = String.fromEnvironment(
  'API_URL',
  defaultValue: 'http://10.0.2.2:8000',
);

/// Tiempo máximo de espera de una respuesta.
const Duration esperaMaxima = Duration(seconds: 20);

/// Si el personaje se dibuja con la animación de Rive (abuela2.riv), que es la que cambia de
/// estado (inactivo, escuchando, procesando, hablando). Si Rive no carga, la app usa sola la
/// imagen del personaje con movimientos de Flutter.
/// Para forzar la imagen:  flutter run --dart-define=USAR_RIVE=false
const bool usarRive = bool.fromEnvironment('USAR_RIVE', defaultValue: true);

/// Motor con el que Rive dibuja el personaje: "flutter" (el de Flutter), "rive" (el propio de
/// Rive, que dibuja en una textura) o "panel" (el de Rive con fondo transparente explícito).
/// Si con uno aparece fondo, prueba otro:  flutter run --dart-define=RIVE_MOTOR=flutter
const String motorRive = String.fromEnvironment(
  'RIVE_MOTOR',
  defaultValue: 'panel',
);
