import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';

import 'avatar_asistente.dart';
import 'cliente_asistente.dart';
import 'config.dart';
import 'estado_asistente.dart';
import 'fondo/fondo_animado.dart';
import 'paleta.dart';
import 'servicio_voz.dart';
import 'servicios/acciones.dart';
import 'servicios/ajustes.dart';
import 'servicios/aviso_diario.dart';
import 'servicios/efectos.dart';
import 'servicios/eventos_hoy.dart';
import 'servicios/ubicacion.dart';
import 'tipografia.dart';
import 'widgets/ajustes_extra.dart';
import 'widgets/barra_inferior.dart';
import 'widgets/barra_superior.dart';
import 'widgets/globo_dialogo.dart';
import 'widgets/linea_fuente.dart';
import 'widgets/tarjeta_hoy.dart';

/// Un mensaje de la conversación.
class Mensaje {
  const Mensaje({
    required this.texto,
    required this.esUsuario,
    this.esError = false,
    this.fuente,
  });
  final String texto;
  final bool esUsuario;
  final bool esError;

  /// Línea de fuente de la respuesta («Fuente: Wikipedia», «Verificado el 12/10/2026»).
  final String? fuente;
}

/// Lo que dice la guía al tocar Ayuda (tres oraciones).
const String _textoAyudaHablado =
    'Soy tu guía de Cochabamba: puedes hablarme o escribirme. '
    'Prueba con: ¿qué hay hoy?, cuéntame del Cristo, ¿cómo llego a La Cancha?, '
    'arma un recorrido, o avisa a mi familia. '
    'Todo lo que digo también aparece escrito.';

