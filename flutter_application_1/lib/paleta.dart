import 'package:flutter/material.dart';

/// ÚNICA tabla de colores de la app. Ningún otro archivo escribe colores a mano:
/// todo sale de aquí (directo o a través del tema).
///
/// Cada par texto/fondo cumple WCAG AA: 4,5:1 para texto y 3:1 para bordes e íconos.
/// Lo comprueba test/paleta_test.dart; si se cambia un color y deja de cumplir, la prueba falla.
///
/// Origen de los colores: el crema del fondo del personaje, el azul de su pollera y el
/// fucsia de su manta, oscurecidos o aclarados lo necesario para que se lean bien.
class Paleta {
  const Paleta({
    required this.fondo,
    required this.superficie,
    required this.superficieAlta,
    required this.texto,
    required this.textoSuave,
    required this.primario,
    required this.sobrePrimario,
    required this.acento,
    required this.sobreAcento,
    required this.error,
    required this.sobreError,
    required this.borde,
  });

  /// Fondo de la pantalla.
  final Color fondo;

  /// Tarjetas y hojas (mensaje del asistente, ajustes).
  final Color superficie;

  /// Superficies secundarias (etiqueta de estado, burbujas del historial).
  final Color superficieAlta;

  /// Texto principal y texto secundario.
  final Color texto;
  final Color textoSuave;

  /// Acción principal (botón Hablar) y su texto o ícono.
  final Color primario;
  final Color sobrePrimario;

  /// Estado "escuchando" y su texto o ícono.
  final Color acento;
  final Color sobreAcento;

  /// Errores y su texto o ícono.
  final Color error;
  final Color sobreError;

  /// Bordes de botones, tarjetas y campos de texto.
  final Color borde;

  /// Fondo crema del personaje; es el mismo en modo claro y oscuro porque es el de la ilustración.
  static const Color fondoPersonaje = Color(0xFFF9EDDC);

  static const Paleta claro = Paleta(
    fondo: Color(0xFFFAF5EC),
    superficie: Color(0xFFFFFFFF),
    superficieAlta: Color(0xFFF1E7D6),
    texto: Color(0xFF1B1F2A),
    textoSuave: Color(0xFF454B59),
    primario: Color(0xFF1B4F8F),
    sobrePrimario: Color(0xFFFFFFFF),
    acento: Color(0xFFA31560),
    sobreAcento: Color(0xFFFFFFFF),
    error: Color(0xFFB3261E),
    sobreError: Color(0xFFFFFFFF),
    borde: Color(0xFF6A6F7B),
  );

  static const Paleta oscuro = Paleta(
    fondo: Color(0xFF12151C),
    superficie: Color(0xFF1C212B),
    superficieAlta: Color(0xFF272D3A),
    texto: Color(0xFFF2EEE6),
    textoSuave: Color(0xFFC5C9D3),
    primario: Color(0xFF9CC1F5),
    sobrePrimario: Color(0xFF0B2545),
    acento: Color(0xFFF5A3C9),
    sobreAcento: Color(0xFF3A0A22),
    error: Color(0xFFFFB4AB),
    sobreError: Color(0xFF5C0F0A),
    borde: Color(0xFF8E94A3),
  );

  /// Pares (texto, fondo, mínimo exigido) que deben cumplir contraste. Los usa la prueba.
  List<(String, Color, Color, double)> get paresAContrastar => [
    ('texto sobre fondo', texto, fondo, 4.5),
    ('texto sobre superficie', texto, superficie, 4.5),
    ('texto sobre superficie alta', texto, superficieAlta, 4.5),
    ('texto suave sobre fondo', textoSuave, fondo, 4.5),
    ('texto suave sobre superficie', textoSuave, superficie, 4.5),
    ('texto suave sobre superficie alta', textoSuave, superficieAlta, 4.5),
    ('texto sobre primario', sobrePrimario, primario, 4.5),
    ('texto sobre acento', sobreAcento, acento, 4.5),
    ('texto sobre error', sobreError, error, 4.5),
    ('primario sobre fondo (ícono, etiqueta)', primario, fondo, 4.5),
    ('primario sobre superficie (ícono)', primario, superficie, 4.5),
    ('borde sobre fondo', borde, fondo, 3.0),
    ('borde sobre superficie', borde, superficie, 3.0),
    ('acento sobre fondo (borde del personaje)', acento, fondo, 3.0),
    ('primario sobre fondo (borde del personaje)', primario, fondo, 3.0),
  ];

