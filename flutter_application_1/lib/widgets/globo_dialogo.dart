import 'package:flutter/material.dart';

import '../paleta.dart';
import '../tipografia.dart';

/// Globo de diálogo con lo último que dijo el asistente (o lo que se va entendiendo al hablar).
///
/// - Flota 3 px hacia arriba y abajo cada 5 s (quieto si el teléfono pide reducir animaciones).
/// - Si el texto es largo, el globo crece hasta [alturaMaxima] y después se puede desplazar.
/// - Las respuestas nuevas se anuncian a TalkBack como región viva ([anunciar]).
class GloboDialogo extends StatefulWidget {
  const GloboDialogo({
    super.key,
    required this.texto,
    required this.etiquetaAccesible,
    required this.alturaMaxima,
    this.anunciar = false,
    this.esError = false,
  });

  final String texto;

  /// Lo que lee TalkBack (incluye quién habla, por ejemplo "Guía: ...").
  final String etiquetaAccesible;
  final double alturaMaxima;
  final bool anunciar;
  final bool esError;

  @override
  State<GloboDialogo> createState() => _GloboDialogoState();
}

class _GloboDialogoState extends State<GloboDialogo>
    with SingleTickerProviderStateMixin {
  late final AnimationController _flota = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 5),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (MediaQuery.disableAnimationsOf(context)) {
      _flota.stop();
    } else if (!_flota.isAnimating) {
      _flota.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _flota.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final fondo = widget.esError ? Paleta.claro.error : Escena.blanco;
    final letra = widget.esError ? Paleta.claro.sobreError : Escena.tinta;

    final globo = Container(
      constraints: BoxConstraints(maxHeight: widget.alturaMaxima),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        color: fondo,
        // Esquina inferior izquierda más cerrada: apunta hacia el personaje.
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(18),
          topRight: Radius.circular(18),
          bottomRight: Radius.circular(18),
          bottomLeft: Radius.circular(6),
        ),
        boxShadow: [
          BoxShadow(
            color: Escena.tinta.withValues(alpha: 0.16),
            blurRadius: 18,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: SingleChildScrollView(
        child: Text(widget.texto, style: Tipografia.nunito(15, letra)),
      ),
    );

    return AnimatedBuilder(
      animation: _flota,
      builder: (context, hijo) => Transform.translate(
        offset: Offset(0, -3 + 6 * Curves.easeInOut.transform(_flota.value)),
        child: hijo,
      ),
      child: Semantics(
        label: widget.etiquetaAccesible,
        liveRegion: widget.anunciar,
        excludeSemantics: true,
        child: globo,
      ),
    );
  }
}
