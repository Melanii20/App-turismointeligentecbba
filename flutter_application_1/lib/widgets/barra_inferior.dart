import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../estado_asistente.dart';
import '../paleta.dart';
import '../tipografia.dart';

/// Tarjeta blanca de abajo (solo el fondo; los botones se colocan encima).
class FondoBarraInferior extends StatelessWidget {
  const FondoBarraInferior({super.key});

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Escena.blanco.withValues(alpha: 0.80),
        borderRadius: BorderRadius.circular(30),
        boxShadow: [
          BoxShadow(
            color: Escena.tinta.withValues(alpha: 0.14),
            blurRadius: 24,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: const SizedBox.expand(),
    );
  }
}

/// Botón lateral: círculo de 52 con ícono y su nombre escrito debajo (Escribir, Repetir).
class BotonLateral extends StatelessWidget {
  const BotonLateral({
    super.key,
    required this.icono,
    required this.etiqueta,
    required this.nombreAccesible,
    required this.alPulsar,
  });

  final IconData icono;
  final String etiqueta; // texto visible
  final String
  nombreAccesible; // lo que lee TalkBack; contiene el texto visible
  final VoidCallback? alPulsar;

  @override
  Widget build(BuildContext context) {
    final habilitado = alPulsar != null;
    return Semantics(
      button: true,
      enabled: habilitado,
      label: nombreAccesible,
      excludeSemantics: true,
      child: InkWell(
        onTap: alPulsar,
        borderRadius: BorderRadius.circular(20),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minWidth: 64, minHeight: 48),
          child: Opacity(
            opacity: habilitado ? 1 : 0.5,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 52,
                    height: 52,
                    decoration: BoxDecoration(
                      color: Escena.blanco,
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: Escena.tinta.withValues(alpha: 0.35),
                        width: 1.5,
                      ),
                    ),
                    child: Icon(icono, size: 28, color: Escena.tinta),
                  ),
                  const SizedBox(height: 4),
                  // Si el nombre no cabe (letra enorme) se achica en vez de salirse.
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      etiqueta,
                      maxLines: 1,
                      style: Tipografia.nunito(14, Escena.tinta, grosor: 800),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Botón central Hablar / Detener: círculo azul de 84 con borde blanco, dos anillos que
/// crecen y se desvanecen, y un halo que late. Más rápidos mientras escucha. Sin movimiento
/// si el teléfono pide reducir animaciones.
class BotonHablar extends StatefulWidget {
  const BotonHablar({
    super.key,
    required this.estado,
    required this.alPulsar,
    required this.nombreAccesible,
    required this.etiqueta,
  });

  final EstadoAsistente estado;
  final VoidCallback? alPulsar;
  final String nombreAccesible;
  final String etiqueta;

  /// Alto que ocupa el círculo (84) y su etiqueta, para que quien lo coloque sepa el espacio.
  static const diametro = 84.0;

  @override
  State<BotonHablar> createState() => _BotonHablarState();
}

class _BotonHablarState extends State<BotonHablar>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctl = AnimationController(vsync: this);

  Duration get _periodo => widget.estado == EstadoAsistente.escuchando
      ? const Duration(milliseconds: 1200)
      : const Duration(milliseconds: 2400);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _actualizar();
  }

  @override
  void didUpdateWidget(BotonHablar anterior) {
    super.didUpdateWidget(anterior);
    if (anterior.estado != widget.estado) _actualizar();
  }

  void _actualizar() {
    if (MediaQuery.disableAnimationsOf(context)) {
      _ctl.stop();
      return;
    }
    _ctl.duration = _periodo;
    _ctl.repeat();
  }

  @override
  void dispose() {
    _ctl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final detener =
        widget.estado == EstadoAsistente.escuchando ||
        widget.estado == EstadoAsistente.hablando;
    final habilitado = widget.alPulsar != null;
    const d = BotonHablar.diametro;

    return Semantics(
      button: true,
      enabled: habilitado,
      label: widget.nombreAccesible,
      excludeSemantics: true,
      child: InkWell(
        onTap: widget.alPulsar,
        borderRadius: BorderRadius.circular(d / 2),
        child: Opacity(
          opacity: habilitado ? 1 : 0.6,
          // Mismo relleno vertical que Escribir y Repetir: así las tres etiquetas quedan alineadas.
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 2),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                SizedBox(
                  width: d,
                  height: d,
                  child: Stack(
                    alignment: Alignment.center,
                    clipBehavior: Clip.none,
                    children: [
                      // Anillos y halo: dibujados fuera del círculo, sin recibir toques.
                      if (!MediaQuery.disableAnimationsOf(context))
                        IgnorePointer(
                          child: AnimatedBuilder(
                            animation: _ctl,
                            builder: (context, _) => CustomPaint(
                              size: const Size.square(d),
                              painter: _PintorDeAnillos(_ctl.value),
                            ),
                          ),
                        ),
                      Container(
                        width: d,
                        height: d,
                        decoration: BoxDecoration(
                          color: Escena.acento,
                          shape: BoxShape.circle,
                          border: Border.all(color: Escena.blanco, width: 5),
                          boxShadow: [
                            BoxShadow(
                              color: Escena.acento.withValues(alpha: 0.4),
                              blurRadius: 18,
                              offset: const Offset(0, 6),
                            ),
                          ],
                        ),
                        child: Icon(
                          detener ? Icons.stop_rounded : Icons.mic,
                          size: 40,
                          color: Escena.sobreAcento,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 4),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    widget.etiqueta,
                    maxLines: 1,
                    style: Tipografia.nunito(14, Escena.tinta, grosor: 800),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Dos anillos del color del botón (de escala 1 a 1,75, desvaneciéndose; el segundo con medio
/// ciclo de retraso) y un halo que late.
class _PintorDeAnillos extends CustomPainter {
  _PintorDeAnillos(this.t);
  final double t;

  @override
  void paint(Canvas canvas, Size size) {
    final centro = size.center(Offset.zero);
    final radio = size.width / 2;

    // Halo que late
    final latido = 0.5 + 0.5 * math.sin(t * 2 * math.pi);
    canvas.drawCircle(
      centro,
      radio * (1.25 + 0.1 * latido),
      Paint()..color = Escena.acento.withValues(alpha: 0.10 + 0.08 * latido),
    );

    for (final retraso in [0.0, 0.5]) {
      final f = (t + retraso) % 1.0;
      canvas.drawCircle(
        centro,
        radio * (1 + 0.75 * f),
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 3
          ..color = Escena.acento.withValues(alpha: 0.45 * (1 - f)),
      );
    }
  }

  @override
  bool shouldRepaint(_PintorDeAnillos anterior) => anterior.t != t;
}