  ColorScheme esquema(Brightness brillo) => ColorScheme(
    brightness: brillo,
    primary: primario,
    onPrimary: sobrePrimario,
    secondary: acento,
    onSecondary: sobreAcento,
    secondaryContainer: superficieAlta,
    onSecondaryContainer: texto,
    error: error,
    onError: sobreError,
    surface: superficie,
    onSurface: texto,
    onSurfaceVariant: textoSuave,
    surfaceContainerHighest: superficieAlta,
    outline: borde,
    outlineVariant: borde,
  );

  ThemeData tema(Brightness brillo) {
    final redondeo = BorderRadius.circular(14);
    return ThemeData(
      useMaterial3: true,
      colorScheme: esquema(brillo),
      scaffoldBackgroundColor: fondo,
      appBarTheme: AppBarTheme(
        backgroundColor: fondo,
        foregroundColor: texto,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        titleTextStyle: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w600,
          color: texto,
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: superficie,
        surfaceTintColor: Colors.transparent,
        showDragHandle: true,
        dragHandleColor: borde,
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(borderRadius: redondeo),
        enabledBorder: OutlineInputBorder(
          borderRadius: redondeo,
          borderSide: BorderSide(color: borde, width: 1.5),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: redondeo,
          borderSide: BorderSide(color: primario, width: 3),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: redondeo,
          borderSide: BorderSide(color: error, width: 2),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: redondeo,
          borderSide: BorderSide(color: error, width: 3),
        ),
        labelStyle: TextStyle(color: textoSuave, fontSize: 18),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(48, 56),
          textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          shape: RoundedRectangleBorder(borderRadius: redondeo),
        ),
      ),
      switchTheme: SwitchThemeData(
        trackOutlineColor: WidgetStatePropertyAll(borde),
      ),
    );
  }
}

/// Colores de la escena de la pantalla principal (cielo, paisaje, botones). Es una escena de día
/// que se ve igual en modo claro y oscuro. Los textos van sobre fondos claros: los pares que
/// importan están en [pares] y los comprueba test/paleta_test.dart.
class Escena {
  const Escena._();

  // Cielo, de arriba hacia abajo.
  static const cielo = [
    Color(0xFFB9D9F2),
    Color(0xFFDCEBF7),
    Color(0xFFF6EEE6),
    Color(0xFFFFF3E2),
  ];
  static const cieloParadas = [0.0, 0.38, 0.62, 1.0];

  static const sol = Color(0xFFFFF6D2);
  static const montana = Color(0xFF9FB9D6);
  static const nieve = Color(0xFFFFFFFF);
  static const verde1 = Color(0xFF9CC28E);
  static const verde2 = Color(0xFFA9CD97);
  static const lila1 = Color(0xFFB9A0DD);
  static const lila2 = Color(0xFFB48AD8);
  static const petalo1 = Color(0xFFA57BD3);
  static const petalo2 = Color(0xFFC29BE6);
  static const neblina = Color(0xFFFFFAF3);

  /// Texto principal (título, globo, nombres de botones) y texto del estado.
  static const tinta = Color(0xFF1F2A44);
  static const tintaSuave = Color(0xFF3A4660);

  /// Azul de acento (palabra "Cochabamba", botón Hablar).
  static const acento = Color(0xFF1F6FB8);
  static const sobreAcento = Color(0xFFFFFFFF);

  static const blanco = Color(0xFFFFFFFF);

  /// (nombre, texto, fondo más desfavorable, mínimo). El título es texto grande: pide 3:1.
  static const List<(String, Color, Color, double)> pares = [
    ('título sobre cielo', tinta, Color(0xFFB9D9F2), 4.5),
    ('"Cochabamba" (acento) sobre cielo, texto grande', acento, Color(0xFFB9D9F2), 3.0),
    ('globo: texto sobre blanco', tinta, blanco, 4.5),
    ('estado sobre neblina', tintaSuave, neblina, 4.5),
    ('estado sobre cielo bajo', tintaSuave, Color(0xFFF6EEE6), 4.5),
    ('botón Hablar: ícono sobre acento', sobreAcento, acento, 4.5),
    ('nombres de botones sobre blanco', tinta, blanco, 4.5),
    ('ícono de acento sobre blanco', acento, blanco, 4.5),
  ];
}
