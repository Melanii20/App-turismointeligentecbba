import 'package:flutter/material.dart';
import 'package:rive/rive.dart' as rive;

import 'cliente_asistente.dart';
import 'paleta.dart';
import 'pantalla_chat.dart';
import 'servicio_voz.dart';
import 'servicios/acciones.dart';
import 'servicios/ajustes.dart';
import 'servicios/aviso_diario.dart';
import 'servicios/cliente_consulta.dart';
import 'servicios/efectos.dart';
import 'servicios/eventos_hoy.dart';
import 'servicios/ubicacion.dart';

Future<void> main() async {
  // Los plugins (voz, micrófono, Rive) necesitan que Flutter esté iniciado antes de usarse.
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await rive.RiveNative.init();
  } catch (error) {
    // Si Rive no arranca, la app sigue y el personaje se muestra como imagen.
    debugPrint('Rive no se pudo iniciar: $error');
  }
  // Ajustes guardados en el teléfono y servicios nuevos (conexión con /api/consulta, eventos de
  // hoy, sonidos y vibración, acciones del asistente). Se pasan a la pantalla sin cambiar su diseño.
  final ajustes = await Ajustes.cargar();
  final ubicacion = UbicacionReal(ajustes);
  runApp(
    AplicacionAsistente(
      cliente: ClienteConsulta(ubicacion: ubicacion),
      voz: ServicioVozReal(ajustes: ajustes),
      ajustes: ajustes,
      ubicacion: ubicacion,
      eventos: EventosHttp(ubicacion: ubicacion),
      efectos: EfectosReales(ajustes),
      acciones: AccionesReales(ajustes),
      aviso: AvisoDiarioReal(),
    ),
  );
}

class AplicacionAsistente extends StatelessWidget {
  const AplicacionAsistente({
    super.key,
    required this.cliente,
    required this.voz,
    this.ajustes,
    this.ubicacion,
    this.eventos,
    this.efectos,
    this.acciones,
    this.aviso,
  });

  final ClienteAsistente cliente;
  final ServicioVoz voz;
  final Ajustes? ajustes;
  final ServicioUbicacion? ubicacion;
  final ServicioEventos? eventos;
  final Efectos? efectos;
  final EjecutorAcciones? acciones;
  final ServicioAviso? aviso;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Asistente turístico',
      debugShowCheckedModeBanner: false,
      // Sigue el modo claro/oscuro del teléfono. Todos los colores salen de Paleta.
      themeMode: ThemeMode.system,
      theme: Paleta.claro.tema(Brightness.light),
      darkTheme: Paleta.oscuro.tema(Brightness.dark),
      home: PantallaChat(
        cliente: cliente,
        voz: voz,
        ajustes: ajustes,
        ubicacion: ubicacion,
        eventos: eventos,
        efectos: efectos,
        acciones: acciones,
        aviso: aviso,
      ),
    );
  }
}
