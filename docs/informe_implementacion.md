# Informe de implementación (11 de noviembre de 2026)

Resumen: se implementó el backend completo (grafo de decisión, herramientas, API, Wikipedia con caché,
bot de Telegram, métricas), las migraciones 1 a 6, el panel con los campos nuevos y la app Flutter
(solo agregando). **Pasan 56 pruebas de Python y 43 pruebas de Flutter, `flutter analyze` no encuentra
problemas y la app compila (`flutter build apk --debug`).** Lo que NO se pudo comprobar desde aquí
está en la sección 2: no corrí la app en el emulador ni en tu teléfono, no probé el LLM (no hay clave)
y Wikipedia no se consultó en vivo.

## 1. Qué quedó funcionando, parte por parte

**Parte 1 · Preparación.** `docker-compose.yml` (backend en el puerto 8000, panel en el 8080, bot de
Telegram con perfil aparte), `.env` y `.env.ejemplo`, `requirements.txt`, `GET /api/estado`. Se comprobó
con `docker compose up backend panel`: `/api/estado` responde `ok` y el panel carga su pantalla de login.

**Parte 2 · Base de datos.** Respaldo hecho antes de tocar nada (`respaldo_antes_implementacion.sql`,
185 KB, no se sube a git). Migraciones 001 a 006 aplicadas y guardadas en `migraciones/` (la 001, `estado`,
ya existía en la base: es idempotente). `construir_texto()` ahora usa nombre, tipo, descripción, relato,
qué ver y descripción sensorial, y solo genera frases de accesibilidad si el dato existe (NULL no genera
nada). Los 18 embeddings se regeneraron con `generar_embeddings.py --todos`.

**Parte 3 · Panel.** El login con bcrypt ya existía (el usuario ya tiene un hash `$2b$`, no se tocó).
Sitios (listar con filtro, crear, editar → vuelve a borrador, verificar, embedding al guardar) ya
funcionaban. Se agregaron al formulario de sitios: historia o leyenda, qué ver, horario, costo de ingreso,
duración de la visita y servicios. Eventos ahora tienen hora de inicio y fin, latitud y longitud
(opcionales; las coordenadas se copian de Google Maps). Probado contra la base real (crear, editar,
validar, borrar) y los datos temporales se limpian al terminar.

**Parte 4 · Grafo y herramientas** (`asistente/servicios/`). Router por reglas con la prioridad del
CLAUDE.md (incluye confirmación, cultura, "si nombra un sitio siempre es información"), resolver sitio
(nombre → último sitio del contexto → "¿A qué lugar te refieres?"), las 11 herramientas con su registro,
`decidir_accion` (tabla del nodo 7), `accion_pendiente`, `escuchar_despues`, `POST /api/consulta` con el
contrato exacto, `GET /api/eventos/hoy` (el más cercano primero dentro de 3 km), métricas sin datos
personales y límite de 20 consultas por minuto con slowapi. Búsqueda híbrida: "tranquilo" → ruido bajo,
"piso táctil", "perro guía" y el tipo se filtran con SQL exacto (los sitios con ese dato en NULL nunca
entran). La API anterior `/preguntar` sigue igual.

**Parte 5 · LLM y Wikipedia.** `servicios/llm.py` es un adaptador configurable desde el `.env`
(`LLM_PROVEEDOR` = `ninguno`, `anthropic` u `openai`-compatible; `LLM_MODELO`, `LLM_API_KEY`). **Sin
clave todo funciona con plantillas** (así se probó todo). `buscar_wikipedia` usa la caché (30 días), solo
se llama desde `cultura` después del RAG, y descarta lo que no menciona Cochabamba. `evaluar_ragas.py`
queda preparado (no se ejecutó, como pediste).

**Parte 6 · App Flutter (solo agregando).** Ver sección 4. Conexión con `/api/consulta` enviando el
contexto; `_cambiarEstado()` ahora también dispara sonido y vibración; tarjeta "Hoy" con el evento más
cercano y anuncio al abrir; línea de fuente bajo el globo; acciones sin botones (navegación automática al
terminar de hablar con `geo:` y respaldo de Google Maps, cancelable con Detener; compartir por `wa.me`, `sms:`
o la hoja de compartir; micrófono automático con `escuchar_despues`); Ajustes (velocidad de voz, anunciar
eventos, sonidos, vibración, ubicación, aviso diario y contacto de confianza); ayuda por voz.

**Parte 7 · Prioridad baja.** Aviso diario de eventos (workmanager + notificaciones locales, desactivado
por defecto, se activa en Ajustes). Bot de Telegram en `asistente/telegram_bot.py`: sin `TELEGRAM_TOKEN`
no arranca y no rompe nada (comprobado); no guarda `chat_id` ni conversaciones.

**Parte 8 · Pruebas** (`pruebas/`): `preguntas_router.json` con 65 preguntas (al menos 5 por intención;
acierto del router: 100 %), `test_acciones.py` (una prueba por fila del nodo 7), `test_herramientas.py`
(con la base de prueba) y `test_fuentes.py` ("un sitio que no está en la base nunca llega a Wikipedia",
borrador incluido; eventos nunca usan Wikipedia; la caché; el contrato de la API; límites de entrada).
`docs/grafo_asistente.mmd` actualizado (ver sección 2, punto 8).

## 2. Qué falló o quedó incompleto

1. **Wikipedia respondía 403 en vivo.** Wikimedia exige un contacto en el `User-Agent`; el texto del
   CLAUDE.md (`GuiaCochala/1.0 (proyecto de grado UNIFRANZ)`) no alcanza. Lo comprobé con una petición real.
   No puse tu correo sin preguntarte: ahora el contacto sale de `WIKIPEDIA_CONTACTO` en el `.env`
   (vacío por defecto). **Sin esa variable Wikipedia no se consulta** y las preguntas culturales sin
   respuesta en la base dicen "No tengo información sobre eso". Las pruebas usan respuestas simuladas, así
   que la consulta real no se comprobó con el contacto puesto.
2. **El LLM no se probó** (no hay clave). Solo se probó el camino de plantillas. El código del LLM (prompt
   con las reglas del nodo 6, clasificador 2b, tiempo máximo de 15 s) existe pero no se ejecutó contra un
   servicio real.
