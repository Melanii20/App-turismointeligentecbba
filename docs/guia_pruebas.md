# Guía de pruebas · Guía Cochala

Esta guía explica cada parte del sistema (agentes, especialistas y herramientas), qué hace, cómo probarla, con qué preguntas y qué debe pasar. Úsala para las pruebas de desarrollo y como base para el Capítulo VI.

## Antes de probar

1. Docker Desktop encendido y `docker compose up` en `C:\tesis`: backend en `http://localhost:8000` y panel en `http://localhost:8080`.
2. Datos de prueba cargados: 3 sitios (Cristo de la Concordia, Convento de Santa Teresa, La Cancha), eventos ficticios y el documento ficticio "Guía de prueba de Cochabamba (FICTICIO)".
3. Verifica los sitios en el panel. Si no están verificados, el asistente no los ve.
4. En el emulador, fija la ubicación en la plaza principal: **Extended controls → Location** → `-17.3935, -66.1570`.
5. Prueba rápida de las claves: `GET http://localhost:8000/api/estado` debe decir si Gemini, Tavily y Wikipedia están configurados. Nunca muestra las claves.

### Probar por texto, sin la app (PowerShell)

```powershell
function Preguntar($p) {
  $body = @{ pregunta = $p; canal = "app"; contexto = @{ turnos = @(); ultimo_sitio_id = $null; accion_pendiente = $null } } | ConvertTo-Json -Depth 5
  Invoke-RestMethod http://localhost:8000/api/consulta -Method Post -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($body))
}
Preguntar "¿Qué es el silpancho?"
```

Las conversaciones de varios turnos ("¿dónde queda…?" → "sí") se prueban con el script `pruebas/probar_guia.py`, que guarda el contexto entre turnos e imprime PASA o FALLA por cada fila:

```powershell
docker compose run --rm backend python pruebas/probar_guia.py
```

## Cómo leer la respuesta

| Campo | Qué revisar |
|---|---|
| `intencion` | Que coincida con la esperada |
| `nivel_fuente` | `base`, `documento`, `cache_web`, `web` o `ninguna` |
| `fuente` / `fuentes` | Quién lo dice (verificación, documento y página, sitio web) |
| `uso_llm` | Si se llamó a Gemini |
| `acciones` / `accion_pendiente` | Navegación o compartir |

---

## 1. Orquestador (grafo de reglas)

**Qué es:** el "jefe". No usa IA. Lee la pregunta, decide la intención y el tipo de dato (operativo o narrativo) y se la pasa al especialista que corresponde.

| # | Pregunta | Debe pasar |
|---|---|---|
| 1.1 | ¿Qué puedes hacer? | `ayuda`, explica con ejemplos, `uso_llm=false` |
| 1.2 | ¿Quién ganó el partido de ayer? | `fuera_de_alcance`, mensaje de alcance, `uso_llm=false` |
| 1.3 | ¿Qué horario tiene? (primer turno, sin sitio) | Pregunta aclaratoria: "¿A qué lugar te refieres?" |
| 1.4 | ¿Cuánto cuesta un silpancho? | Operativo → solo base → "No tengo precios verificados…". NO va a la web |
| 1.5 | ¿Qué es la chicha y dónde la puedo probar? | Pregunta compuesta: qué es (cascada narrativa) + dónde (solo sitios de la base; si no hay, lo dice) |

## 2. Agente clasificador (Gemini, solo de respaldo)

**Qué es:** se usa solo cuando ninguna regla entiende la pregunta. Devuelve la intención en formato fijo.

| # | Pregunta | Debe pasar |
|---|---|---|
| 2.1 | Me da curiosidad lo que comen los cochabambinos | Clasificador → `saberes` (gastronomía), `uso_llm=true` |
| 2.2 | Quiero conocer algo bonito para pasear | Clasificador → `itinerario` o `cercania` |

## 3. Agente de sitios (Gemini; solo la base, sin web)

**Qué es:** redacta sobre los sitios con los datos verificados y la fecha de verificación. No puede ir a internet.

| # | Pregunta | Debe pasar |
|---|---|---|
| 3.1 | Cuéntame del Cristo de la Concordia | Responde desde la base, menciona la fecha de verificación, `nivel_fuente=base` |
| 3.2 | ¿El Cristo tiene piso táctil? | Operativo. Si el dato es NULL → "No tengo ese dato verificado". Nunca inventa |
| 3.3 | ¿La Cancha es ruidosa? | Lee `acceso_nivel_ruido` o dice que no está registrado |
| 3.4 | Busco un lugar tranquilo | Filtro `acceso_nivel_ruido = 'bajo'` |
| 3.5 | Cuéntame del Museo del Louvre | No es de Cochabamba → "No tengo información…" y ofrece alternativas |