/// Pantalla única: paisaje animado, el personaje, un globo con lo que se dice y tres botones
/// (Escribir, Hablar, Repetir). Ayuda y Ajustes están en la barra de arriba; el historial,
/// dentro de Ajustes.
///
/// Todo lo que el asistente dice queda por escrito en la tarjeta (para quien no puede oír) y
/// todo lo que se dice por voz se ve escrito antes de enviarse (para quien no puede hablar).
class PantallaChat extends StatefulWidget {
  const PantallaChat({
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

  // Servicios opcionales. Sin ellos (por ejemplo en las pruebas), la pantalla funciona igual,
  // sin eventos, sonidos ni acciones.
  final Ajustes? ajustes;
  final ServicioUbicacion? ubicacion;
  final ServicioEventos? eventos;
  final Efectos? efectos;
  final EjecutorAcciones? acciones;
  final ServicioAviso? aviso;

  @override
  State<PantallaChat> createState() => _PantallaChatState();
}

class _PantallaChatState extends State<PantallaChat> {
  final _campo = TextEditingController();
  final List<Mensaje> _mensajes = [
    const Mensaje(
      texto: '¡Hola, viajero! ¿Qué descubriremos hoy?',
      esUsuario: false,
    ),
  ];

  EstadoAsistente _estado = EstadoAsistente.reposo;
  String _transcripcion = ''; // lo que se va entendiendo mientras se habla
  String _ultimaPregunta = '';

  /// Si el asistente lee sus respuestas en voz alta. Con un lector de pantalla (TalkBack) activado
  /// empieza apagado: el lector ya anuncia cada respuesta y dos voces a la vez se pisarían.
  bool? _leerEnVozAlta;

  // ---- Servicios y estado agregados (ajustes, eventos de hoy, efectos y acciones) ----
  late final Ajustes _ajustes = widget.ajustes ?? Ajustes.enMemoria();
  late final ServicioUbicacion _ubicacion =
      widget.ubicacion ?? const UbicacionNula();
  late final ServicioEventos _servicioEventos =
      widget.eventos ?? const EventosNulos();
  late final Efectos _efectos = widget.efectos ?? const EfectosNulos();
  late final EjecutorAcciones _ejecutor =
      widget.acciones ?? const AccionesNulas();

  List<EventoHoy> _eventosHoy = const [];

  /// Texto que reemplaza a la etiqueta del estado un momento («Abriendo navegación…»).
  String? _avisoEstado;

  /// Acciones que decidió el asistente; se ejecutan al terminar de hablar. «Detener» las cancela.
  List<AccionAsistente> _accionesPorEjecutar = const [];
  bool _escucharAlTerminar = false;
  Timer? _temporizadorAcciones;

  @override
  void initState() {
    super.initState();
    _cargarEventosHoy();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _leerEnVozAlta ??= !MediaQuery.accessibleNavigationOf(context);
  }

  @override
  void dispose() {
    _cancelarAcciones();
    widget.voz.callar();
    widget.voz.detenerEscucha();
    _campo.dispose();
    super.dispose();
  }

  /// ÚNICO lugar donde cambia el estado: el personaje, la etiqueta de texto (que lee TalkBack) y los
  /// botones se actualizan juntos desde aquí. También dispara el sonido y la vibración del estado.
  void _cambiarEstado(EstadoAsistente nuevo) {
    if (!mounted || _estado == nuevo) return;
    setState(() => _estado = nuevo);
    _efectos.alCambiarEstado(nuevo);
  }

  // ---------- Eventos de hoy ----------
  Future<void> _cargarEventosHoy() async {
    final lista = await _servicioEventos.hoy();
    if (!mounted || lista.isEmpty) return;
    setState(() => _eventosHoy = lista);
    // Después del saludo, la guía anuncia el primero (se puede desactivar en Ajustes).
    if (_ajustes.anunciarEventos && _estado == EstadoAsistente.reposo) {
      final mas = lista.length > 1 ? ' Toca la tarjeta de arriba para escuchar los demás.' : '';
      final texto = 'Hoy hay: ${lista.first.texto}$mas';
      setState(() => _mensajes.add(Mensaje(texto: texto, esUsuario: false)));
      await _leer(texto);
    }
  }

  /// Toca la tarjeta «Hoy»: la guía lee todos los eventos de hoy.
  Future<void> _leerEventosDeHoy() async {
    if (_estado == EstadoAsistente.pensando || _estado == EstadoAsistente.escuchando) return;
    await _callar();
    final texto = 'Eventos de hoy: ${_eventosHoy.map((e) => e.texto).join(' ')}';
    if (!mounted) return;
    setState(() => _mensajes.add(Mensaje(texto: texto, esUsuario: false)));
    await _leer(texto);
  }

  // ---------- Acciones que decide el asistente ----------
  /// Callar la voz por pedido de la persona: también cancela las acciones anunciadas.
  Future<void> _callar() async {
    _cancelarAcciones();
    await widget.voz.callar();
  }

  void _cancelarAcciones() {
    _temporizadorAcciones?.cancel();
    _temporizadorAcciones = null;
    _accionesPorEjecutar = const [];
    _escucharAlTerminar = false;
  }

  /// Se llama cuando la guía termina de hablar (o, con la voz apagada, pasado un tiempo de lectura).
  Future<void> _alTerminarDeHablar() async {
    final acciones = _accionesPorEjecutar;
    final escuchar = _escucharAlTerminar;
    _cancelarAcciones();
    if (!mounted) return;
    for (final a in acciones) {
      await _ejecutarAccion(a);
    }
    // «¿Quieres que te lleve?»: se abre el micrófono solo para oír el «sí» o el «no».
    if (mounted && escuchar && acciones.isEmpty) await _alternarEscucha();
  }

  Future<void> _ejecutarAccion(AccionAsistente a) async {
    try {
      if (a.tipo == 'abrir_navegacion' && a.latitud != null && a.longitud != null) {
        setState(() => _avisoEstado = 'Abriendo navegación…');
        _efectos.abriendoNavegacion();
        await Future<void>.delayed(const Duration(milliseconds: 900));
        await _ejecutor.abrirNavegacion(a.latitud!, a.longitud!, a.nombre ?? 'Destino');
      } else if (a.tipo == 'compartir' && a.texto != null) {
        setState(() => _avisoEstado = 'Preparando el mensaje…');
        _efectos.abriendoNavegacion();
        await Future<void>.delayed(const Duration(milliseconds: 900));
        await _ejecutor.compartir(a.texto!, numeroContacto: a.numeroContacto);
      }
    } catch (_) {
      if (mounted) {
        _efectos.error();
        setState(
          () => _mensajes.add(
            const Mensaje(
              texto: 'No pude abrir esa aplicación. Revisa que tengas una instalada.',
              esUsuario: false,
              esError: true,
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _avisoEstado = null);
    }
  }

  Mensaje get _ultimoDelAsistente => _mensajes.lastWhere((m) => !m.esUsuario);

  // ---------- Enviar una pregunta (escrita o hablada) ----------
  Future<void> _enviar() async {
    final pregunta = _campo.text.trim();
    if (pregunta.length < 2 || _estado == EstadoAsistente.pensando) return;

    await widget.voz.detenerEscucha();
    await _callar();

    setState(() {
      _mensajes.add(Mensaje(texto: pregunta, esUsuario: true));
      _ultimaPregunta = pregunta;
      _transcripcion = '';
    });
    _cambiarEstado(EstadoAsistente.pensando);
    _campo.clear();

    Mensaje respuesta;
    try {
      // Si pasan más de 20 segundos sin respuesta, se vuelve al reposo y se avisa.
      final r = await widget.cliente.preguntar(pregunta).timeout(esperaMaxima);
      respuesta = Mensaje(texto: r.texto, esUsuario: false, fuente: r.fuente);
      _accionesPorEjecutar = r.acciones;
      _escucharAlTerminar = r.escucharDespues;
    } on ErrorAsistente catch (e) {
      respuesta = Mensaje(texto: e.mensaje, esUsuario: false, esError: true);
    } on TimeoutException {
      respuesta = const Mensaje(
        texto: 'No se pudo obtener la respuesta. Intenta de nuevo.',
        esUsuario: false,
        esError: true,
      );
    }

    if (!mounted) return;
    setState(() => _mensajes.add(respuesta));
    // Aviso al tacto de que llegó la respuesta (útil sin oír); si falló, doble vibración y sonido de error.
    respuesta.esError ? _efectos.error() : _efectos.respuestaLista();
    await _leer(respuesta.texto);
  }

  /// Lee un texto en voz alta (también los mensajes de error). El estado "hablando" llega cuando
  /// la voz realmente empieza a sonar; mientras tanto se muestra el texto en la tarjeta.
  /// [forzar] lee aunque la voz esté desactivada en Ajustes (lo usa "Repetir").
  Future<void> _leer(String texto, {bool forzar = false}) async {
    _cambiarEstado(EstadoAsistente.reposo);
    if (!forzar && _leerEnVozAlta != true) {
      // Sin voz propia (por ejemplo con TalkBack), las acciones esperan un rato de lectura.
      if (_accionesPorEjecutar.isNotEmpty || _escucharAlTerminar) {
        final ms = (texto.length * 70).clamp(2500, 15000);
        _temporizadorAcciones?.cancel();
        _temporizadorAcciones = Timer(Duration(milliseconds: ms), _alTerminarDeHablar);
      }
      return;
    }
    try {
      await widget.voz.hablar(
        texto,
        alEmpezar: () {
          if (_estado == EstadoAsistente.reposo) {
            _cambiarEstado(EstadoAsistente.hablando);
          }
        },
        alTerminar: () {
          if (_estado == EstadoAsistente.hablando) {
            _cambiarEstado(EstadoAsistente.reposo);
          }
          _alTerminarDeHablar();
        },
      );
    } catch (_) {
      _cambiarEstado(EstadoAsistente.reposo);
    }
  }

  /// Vuelve a leer la última respuesta del asistente.
  Future<void> _repetir() async {
    if (_estado == EstadoAsistente.pensando ||
        _estado == EstadoAsistente.escuchando) {
      return;
    }
    await _callar();
    await _leer(_ultimoDelAsistente.texto, forzar: true);
  }

  // ---------- Hablar con el micrófono ----------
  Future<void> _alternarEscucha() async {
    if (_estado == EstadoAsistente.hablando) {
      // El mismo botón es "Detener" mientras el asistente habla.
      await _callar(); // «Detener» también cancela una acción anunciada («Te abro la navegación»)
      _cambiarEstado(EstadoAsistente.reposo);
      return;
    }
    if (_estado == EstadoAsistente.escuchando) {
      await widget.voz.detenerEscucha();
      return;
    }
    if (_estado == EstadoAsistente.pensando) return;

    await _callar(); // el asistente se calla para poder oírte
    _campo.clear();
    final empezo = await widget.voz.iniciarEscucha(
      alResultado: (texto, esFinal) {
        if (!mounted) return;
        _campo.text = texto;
        setState(() => _transcripcion = texto); // se ve lo que se entendió
        if (esFinal && texto.trim().length >= 2) _enviar();
      },
      alTerminar: () {
        if (!mounted || _estado != EstadoAsistente.escuchando) return;
        _cambiarEstado(EstadoAsistente.reposo);
        // Si quedó algo entendido que no llegó a marcarse como final, también se envía.
        if (_campo.text.trim().length >= 2) {
          _enviar();
        } else {
          // No se entendió nada: se avisa por texto, sonido y vibración.
          _efectos.error();
          setState(
            () => _mensajes.add(
              const Mensaje(
                texto: 'No te entendí, intenta de nuevo.',
                esUsuario: false,
                esError: true,
              ),
            ),
          );
        }
      },
    );

    if (!mounted) return;
    if (empezo) {
      // La vibración corta y el sonido de «escuchando» salen de _cambiarEstado.
      setState(() => _transcripcion = '');
      _cambiarEstado(EstadoAsistente.escuchando);
    } else {
      setState(
        () => _mensajes.add(
          const Mensaje(
            texto: 'No pude usar el micrófono. Revisa que la app tenga permiso para usarlo, o escribe tu pregunta.',
            esUsuario: false,
            esError: true,
          ),
        ),
      );
    }
  }

  // ---------- Hojas: escribir, historial, ajustes ----------
  Future<void> _abrirEscribir() async {
    if (_estado == EstadoAsistente.pensando) return;
    await widget.voz.detenerEscucha();
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (contexto) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.viewInsetsOf(contexto).bottom,
        ),
        child: _HojaEscribir(
          campo: _campo,
          alEnviar: () {
            Navigator.of(contexto).pop();
            _enviar();
          },
        ),
      ),
    );
  }

  Future<void> _abrirHistorial() {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (contexto) => _HojaHistorial(mensajes: List.of(_mensajes)),
    );
  }

  Future<void> _abrirAyuda() {
    // Ayuda por voz: la guía explica en tres oraciones qué se le puede preguntar.
    _leer(_textoAyudaHablado);
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (contexto) => const _HojaAyuda(),
    ).whenComplete(widget.voz.callar);
  }