3. **La app no se corrió en un emulador ni en un teléfono desde aquí.** Solo se comprobó que compila y que
   pasan sus pruebas con voz, red, sonido y acciones simulados. Sonidos, vibración, ubicación, abrir mapas
   y WhatsApp, y el aviso diario hay que probarlos en el teléfono.
4. **Un sitio con nombre propio que no está en la base puede recibir el sitio más parecido.** Ejemplo:
   "Cuéntame del Museo del Louvre" devuelve "Lo que mejor encaja con tu pregunta es: Museo Arqueológico…".
   Es honesto (lo dice) y nunca va a Wikipedia, pero lo ideal sería responder "No tengo información". Se
   arregla con más datos reales y recalibrando `UMBRAL` (ahora 0.50, calibrado con 3 sitios).
5. **Datos de prueba.** `datos_prueba.sql` (15 sitios y 7 eventos con datos `acceso_*` INVENTADOS) ya estaba
   cargado en la base antes de esta sesión, porque lo pediste para ver el sistema funcionando. Tú me
   dijiste que no lo ejecutara si rellenaba `acceso_*` con datos inventados: **no lo volví a ejecutar**, pero
   sí agregué `datos_prueba_eventos_ubicacion.sql` (también ficticio: coordenadas y horario de los eventos de
   prueba) y todas las pruebas usan esos datos. Antes de calibrar, evaluar con Ragas o probar con usuarios,
   ejecuta `borrar_datos_prueba.sql`. Las pruebas de herramientas dependen de esos datos, así que después de
   borrarlos fallarán hasta que cargues datos reales.
6. **Los 3 sitios originales** (Cristo, Convento, La Cancha) siguen en borrador y tienen `acceso_piso_tactil =
   false`, braille `false` y perros `true` que vienen del antiguo valor por defecto, no de una verificación.
   La migración 3 solo quita el valor por defecto; no cambia filas. Revísalos y déjalos en NULL.
7. **Con la voz propia apagada** (TalkBack), la app no sabe cuándo termina TalkBack de leer: las acciones se
   ejecutan pasado un tiempo proporcional al largo del texto (entre 2,5 y 15 s). Mientras tanto se puede
   cancelar pulsando Hablar o Escribir.
8. **Diferencias con el grafo del CLAUDE.md** (ya reflejadas en `docs/grafo_asistente.mmd`): sin LLM
   configurado, una pregunta que ninguna regla reconoce se manda al RAG (que responde "No tengo información"
   si no hay nada) en vez de "no clara"; `cercania` responde con plantilla y no con LLM; si una pregunta
   cultural nombra un tipo de lugar que no está en la base ("la leyenda del Museo X"), va a `informacion` y
   nunca a Wikipedia.
9. **Cambié el puerto del panel a 8080 solo dentro de `docker-compose.yml`** (el backend usa el 8000, como
   pediste). Tus comandos `docker run` del panel siguen funcionando igual, en el 8000.
10. **Al hacer el commit "antes de implementar" entró `panel/static/mapa.js`**, que tenías modificado sin
    commitear, porque agregué toda la carpeta `panel/`. Está en el commit `8298394b`. No toqué su contenido.
11. **Flutter**: `flutter_local_notifications` 21 exige `compileSdk 37` (tu proyecto compila con 36 y el
    plugin de Android lo limita a 36), así que fijé la versión **19.5.0**. También activé `coreLibraryDesugaring`
    en `android/app/build.gradle.kts`. La compilación pasa. Para `flutter run` el resultado debería ser igual.

## 3. Archivos nuevos y modificados

**Base de datos**
- `migraciones/001…006_*.sql` (nuevos): los seis cambios de esquema.
- `texto_embedding.py` (modificado): `construir_texto()` nuevo y `COLUMNAS_TEXTO`.
- `generar_embeddings.py` (modificado): lee las columnas nuevas; opción `--todos`.
- `datos_prueba_eventos_ubicacion.sql` (nuevo, ficticio): coordenadas y horario de eventos de prueba.

**Backend (`asistente/`)**
- `config.py` (modificado): parámetros de búsqueda, radios, límite, LLM, Wikipedia, Telegram.
- `main.py` (modificado): agrega el router `/api/*` y slowapi; `/preguntar` queda igual.
- `api/rutas.py` (nuevo): `/api/consulta`, `/api/eventos/hoy`, `/api/estado`, métricas.
- `servicios/grafo.py` (nuevo): los nodos del grafo.
- `servicios/router_reglas.py` (nuevo): normalizar + router por reglas.
- `servicios/llm.py` (nuevo): adaptador de LLM; sin clave devuelve None.
- `servicios/geo.py` (nuevo): haversine, distancia dicha en voz alta, enlace de mapa.
- `servicios/herramientas/*.py` (nuevos): `buscar_sitios`, `sitios_cercanos`, `datos_practicos`,
  `como_llegar`, `eventos` (`eventos_por_fecha` y `eventos_de_hoy`), `armar_itinerario`,
  `armar_mensaje_compartir`, `buscar_wikipedia`, `decidir_accion`, `generar_respuesta`, `datos` y el
  registro en `__init__.py`.
- `telegram_bot.py` (nuevo): bot opcional. `requirements.txt` (modificado): httpx, slowapi, pytest,
  python-telegram-bot.
- `busqueda.py`, `generador.py`, `intencion.py`, `nombres.py`, `modelo.py`, `db.py`: sin cambios (se reutilizan).

**Panel (`panel/`)**: `main.py` (campos nuevos de sitios y eventos), `templates/sitio_form.html` (sección
"Información para visitantes"), `templates/evento_form.html` (hora y coordenadas). Las rutas y plantillas
de eventos de la sesión anterior se mantienen.

**Raíz**: `docker-compose.yml`, `.env.ejemplo`, `.env` (no se sube), `requirements.txt`,
`evaluar_ragas.py` (preparado), `pruebas/` (nuevo), `CLAUDE.md` (reglas de diseño, Git, estructura real),
`docs/grafo_asistente.mmd`, `.gitignore` (respaldos `.sql`), `docs/informe_implementacion.md`.

**App (`flutter_application_1/`)**: ver la sección 4.

## 4. Cambios en `flutter_application_1` y confirmación de que el diseño sigue igual

