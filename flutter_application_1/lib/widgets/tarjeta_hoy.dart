import 'package:flutter/material.dart';

import '../paleta.dart';
import '../servicios/eventos_hoy.dart';
import '../tipografia.dart';

/// Tarjeta «Hoy» con un evento (el más cercano si hay ubicación). Al tocarla, la guía lee los
/// eventos de hoy. Si no hay eventos, no se dibuja. Usa los mismos colores, sombra y tipografía
/// que el globo de diálogo.
class TarjetaHoy extends StatelessWidget {
  const TarjetaHoy({
    super.key,
    required this.eventos,
    required this.cerca,
    required this.alEscuchar,
    this.compacta = false,
  });

  /// En pantallas con poco espacio entre el título y el personaje, la tarjeta se reduce a un
  /// botón de 48 dp de alto y menos ancho (para no tapar al personaje ni al globo).
  final bool compacta;

  final List<EventoHoy> eventos;

  /// Si el orden de los eventos es por cercanía (se envió la ubicación).
  final bool cerca;
  final VoidCallback alEscuchar;

  @override
  Widget build(BuildContext context) {
    if (eventos.isEmpty) return const SizedBox.shrink();
    final primero = eventos.first;
    final titulo = primero.titulo(cerca: cerca);
    final mas = eventos.length > 1 ? ' · y ${eventos.length - 1} más' : '';

    return Semantics(
      button: true,
      label: 'Escuchar eventos de hoy. $titulo$mas',
      excludeSemantics: true,
      child: Material(
        color: Colors.transparent,
        child: Ink(
          decoration: BoxDecoration(
            color: Escena.blanco.withValues(alpha: 0.94),
            borderRadius: BorderRadius.circular(18),
            boxShadow: [
              BoxShadow(
                color: Escena.tinta.withValues(alpha: 0.14),
                blurRadius: 14,
                offset: const Offset(0, 5),
              ),
            ],
          ),
          child: InkWell(
            borderRadius: BorderRadius.circular(18),
            onTap: alEscuchar,
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: compacta ? 48 : 52),
              child: Padding(
                padding: EdgeInsets.symmetric(
                  horizontal: compacta ? 10 : 14,
                  vertical: compacta ? 4 : 8,
                ),
                child: Row(
                  children: [
                    Icon(Icons.event, color: Escena.acento, size: compacta ? 22 : 24),
                    SizedBox(width: compacta ? 6 : 10),
                    Expanded(
                      child: MediaQuery.withClampedTextScaling(
                        maxScaleFactor: compacta ? 1.15 : 1.3,
                        child: Text(
                          '$titulo$mas',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: Tipografia.nunito(compacta ? 12 : 13.5, Escena.tinta),
                        ),
                      ),
                    ),
                    if (!compacta) ...[
                      const SizedBox(width: 8),
                      const Icon(Icons.volume_up_outlined, color: Escena.acento, size: 22),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
