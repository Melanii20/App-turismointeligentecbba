import 'package:flutter/material.dart';
import 'package:rive/rive.dart' as rive;

import '../config.dart';

/// Maneja las dos propiedades del View Model "Abuela" del archivo Rive.
///
/// - `estado`: 0 inactivo, 1 escuchando, 2 procesando, 3 hablando.
/// - `boca`: 10 sonrisa, 0 reposo, 11 pensando ("mmm"), 12 habla automática.
///
/// Se asignan juntas para que la boca siempre acompañe al estado.
class AvatarControl {
  rive.ViewModelInstanceNumber? _estado;
  rive.ViewModelInstanceNumber? _boca;

  /// Boca que corresponde a cada estado.
  static const bocaPorEstado = {0: 10, 1: 0, 2: 11, 3: 12};

  /// Último estado pedido; se aplica apenas el archivo termina de cargar.
  int estadoActual = 0;

  /// Si ya está conectado al archivo de Rive.
  bool get conectado => _estado != null;

  void conectar(
    rive.ViewModelInstanceNumber estado,
    rive.ViewModelInstanceNumber? boca,
  ) {
    _estado = estado;
    _boca = boca;
    ponerEstado(estadoActual);
  }

  void ponerEstado(int e) {
    estadoActual = e;
    _estado?.value = e.toDouble();
    _boca?.value = (bocaPorEstado[e] ?? 10).toDouble();
  }

  void desconectar() {
    _estado = null;
    _boca = null;
  }
}

/// El personaje animado: carga abuela2.riv, enlaza el View Model automáticamente y libera todo al salir.
///
/// - Mientras carga muestra un espacio vacío del mismo tamaño.
/// - Si el archivo no carga, la app sigue funcionando: registra el error en la consola y
///   muestra [respaldo] (por ejemplo, la imagen del personaje).
/// - Es decorativo: TalkBack lo ignora (la respuesta ya llega por texto y voz).
///
/// El archivo saluda solo al abrir y al tocar al personaje; no hace falta disparar "saludar".
class AvatarAbuela extends StatefulWidget {
  const AvatarAbuela({
    super.key,
    required this.control,
    required this.respaldo,
  });

  final AvatarControl control;

  /// Lo que se muestra si el archivo de Rive no se puede cargar.
  final Widget respaldo;

  static const rutaRive = 'assets/personaje/abuela2.riv';

  @override
  State<AvatarAbuela> createState() => _AvatarAbuelaState();
}

class _AvatarAbuelaState extends State<AvatarAbuela> {
  rive.File? _archivo;
  rive.RiveWidgetController? _controlador;
  rive.ViewModelInstance? _vmi;
  bool _fallo = false;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    rive.File? archivo;
    rive.RiveWidgetController? controlador;
    rive.ViewModelInstance? vmi;
    try {
      // Factory.flutter dibuja con el motor de Flutter: la opción más compatible con todos los teléfonos.
      archivo = await rive.File.asset(
        AvatarAbuela.rutaRive,
        riveFactory: (motorRive == 'rive' || motorRive == 'panel')
            ? rive.Factory.rive
            : rive.Factory.flutter,
      );
      if (archivo == null) {
        throw StateError('No se pudo leer ${AvatarAbuela.rutaRive}');
      }
      if (!mounted) {
        archivo.dispose();
        return;
      }
      controlador = rive.RiveWidgetController(archivo);
      vmi = controlador.dataBind(rive.DataBind.auto());
      final estado = vmi.number('estado');
      if (estado == null) {
        throw StateError('El View Model del archivo no tiene "estado"');
      }
      widget.control.conectar(estado, vmi.number('boca'));
      setState(() {
        _archivo = archivo;
        _controlador = controlador;
        _vmi = vmi;
      });
    } catch (error) {
      // La app no se cae: se queda con el respaldo.
      debugPrint('Rive no se pudo cargar, se usa el respaldo: $error');
      widget.control.desconectar();
      vmi?.dispose();
      controlador?.dispose();
      archivo?.dispose();
      if (mounted) setState(() => _fallo = true);
    }
  }

  @override
  void dispose() {
    widget.control.desconectar();
    _vmi?.dispose();
    _controlador?.dispose();
    _archivo?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controlador = _controlador;
    final Widget contenido;
    if (_fallo) {
      contenido = widget.respaldo;
    } else if (controlador == null) {
      contenido = const SizedBox.expand(); // cargando
    } else {
      final personaje = rive.RiveWidget(
        controller: controlador,
        // Sin recortar: el personaje se ve completo dentro de su espacio.
        fit: rive.Fit.contain,
        alignment: Alignment.bottomCenter,
        useSharedTexture: motorRive == 'panel',
      );
      // Modo "panel": dibuja en una textura compartida con fondo transparente explícito.
      contenido = motorRive == 'panel'
          ? rive.RivePanel(
              backgroundColor: Colors.transparent,
              child: personaje,
            )
          : personaje;
    }
    return ExcludeSemantics(child: contenido);
  }
}
