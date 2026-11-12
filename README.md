# Guía Cochala · Asistente turístico accesible para Cochabamba

Proyecto de grado de **Melany Aillen Chavarría Morales**, UNIFRANZ Cochabamba, 2026. Tutor: Ing. Richard Jiménez Velasco.

> **"Asistente virtual de turismo inclusivo: diseño de una plataforma multimodal para personas con diversas capacidades, con enfoque inicial en discapacidad visual."**

Guía Cochala es una aplicación móvil de **una sola pantalla**, sin registro, donde una abuela cochabambina animada responde por **voz, texto y avatar** sobre los sitios turísticos, los eventos y la cultura de Cochabamba. Está pensada primero para personas con **baja visión o ceguera**, y bajo los principios del Diseño Universal sirve a cualquier visitante.

---

## Lo que la hace especial

1. **Los datos de accesibilidad los verifica una persona, nunca una IA.** Piso táctil, braille, perros guía, nivel de ruido y la referencia de la entrada los registra una administradora a mano. Un dato sin registrar significa "sin información", nunca un valor inventado. Esa trazabilidad es el argumento central del proyecto.
2. **Regla de dos ejes: lo operativo no se inventa ni se busca en internet.** Si preguntas *dónde, cuándo, cuánto, horario o accesibilidad*, la respuesta sale solo de la base verificada. Si preguntas *qué es, de dónde viene, historia o leyenda*, el asistente recorre una cascada de fuentes citadas.
3. **Cada respuesta dice de dónde salió.** "Según la verificación de octubre de 2026", "según la Guía…, página 3" o "Según Wikipedia (información de internet)". Nunca inventa: si no sabe, lo dice y ofrece una alternativa de la base.
4. **El asistente decide el siguiente paso, sin botones.** Si quieres ir a un lugar, dice "Te abro la navegación" y la app abre tu aplicación de mapas al terminar de hablar. Si solo preguntas dónde queda, ofrece "¿Quieres que te lleve?" y abre el micrófono para escuchar tu "sí". Mientras habla, "Detener" cancela la acción.
5. **La IA es un apoyo, no el cerebro.** Las reglas escritas en código resuelven casi todo (eventos, horarios, cómo llegar, compartir, itinerarios). Gemini solo clasifica lo que las reglas no entienden y redacta con palabras naturales. Si Gemini falla, da error de cuota o tarda más de 15 segundos, la respuesta sale igual con una plantilla que cita su fuente.
6. **Privacidad por diseño.** No se guardan conversaciones, preguntas ni ubicaciones en el servidor. La ubicación solo se usa en la consulta que la necesita. El contacto de confianza vive solo en el teléfono. A los servicios externos nunca se les envía la ubicación ni datos personales.
7. **Costo cero.** Navegación con enlaces gratuitos (`geo:` y Google Maps sin clave), Wikipedia, Tavily (créditos gratuitos) y la capa gratuita de Gemini. No usa ninguna API de mapas de pago.
8. **Se comunica con todos los sentidos.** El estado del asistente se transmite por texto, voz, sonido y vibración, no solo con el avatar. Compatible con TalkBack, con tamaño mínimo de 48 dp, contraste 4,5:1 y respeto a "reducir animaciones".

---

## Cómo funciona (vista general)

```
  App móvil (Flutter)          Bot de Telegram (opcional)
        │                              │
        └────────────┬─────────────────┘
                     ▼
        POST /api/consulta  (FastAPI, límite 20 consultas/min)
                     │
        ┌────────────▼────────────┐
        │ 1 Normalizar            │
        │ 2 Router por reglas     │──(sin coincidencia)──► agente_clasificador (Gemini)
        │ 3 Intención + tipo dato │
        └────────────┬────────────┘
     ┌───────────────┼──────────────────────────────┐
     ▼               ▼                              ▼
 Especialistas   agente_sitios                agente_saberes
 sin IA (SQL)    (base verificada)            cascada N1 → N2 → N3 → N4
 eventos, cómo   sitios + documentos          base y documentos → caché web
 llegar, datos   + eventos                    → Tavily / Wikipedia → alternativa
 prácticos,
 compartir,
 itinerario
     └───────────────┼──────────────────────────────┘
                     ▼
        7 Decidir la acción  →  8 Respuesta (texto + fuente + acciones)
                     │
        PostgreSQL + pgvector (sitios, eventos, documentos, caché web, métricas)
```

El diagrama completo del grafo está en [`docs/grafo_asistente.mmd`](docs/grafo_asistente.mmd) (formato Mermaid).

---

## Funcionalidades

### 1. Asistente conversacional

