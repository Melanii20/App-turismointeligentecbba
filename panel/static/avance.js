/* Avance hacia la verificación: muestra "X de 7 datos listos" mientras se llena el formulario.

   Es solo una GUÍA con lo que se ve en pantalla. Quien decide si un sitio se puede verificar
   es el servidor (verificar_sitio en main.py), que revisa lo que está guardado en la base.
   La lista de requisitos viene del servidor dentro de la propia página (los <li data-campo>),
   así que aquí no se repite.

   Mejora progresiva: la tarjeta está oculta hasta que este script la muestra. */
(function () {
  'use strict';

  var tarjeta = document.getElementById('avance');
  var formulario = document.querySelector('form.formulario');
  if (!tarjeta || !formulario) { return; }

  var items = tarjeta.querySelectorAll('li[data-campo]');
  var textoAvance = document.getElementById('avance-texto');
  var progreso = document.getElementById('avance-progreso');
  var estado = document.getElementById('avance-estado');
  var textoBarra = document.getElementById('avance-barra-texto');
  if (!items.length || !textoAvance || !progreso) { return; }

  var hayVerificar = !!document.getElementById('verificacion');
  var completoAntes = null; // para avisar solo cuando cambia entre completo e incompleto

  tarjeta.hidden = false;
  if (textoBarra) { textoBarra.hidden = false; }

  // Un dato está listo si tiene texto, o si se eligió "Sí"/"No" (no "Sin verificar").
  function estaListo(campo) {
    var radios = formulario.querySelectorAll('input[type="radio"][name="' + campo + '"]');
    if (radios.length) {
      for (var i = 0; i < radios.length; i++) {
        if (radios[i].checked) { return radios[i].value !== ''; }
      }
      return false;
    }
    var elemento = document.getElementById(campo);
    return !!elemento && typeof elemento.value === 'string' && elemento.value.trim() !== '';
  }

  function actualizar() {
    var listos = 0;
    for (var i = 0; i < items.length; i++) {
      var ok = estaListo(items[i].getAttribute('data-campo'));
      items[i].querySelector('.listo').hidden = !ok;
      items[i].querySelector('.falta').hidden = ok;
      items[i].classList.toggle('completo', ok);
      if (ok) { listos++; }
    }

    var total = items.length;
    textoAvance.textContent = listos + ' de ' + total;
    progreso.value = listos;
    if (textoBarra) { textoBarra.textContent = listos + ' de ' + total + ' datos listos para verificar'; }

    var completo = listos === total;
    if (completo !== completoAntes) {
      // No se dice nada al cargar la página si faltan datos; solo cuando cambia el estado.
      if (completo) {
        estado.textContent = hayVerificar
          ? 'Todos los datos están listos. Guarda los cambios y pulsa «Verificar sitio».'
          : 'Todos los datos están listos. Guarda el sitio y luego, desde «Editar», pulsa «Verificar sitio».';
      } else if (completoAntes !== null) {
        estado.textContent = 'Faltan datos para poder verificar el sitio.';
      }
      completoAntes = completo;
    }
  }

  formulario.addEventListener('input', actualizar);
  formulario.addEventListener('change', actualizar);
  actualizar();
})();
