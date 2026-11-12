import 'package:flutter/material.dart';

/// Tipografías de la pantalla principal: Fredoka para títulos y Nunito para el texto.
/// Son fuentes variables, así que el grosor se pide con el eje "wght".
class Tipografia {
  const Tipografia._();

  static TextStyle fredoka(double tamano, Color color, {double grosor = 600}) =>
      TextStyle(
        fontFamily: 'Fredoka',
        fontSize: tamano,
        color: color,
        height: 1.15,
        fontVariations: [FontVariation('wght', grosor)],
      );

  static TextStyle nunito(
    double tamano,
    Color color, {
    double grosor = 700,
    double altura = 1.3,
  }) => TextStyle(
    fontFamily: 'Nunito',
    fontSize: tamano,
    color: color,
    height: altura,
    fontVariations: [FontVariation('wght', grosor)],
  );
}