Archivos EXISTENTES que modifiqué (todo son líneas agregadas o conexiones mínimas):

| Archivo | Qué cambió |
|---|---|
| `lib/pantalla_chat.dart` | Parámetros opcionales nuevos del constructor; `_cambiarEstado()` llama a los efectos; métodos nuevos (eventos de hoy, acciones, `_callar`); el globo ahora va en una `Column` junto a la línea de fuente; la tarjeta "Hoy" se agrega como un `Positioned` nuevo; el texto de estado puede mostrar "Abriendo navegación…" (`_avisoEstado ?? _estado.etiqueta`); `_HojaAjustes` recibe los servicios y agrega `AjustesAdicionales` al final; Ayuda también se lee en voz alta; "No te entendí, intenta de nuevo". Se **reemplazaron** tres líneas: `widget.voz.callar()` por `_callar()` (que además cancela acciones), y las dos llamadas directas a `HapticFeedback` por los efectos (para respetar el ajuste de vibración). |
| `lib/main.dart` | Crea los servicios nuevos y los pasa a la pantalla; usa `ClienteConsulta` en lugar de `ClienteHttp`. |
| `lib/cliente_asistente.dart` | Clase `AccionAsistente` nueva y tres campos opcionales en `RespuestaAsistente` (`fuente`, `acciones`, `escucharDespues`). |
| `lib/servicio_voz.dart` | `ServicioVozReal` acepta los ajustes para la velocidad de la voz. |
| `lib/config.dart` | La dirección por defecto pasó de `http://localhost:8001` a `http://10.0.2.2:8000`. |
| `pubspec.yaml`, `android/app/src/main/AndroidManifest.xml`, `android/app/build.gradle.kts` | Paquetes, permisos (ubicación, notificaciones), `queries` para abrir mapas/WhatsApp/SMS, desugaring. |
| `test/widget_test.dart` | 2 líneas: el interruptor de la voz ahora es `.first` (Ajustes tiene varios) y la hoja de Ajustes se cierra con `Navigator.pop`. |

Archivos NUEVOS: `lib/servicios/` (`ajustes`, `acciones`, `efectos`, `ubicacion`, `eventos_hoy`,
`cliente_consulta`, `aviso_diario`), `lib/widgets/` (`tarjeta_hoy`, `linea_fuente`, `ajustes_extra`),
`assets/sonidos/` (3 `.wav`) y `test/funciones_nuevas_test.dart`.

**Confirmación:** no se modificó ningún archivo del fondo (`fondo_animado.dart`, `petalos.dart`), de los
colores y tipografías (`paleta.dart`, `tipografia.dart`), del avatar (`avatar_asistente.dart`,
`widgets/avatar_abuela.dart`, los `.riv`), de los botones ni del globo (`barra_inferior.dart`,
`barra_superior.dart`, `globo_dialogo.dart`). Sus pruebas siguen pasando sin cambios (paleta, contraste,
personaje decorativo, orden de lectura, 48 dp, letra al 150 % y 200 %, "quitar animaciones"). Lo que **vas a ver
distinto**: aparece la línea de fuente bajo el globo (solo con respuestas de la base o de Wikipedia), la tarjeta
"Hoy" (si hay eventos hoy) y más opciones en Ajustes. Me falta que lo mires tú en pantalla.

## 5. Comandos para probar cada parte (PowerShell, desde `C:\tesis`)

```powershell
# 1) Levantar backend (8000) y panel (8080). La base es tu contenedor postgres-tesis.
docker start postgres-tesis
docker compose up -d backend panel
Invoke-RestMethod http://localhost:8000/api/estado            # {"estado":"ok", ...}

# 2) Consultas de ejemplo (el cuerpo va en UTF-8 para que los acentos lleguen bien)
$b = [Text.Encoding]::UTF8.GetBytes((@{pregunta="¿Cómo llego a la Catedral Metropolitana?"; latitud=-17.3935; longitud=-66.157} | ConvertTo-Json))
Invoke-RestMethod http://localhost:8000/api/consulta -Method Post -Body $b -ContentType "application/json; charset=utf-8"
# otras: "¿Qué lugar tiene piso táctil?", "¿Qué hay este fin de semana?", "Arma un recorrido", "¿Qué hay cerca de mí?"
Invoke-RestMethod "http://localhost:8000/api/eventos/hoy?latitud=-17.3935&longitud=-66.157"
# (los acentos pueden verse mal en la consola de PowerShell; la app los muestra bien)

# 3) Panel: http://localhost:8080  (login con admin@turismo.test y TU contraseña)

# 4) Pruebas de Python (dentro de Docker)
docker run --rm -v C:\tesis:/app -v tesis-modelos:/root/.cache/huggingface -e DB_HOST=host.docker.internal -e PYTHONPATH=/app/asistente:/app -w /app tesis-asistente python -m pytest pruebas -q -s

# 5) Recalcular embeddings (si cambias construir_texto)
docker run --rm -v C:\tesis:/app -v tesis-modelos:/root/.cache/huggingface -e DB_HOST=host.docker.internal -w /app tesis-python python generar_embeddings.py --todos

# 6) Bot de Telegram (opcional): pon TELEGRAM_TOKEN en .env y
docker compose --profile telegram up telegram

# 7) App en el emulador (el emulador ve tu PC como 10.0.2.2, que ya es la dirección por defecto)
cd C:\tesis\flutter_application_1
flutter pub get
flutter analyze
flutter test
flutter run -d emulator-5554
#   teléfono real por USB:  adb reverse tcp:8000 tcp:8000   y luego
#   flutter run --dart-define=API_URL=http://localhost:8000

# 8) Borrar los datos ficticios (antes de calibrar / Ragas / pruebas con usuarios)
docker cp borrar_datos_prueba.sql postgres-tesis:/tmp/b.sql
docker exec postgres-tesis psql -U postgres -d turismo_db -f /tmp/b.sql
```

## 6. Lo que necesitas hacer tú

- **Clave del LLM:** elige proveedor y pon `LLM_PROVEEDOR`, `LLM_MODELO` y `LLM_API_KEY` en el `.env`
  (solo allí). Después prueba preguntas y revisa a mano que el LLM no agregue datos de accesibilidad.
