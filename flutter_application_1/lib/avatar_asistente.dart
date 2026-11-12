import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'config.dart';
import 'estado_asistente.dart';
import 'widgets/avatar_abuela.dart';

/// Personaje del asistente, sin marco ni recorte (ver [AvatarAbuela], que carga abuela2.riv).
///
/// El estado del asistente se envía al archivo de Rive con [AvatarControl.ponerEstado]:
/// 0 inactivo, 1 escuchando, 2 procesando, 3 hablando (ver [EstadoAsistente.numero]).
///
/// Es una ilustración decorativa: los lectores de pantalla la ignoran. El estado se comunica
/// aparte con texto, así nadie depende de la animación.
///
/// Se usa la imagen con movimientos de Flutter en vez de Rive si el archivo no se puede cargar
/// o si el teléfono tiene activada la opción de quitar animaciones.
class AvatarAsistente extends StatefulWidget {
  const AvatarAsistente({
    super.key,
    required this.estado,
    required this.ancho,
    required this.alto,
  });

  final EstadoAsistente estado;
  final double ancho;
  final double alto;

  static const rutaImagen = 'assets/personaje/personaje_sombrero_cochala.png';

  @override
  State<AvatarAsistente> createState() => _AvatarAsistenteState();
}

class _AvatarAsistenteState extends State<AvatarAsistente>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctl = AnimationController(vsync: this);
  final AvatarControl _control = AvatarControl();

  /// Duración de un ciclo de movimiento según el estado.
  static Duration _periodo(EstadoAsistente e) => switch (e) {
    EstadoAsistente.reposo => const Duration(milliseconds: 3600),
    EstadoAsistente.escuchando => const Duration(milliseconds: 1500),
    EstadoAsistente.pensando => const Duration(milliseconds: 2200),
    EstadoAsistente.hablando => const Duration(milliseconds: 650),
  };

  @override
  void initState() {
    super.initState();
    _control.estadoActual = widget.estado.numero;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _actualizarMovimiento();
  }

  @override
  void didUpdateWidget(AvatarAsistente anterior) {
    super.didUpdateWidget(anterior);
    if (anterior.estado != widget.estado) {
      _control.ponerEstado(widget.estado.numero);
      _actualizarMovimiento();
    }
  }

  void _actualizarMovimiento() {
    if (MediaQuery.disableAnimationsOf(context)) {
      _ctl.stop();
      return;
    }
    _ctl.duration = _periodo(widget.estado);
    _ctl.repeat();
  }

  @override
  void dispose() {
    _ctl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final quieto = MediaQuery.disableAnimationsOf(context);
    final imagen = _ImagenAnimada(
      estado: widget.estado,
      animacion: _ctl,
      quieta: quieto,
    );
    final Widget personaje = (quieto || !usarRive)
        ? imagen
        : AvatarAbuela(control: _control, respaldo: imagen);

    // ExcludeSemantics: es decorativo; el estado lo dice el texto de estado.
    return ExcludeSemantics(
      child: SizedBox(
        width: widget.ancho,
        height: widget.alto,
        child: personaje,
      ),
    );
  }
}

/// La imagen del personaje con movimientos de Flutter, con los mismos 4 estados que la de Rive.
class _ImagenAnimada extends StatelessWidget {
  const _ImagenAnimada({
    required this.estado,
    required this.animacion,
    required this.quieta,
  });

  final EstadoAsistente estado;
  final Animation<double> animacion;
  final bool quieta;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: animacion,
      builder: (context, hijo) {
        final onda = quieta ? 0.0 : math.sin(2 * math.pi * animacion.value);
        double giro = 0, escala = 1, salto = 0;
        switch (estado) {
          case EstadoAsistente.reposo:
            escala = 1 + 0.012 * onda; // respira
          case EstadoAsistente.escuchando:
            giro = 0.03; // se inclina hacia quien habla
          case EstadoAsistente.pensando:
            giro = 0.04 * onda; // balanceo lento
          case EstadoAsistente.hablando:
            escala = 1 + 0.018 * onda.abs();
            salto = -4 * onda.abs();
        }
        return Transform.translate(
          offset: Offset(0, salto),
          child: Transform.rotate(
            angle: giro,
            alignment: Alignment.bottomCenter,
            child: Transform.scale(
              scale: escala,
              alignment: Alignment.bottomCenter,
              child: hijo,
            ),
          ),
        );
      },
      child: Image.asset(
        AvatarAsistente.rutaImagen,
        fit: BoxFit.contain,
        alignment: Alignment.bottomCenter,
      ),
    );
  }
}