- **Router por reglas** con 13 intenciones, revisadas en orden de prioridad: confirmación, más información, ayuda, compartir, cómo llegar, itinerario, eventos, datos prácticos, cercanía, información de un sitio, saberes, fuera de alcance. Acierta el 100 % de las 77 preguntas del conjunto de pruebas.
- **Búsqueda híbrida** en PostgreSQL con pgvector: coincidencia por nombre del sitio, búsqueda semántica (distancia coseno, modelo `paraphrase-multilingual-mpnet-base-v2`) y filtros SQL exactos ("tranquilo" → ruido bajo, "piso táctil", "perro guía", tipo de lugar). Solo se ven los sitios `verificado`.
- **Tres agentes** con Pydantic AI y Gemini: `agente_clasificador`, `agente_sitios` y `agente_saberes`, con salida tipada y límites de solicitudes por pregunta.
- **Especialistas sin IA**, rápidos y predecibles: eventos, movilidad, compartir e itinerario, datos prácticos.
- **Preguntas compuestas** ("¿Qué es la chicha y dónde la puedo probar?"): se dividen en parte narrativa y parte operativa, y cada una sigue su regla.
- **"¿Quieres saber más?"**: si la respuesta salió de la base y es corta, la abuela ofrece profundizar y, con un "sí", baja al siguiente nivel de la cascada.
- **Lugares inexistentes o de otra ciudad**: "Cuéntame del Museo del Louvre" responde "No tengo información sobre Museo del Louvre. Puedo contarte de los museos de Cochabamba que tengo registrados."

### 2. Cascada de fuentes para lo narrativo

| Nivel | Fuente | Cita |
|---|---|---|
| N1 | Sitios, eventos y **documentos verificados** | "según la verificación de…" / "según la Guía…, página n" |
| N2 | Caché de contenido de internet (30 días) | "Según Wikipedia (información de internet)…" |
| N3 | **Tavily** (solo dominios de confianza) y, de respaldo, Wikipedia directa | igual que N2 |
| N4 | Nada sirvió | "No tengo información sobre eso, pero puedo contarte de…" |

El orden lo impone el código: la web se niega si antes no se consultaron la base y la caché. Lo que no es de Cochabamba o Bolivia, o es ajeno al turismo (clima, noticias, política, deportes), nunca va a internet.

### 3. Panel de administración web

- Inicio de sesión con contraseña **bcrypt**.
- **Sitios**: crear, editar, filtrar por estado y verificar. Todo sitio nuevo entra como borrador; al verificar se registran quién y cuándo. Editar un sitio verificado lo devuelve a borrador. Al guardar se regenera su embedding.
- **Eventos** con fecha, hora, zona y coordenadas (copiables desde Google Maps).
- **Documentos**: subir PDF, DOCX o TXT con permiso de uso obligatorio; extracción de texto con página; fragmentos de unos 800 caracteres; vista previa; verificar, reemplazar y eliminar con confirmación. Un PDF escaneado como imagen se rechaza.
- **Contenido traído de internet**: lista de lo que el asistente consultó en la web. Se puede convertir en documento (en borrador, con su licencia) o descartar.
- HTML semántico, etiquetas `label`, buen contraste y navegable con teclado.

### 4. App móvil (Flutter, Android)

- **Pantalla única** con el avatar Rive, fondo de paisaje cochabambino difuminado con zoom lento, nubes, pétalos de jacarandá y el botón Hablar con halo y anillos.
- **Tarjeta "Hoy"**: eventos del día, el más cercano primero ("Hoy cerca de ti · Feria X · a 800 m · hasta las 18:00"), con el botón "Escuchar eventos de hoy". La abuela anuncia el primero al abrir.
- **Línea de fuente** bajo cada respuesta ("Fuente: Wikipedia" o "Verificado el 12/10/2026").
- **Estados con texto, voz, sonido y vibración**: En espera, Escuchando, Buscando información, Hablando, Abriendo navegación y error.
- **"¿Cómo llego?"**: la abuela lee la referencia de la entrada y la distancia, y abre tu app de mapas con `geo:` (respaldo: URL de Google Maps).
- **Avisar a un familiar y compartir el recorrido**: deja el mensaje listo en WhatsApp o en la hoja de compartir; la persona pulsa enviar. La ubicación se incluye solo si la pide ("dile dónde estoy").
- **Itinerario**: de 2 a 4 sitios cercanos en orden de recorrido, más los eventos de hoy.
- **Ajustes** (solo en el teléfono): velocidad de la voz, anuncio de eventos, aviso diario, sonidos, vibración y contacto de confianza.
- **Aviso diario de eventos** opcional (notificación local, sin Firebase ni cuentas).
- **Ayuda por voz** con ejemplos de preguntas.

### 5. Bot de Telegram (opcional)

Usa el mismo asistente con `canal = telegram`. Comandos `/eventos`, `/itinerario` y `/ayuda`. No guarda `chat_id`, suscripciones ni conversaciones. Sin `TELEGRAM_TOKEN` no arranca.

### 6. Métricas para la tesis

Cada consulta guarda una fila **sin datos personales** en `metricas_consulta`: intención, tipo de dato, nivel de fuente, si usó IA y por qué no, créditos de Tavily, similitud y tiempo. Sirve para medir qué porcentaje se resuelve sin IA, con la base, con documentos, con la caché o con la web.

---

## Tecnologías