## 4. Agente de saberes (Gemini; cascada base → documentos → caché → web)

**Qué es:** responde datos narrativos: platos, bebidas, tradiciones, fiestas (qué son), mitos y leyendas, danzas y música, artesanías y vestimenta, historia, personajes, quechua y naturaleza. También la historia o leyenda de un sitio, si la base no la tiene. Primero busca en tu base y documentos; solo si no encuentra, va a internet.

| # | Pregunta | Debe pasar |
|---|---|---|
| 4.1 | Cuéntame la leyenda de la piedra que canta | Sale del documento ficticio, con título y página. `nivel_fuente=documento`, 0 créditos de Tavily |
| 4.2 | ¿Qué es el silpancho? (primera vez) | Va a Tavily → "Según <sitio> (información de internet)…" `nivel_fuente=web`, 1 crédito |
| 4.3 | ¿Qué es el silpancho? (segunda vez) | Sale de la caché: `nivel_fuente=cache_web`, 0 créditos |
| 4.4 | ¿De dónde viene la fiesta de Urkupiña? | Narrativo → cascada → cita la fuente |
| 4.5 | ¿Cuándo es Urkupiña? | Operativo → solo eventos de la base. Si no está registrado, lo dice. NO va a la web |
| 4.6 | ¿Cómo se dice gracias en quechua? | Saberes (idioma) → cascada |
| 4.7 | Cuéntame la historia del Cristo → "sí" a "¿Quieres saber más?" | Primero la base. Al aceptar, baja al siguiente nivel (web) solo para la parte narrativa |
| 4.8 | Prueba automática | `agente_saberes` NO puede llamar a la web sin haber buscado antes en la base (la herramienta se niega) |

## 5. Especialista de eventos (sin IA)

| # | Pregunta / acción | Debe pasar |
|---|---|---|
| 5.1 | ¿Qué hay hoy? | Eventos de hoy, el más cercano primero, con distancia y horario |
| 5.2 | ¿Qué fiestas hay este fin de semana? | Eventos del rango de fechas |
| 5.3 | Abrir la app | Tarjeta "Hoy" con el evento más cercano; la abuela lo anuncia después del saludo |
| 5.4 | Tocar "Escuchar eventos de hoy" | Los lee todos |

## 6. Especialista de movilidad (sin IA; decide cuándo abrir la navegación)

| # | Conversación | Debe pasar |
|---|---|---|
| 6.1 | ¿Cómo llego a La Cancha? | Lee la referencia de la entrada (o dice que no está verificada) y la distancia → "Te abro la navegación" → se abre la app de mapas al terminar de hablar |
| 6.2 | ¿Dónde queda el Convento de Santa Teresa? → "sí" | Pregunta "¿Quieres que te lleve?", se abre el micrófono solo, y con "sí" abre la navegación |
| 6.3 | ¿Dónde queda el Convento? → "no" | "Está bien." No abre nada |
| 6.4 | ¿Cómo llego al Cristo? → pulsar Detener mientras habla | No se abre la navegación |
| 6.5 | Sin apps de mapas en el emulador | Se abre la URL de Google Maps en el navegador (respaldo) |

## 7. Especialista de compartir e itinerario (sin IA)

| # | Pregunta | Debe pasar |
|---|---|---|
| 7.1 | Avisa a mi familia que voy a La Cancha | Se abre WhatsApp o compartir con el mensaje y el enlace del mapa, SIN ubicación. La persona pulsa enviar |
| 7.2 | Dile a mi familia dónde estoy | El mensaje incluye "Estoy aquí: <enlace>" |
| 7.3 | Lo mismo con contacto de confianza en Ajustes | Abre directo `wa.me/<número>` |
| 7.4 | Arma un recorrido para hoy | 2 a 4 sitios cercanos en orden + eventos de hoy; ofrece llevar al primero |

## 8. Especialista de datos prácticos (sin IA)

| # | Pregunta | Debe pasar |
|---|---|---|
| 8.1 | ¿A qué hora abre el Convento de Santa Teresa? | Horario de la base, o "no está registrado" |
| 8.2 | ¿Cuánto cuesta entrar al Cristo? → luego "¿y cuánto tiempo se necesita?" | El segundo turno usa el último sitio (contexto) |