  Future<void> _abrirAjustes() {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (contexto) => _HojaAjustes(
        alHistorial: () {
          Navigator.of(contexto).pop();
          _abrirHistorial();
        },
        ajustes: _ajustes,
        ubicacion: _ubicacion,
        aviso: widget.aviso ?? const AvisoNulo(),
        vozActiva: _leerEnVozAlta ?? true,
        alCambiar: (valor) {
          setState(() => _leerEnVozAlta = valor);
          if (!valor) {
            _callar();
            if (_estado == EstadoAsistente.hablando) {
              _cambiarEstado(EstadoAsistente.reposo);
            }
          }
        },
      ),
    );
  }

  // ---------- Pantalla ----------
  @override
  Widget build(BuildContext context) {
    final escuchando = _estado == EstadoAsistente.escuchando;
    final pensando = _estado == EstadoAsistente.pensando;
    final hablando = _estado == EstadoAsistente.hablando;
    final ultimo = _ultimoDelAsistente;

    // Lo que dice el globo: lo que se va entendiendo, la pregunta en curso o la última respuesta.
    final textoGlobo = escuchando
        ? (_transcripcion.isEmpty ? 'Habla ahora…' : _transcripcion)
        : pensando
        ? 'Preguntaste: $_ultimaPregunta'
        : ultimo.texto;
    final esRespuesta = !escuchando && !pensando;

    return Scaffold(
      backgroundColor: Escena.cielo.first,
      resizeToAvoidBottomInset: false, // las hojas con teclado se ajustan solas
      body: LayoutBuilder(
        builder: (context, caja) {
          final m = _Medidas(caja, MediaQuery.paddingOf(context));
          return AnnotatedRegion<SystemUiOverlayStyle>(
            value: SystemUiOverlayStyle
                .dark, // íconos oscuros sobre el cielo claro
            child: Stack(
              children: [
                // El paisaje se apoya a la altura de las rodillas del personaje.
                Positioned.fill(
                  child: FondoAnimado(baseDelPaisaje: m.rodillasY),
                ),
                Positioned.fill(
                  child: _contenido(
                    context,
                    m,
                    textoGlobo: textoGlobo,
                    esRespuesta: esRespuesta,
                    esError: esRespuesta && ultimo.esError,
                    escuchando: escuchando,
                    pensando: pensando,
                    hablando: hablando,
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  /// Todo lo que va encima del fondo. Las medidas del diseño (390 x 844) se escalan por el ancho.
  /// Arriba (barra, título) y abajo (estado, botones) se anclan a sus bordes; el personaje y el
  /// globo usan el espacio que queda en medio, así no se rompe en pantallas más cortas.
  Widget _contenido(
    BuildContext context,
    _Medidas m, {
    required String textoGlobo,
    required bool esRespuesta,
    required bool esError,
    required bool escuchando,
    required bool pensando,
    required bool hablando,
  }) {
    final w = m.w;
    const altoTarjeta = _Medidas.altoTarjeta;
    final barraArriba = m.barraArriba;
    final tituloArriba = m.tituloArriba;
    final tamanoTitulo = m.tamanoTitulo;
    final tarjetaAbajo = m.tarjetaAbajo;
    final estadoArribaY = m.estadoArribaY;
    final personajeArriba = m.personajeArriba;
    final anchoPersonaje = m.anchoPersonaje;
    final altoPersonaje = m.altoPersonaje;
    final globoArriba = m.globoArriba;
    final globoIzquierda = m.globoIzquierda;
    final globoAncho = m.globoAncho;
    final globoAltoMax = m.globoAltoMax;

    return Stack(
      children: [
        // Personaje (decorativo para TalkBack)
        Positioned(
          left: 0,
          top: personajeArriba,
          child: AvatarAsistente(
            estado: _estado,
            ancho: anchoPersonaje,
            alto: altoPersonaje,
          ),
        ),
        // 1. Título
        Positioned(
          left: 16,
          right: 16,
          top: tituloArriba,
          child: Semantics(
            header: true,
            sortKey: const OrdinalSortKey(0),
            label: 'Tu guía de Cochabamba a un toque de voz',
            excludeSemantics: true,
            // Es texto grande: con letra enorme se limita para no tapar al personaje.
            child: MediaQuery.withClampedTextScaling(
              maxScaleFactor: 1.2,
              child: Text.rich(
                TextSpan(
                  style: Tipografia.fredoka(tamanoTitulo, Escena.tinta),
                  children: const [
                    TextSpan(text: 'Tu guía de '),
                    TextSpan(
                      text: 'Cochabamba',
                      style: TextStyle(color: Escena.acento),
                    ),
                    TextSpan(text: '\na un toque de voz'),
                  ],
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ),
        // 2. Globo con la respuesta
        Positioned(
          left: globoIzquierda,
          top: globoArriba,
          width: globoAncho,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Semantics(
                sortKey: const OrdinalSortKey(1),
                child: GloboDialogo(
                  texto: textoGlobo,
                  etiquetaAccesible: esRespuesta
                      ? 'Guía: $textoGlobo'
                      : textoGlobo,
                  alturaMaxima: globoAltoMax,
                  anunciar: esRespuesta,
                  esError: esError,
                ),
              ),
              // Línea pequeña con la fuente de la respuesta (si la hay)
              Semantics(
                sortKey: const OrdinalSortKey(1.5),
                child: LineaFuente(fuente: esRespuesta ? _ultimoDelAsistente.fuente : null),
              ),
            ],
          ),
        ),
        // Tarjeta «Hoy» (eventos). Solo se dibuja si hay eventos y entra entre el título y el
        // personaje sin tapar a ninguno de los dos.
        if (_eventosHoy.isNotEmpty)
          Positioned(
            left: 14,
            right: m.tarjetaHoyCompacta ? null : 14,
            width: m.tarjetaHoyCompacta ? m.globoIzquierda - 28 : null,
            top: m.tarjetaHoyArriba,
            child: Semantics(
              sortKey: const OrdinalSortKey(0.5),
              child: TarjetaHoy(
                eventos: _eventosHoy,
                cerca: _eventosHoy.first.distanciaM != null,
                alEscuchar: _leerEventosDeHoy,
                compacta: m.tarjetaHoyCompacta,
              ),
            ),
          ),
        // 3. Texto de estado. Escuchando y buscando se anuncian solos a TalkBack; hablando no,
        // para no hablarle encima a la voz de la guía.
        Positioned(
          left: 24,
          right: 24,
          top: estadoArribaY,
          height: 44,
          child: Semantics(
            sortKey: const OrdinalSortKey(2),
            liveRegion: escuchando || pensando || _avisoEstado != null,
            label: _avisoEstado ?? _estado.etiqueta,
            excludeSemantics: true,
            child: Align(
              alignment: Alignment.bottomCenter,
              child: MediaQuery.withClampedTextScaling(
                maxScaleFactor: 1.5,
                child: Text(
                  _avisoEstado ?? _estado.etiqueta,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Tipografia.nunito(14, Escena.tintaSuave, grosor: 700),
                ),
              ),
            ),
          ),
        ),
        // Tarjeta de abajo con Escribir y Repetir
        Positioned(
          left: 14,
          right: 14,
          bottom: tarjetaAbajo,
          height: altoTarjeta,
          child: Stack(
            children: [
              const FondoBarraInferior(),
              Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(
                    child: Align(
                      alignment: Alignment.bottomCenter,
                      child: Padding(
                        padding: const EdgeInsets.only(
                          bottom: _Medidas.margenBotones,
                        ),
                        child: Semantics(
                          sortKey: const OrdinalSortKey(4),
                          child: BotonLateral(
                            key: const Key('boton-escribir'),
                            icono: Icons.keyboard_alt_outlined,
                            etiqueta: 'Escribir',
                            nombreAccesible: 'Escribir una pregunta',
                            alPulsar: pensando ? null : _abrirEscribir,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 112), // espacio del botón Hablar
                  Expanded(
                    child: Align(
                      alignment: Alignment.bottomCenter,
                      child: Padding(
                        padding: const EdgeInsets.only(
                          bottom: _Medidas.margenBotones,
                        ),
                        child: Semantics(
                          sortKey: const OrdinalSortKey(5),
                          child: BotonLateral(
                            key: const Key('boton-repetir'),
                            icono: Icons.replay,
                            etiqueta: 'Repetir',
                            nombreAccesible: 'Repetir la última respuesta',
                            alPulsar: (pensando || escuchando)
                                ? null
                                : _repetir,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        // 4. Hablar / Detener: sobresale por encima de la tarjeta. Va aparte (no dentro de la
        // tarjeta) para que toda su superficie reciba toques.
        Positioned(
          left: (w - 112) / 2,
          width: 112,
          bottom: tarjetaAbajo + _Medidas.margenBotones,
          child: Semantics(
            sortKey: const OrdinalSortKey(3),
            child: BotonHablar(
              key: const Key('boton-hablar'),
              estado: _estado,
              etiqueta: (escuchando || hablando) ? 'Detener' : 'Hablar',
              nombreAccesible: escuchando
                  ? 'Detener la escucha'
                  : hablando
                  ? 'Detener la voz de la guía'
                  : 'Hablar con la guía',
              alPulsar: pensando ? null : _alternarEscucha,
            ),
          ),
        ),
        // Barra de arriba: Ayuda, título y Ajustes (al final del orden de lectura)
        Positioned(
          left: 20,
          right: 20,
          top: barraArriba,
          height: 48,
          child: Row(
            children: [
              Semantics(
                sortKey: const OrdinalSortKey(6),
                child: BotonRedondo(
                  key: const Key('boton-ayuda'),
                  icono: Icons.help_outline,
                  nombreAccesible: 'Ayuda',
                  alPulsar: _abrirAyuda,
                ),
              ),
              const Expanded(child: Center(child: TituloDeBarra())),
              Semantics(
                sortKey: const OrdinalSortKey(7),
                child: BotonRedondo(
                  key: const Key('boton-ajustes'),
                  icono: Icons.tune,
                  nombreAccesible: 'Ajustes',
                  alPulsar: _abrirAjustes,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ---------- Hojas ----------

class _HojaEscribir extends StatefulWidget {
  const _HojaEscribir({required this.campo, required this.alEnviar});

  final TextEditingController campo;
  final VoidCallback alEnviar;

  @override
  State<_HojaEscribir> createState() => _HojaEscribirState();
}

class _HojaEscribirState extends State<_HojaEscribir> {
  String? _error;

  void _intentarEnviar() {
    if (widget.campo.text.trim().length < 2) {
      setState(() => _error = 'Escribe al menos 2 letras.');
      return;
    }
    widget.alEnviar();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: widget.campo,
            autofocus: true,
            textInputAction: TextInputAction.send,
            onSubmitted: (_) => _intentarEnviar(),
            onChanged: (_) => setState(() => _error = null),
            maxLength: 300,
            style: const TextStyle(fontSize: 20),
            decoration: InputDecoration(
              labelText: 'Escribe tu pregunta',
              errorText: _error,
              counterText: '',
            ),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: _intentarEnviar,
            icon: const Icon(Icons.send),
            label: const Text('Enviar'),
          ),
        ],
      ),
    );
  }
}

class _HojaHistorial extends StatelessWidget {
  const _HojaHistorial({required this.mensajes});
  final List<Mensaje> mensajes;

  @override
  Widget build(BuildContext context) {
    return FractionallySizedBox(
      heightFactor: 0.85,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 8, 8),
            child: Row(
              children: [
                Expanded(
                  child: Semantics(
                    header: true,
                    child: const Text(
                      'Historial de la conversación',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
                IconButton(
                  tooltip: 'Cerrar el historial',
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.close, size: 28),
                  constraints: const BoxConstraints(
                    minWidth: 48,
                    minHeight: 48,
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              itemCount: mensajes.length,
              itemBuilder: (context, i) => _Burbuja(mensaje: mensajes[i]),
            ),
          ),
        ],
      ),
    );
  }
}

class _Burbuja extends StatelessWidget {
  const _Burbuja({required this.mensaje});
  final Mensaje mensaje;

  @override
  Widget build(BuildContext context) {
    final colores = Theme.of(context).colorScheme;
    final esUsuario = mensaje.esUsuario;
    final fondo = mensaje.esError
        ? colores.error
        : esUsuario
        ? colores.primary
        : colores.surfaceContainerHighest;
    final letra = mensaje.esError
        ? colores.onError
        : esUsuario
        ? colores.onPrimary
        : colores.onSurface;

    return Align(
      alignment: esUsuario ? Alignment.centerRight : Alignment.centerLeft,
      child: Semantics(
        label: esUsuario ? 'Tú: ${mensaje.texto}' : 'Guía: ${mensaje.texto}',
        excludeSemantics: true,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 6),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          constraints: BoxConstraints(
            maxWidth: MediaQuery.sizeOf(context).width * 0.85,
          ),
          decoration: BoxDecoration(
            color: fondo,
            borderRadius: BorderRadius.circular(18),
          ),
          child: Text(
            mensaje.texto,
            style: TextStyle(color: letra, fontSize: 18, height: 1.35),
          ),
        ),
      ),
    );
  }
}

class _HojaAjustes extends StatefulWidget {
  const _HojaAjustes({
    required this.vozActiva,
    required this.alCambiar,
    required this.alHistorial,
    required this.ajustes,
    required this.ubicacion,
    required this.aviso,
  });

  final Ajustes ajustes;
  final ServicioUbicacion ubicacion;
  final ServicioAviso aviso;
  final VoidCallback alHistorial;
  final bool vozActiva;
  final ValueChanged<bool> alCambiar;

  @override
  State<_HojaAjustes> createState() => _HojaAjustesState();
}

class _HojaAjustesState extends State<_HojaAjustes> {
  late bool _voz = widget.vozActiva;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
            child: Semantics(
              header: true,
              child: const Text(
                'Ajustes',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600),
              ),
            ),
          ),
          SwitchListTile(
            value: _voz,
            onChanged: (valor) {
              setState(() => _voz = valor);
              widget.alCambiar(valor);
            },
            title: const Text(
              'Leer las respuestas en voz alta',
              style: TextStyle(fontSize: 18),
            ),
            subtitle: const Text(
              'Si usas TalkBack, déjalo apagado: TalkBack ya lee las respuestas.',
              style: TextStyle(fontSize: 15),
            ),
            contentPadding: const EdgeInsets.symmetric(horizontal: 8),
          ),
          ListTile(
            key: const Key('boton-historial'),
            leading: const Icon(Icons.history, size: 28),
            title: const Text(
              'Ver el historial de la conversación',
              style: TextStyle(fontSize: 18),
            ),
            contentPadding: const EdgeInsets.symmetric(horizontal: 8),
            minVerticalPadding: 12,
            onTap: widget.alHistorial,
          ),
          // Velocidad de voz, eventos, sonidos, vibración, ubicación y contacto de confianza
          AjustesAdicionales(
            ajustes: widget.ajustes,
            ubicacion: widget.ubicacion,
            aviso: widget.aviso,
          ),
        ],
      ),
    );
  }
}

/// Explica cómo usar la app: qué hace cada botón y qué preguntar.
class _HojaAyuda extends StatelessWidget {
  const _HojaAyuda();

  @override
  Widget build(BuildContext context) {
    const estilo = TextStyle(fontSize: 18, height: 1.4);
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(
            header: true,
            child: const Text(
              'Ayuda',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600),
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'Soy tu guía de Cochabamba. Pregúntame por un sitio turístico o '
            'patrimonial, por ejemplo: «¿cómo llego a La Cancha?» o '
            '«¿es ruidoso el Convento de Santa Teresa?».',
            style: estilo,
          ),
          const SizedBox(height: 12),
          const Text(
            '• Hablar: toca el micrófono y di tu pregunta.',
            style: estilo,
          ),
          const Text(
            '• Escribir: escribe tu pregunta con el teclado.',
            style: estilo,
          ),
          const Text(
            '• Repetir: vuelvo a leer la última respuesta.',
            style: estilo,
          ),
          const Text(
            '• Todo lo que digo también aparece escrito en el globo.',
            style: estilo,
          ),
          const SizedBox(height: 12),
          const Text(
            'Solo hablo de sitios cuya información fue verificada.',
            style: estilo,
          ),
        ],
      ),
    );
  }
}

/// Medidas de la pantalla, compartidas por el fondo y por lo que va encima. Las del diseño
/// (390 x 844) se escalan por el ancho; arriba y abajo se anclan a sus bordes.
class _Medidas {
  _Medidas(BoxConstraints caja, EdgeInsets relleno) {
    w = caja.maxWidth;
    h = caja.maxHeight;
    s = (w / 390).clamp(0.8, 1.3);

    barraArriba = relleno.top + 8;
    tituloArriba = barraArriba + 48 + 12;
    tamanoTitulo = 32 * s;

    tarjetaAbajo = relleno.bottom + 14;
    tarjetaArriba = h - tarjetaAbajo - altoTarjeta;
    estadoAbajoY = tarjetaArriba - 66; // deja libres los anillos del micrófono
    estadoArribaY = estadoAbajoY - 44;

    // Personaje: 0,72 del ancho y 0,50 del alto, abajo a la izquierda, con su borde inferior
    // justo encima del texto de estado (una línea de 14 px y un respiro).
    anchoPersonaje = 0.72 * w;
    altoPersonaje = 0.50 * h;
    final personajeAbajo = estadoAbajoY - 22;
    personajeArriba = personajeAbajo - altoPersonaje;
    // Las rodillas están a ~82 % de la altura del personaje, contando desde arriba.
    rodillasY = personajeArriba + 0.82 * altoPersonaje;

    // Globo: a la derecha de la cabeza, a la altura del sombrero (borde superior del personaje).
    globoIzquierda = math.min(anchoPersonaje * 0.72, w - 150);
    globoAncho = w - globoIzquierda - 14;
    globoArriba = personajeArriba;
    globoAltoMax =
        altoPersonaje *
        0.36; // no baja hasta la mano; si es largo, tiene scroll

    // Tarjeta «Hoy»: justo debajo del título (dos líneas), antes del personaje.
    tarjetaHoyArriba = tituloArriba + tamanoTitulo * 2.3 + 8;
    // Si no hay espacio para la tarjeta completa, se usa la compacta: queda a la izquierda, sin
    // llegar al globo, y solo toca la esquina superior del recuadro del personaje (que es transparente).
    tarjetaHoyCompacta = personajeArriba - tarjetaHoyArriba < 56;
  }

  static const altoTarjeta = 98.0;

  /// Distancia entre la base de los botones y el borde inferior de la tarjeta.
  static const margenBotones = 10.0;

  late final double w, h, s;
  late final double barraArriba, tituloArriba, tamanoTitulo;
  late final double tarjetaAbajo, tarjetaArriba, estadoAbajoY, estadoArribaY;
  late final double anchoPersonaje, altoPersonaje, personajeArriba, rodillasY;
  late final double globoIzquierda, globoAncho, globoArriba, globoAltoMax;
  late final double tarjetaHoyArriba;
  late final bool tarjetaHoyCompacta;
}
