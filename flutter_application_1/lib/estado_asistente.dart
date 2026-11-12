/// Los 4 estados del personaje. El número coincide con la entrada "estado" que tendrá la
/// máquina de estados de Rive más adelante (0 inactivo, 1 escuchando, 2 procesando, 3 hablando).
enum EstadoAsistente {
  reposo(0, 'En espera · toca el micrófono para hablar'),
  escuchando(1, 'Escuchando…'),
  pensando(2, 'Buscando información…'),
  hablando(3, 'Hablando…');

  const EstadoAsistente(this.numero, this.etiqueta);

  final int numero;

  /// Texto visible (y leído por TalkBack) que describe el estado, para que no dependa solo de la animación.
  final String etiqueta;
}
