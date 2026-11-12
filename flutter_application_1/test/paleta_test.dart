import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_application_1/paleta.dart';

/// Relación de contraste WCAG entre dos colores (de 1:1 a 21:1).
double contraste(Color a, Color b) {
  final x = a.computeLuminance();
  final y = b.computeLuminance();
  final claro = x > y ? x : y;
  final oscuro = x > y ? y : x;
  return (claro + 0.05) / (oscuro + 0.05);
}

void main() {
  for (final (nombre, paleta) in [
    ('claro', Paleta.claro),
    ('oscuro', Paleta.oscuro),
  ]) {
    test(
      'la paleta en modo $nombre cumple el contraste WCAG AA en todos sus pares',
      () {
        for (final (par, frente, fondo, minimo) in paleta.paresAContrastar) {
          final c = contraste(frente, fondo);
          expect(
            c,
            greaterThanOrEqualTo(minimo),
            reason: '$par: ${c.toStringAsFixed(2)}:1 (mínimo $minimo:1)',
          );
        }
      },
    );
  }

  test('los colores de la escena cumplen el contraste que les toca', () {
    for (final (par, frente, fondo, minimo) in Escena.pares) {
      final c = contraste(frente, fondo);
      expect(
        c,
        greaterThanOrEqualTo(minimo),
        reason: '$par: ${c.toStringAsFixed(2)}:1 (mínimo $minimo:1)',
      );
    }
  });
}
