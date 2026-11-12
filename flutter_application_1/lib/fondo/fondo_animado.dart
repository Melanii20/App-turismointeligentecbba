import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import '../paleta.dart';
import 'petalos.dart';

/// Fondo decorativo de la pantalla principal: cielo, sol, nubes, cordillera, paisaje,
/// vegetación, pétalos y neblina. Todo es decorativo (ExcludeSemantics).
///
/// Rendimiento:
/// - Va dentro de un RepaintBoundary: lo que se anima aquí no repinta el resto de la pantalla.
/// - Cada capa es su propio RepaintBoundary: lo que se ve borroso se dibuja una vez y después
///   solo se mueve, no se vuelve a calcular el desenfoque en cada cuadro.
/// - Con "reducir animaciones" activado en el teléfono ningún controlador arranca.
class FondoAnimado extends StatefulWidget {
  const FondoAnimado({super.key, required this.baseDelPaisaje});

  /// Altura (desde arriba de la pantalla) donde se apoya la parte de abajo del paisaje.
  final double baseDelPaisaje;

  static const rutaPaisaje = 'assets/personaje/fondo_paisaje_cochabamba.png';

  /// Proporción de la imagen del paisaje (ancho 780, alto 380).
  static const _proporcionPaisaje = 380 / 780;

  @override
  State<FondoAnimado> createState() => _FondoAnimadoState();
}