## 9. Documentos (panel + RAG)

| # | Acción | Debe pasar |
|---|---|---|
| 9.1 | Subir un PDF con texto | Se crean fragmentos con número de página; queda en borrador; el asistente aún no lo usa |
| 9.2 | Verificar el documento | Ahora sí aparece en las respuestas, con cita y página |
| 9.3 | Subir un PDF escaneado (imagen) | Aviso: "este PDF es una imagen; súbelo con texto" |
| 9.4 | Subir sin llenar "permiso de uso" | No deja guardar |
| 9.5 | Preguntar por accesibilidad de un sitio que un documento menciona | Responde solo con los campos verificados del sitio, nunca con el documento |
| 9.6 | Eliminar un documento | Pide confirmación; sus fragmentos desaparecen de las respuestas |

## 10. Contenido traído de internet (panel)

| # | Acción | Debe pasar |
|---|---|---|
| 10.1 | Después de la prueba 4.2, abrir "Contenido traído de internet" | Aparece lo del silpancho con su URL, dominio y fecha |
| 10.2 | "Convertir en documento" → verificar | La siguiente pregunta del silpancho sale con `nivel_fuente=documento`, sin web |

## 11. Panel de sitios y eventos

| # | Acción | Debe pasar |
|---|---|---|
| 11.1 | Iniciar sesión con una contraseña incorrecta | Rechaza |
| 11.2 | Crear un sitio | Queda en borrador; el asistente no lo ve |
| 11.3 | Verificar el sitio | Se llenan verificado_por y fecha_verificacion; el asistente lo ve |
| 11.4 | Editar un sitio verificado | Vuelve a borrador; se regenera el embedding |
| 11.5 | Crear un evento con coordenadas para hoy | Aparece en la tarjeta "Hoy" |
| 11.6 | Navegar el panel solo con teclado | Se llega a todo; las etiquetas se leen bien |

## 12. Fallos y respaldos

| # | Cómo provocarlo | Debe pasar |
|---|---|---|
| 12.1 | Poner mal GOOGLE_API_KEY y reiniciar | Responde con plantillas (lee la descripción o el fragmento citando la fuente). La app no se cae |
| 12.2 | Quitar TAVILY_API_KEY | La cascada usa Wikipedia directa (si WIKIPEDIA_CONTACTO tiene valor); si no, "No tengo información" |
| 12.3 | Apagar el backend con la app abierta | Mensaje de error hablado, sonido de error y vuelve a "En espera" |
| 12.4 | 25 preguntas en un minuto | A partir de la 21, límite de consultas (slowapi) |

## 13. App: accesibilidad y sentidos (en teléfono real)

| # | Prueba | Debe pasar |
|---|---|---|
| 13.1 | Recorrer la pantalla con TalkBack | Todo tiene etiqueta en español; el avatar y el fondo no se leen |
| 13.2 | Pulsar Hablar | Sonido "tin" + vibración corta + "Escuchando…" |
| 13.3 | Termina de escuchar | Sonido "tun" + "Buscando información…" |
| 13.4 | No se entendió nada | Sonido de error + doble vibración + "No te entendí" |
| 13.5 | Activar "reducir animaciones" en Android | El fondo y los pétalos quedan quietos |
| 13.6 | Ajustes → voz rápida | La abuela habla más rápido |
| 13.7 | El diseño | Fondo, colores, halo y avatar iguales que antes de la implementación |

## 14. Privacidad y métricas

| # | Prueba | Debe pasar |
|---|---|---|
| 14.1 | `SELECT * FROM metricas_consulta ORDER BY id DESC LIMIT 10;` | Hay intención, nivel_fuente, uso_llm, créditos y tiempo, pero NO el texto de la pregunta ni la ubicación |
| 14.2 | Revisar el registro de llamadas a Gemini y Tavily | No se envió la ubicación ni el contacto |
| 14.3 | `SELECT nivel_fuente, count(*) FROM metricas_consulta GROUP BY 1;` | Porcentaje de respuestas por nivel (sirve para el Capítulo VI) |

## 15. Opcionales (si están activados)

| # | Prueba | Debe pasar |
|---|---|---|
| 15.1 | Aviso diario activado en Ajustes | Notificación con el evento del día; al tocarla, la abuela lo lee |
| 15.2 | Bot de Telegram: `/eventos`, `/ayuda`, "¿Qué es el silpancho?" | Mismas respuestas que la app, con enlaces; no guarda chat_id |