- **Contacto para Wikipedia:** pon tu correo o la página del proyecto en `WIKIPEDIA_CONTACTO` del `.env`.
- **Sonidos definitivos:** los 3 de `assets/sonidos/` son tonos generados (placeholder, sin copyright, `.wav`).
  Cámbialos por sonidos CC0 (puedes usar `.ogg`; actualiza los nombres en `lib/servicios/efectos.dart`).
- **Datos de accesibilidad reales:** verifica sitios reales en el panel, borra los de prueba, y revisa los 3
  sitios originales (sección 2, punto 6). Luego recalibra `UMBRAL` y `MARGEN` con `calibrar_umbral.py`.
- **Avisos de accesibilidad visual** (no los cambié, como pediste):
  - En pantallas bajas, entre el título y el personaje no cabe la tarjeta "Hoy" completa; se usa una versión
    **compacta** (48 dp de alto, 12 sp) a la izquierda que toca la esquina superior del recuadro del personaje
    (es transparente). Si te molesta, la opción que menos altera el diseño es dejarla compacta siempre.
  - La línea de fuente (12 sp, color `tintaSuave`) y el texto de la tarjeta compacta son pequeños; para quien tenga
    baja visión conviene probar con "tamaño de fuente grande" del teléfono (los textos crecen hasta 130 %).
  - La hoja de Ajustes ahora es larga: hace scroll. Con TalkBack se recorre en orden.
- **Probar en el teléfono:** sonidos, vibración, ubicación, abrir navegación/WhatsApp, aviso diario, TalkBack.
- **Commits:** ya hay 5 commits míos (sin `git push`; sigue sin haber remoto). `.claude/` y `CLAUDE_anterior.md`
  quedaron sin subir a propósito.

## 7. Qué partes de la tesis actualizar

- **Capítulo IV (diseño):** requerimientos funcionales nuevos (Wikipedia solo cultural y después del RAG,
  tarjeta de eventos con el más cercano, el asistente decide la navegación, enviar a un familiar, itinerario,
  sonidos y vibración, aviso diario, Telegram); figura del grafo (`docs/grafo_asistente.mmd`, regenerar el PNG);
  diagrama de despliegue (backend, panel, base, Wikipedia, Telegram); 4.5 y 4.6 con las pantallas finales.
- **Diccionario de datos:** columnas nuevas de `sitios_turisticos` y `eventos`, tablas `contenido_web` y
  `metricas_consulta`, y la decisión de quitar los valores por defecto de `acceso_*`.
- **Capítulo V (costos):** todo cero salvo el LLM por API; mencionar Wikipedia, `geo:`, `wa.me`, notificaciones locales.
- **Capítulo VI:** pruebas automáticas (65 preguntas del router con 100 % de acierto, 56 pruebas de Python y 43
  de Flutter), métricas sin datos personales, Ragas (fidelidad y relevancia) y pruebas con usuarios con TalkBack.
- **Capítulo III y bibliografía:** secciones duplicadas (3.5/3.7 y 3.9/3.10), marcadores "[fecha]; [hora]" y
  las páginas citadas de Oviatt (286–304), como ya estaba anotado.


---

# Informe de la sesión del 11/11/2026: documentos, agentes y cascada de fuentes

Este informe se agrega al anterior. Está escrito para leerse sin saber programar. Las partes A a G del pedido están hechas y con commit.

## 0. Antes de empezar: las claves

Comprobé el `.env` sin mostrar ningún valor:

| Variable | Estado |
|---|---|
| `LLM_MODELO` | existe |
| `LLM_PROVEEDOR` | existe (con el valor `gemini`; el código acepta `gemini` y `google`) |
| `WIKIPEDIA_CONTACTO` | existe |
| `GOOGLE_API_KEY` | **no existe** en el archivo |
| `TAVILY_API_KEY` | **no existe** en el archivo |
| `DOMINIOS_CONFIABLES`, `TAVILY_SCORE_MIN` | no existen (el código usa los valores por defecto: `es.wikipedia.org` y 0.5) |

Lo que hice: el código lee la clave de Gemini de `GOOGLE_API_KEY` y, si no existe, de `LLM_API_KEY` (que sí tiene un valor y funciona con Gemini: las llamadas reales de humo pasaron). **Tavily no se pudo probar en vivo**: sin clave, el sistema usa Wikipedia directa, y eso sí lo probé. No modifiqué tu `.env` (el sistema de permisos bloqueó esa acción); agregué las líneas nuevas al `.env.ejemplo`. Cuando tengas la clave de Tavily, agrega estas líneas al `.env`:

```
TAVILY_API_KEY=<tu clave>
TAVILY_SCORE_MIN=0.5
DOMINIOS_CONFIABLES=es.wikipedia.org
```

(En `DOMINIOS_CONFIABLES` puedes agregar sitios oficiales separados por comas, y si quieres, cambia `LLM_PROVEEDOR` a `google`; ambos valores funcionan.)

## 1. Qué funciona y qué falló

**Funciona** (verificado con pruebas): 102 pruebas del backend pasan y 1 se omite a propósito; 13 pruebas del panel pasan; las 3 llamadas reales de humo a Gemini pasan; `probar_guia.py` da 0 filas en FALLA (manual: 11, no ejecutable: 11, pasa: 37).