| Parte | Tecnología |
|---|---|
| Backend y panel | Python 3.12, FastAPI, Jinja2, slowapi |
| Base de datos | PostgreSQL 16 con pgvector (índice HNSW) |
| Embeddings | sentence-transformers `paraphrase-multilingual-mpnet-base-v2` (768 dimensiones) |
| Agentes | Pydantic AI con Gemini |
| Web | Tavily (con dominios de confianza) y Wikipedia |
| Documentos | pypdf, python-docx |
| App móvil | Flutter, Rive, speech_to_text, flutter_tts, geolocator, url_launcher, share_plus, audioplayers, workmanager |
| Despliegue local | Docker y Docker Compose |
| Pruebas | pytest, Ragas (preparado) |

---

## Cómo ejecutarlo

Todo el código Python se ejecuta dentro de Docker.

### Requisitos
Docker Desktop, Flutter, el SDK de Android y un contenedor de PostgreSQL con pgvector llamado `postgres-tesis` (imagen `pgvector/pgvector:pg16`, base `turismo_db`, usuario `postgres`).

### 1. Configuración
```powershell
Copy-Item .env.ejemplo .env
Copy-Item panel\.env.example panel\.env
```
Abre `.env` y completa los valores (nunca los subas a git):

| Variable | Para qué |
|---|---|
| `LLM_PROVEEDOR`, `LLM_MODELO`, `GOOGLE_API_KEY` (o `LLM_API_KEY`) | Gemini ([clave gratuita](https://aistudio.google.com/apikey)) |
| `TAVILY_API_KEY`, `TAVILY_SCORE_MIN`, `DOMINIOS_CONFIABLES` | Búsqueda web ([clave gratuita](https://app.tavily.com)) |
| `WIKIPEDIA_CONTACTO` | Contacto que exige Wikimedia en el User-Agent |
| `UMBRAL`, `MARGEN`, `TOP_K` | Calibración de la búsqueda |
| `TELEGRAM_TOKEN` | Solo si usas el bot |

Sin las claves el sistema igual funciona, con plantillas y Wikipedia directa.

### 2. Base de datos
Las migraciones están en [`migraciones/`](migraciones) (001 a 010) y se aplican en orden. Para ver el sistema funcionando hay datos **ficticios** (`datos_prueba.sql`, `datos_prueba_eventos_ubicacion.sql` y `cargar_documento_prueba.py`) que se borran con `borrar_datos_prueba.sql` antes de usar datos reales.

### 3. Levantar backend y panel
```powershell
docker start postgres-tesis
docker compose up -d backend panel
```
- API: http://localhost:8000 (revisa `/api/estado`)
- Panel: http://localhost:8080

### 4. App en un teléfono Android por USB
```powershell
adb devices
adb reverse tcp:8000 tcp:8000
cd flutter_application_1
flutter run --dart-define=API_URL=http://localhost:8000
```
En el emulador de Android Studio no hace falta configurar nada: la app usa `http://10.0.2.2:8000`.

### 5. Pruebas
```powershell
docker compose run --rm backend python -m pytest /app/pruebas -q
docker compose run --rm panel python -m pytest /app/pruebas/test_panel_documentos.py -q -p no:cacheprovider
docker compose run --rm backend python pruebas/probar_guia.py
cd flutter_application_1; flutter test
```
Las pruebas del backend no gastan cuota de Gemini ni créditos de Tavily. `pruebas/probar_guia.py` ejecuta las filas automatizables de [`docs/guia_pruebas.md`](docs/guia_pruebas.md).

---

## Estructura del proyecto

```
├── asistente/            Backend: API, router, grafo, cascada, agentes y herramientas
│   ├── api/              /api/consulta, /api/eventos/hoy, /api/estado
│   └── servicios/        grafo.py, router_reglas.py, cascada.py, agentes/, herramientas/
├── panel/                Panel de administración (sitios, eventos, documentos, contenido web)
├── flutter_application_1/  App móvil
├── migraciones/          Cambios de esquema numerados
├── pruebas/              Pruebas automáticas y preguntas del router
├── docs/                 Grafo, guía de pruebas, informes
└── docker-compose.yml    Backend (8000) y panel (8080)
```

---

## Privacidad y datos

- No se guardan conversaciones, preguntas ni ubicaciones en el servidor.
- A Gemini y Tavily solo se les envía el texto de la pregunta, sin correos ni números largos, y el contexto recuperado. En la capa gratuita de Gemini, Google puede usar el contenido para mejorar sus productos; por eso no se envían datos personales.
- Los datos de prueba incluidos son **inventados**. No representan información real de ningún sitio.
- El texto de Wikipedia se usa bajo licencia CC BY-SA 4.0 y siempre se cita su URL.

## Estado y trabajo futuro

Hecho: panel, asistente con RAG y cascada de fuentes, documentos, agentes, app móvil con sonidos, vibración, acciones, ajustes y aviso diario, y bot de Telegram.

Pendiente o futuro: pruebas con personas con discapacidad visual, calibración de umbrales con datos reales, evaluación con Ragas, interfaz para otras discapacidades (auditiva y motora), modo sin conexión, quechua e inglés, y un servidor MCP que exponga las herramientas.

## Autoría

Melany Aillen Chavarría Morales · Proyecto de grado, UNIFRANZ Cochabamba, 2026.
