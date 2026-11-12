import 'package:flutter/material.dart';

import '../paleta.dart';
import '../tipografia.dart';

/// Botón redondo de la barra superior (Ayuda, Ajustes). Mide 48 dp para poder tocarse bien.
class BotonRedondo extends StatelessWidget {
  const BotonRedondo({
    super.key,
    required this.icono,
    required this.nombreAccesible,
    required this.alPulsar,
  });

  final IconData icono;

  /// Lo que lee TalkBack, por ejemplo "Ayuda".
  final String nombreAccesible;
  final VoidCallback alPulsar;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: nombreAccesible,
      excludeSemantics: true,
      child: Tooltip(
        message: nombreAccesible,
        excludeFromSemantics: true,
        child: Material(
          color: Escena.blanco.withValues(alpha: 0.82),
          shape: const CircleBorder(),
          elevation: 3,
          shadowColor: Escena.tinta.withValues(alpha: 0.25),
          child: InkWell(
            customBorder: const CircleBorder(),
            onTap: alPulsar,
            child: SizedBox(
              width: 48,
              height: 48,
              child: Icon(icono, size: 26, color: Escena.tinta),
            ),
          ),
        ),
      ),
    );
  }
}

/// Título "Guía Cochala" de la barra superior. Es decorativo para TalkBack: el nombre de la
/// guía ya está en el título grande de la pantalla.
class TituloDeBarra extends StatelessWidget {
  const TituloDeBarra({super.key});

  @override
  Widget build(BuildContext context) {
    return ExcludeSemantics(
      child: Text(
        'Guía Cochala',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: Tipografia.fredoka(17, Escena.tinta),
      ),
    );
  }
}