- **A** · Un lugar con nombre propio que no está en la base ("Museo del Louvre", "Torre Eiffel") responde "No tengo información sobre <lugar>. Puedo contarte de los museos de Cochabamba que tengo registrados." y nunca dice "Lo que mejor encaja". `GET /api/estado` dice con verdadero o falso si están configurados la base, Gemini, Tavily y Wikipedia, sin mostrar claves. El CLAUDE.md tiene la sección Entorno nueva. `.claude/` y `CLAUDE_anterior.md` ya están en git.
- **B** · Sección "Documentos" del panel: subir PDF, DOCX o TXT con permiso de uso obligatorio, fragmentos de unos 800 caracteres con 150 de solapamiento, vista previa, verificar, editar o reemplazar (vuelve a borrador), eliminar con confirmación, y aviso "este PDF es una imagen; súbelo con texto". El asistente consulta sitios, eventos y documentos verificados (`buscar_en_base`) y cada resultado dice su origen y su página. Documento ficticio cargado y verificado.
- **C** · Regla de dos ejes (operativo o narrativo) y cascada N1 base y documentos → N2 caché → N3 web → N4 alternativa de la base. La intención `cultura` ahora se llama `saberes`. Preguntas compuestas, "¿Quieres saber más?" y "cuéntame más". El orden de los niveles lo impone el código (la web se niega si antes no se consultó la base y la caché).
- **D** · Tres agentes con Pydantic AI y Gemini (clasificador, sitios, saberes) con salida tipada, límite de 1, 1 y 3 solicitudes, y 15 segundos. Si Gemini falla, da 429 o tarda, el sistema responde con una plantilla que lee el fragmento citando la fuente.
- **E** · Panel "Contenido traído de internet": lista con título, dominio, URL, tema, fecha y estado; "Convertir en documento" y "Descartar".
- **F** · `pruebas/probar_guia.py` (resultado completo abajo).
- **G** · CLAUDE.md actualizado (dos ejes, cascada, tabla de agentes, documentos, funciones congeladas y funciones terminadas) y `docs/grafo_asistente.mmd` actualizado.

**Falló o quedó incompleto** (con el error exacto):

1. **Tavily no probado en vivo**: falta `TAVILY_API_KEY`. Las pruebas con Tavily simulado verifican los parámetros que se le envían (`search_depth="basic"`, `max_results=3`, `country="bolivia"`, `include_answer=False`, `include_domains_mode="restrict"`), pero ninguna llamada real.
2. **Gemini a veces responde con alta demanda**: `ModelUnavailableError: status_code: 503 ... 'This model is currently experiencing high demand'` con el modelo `gemini-3.5-flash-lite`. Cuando pasa, el sistema cae a la plantilla y sigue funcionando (es justo lo que prueba la fila 12.1). Una de las 3 llamadas de humo se omitió por eso y pasó al reintentar. Si molesta, prueba otro modelo en `LLM_MODELO`.
3. **Una respuesta de Wikipedia puede ser del tema equivocado**: "¿Qué es la chicha y dónde la puedo probar?" trae el artículo "Chicha morada" (una bebida peruana) porque el texto menciona Bolivia. La regla de aceptación pedida (menciona el tema y Cochabamba o Bolivia) lo deja pasar. Con Tavily y tus sitios oficiales en `DOMINIOS_CONFIABLES` debería mejorar; si no, habría que endurecer la regla para bebidas y platos.
4. **Pruebas que no se pudieron correr tal cual** (ver tabla): las filas que nombran al Cristo de la Concordia, La Cancha y el Convento de Santa Teresa están "NO EJECUTABLE" porque esos 3 sitios siguen en borrador y no se pueden verificar sin registrar sus datos de accesibilidad reales (no los voy a inventar). Corrí variantes equivalentes con sitios de prueba ya verificados (filas con "b").
5. **Errores que tuve y corregí** (hasta 3 intentos cada uno):
   - `pg_dump: could not open output file "C:/Users/.../r2.sql"`: Git Bash cambió la ruta `/tmp`; usé otra ruta.
   - Primera corrida de `probar_guia.py`: 13 filas en FALLA con `KeyError: 'creditos_tavily'` (y `eje_dato`, `motivo_sin_llm`, `accion_pendiente`). Era el script, no el sistema: esos datos no viajan en la respuesta de la API (los créditos y el eje van solo a las métricas y la acción pendiente va dentro de `contexto`). El script ahora los lee de ahí.
   - Fila 2.1: el clasificador a veces devolvía `informacion` en vez de `saberes`. Mejoré sus instrucciones; salió bien 3 veces seguidas.
   - Un documento ficticio de "leyenda" contestaba una pregunta sobre otra leyenda (similitud 0.534): agregué `UMBRAL_DOCUMENTOS` = 0.60 para los fragmentos de documentos.
   - La caché devolvía el artículo del Tinku para "gracias en quechua": ahora exige que coincida el 75 % de las palabras importantes.
   - `agente_saberes` pedía las tres herramientas aunque el contexto ya traía la respuesta y se pasaba del límite de 3 solicitudes (`limite_solicitudes`): el contexto ahora le dice que no llame herramientas si ya hay información.
   - Un error de `pytest` en la imagen del backend por importar el panel: las pruebas del panel se omiten solas fuera de la imagen del panel.

## 2. Resultado de `probar_guia.py`

Se ejecuta con (desde `C:\tesis`): `docker compose run --rm backend python pruebas/probar_guia.py`. El archivo `asistente/pruebas/probar_guia.py` es solo un atajo: el comando de la guía se ejecuta dentro de la carpeta `/app/asistente`, donde no existe `pruebas/`. El resultado completo queda en `docs/resultado_probar_guia.md`.

Resumen: MANUAL: 11, NO EJECUTABLE: 11, PASA: 37

