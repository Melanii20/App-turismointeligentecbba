import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../paleta.dart';

/// Los 8 pétalos de jacarandá que caen. Se dibujan todos juntos en un solo CustomPainter
/// que se repinta con un único AnimationController (no son 8 widgets animados).
///
/// [segundos] es el reloj: un valor que crece (en segundos). Cada pétalo tiene su duración
/// (13 a 17 s) y su retraso, así que nunca caen todos a la vez.
class PintorDePetalos extends CustomPainter {
  PintorDePetalos({required this.segundos}) : super(repaint: segundos);

  final Animation<double> segundos;

  // (posición horizontal 0..1, duración s, retraso s, balanceo en px, color)
  static const _petalos = [
    (0.06, 15.0, 0.0, 14.0, Escena.petalo1),
    (0.22, 13.0, 3.5, 10.0, Escena.petalo2),
    (0.38, 16.0, 7.0, 18.0, Escena.petalo1),
    (0.52, 14.0, 1.5, 12.0, Escena.petalo2),
    (0.66, 17.0, 9.5, 16.0, Escena.petalo1),
    (0.78, 13.5, 5.0, 11.0, Escena.petalo2),
    (0.90, 15.5, 11.0, 15.0, Escena.petalo1),
    (0.46, 16.5, 12.5, 13.0, Escena.petalo2),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final escala = size.width / 390;
    final t = segundos.value;
    for (var i = 0; i < _petalos.length; i++) {
      final (x, duracion, retraso, balanceo, color) = _petalos[i];
      final fase = ((t + retraso) % duracion) / duracion; // 0 arriba, 1 abajo
      final dx =
          x * size.width +
          math.sin(fase * 2 * math.pi * 2 + i) * balanceo * escala;
      final dy = -12 + fase * (size.height + 24);
      // Aparece y desaparece suavemente en los extremos.
      final opacidad = (math.min(fase, 1 - fase) * 8).clamp(0.0, 1.0) * 0.9;
      canvas
        ..save()
        ..translate(dx, dy)
        ..rotate(fase * 2 * math.pi * 1.5 + i);
      canvas.drawOval(
        Rect.fromCenter(
          center: Offset.zero,
          width: 11 * escala,
          height: 7 * escala,
        ),
        Paint()
          ..color = color.withValues(alpha: opacidad)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 0.6),
      );
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(PintorDePetalos anterior) => false; // se repinta por [segundos]
}