class _FondoAnimadoState extends State<FondoAnimado>
    with TickerProviderStateMixin {
  // Cada controlador va y vuelve (reverse) con la duración que pide el diseño.
  late final _sol = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 7),
  );
  late final _nubesA = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 38),
  );
  late final _nubesB = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 52),
  );
  late final _cordillera = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 14),
  );
  late final _zoom = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 24),
  );
  // Reloj de los pétalos: da vueltas de 1000 s y su valor se lee como segundos.
  late final _petalosReloj = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 1000),
    upperBound: 1000,
  );

  late final List<AnimationController> _todos = [
    _sol,
    _nubesA,
    _nubesB,
    _cordillera,
    _zoom,
    _petalosReloj,
  ];

  bool? _quieto;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final quieto = MediaQuery.disableAnimationsOf(context);
    if (quieto == _quieto) return;
    _quieto = quieto;
    if (quieto) {
      for (final c in _todos) {
        c.stop();
      }
    } else {
      for (final c in [_sol, _nubesA, _nubesB, _cordillera, _zoom]) {
        c.repeat(reverse: true);
      }
      _petalosReloj.repeat();
    }
  }

  @override
  void dispose() {
    for (final c in _todos) {
      c.dispose();
    }
    super.dispose();
  }

  /// Curva suave para el ir y venir.
  static double _suave(double v) => Curves.easeInOut.transform(v);

  @override
  Widget build(BuildContext context) {
    return ExcludeSemantics(
      child: RepaintBoundary(
        child: LayoutBuilder(
          builder: (context, caja) {
            final w = caja.maxWidth;
            final h = caja.maxHeight;
            final s = w / 390; // todo se escala por el ancho
            final k = h / 844; // las alturas, por el alto
            return Stack(
              clipBehavior: Clip.hardEdge,
              children: [
                // 1. Cielo
                const Positioned.fill(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: Escena.cielo,
                        stops: Escena.cieloParadas,
                      ),
                    ),
                  ),
                ),
                // 2. Sol: late (opacidad 0,7 a 1 y escala 1 a 1,08)
                Positioned(
                  left: 230 * s,
                  top: 120 * k,
                  width: 220 * s,
                  height: 220 * s,
                  child: AnimatedBuilder(
                    animation: _sol,
                    builder: (context, hijo) {
                      final v = _suave(_sol.value);
                      return Opacity(
                        opacity: 0.7 + 0.3 * v,
                        child: Transform.scale(
                          scale: 1 + 0.08 * v,
                          child: hijo,
                        ),
                      );
                    },
                    child: const RepaintBoundary(
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [Escena.sol, Color(0x00FFF6D2)],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                // 3. Nubes (dos grupos que van en sentidos opuestos)
                _grupoDeNubes(
                  control: _nubesA,
                  sentido: 1,
                  s: s,
                  k: k,
                  nubes: const [(30, 150, 140, 36), (190, 225, 180, 28)],
                ),
                _grupoDeNubes(
                  control: _nubesB,
                  sentido: -1,
                  s: s,
                  k: k,
                  nubes: const [(225, 125, 140, 36), (40, 215, 180, 28)],
                ),
                // 4. Cordillera lejana: sube y baja 4 px
                Positioned(
                  left: 0,
                  right: 0,
                  top: 330 * k,
                  height: 120 * k,
                  child: AnimatedBuilder(
                    animation: _cordillera,
                    builder: (context, hijo) => Transform.translate(
                      offset: Offset(0, -4 + 8 * _suave(_cordillera.value)),
                      child: hijo,
                    ),
                    child: const RepaintBoundary(
                      child: CustomPaint(painter: _PintorCordillera()),
                    ),
                  ),
                ),
                // 5. Paisaje con zoom muy lento (1 a 1,06 y 8 px a la izquierda)
                Positioned(
                  left: 0,
                  top:
                      widget.baseDelPaisaje -
                      w * FondoAnimado._proporcionPaisaje,
                  width: w,
                  child: AnimatedBuilder(
                    animation: _zoom,
                    builder: (context, hijo) {
                      final v = _suave(_zoom.value);
                      return Transform.translate(
                        offset: Offset(-8 * s * v, 0),
                        child: Transform.scale(
                          scale: 1 + 0.06 * v,
                          alignment: Alignment.bottomRight,
                          child: hijo,
                        ),
                      );
                    },
                    child: const RepaintBoundary(
                      child: Image(
                        image: AssetImage(FondoAnimado.rutaPaisaje),
                        fit: BoxFit.fitWidth,
                        filterQuality: FilterQuality.low,
                      ),
                    ),
                  ),
                ),
                // 6. Vegetación y lilas de jacarandá
                Positioned.fill(
                  child: RepaintBoundary(
                    child: CustomPaint(painter: _PintorVegetacion(k: k)),
                  ),
                ),
                // 7. Pétalos
                Positioned.fill(
                  child: RepaintBoundary(
                    child: CustomPaint(
                      painter: PintorDePetalos(segundos: _petalosReloj),
                    ),
                  ),
                ),
                // 8. Neblina inferior: transparente a crema en los últimos 300 px
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 0,
                  height: 300 * k,
                  child: const DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [Color(0x00FFFAF3), Escena.neblina],
                      ),
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  /// Un grupo de nubes que se desplaza de lado a lado. Cada nube es un óvalo alargado y
  /// desenfocado (se dibuja una sola vez dentro de su RepaintBoundary y después solo se mueve).
  Widget _grupoDeNubes({
    required AnimationController control,
    required int sentido,
    required double s,
    required double k,
    required List<(double, double, double, double)> nubes,
  }) {
    return Positioned.fill(
      child: AnimatedBuilder(
        animation: control,
        builder: (context, hijo) => Transform.translate(
          offset: Offset(sentido * (-45 + 90 * _suave(control.value)) * s, 0),
          child: hijo,
        ),
        child: RepaintBoundary(
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              for (final (x, y, an, al) in nubes)
                Positioned(
                  // El margen de 24 deja sitio al desenfoque para que no se corte.
                  left: x * s - 24,
                  top: y * k - 24,
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: ImageFiltered(
                      imageFilter: ImageFilter.blur(
                        sigmaX: 8,
                        sigmaY: 8,
                        tileMode: TileMode.decal,
                      ),
                      // Óvalo alargado blanco con opacidad 0,8.
                      child: Container(
                        width: an * s,
                        height: al * s,
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.8),
                          borderRadius: BorderRadius.circular(al * s),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Silueta de montañas lejanas con un pico nevado.
class _PintorCordillera extends CustomPainter {
  const _PintorCordillera();

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;
    final ruta = Path()
      ..moveTo(-20, h)
      ..lineTo(-20, h * 0.55)
      ..lineTo(w * 0.12, h * 0.30)
      ..lineTo(w * 0.24, h * 0.52)
      ..lineTo(w * 0.40, h * 0.12) // pico nevado
      ..lineTo(w * 0.55, h * 0.50)
      ..lineTo(w * 0.70, h * 0.28)
      ..lineTo(w * 0.86, h * 0.55)
      ..lineTo(w + 20, h * 0.35)
      ..lineTo(w + 20, h)
      ..close();
    canvas.drawPath(
      ruta,
      Paint()
        ..color = Escena.montana
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5),
    );
    final nieve = Path()
      ..moveTo(w * 0.40, h * 0.12)
      ..lineTo(w * 0.355, h * 0.26)
      ..lineTo(w * 0.385, h * 0.23)
      ..lineTo(w * 0.40, h * 0.29)
      ..lineTo(w * 0.425, h * 0.23)
      ..lineTo(w * 0.455, h * 0.27)
      ..close();
    canvas.drawPath(
      nieve,
      Paint()
        ..color = Escena.nieve.withValues(alpha: 0.9)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4),
    );
  }

  @override
  bool shouldRepaint(_PintorCordillera anterior) => false;
}

/// Manchas muy difusas: verdes abajo en las esquinas y lilas de jacarandá arriba.
class _PintorVegetacion extends CustomPainter {
  const _PintorVegetacion({required this.k});
  final double k;

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width / 390;
    void mancha(
      Color color,
      double x,
      double y,
      double radio, [
      double opacidad = 1,
    ]) {
      canvas.drawCircle(
        Offset(x * s, y * k),
        radio * s,
        Paint()
          ..color = color.withValues(alpha: opacidad)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14),
      );
    }

    mancha(Escena.verde1, 10, 610, 90);
    mancha(Escena.verde2, 390, 600, 100);
    mancha(Escena.verde1, 60, 660, 60, 0.8);
    mancha(Escena.lila1, 20, 40, 120, 0.45);
    mancha(Escena.lila2, 390, 520, 55, 0.7);
    mancha(Escena.lila1, 370, 650, 45, 0.6);
  }

  @override
  bool shouldRepaint(_PintorVegetacion anterior) => anterior.k != k;
}