| Fila | Pregunta o acción | Resultado | Motivo |
|---|---|---|---|
| 1.1 | ¿Qué puedes hacer? | PASA |  |
| 1.2 | ¿Quién ganó el partido de ayer? | PASA |  |
| 1.3 | ¿Qué horario tiene? (sin sitio) | PASA |  |
| 1.4 | ¿Cuánto cuesta un silpancho? | PASA |  |
| 1.5 | ¿Qué es la chicha y dónde la puedo probar? | PASA |  |
| 2.1 | Me da curiosidad lo que comen los cochabambinos | PASA |  |
| 2.2 | Quiero conocer algo bonito para pasear | PASA |  |
| 3.1 | Cuéntame del Cristo de la Concordia | NO EJECUTABLE | «Cristo de la Concordia» está en borrador (no se pueden inventar sus datos acceso_*) |
| 3.1b | Cuéntame de la Catedral Metropolitana | PASA |  |
| 3.2 | ¿El Cristo tiene piso táctil? | NO EJECUTABLE | «Cristo de la Concordia» está en borrador (no se pueden inventar sus datos acceso_*) |
| 3.2b | ¿La Catedral Metropolitana tiene piso táctil? | PASA |  |
| 3.3 | ¿La Cancha es ruidosa? | NO EJECUTABLE | «La Cancha» está en borrador (no se pueden inventar sus datos acceso_*) |
| 3.3b | ¿El Mercado 25 de Mayo es ruidoso? | PASA |  |
| 3.4 | Busco un lugar tranquilo | PASA |  |
| 3.5 | Cuéntame del Museo del Louvre | PASA |  |
| 4.1 | Cuéntame la leyenda de la piedra que canta | PASA |  |
| 4.2 | ¿Qué es el silpancho? (primera vez) | NO EJECUTABLE | falta TAVILY_API_KEY: no se puede verificar «1 crédito» |
| 4.2b | ¿Qué es el silpancho? (Wikipedia directa, sin Tavily) | PASA |  |
| 4.3 | ¿Qué es el silpancho? (segunda vez) | PASA |  |
| 4.4 | ¿De dónde viene la fiesta de Urkupiña? | PASA |  |
| 4.5 | ¿Cuándo es Urkupiña? | PASA |  |
| 4.6 | ¿Cómo se dice gracias en quechua? | PASA |  |
| 4.7 | Cuéntame la historia del Cristo → sí | NO EJECUTABLE | «Cristo de la Concordia» está en borrador |
| 4.7b | Cuéntame la historia de la Catedral Metropolitana → sí | PASA |  |
| 4.8 | agente_saberes no puede usar la web antes de la base | PASA | ..                                                                       [100%] 2 passed, 13 deselected in 12.88s  |
| 5.1 | ¿Qué hay hoy? | PASA |  |
| 5.1b | GET /api/eventos/hoy | PASA | HTTP 200 |
| 5.2 | ¿Qué fiestas hay este fin de semana? | PASA |  |
| 5.3 | Abrir la app (tarjeta Hoy) | MANUAL | necesita la app |
| 5.4 | Tocar «Escuchar eventos de hoy» | MANUAL | necesita la app |
| 6.1 | ¿Cómo llego a La Cancha? | NO EJECUTABLE | «La Cancha» está en borrador (no se pueden inventar sus datos acceso_*) |
| 6.1b | ¿Cómo llego a la Catedral Metropolitana? | PASA |  |
| 6.2 | ¿Dónde queda el Convento de Santa Teresa? → sí | NO EJECUTABLE | «Convento de Santa Teresa» está en borrador (no se pueden inventar sus datos acceso_*) |
| 6.2b | ¿Dónde queda la Iglesia de San Francisco? → sí | PASA |  |
| 6.3 | ¿Dónde queda el Convento? → no | NO EJECUTABLE | «Convento de Santa Teresa» está en borrador (no se pueden inventar sus datos acceso_*) |
| 6.3b | ¿Dónde queda la Iglesia de San Francisco? → no | PASA |  |
| 6.4 | ¿Cómo llego al Cristo? → Detener | MANUAL | necesita la app (el botón Detener) |
| 6.5 | Sin apps de mapas en el emulador | MANUAL | necesita el emulador |
| 7.1 | Avisa a mi familia que voy a La Cancha | NO EJECUTABLE | «La Cancha» está en borrador (no se pueden inventar sus datos acceso_*) |
| 7.1b | Avisa a mi familia que voy a la Catedral Metropolitana | PASA |  |
| 7.2 | Dile a mi familia dónde estoy | PASA |  |
| 7.3 | Contacto de confianza en Ajustes | MANUAL | necesita la app |
| 7.4 | Arma un recorrido para hoy | PASA |  |
| 8.1 | ¿A qué hora abre el Convento de Santa Teresa? | NO EJECUTABLE | «Convento de Santa Teresa» está en borrador (no se pueden inventar sus datos acceso_*) |
| 8.1b | ¿A qué hora abre la Catedral Metropolitana? | PASA |  |
| 8.2 | ¿Cuánto cuesta entrar al Cristo? → ¿y cuánto tiempo se necesita? | NO EJECUTABLE | «Cristo de la Concordia» está en borrador (no se pueden inventar sus datos acceso_*) |
| 8.2b | ¿Cuánto cuesta entrar a la Catedral Metropolitana? → ¿y cuánto tiempo? | PASA |  |
| 12.1 | GOOGLE_API_KEY incorrecta | PASA |  |
| 12.2 | Sin TAVILY_API_KEY | PASA |  |
| 12.3 | Apagar el backend con la app abierta | MANUAL | necesita la app |
| 12.4 | 25 preguntas en un minuto | PASA | códigos: [200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 429, 429, 429, 429, 429] |
| 14.1 | SELECT * FROM metricas_consulta ... LIMIT 10 | PASA | columnas: ['canal', 'creditos_tavily', 'eje_dato', 'fecha', 'fuente', 'id', 'intencion', 'motivo_sin_llm', 'nivel_fuente', 'similitud_maxima', 'sitio_id', 'tiempo_ms', 'uso_llm'] |
| 14.2 | No se envía ubicación ni contacto a Gemini/Tavily | PASA | prueba automática test_nunca_se_envia_la_ubicacion_ni_datos_personales_al_llm |
| 14.3 | SELECT nivel_fuente, count(*) ... GROUP BY 1 | PASA | [('ninguna', 199), ('base', 110), (None, 23), ('web', 18), ('cache_web', 16), ('documento', 6)] |
| 9 | Documentos (panel) | MANUAL | necesita el panel, la app o el teléfono |
| 10 | Contenido traído de internet (panel) | MANUAL | necesita el panel, la app o el teléfono |
| 11 | Panel de sitios y eventos | MANUAL | necesita el panel, la app o el teléfono |
| 13 | App: accesibilidad y sentidos (teléfono real) | MANUAL | necesita el panel, la app o el teléfono |
| 15 | Opcionales: aviso diario y Telegram | MANUAL | necesita el panel, la app o el teléfono |

Las filas 9, 10, 11, 13 y 15 (y 5.3, 5.4, 6.4, 6.5, 7.3 y 12.3) son **pruebas manuales** (necesitan el panel, la app o el teléfono). Detalles de lo que no coincide con la guía (no la cambié):

