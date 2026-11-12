import 'package:flutter/material.dart';

import '../servicios/ajustes.dart';
import '../servicios/aviso_diario.dart';
import '../servicios/ubicacion.dart';

/// Ajustes agregados: velocidad de la voz, anunciar eventos, sonidos, vibración, ubicación y
/// contacto de confianza. Se guardan solo en el teléfono. Va dentro de la hoja de Ajustes, con
/// el mismo estilo que sus otras opciones.
class AjustesAdicionales extends StatefulWidget {
  const AjustesAdicionales({
    super.key,
    required this.ajustes,
    required this.ubicacion,
    this.aviso = const AvisoNulo(),
  });

  final Ajustes ajustes;
  final ServicioUbicacion ubicacion;
  final ServicioAviso aviso;

  @override
  State<AjustesAdicionales> createState() => _AjustesAdicionalesState();
}

class _AjustesAdicionalesState extends State<AjustesAdicionales> {
  late final TextEditingController _contacto = TextEditingController(
    text: widget.ajustes.contacto,
  );
  String? _avisoUbicacion;

  Ajustes get _a => widget.ajustes;

  @override
  void dispose() {
    _contacto.dispose();
    super.dispose();
  }

  Future<void> _cambiarUbicacion(bool valor) async {
    if (!valor) {
      setState(() {
        _a.usarUbicacion = false;
        _avisoUbicacion = null;
      });
      return;
    }
    // El permiso se pide aquí, después de explicar para qué se usa (ver el subtítulo).
    final concedido = await widget.ubicacion.pedirPermiso();
    if (!mounted) return;
    setState(() {
      _a.usarUbicacion = concedido;
      _avisoUbicacion = concedido
          ? null
          : 'No se concedió el permiso de ubicación. Puedes activarlo en los ajustes del teléfono.';
    });
  }

  String? _avisoNotificaciones;

  Future<void> _cambiarAviso(bool valor) async {
    if (!valor) {
      await widget.aviso.desactivar();
      if (!mounted) return;
      setState(() {
        _a.avisoDiario = false;
        _avisoNotificaciones = null;
      });
      return;
    }
    final activado = await widget.aviso.activar(); // pide el permiso de notificaciones
    if (!mounted) return;
    setState(() {
      _a.avisoDiario = activado;
      _avisoNotificaciones = activado
          ? null
          : 'No se pudo activar. Revisa que las notificaciones estén permitidas para esta app.';
    });
  }

  @override
  Widget build(BuildContext context) {
    const titulo = TextStyle(fontSize: 18);
    const detalle = TextStyle(fontSize: 15);
    const relleno = EdgeInsets.symmetric(horizontal: 8);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(8, 12, 8, 4),
          child: Text('Velocidad de la voz', style: titulo),
        ),
        Padding(
          padding: relleno,
          child: SegmentedButton<VelocidadVoz>(
            key: const Key('velocidad-voz'),
            showSelectedIcon: false,
            segments: [
              for (final v in VelocidadVoz.values)
                ButtonSegment(value: v, label: Text(v.etiqueta)),
            ],
            selected: {_a.velocidad},
            onSelectionChanged: (s) => setState(() => _a.velocidad = s.first),
          ),
        ),
        SwitchListTile(
          key: const Key('ajuste-eventos'),
          value: _a.anunciarEventos,
          onChanged: (v) => setState(() => _a.anunciarEventos = v),
          title: const Text('Anunciar los eventos de hoy al abrir', style: titulo),
          contentPadding: relleno,
        ),
        SwitchListTile(
          key: const Key('ajuste-aviso-diario'),
          value: _a.avisoDiario,
          onChanged: _cambiarAviso,
          title: const Text('Aviso diario de eventos', style: titulo),
          subtitle: Text(
            _avisoNotificaciones ??
                'Cada día a las 8:00, una notificación con los eventos de hoy. Está desactivado por defecto.',
            style: detalle,
          ),
          contentPadding: relleno,
        ),
        SwitchListTile(
          key: const Key('ajuste-sonidos'),
          value: _a.sonidos,
          onChanged: (v) => setState(() => _a.sonidos = v),
          title: const Text('Sonidos', style: titulo),
          subtitle: const Text('Un sonido corto al escuchar, buscar y al fallar.', style: detalle),
          contentPadding: relleno,
        ),
        SwitchListTile(
          key: const Key('ajuste-vibracion'),
          value: _a.vibracion,
          onChanged: (v) => setState(() => _a.vibracion = v),
          title: const Text('Vibración', style: titulo),
          contentPadding: relleno,
        ),
        SwitchListTile(
          key: const Key('ajuste-ubicacion'),
          value: _a.usarUbicacion,
          onChanged: _cambiarUbicacion,
          title: const Text('Usar mi ubicación', style: titulo),
          subtitle: Text(
            _avisoUbicacion ??
                'Sirve para decirte qué hay cerca y cuánto falta. Solo se usa al preguntar y no se guarda.',
            style: detalle,
          ),
          contentPadding: relleno,
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
          child: TextField(
            key: const Key('ajuste-contacto'),
            controller: _contacto,
            keyboardType: TextInputType.phone,
            style: titulo,
            decoration: const InputDecoration(
              labelText: 'Contacto de confianza',
              helperText:
                  'Número con código de país, por ejemplo 59170000000. Se guarda solo en este teléfono.',
              helperMaxLines: 3,
            ),
            onChanged: (v) => _a.contacto = v,
          ),
        ),
      ],
    );
  }
}
