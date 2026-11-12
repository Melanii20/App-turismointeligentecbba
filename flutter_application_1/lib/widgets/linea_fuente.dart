import 'package:flutter/material.dart';

import '../paleta.dart';
import '../tipografia.dart';

/// Línea pequeña bajo el globo con la fuente de la respuesta: «Fuente: Wikipedia» o
/// «Verificado el 12/10/2026». Si no hay fuente, no ocupa espacio.
class LineaFuente extends StatelessWidget {
  const LineaFuente({super.key, required this.fuente});

  final String? fuente;

  @override
  Widget build(BuildContext context) {
    final texto = fuente;
    if (texto == null || texto.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(6, 6, 6, 0),
      child: Semantics(
        label: texto.startsWith('Fuente') ? texto : 'Fuente: $texto',
        excludeSemantics: true,
        child: MediaQuery.withClampedTextScaling(
          maxScaleFactor: 1.3,
          child: Text(
            texto,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Tipografia.nunito(12, Escena.tintaSuave),
          ),
        ),
      ),
    );
  }
}