- Filas 3.1, 3.2, 3.3, 4.7, 6.1, 6.2, 6.3, 7.1, 8.1 y 8.2: la guía usa el Cristo, La Cancha y el Convento, que están en borrador.
- Fila 4.2: pide "1 crédito" de Tavily y no hay clave; la variante 4.2b prueba la ruta de respaldo (Wikipedia directa).
- Fila 1.4: la guía dice "No tengo precios verificados…"; el asistente dice "No tengo ese dato verificado. Solo doy precios, horarios y direcciones de la base verificada." (es el texto que pidió la regla central).
- Fila 5.1: hoy no hay eventos vigentes en los datos de prueba, así que responde "No tengo eventos registrados hoy".
- Fila 5.1 y 14: la guía habla de `accion_pendiente` y `creditos`/`nivel_fuente` como campos de la respuesta; en el contrato, `accion_pendiente` va dentro de `contexto` y los créditos solo se guardan en `metricas_consulta`.

## 3. Eliminado o reemplazado

| Qué | Con qué lo reemplacé | Por qué |
|---|---|---|
| Intención `cultura` | `saberes` (en el router, el grafo, `preguntas_router.json`, las pruebas, el CLAUDE.md y el diagrama) | Lo pidió la parte C; además el alcance es más amplio (gastronomía, artesanías, quechua, naturaleza). |
| `asistente/servicios/herramientas/buscar_wikipedia.py` y su entrada en el registro | `buscar_web.py` (Tavily y Wikipedia directa) y `buscar_en_cache`; el registro ahora tiene `buscar_en_base`, `buscar_en_cache` y `buscar_web` | Parte C3. |
| `asistente/servicios/llm.py` (adaptador con `anthropic` y `openai`) | `asistente/servicios/agentes/` con Pydantic AI y Gemini | Parte D. Ya no se usan `LLM_PROVEEDOR=anthropic` ni `openai`; solo `google` o `gemini`. `LLM_URL_BASE` ya no se usa. |
| `generar_respuesta_wikipedia()` | `agente_saberes` y la plantilla de `cascada.py` | La redacción con web ahora la hace el agente de saberes. |
| `generar_respuesta_sitios()` devolvía `(texto, uso_llm)` | devuelve `(texto, uso_llm, motivo_sin_llm)` y usa `agente_sitios` | Parte D. |
| Parámetro `wikipedia=` de `grafo.procesar()` y de `responder()` | `web=` | Ya no es solo Wikipedia. |
| Variable del `.env` `TEMAS_WIKIPEDIA` | (ya no se usa) los temas están en el código (`buscar_web.TEMAS`) | El alcance lo define la intención `saberes`. Puedes borrarla del `.env`. |
| Constante `CLASIFICADOR_SISTEMA` de `grafo.py` | instrucciones de `agente_clasificador` | Parte D. |
| Caché por título (`ILIKE`) | caché por palabras clave (75 %), sin lo descartado | Evita respuestas del tema equivocado. |
| "Lo que mejor encaja con tu pregunta es:" bajo el UMBRAL | nunca se dice bajo el UMBRAL | Parte A1. |
| "No tengo información sobre eso." a secas | "No tengo información sobre eso, pero puedo contarte de <un sitio de la base>." (nivel 4) | Parte C2. Si no hay sitios, queda la frase corta. |
| Pruebas `test_fuentes.py` de Wikipedia | pruebas equivalentes con Tavily y Wikipedia simulados; la prueba de métricas acepta las columnas nuevas | Siguen el cambio de nombres y de columnas. |
| Archivos borrados | ninguno de datos de la estudiante. Solo los dos del código de arriba. | — |

## 4. Requiere cambio en algo congelado

No cambié nada congelado sin avisar. Estas son cosas que encontré y que **requieren cambio** (no las toqué):

1. **App Flutter, línea de fuente**: si una respuesta viene de internet con un dominio que no es Wikipedia, `fuente` vale `web` y la app no muestra la línea "Fuente: …" (solo conoce `wikipedia` y `base_verificada`). Hoy no pasa porque `DOMINIOS_CONFIABLES` solo tiene Wikipedia; pasará cuando agregues sitios oficiales. La respuesta hablada sí cita la fuente. Cambio mínimo: en `lib/servicios/cliente_consulta.dart`, tratar `web` igual que `wikipedia` mostrando "Fuente: <nombre>".
2. **Métrica `eje_dato`** para `ayuda`, `fuera_de_alcance` y `confirmacion`: queda como "narrativo" por defecto; debería quedar vacía. Cambio mínimo en `grafo.procesar()`.
3. **`agente_sitios` y `cercania`**: el pedido dice que atiende `informacion` y `cercania`. La respuesta de cercanía sigue saliendo de SQL y plantilla (la distancia y el orden vienen de la base y el LLM no aporta). Si quieres que Gemini la redacte, hay que cambiar la rama `cercania` del grafo.
4. **Commit B**: el commit de la parte B incluye el borrado de `buscar_wikipedia.py` y `llm.py` (ya estaban preparados) y el de las partes C y D va junto en un solo commit (`3270bd41`) porque el grafo, la cascada y los agentes se importan entre sí.

## 5. SQL aplicado y filas afectadas

Antes de cambiar la base hice un respaldo (`respaldo_antes_sesion_b.sql`, no se sube a git). Migraciones en `migraciones/`:

| Migración | SQL | Filas |
|---|---|---|
| 007 | `UPDATE sitios_turisticos SET acceso_piso_tactil = NULL, acceso_señalizacion_braille = NULL, acceso_permite_perros_guia = NULL WHERE fecha_verificacion IS NULL;` | 3 filas tocadas (las 3 originales; ya tenían esos tres campos en NULL, así que no cambió ningún valor) |
| 008 | `CREATE TABLE documentos`, `CREATE TABLE fragmentos_documento`, índice HNSW y un índice por `documento_id` | — |
| 009 | `ALTER TABLE contenido_web ADD COLUMN dominio, ADD COLUMN estado_revision` (la columna `tema` ya existía desde la 005, la omití) y `UPDATE ... SET dominio` | 0 filas en el UPDATE |
| 010 | `ALTER TABLE metricas_consulta ADD COLUMN nivel_fuente, eje_dato, creditos_tavily, motivo_sin_llm` | — |
| Datos de prueba | `cargar_documento_prueba.py`: 1 documento ficticio verificado y 3 fragmentos; `borrar_datos_prueba.sql` también lo borra | 1 + 3 |

