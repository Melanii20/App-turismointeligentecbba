/* Mapa para elegir la ubicación de un sitio (Leaflet + OpenStreetMap).

   Es una AYUDA OPCIONAL: los campos de latitud y longitud siguen siendo la vía
   principal, y el formulario funciona igual sin JavaScript (el bloque del mapa
   está oculto hasta que este script lo muestra).

   Qué hace:
   - Clic en el mapa: coloca el marcador y llena latitud y longitud.
   - Arrastrar el marcador (o moverlo con las flechas del teclado): actualiza los campos.
   - Escribir en los campos: mueve el marcador.
   - Botones: usar mi ubicación actual, marcar el centro del mapa, quitar ubicación.
   - Un aviso con aria-live anuncia cada cambio a quien usa lector de pantalla. */
(function () {
  'use strict';

  var bloque = document.getElementById('bloque-mapa');
  var contenedor = document.getElementById('mapa');
  var campoLat = document.getElementById('latitud');
  var campoLon = document.getElementById('longitud');
  var aviso = document.getElementById('estado-mapa');
  var botonUbicacion = document.getElementById('mapa-mi-ubicacion');
  var botonCentro = document.getElementById('mapa-marcar-centro');
  var botonQuitar = document.getElementById('mapa-quitar');

  if (!bloque || !contenedor || !campoLat || !campoLon || typeof L === 'undefined') {
    return; // sin mapa: el formulario sigue funcionando con los campos de texto
  }

  // Solo sirve para encuadrar el mapa al abrirlo (Cochabamba). NO se guarda ni se
  // usa para rellenar los campos: la ubicación solo existe si la administradora la marca.
  var CENTRO_INICIAL = [-17.3935, -66.157];
  var ZOOM_INICIAL = 13;
  var ZOOM_SITIO = 17;
  var PASO_TECLADO = 10; // píxeles que se mueve el marcador con cada flecha (x5 con Mayús)

  bloque.hidden = false;
  L.Icon.Default.imagePath = contenedor.getAttribute('data-imagenes') || '';

  var mapa = L.map(contenedor, { zoomControl: false });
  L.control.zoom({ zoomInTitle: 'Acercar', zoomOutTitle: 'Alejar' }).addTo(mapa);
  var capaMosaicos = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">Colaboradores de OpenStreetMap</a>'
  }).addTo(mapa);

  var marcador = null;

  // Si por algún motivo el mapa quedó sin altura (CSS que no cargó), se le da una para que se vea.
  if (contenedor.offsetHeight < 50) {
    contenedor.style.height = '22rem';
    mapa.invalidateSize();
  }

  // Si los mosaicos no cargan (sin internet o bloqueados), se avisa una sola vez.
  var avisoMosaicos = false;
  capaMosaicos.on('tileerror', function () {
    if (avisoMosaicos) { return; }
    avisoMosaicos = true;
    anunciar('No se pudo cargar la imagen del mapa (¿sin conexión a internet?). ' +
             'Puedes seguir escribiendo la latitud y la longitud.');
  });

  function leerNumero(texto, minimo, maximo) {
    var t = String(texto).trim().replace(',', '.');
    if (!/^-?\d+(\.\d+)?$/.test(t)) { return null; }
    var n = parseFloat(t);
    return (n >= minimo && n <= maximo) ? n : null;
  }

  function leerCampos() {
    var lat = leerNumero(campoLat.value, -90, 90);
    var lon = leerNumero(campoLon.value, -180, 180);
    return (lat !== null && lon !== null) ? L.latLng(lat, lon) : null;
  }

  function anunciar(texto) {
    if (aviso) { aviso.textContent = texto; }
  }

  function escribirCampos(punto) {
    campoLat.value = punto.lat.toFixed(6);
    campoLon.value = punto.lng.toFixed(6);
  }

  function textoUbicacion(punto) {
    return 'Ubicación seleccionada: latitud ' + punto.lat.toFixed(6) +
           ', longitud ' + punto.lng.toFixed(6) + '.';
  }

  // Mueve el marcador con las flechas cuando tiene el foco (alternativa al arrastre con ratón).
  function moverConFlechas(evento) {
    var dx = 0, dy = 0;
    var paso = PASO_TECLADO * (evento.shiftKey ? 5 : 1);
    if (evento.key === 'ArrowLeft') { dx = -paso; }
    else if (evento.key === 'ArrowRight') { dx = paso; }
    else if (evento.key === 'ArrowUp') { dy = -paso; }
    else if (evento.key === 'ArrowDown') { dy = paso; }
    else { return; }
    evento.preventDefault();
    evento.stopPropagation(); // que no se desplace el mapa a la vez
    var px = mapa.latLngToContainerPoint(marcador.getLatLng());
    var nuevo = mapa.containerPointToLatLng(L.point(px.x + dx, px.y + dy)).wrap();
    marcador.setLatLng(nuevo);
    escribirCampos(nuevo);
    anunciar(textoUbicacion(nuevo));
  }

  // Coloca (o mueve) el marcador. Si 'zoom' tiene valor, acerca el mapa a ese punto.
  function colocar(punto, zoom) {
    if (!marcador) {
      marcador = L.marker(punto, {
        draggable: true,
        keyboard: true,
        title: 'Ubicación del sitio. Usa las flechas para moverla.',
        alt: 'Marcador de la ubicación del sitio'
      }).addTo(mapa);
      marcador.on('dragend', function () {
        var p = marcador.getLatLng().wrap();
        marcador.setLatLng(p);
        escribirCampos(p);
        anunciar(textoUbicacion(p));
      });
      marcador.getElement().addEventListener('keydown', moverConFlechas);
    } else {
      marcador.setLatLng(punto);
    }
    if (zoom) { mapa.setView(punto, zoom); }
  }

  function quitar() {
    if (marcador) { mapa.removeLayer(marcador); marcador = null; }
    campoLat.value = '';
    campoLon.value = '';
    anunciar('Ubicación quitada. Los campos de latitud y longitud quedaron vacíos.');
  }

  // --- Estado inicial: al editar, el marcador aparece donde ya está guardado el sitio ---
  // Primero hay que darle una vista al mapa; Leaflet no dibuja marcadores antes.
  var inicial = leerCampos();
  mapa.setView(inicial || CENTRO_INICIAL, inicial ? ZOOM_SITIO : ZOOM_INICIAL);
  if (inicial) { colocar(inicial); }

  // --- Clic en el mapa ---
  mapa.on('click', function (e) {
    var p = e.latlng.wrap();
    colocar(p);
    escribirCampos(p);
    anunciar(textoUbicacion(p));
  });

  // --- Escribir en los campos mueve el marcador ---
  function alCambiarCampos() {
    var vacios = campoLat.value.trim() === '' && campoLon.value.trim() === '';
    if (vacios) { quitar(); return; }
    var p = leerCampos();
    if (p) {
      colocar(p, Math.max(mapa.getZoom(), ZOOM_SITIO));
      anunciar(textoUbicacion(p));
    } else {
      anunciar('Las coordenadas todavía no son válidas: la latitud va de -90 a 90 y la longitud de -180 a 180.');
    }
  }
  campoLat.addEventListener('change', alCambiarCampos);
  campoLon.addEventListener('change', alCambiarCampos);

  // --- Botones ---
  if (botonCentro) {
    botonCentro.addEventListener('click', function () {
      var p = mapa.getCenter().wrap();
      colocar(p);
      escribirCampos(p);
      anunciar(textoUbicacion(p) + ' Mueve el marcador con las flechas si hace falta.');
      marcador.getElement().focus();
    });
  }

  if (botonQuitar) {
    botonQuitar.addEventListener('click', quitar);
  }

  if (botonUbicacion) {
    if (!navigator.geolocation) {
      botonUbicacion.disabled = true;
      botonUbicacion.title = 'Tu navegador no permite obtener la ubicación.';
    } else {
      botonUbicacion.addEventListener('click', function () {
        // Los navegadores solo dan la ubicación en conexiones seguras (https) o en localhost.
        // Al entrar desde otro equipo por http://192.168..., no la dan aunque aceptes el permiso.
        if (window.isSecureContext === false) {
          anunciar('El navegador solo permite usar la ubicación en conexiones seguras (https) o en localhost. ' +
                   'Marca el punto en el mapa o escribe las coordenadas.');
          return;
        }
        anunciar('Buscando tu ubicación...');
        navigator.geolocation.getCurrentPosition(
          function (posicion) {
            var p = L.latLng(posicion.coords.latitude, posicion.coords.longitude);
            colocar(p, 18);
            escribirCampos(p);
            anunciar(textoUbicacion(p) + ' Precisión aproximada: ' +
                     Math.round(posicion.coords.accuracy) + ' metros.');
          },
          function (error) {
            var mensajes = {
              1: 'No diste permiso para usar tu ubicación. Puedes marcarla en el mapa o escribir las coordenadas.',
              2: 'No se pudo determinar tu ubicación. Márcala en el mapa o escribe las coordenadas.',
              3: 'La búsqueda de tu ubicación tardó demasiado. Inténtalo de nuevo o márcala en el mapa.'
            };
            anunciar(mensajes[error.code] || 'No se pudo obtener tu ubicación.');
          },
          { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
        );
      });
    }
  }
})();
