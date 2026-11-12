# Resultado de pruebas/probar_guia.py

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
