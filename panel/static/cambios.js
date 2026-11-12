/* Avisa antes de salir de la página si hay cambios sin guardar en el formulario.

   Compara el contenido del formulario al cargar la página con el que hay al salir.
   Al guardar (enviar el formulario) no avisa. El mensaje lo pone el navegador. */
(function () {
  'use strict';

  var formulario = document.querySelector('form.formulario');
  if (!formulario) { return; }

  function foto() {
    var partes = [];
    new FormData(formulario).forEach(function (valor, nombre) {
      partes.push(nombre + '=' + valor);
    });
    return partes.join('&');
  }

  var inicial = foto();
  var guardando = false;

  formulario.addEventListener('submit', function () { guardando = true; });

  window.addEventListener('beforeunload', function (evento) {
    if (guardando) { return; }
    if (foto() !== inicial) {
      evento.preventDefault();
      evento.returnValue = '';
    }
  });
})();