Efectos de las pruebas: `probar_guia.py` borra de `contenido_web` solo lo guardado sobre "silpancho" y "tinku" (para repetir la prueba desde cero) y las pruebas automáticas crean y borran filas con el prefijo "ZZ". En `metricas_consulta` quedaron unas 360 filas de pruebas; bórralas antes de medir para el Capítulo VI (`DELETE FROM metricas_consulta;`, solo si estás de acuerdo).

## 6. Solicitudes al LLM y créditos de Tavily por tipo de pregunta

Las preguntas de reglas, eventos, datos prácticos, cómo llegar, compartir, itinerario, ayuda y fuera de alcance usan **0 solicitudes** a Gemini y 0 créditos. Cada pregunta con LLM usa como máximo: 1 solicitud (clasificador), 1 (sitios) o 3 (saberes, normalmente 1). Créditos de Tavily: 1 por búsqueda web (nivel 3); 0 si responde la base, un documento o la caché.

Datos medidos de las pruebas (incluyen las corridas repetidas de `probar_guia.py`; no son tráfico real):

| Intención | Eje | Consultas | Con Gemini | Sin Gemini | Créditos Tavily |
|---|---|---|---|---|---|
| ayuda | — | 142 | 0 | 142 | 0 |
| saberes | narrativo | 52 | 29 | 23 | 0 |
| datos_practicos | operativo | 30 | 0 | 30 | 0 |
| informacion | narrativo | 27 | 12 | 15 | 0 |
| como_llegar | operativo | 26 | 0 | 26 | 0 |
| informacion | operativo | 18 | 16 | 2 | 0 |
| eventos | operativo | 18 | 0 | 18 | 0 |
| confirmacion | — | 18 | 4 | 14 | 0 |
| compartir | operativo | 12 | 0 | 12 | 0 |
| itinerario | operativo | 12 | 6 | 6 | 0 |
| fuera_de_alcance | — | 6 | 0 | 6 | 0 |

Créditos de Tavily: **0** en total, porque no hay clave (las 18 respuestas de nivel "web" vinieron de Wikipedia directa). Cuando uses Tavily, la consulta que más créditos gasta es `saberes` que no está en la base ni en la caché. Motivos por los que no se usó Gemini en las que sí podían: 18 `error_api` (503 de alta demanda), 7 `limite_solicitudes` (antes de mejorar las instrucciones del agente de saberes), 3 `limite_cuota_429` y 3 `tiempo_agotado`.

## 7. Pruebas manuales pendientes para ti

1. Panel (guía 9, 10 y 11): subir un PDF con texto y uno escaneado; subir sin permiso de uso; verificar; reemplazar el archivo; eliminar; en "Contenido traído de internet" convertir "Silpancho" en documento y verificarlo; navegar solo con teclado y leer el panel con un lector de pantalla.
2. Verificar con datos reales los 3 sitios originales (Cristo, Convento y La Cancha) y volver a correr `probar_guia.py`: las 11 filas "NO EJECUTABLE" pasarán a ejecutarse.
3. Poner `TAVILY_API_KEY` en el `.env`, reiniciar (`docker compose up -d backend`) y correr las filas 4.2 y 4.3 (1 crédito la primera vez, 0 la segunda).
4. App en el teléfono (guía 5.3, 5.4, 6.4, 6.5, 7.3, 12.3, 13 y 15): sobre todo decir "sí" a "¿Quieres saber más?" y probar que el micrófono se abre solo.
5. Agregar sitios oficiales a `DOMINIOS_CONFIABLES` y revisar el cambio de la app del punto 4.1.
6. Borrar los datos de prueba (`borrar_datos_prueba.sql`) antes de calibrar `UMBRAL`, `MARGEN` y `UMBRAL_DOCUMENTOS`, usar Ragas o probar con usuarios.
7. Decidir si el commit de `docs/guia_pruebas.md` (todavía sin subir a git) lo haces tú.

## 8. Qué partes de la tesis cambian

- **Capítulo IV (diseño):** el grafo de decisión (nuevo `docs/grafo_asistente.mmd`; hay que regenerar `docs/grafo_asistente.png`, no hay `mmdc` instalado), la regla de dos ejes, la cascada N1 a N4, la tabla de agentes (clasificador, sitios, saberes y los especialistas sin LLM), el módulo de documentos y el flujo de "Contenido traído de internet".
- **Diccionario de datos:** tablas `documentos` y `fragmentos_documento`, columnas nuevas de `contenido_web` (`dominio`, `estado_revision`) y de `metricas_consulta` (`nivel_fuente`, `eje_dato`, `creditos_tavily`, `motivo_sin_llm`).
- **Requerimientos funcionales:** documentos verificados con permiso de uso, "¿Quieres saber más?", preguntas compuestas, citas por nivel, y la regla de que lo operativo solo sale de la base verificada.
- **Capítulo III / V (herramientas y costos):** Pydantic AI, Gemini (capa gratuita; Google puede usar el contenido para mejorar sus productos, por eso no se envían datos personales), Tavily (créditos gratuitos limitados), pypdf y python-docx. El costo sigue siendo cero salvo el LLM.
- **Capítulo VI (pruebas y métricas):** el porcentaje de respuestas por `nivel_fuente`, créditos por tipo de pregunta, `motivo_sin_llm`, la guía de pruebas con `probar_guia.py` y las pruebas con modelos falsos de Pydantic AI.
- **Limitaciones:** la calidad del respaldo web depende de los dominios de confianza; `UMBRAL_DOCUMENTOS` debe calibrarse con documentos reales; el modelo gratuito de Gemini puede devolver 503.

## Comandos de PowerShell de esta sesión

```powershell
# Levantar y apagar
docker compose up -d backend panel
docker compose down

# Pruebas del backend (sin gastar cuota)
docker compose run --rm backend python -m pytest /app/pruebas -q

# Pruebas del panel
docker compose run --rm panel python -m pytest /app/pruebas/test_panel_documentos.py -q -p no:cacheprovider

# Guía de pruebas (usa Gemini y Tavily reales si hay claves)
docker compose run --rm backend python pruebas/probar_guia.py

# 3 llamadas reales de humo a Gemini
docker compose run --rm backend python -m pytest /app/pruebas/humo_agentes.py -q -p no:cacheprovider

# Cargar el documento ficticio (ya está cargado)
docker compose run --rm panel python /app/cargar_documento_prueba.py
```
