-- DATOS DE PRUEBA (FICTICIOS) para ver cómo funcionan el asistente y el panel.
--
-- ATENCIÓN: estos datos NO son reales y NO fueron verificados en el lugar. Los campos de
-- accesibilidad (acceso_*) están INVENTADOS. Es una excepción pedida por la estudiante para poder
-- probar, y va contra la regla de CLAUDE.md. Por eso:
--   * la columna `fuente` de cada sitio empieza con 'DATO DE PRUEBA';
--   * la descripción de cada evento empieza con 'DATO DE PRUEBA';
--   * borrar_datos_prueba.sql los elimina todos de una vez.
-- BORRARLOS antes de cargar datos reales, de calibrar o de evaluar con Ragas.
-- Las coordenadas son aproximadas.
--
-- Los sitios entran como 'verificado' (para que el asistente los vea) con el primer usuario
-- del sistema como "verificador". No tienen embedding: hay que generarlo después con
-- generar_embeddings.py. Es seguro ejecutarlo dos veces: no repite los que ya existen.

SET client_encoding = 'UTF8';
BEGIN;

INSERT INTO sitios_turisticos (
    nombre, tipo, descripcion, latitud, longitud, direccion, fuente,
    acceso_descripcion_sensorial, acceso_punto_referencia_entrada, acceso_tipo_piso,
    acceso_piso_tactil, acceso_señalizacion_braille, acceso_permite_perros_guia,
    acceso_nivel_ruido, acceso_recomendacion,
    estado, verificado_por, fecha_verificacion
)
SELECT
    d.nombre, d.tipo, d.descripcion, d.latitud, d.longitud, d.direccion,
    'DATO DE PRUEBA (ficticio, borrar antes de usar datos reales)',
    d.sensorial, d.referencia, d.piso, d.tactil, d.braille, d.perros, d.ruido, d.recomendacion,
    'verificado', (SELECT id FROM usuarios ORDER BY id LIMIT 1), now()
FROM (VALUES
 ('Plaza 14 de Septiembre', 'plaza',
  'Plaza principal del centro histórico de Cochabamba, rodeada de arcos y edificios coloniales, con árboles, bancas y palomas.',
  -17.393870, -66.156950, 'Centro histórico de Cochabamba',
  'Se oyen las palomas y las campanas de la catedral. Huele a café y a comida de los puestos cercanos. Hay sombra de árboles.',
  'Se reconoce por la fuente de la esquina y los arcos de la vereda; el acceso principal está junto a los arcos.',
  'baldosa', false, false, true, 'medio',
  'Entra por el lado de los arcos, donde la vereda es más ancha y pareja.'),
 ('Catedral Metropolitana', 'iglesia',
  'Iglesia principal de la ciudad, con fachada de piedra y una nave amplia donde se celebran misas y ceremonias.',
  -17.393700, -66.156400, 'Frente a la plaza principal',
  'Dentro hay silencio con eco suave, olor a incienso y a madera antigua, y el aire es fresco.',
  'La puerta principal es de madera, con dos escalones de piedra y una barandilla metálica a la derecha.',
  'piedra', false, false, true, 'bajo',
  'Hay una rampa lateral para silla de ruedas; pregunta por ella al guardia de la puerta.'),
 ('Palacio Portales', 'museo',
  'Antigua mansión rodeada de jardines, hoy centro cultural con salones decorados y exposiciones de arte.',
  -17.375800, -66.147700, 'Zona norte de la ciudad',
  'En los jardines se oye una fuente y el viento entre los árboles. Los salones tienen eco y huelen a madera encerada.',
  'El portón de hierro negro está junto a una caseta de guardia; el camino de entrada es largo y de grava fina.',
  'grava', false, true, true, 'bajo',
  'Pide acompañamiento en el camino de grava y en las escaleras interiores.'),
 ('Museo Arqueológico', 'museo',
  'Museo con piezas de culturas prehispánicas de los valles y el altiplano: cerámica, textiles y herramientas de piedra.',
  -17.392900, -66.151300, 'Cerca del centro histórico',
  'Salas silenciosas con vitrinas de vidrio. Algunas piezas se pueden tocar en una sala de réplicas.',
  'La entrada tiene una puerta de vidrio con una alfombra gruesa y una caseta de boletos a la derecha.',
  'cerámica', true, true, true, 'bajo',
  'Pregunta por la sala de réplicas táctiles. Hay un ascensor al fondo del pasillo.'),
 ('Teatro Achá', 'teatro',
  'Teatro histórico con sala a la italiana, palcos y escenario donde se presentan obras, música y danza.',
  -17.394300, -66.158000, 'Centro histórico de Cochabamba',
  'En la sala hay acústica cálida, olor a terciopelo y telón pesado. Antes de la función se oye mucha gente.',
  'La entrada se reconoce por tres arcos de piedra y una taquilla de madera a la izquierda.',
  'madera', false, false, false, 'medio',
  'Llega 20 minutos antes y pide ayuda al personal para ubicar tu butaca.'),
 ('Mercado 25 de Mayo', 'mercado',
  'Mercado cubierto con puestos de comida, frutas, verduras y artesanías, lleno de movimiento durante todo el día.',
  -17.396100, -66.155500, 'Centro de la ciudad',
  'Mucho ruido de vendedores y de ollas. Huele a comida cocinada, hierbas y fruta. El piso puede estar mojado.',
  'Las puertas son anchas y abiertas; se reconocen por los puestos de jugos a ambos lados.',
  'cemento', false, false, true, 'alto',
  'Ve acompañado y en horas de menos gente, por la mañana temprano.'),
 ('Parque Fidel Anze', 'parque',
  'Parque tranquilo con caminos, áreas verdes, bancas y juegos para niños, ideal para descansar.',
  -17.376500, -66.162400, 'Zona norte de la ciudad',
  'Se oyen pájaros y niños jugando a lo lejos. Huele a pasto y a flores. Hay bancas bajo los árboles.',
  'El acceso principal es un arco de piedra con una pequeña pendiente suave hacia el interior.',
  'cemento', true, false, true, 'bajo',
  'Los caminos principales son anchos y parejos; evita los senderos de tierra.'),
 ('Plaza Colón', 'plaza',
  'Plaza con una estatua en el centro, árboles altos y bancas, muy usada para ferias y presentaciones al aire libre.',
  -17.390000, -66.153000, 'Zona centro-norte',
  'Se oyen conversaciones y la música de los puestos de las ferias. Hay mucha sombra de árboles.',
  'La entrada se reconoce por los cuatro accesos con escalones bajos y un monumento al centro.',
  'baldosa', false, false, true, 'medio',
  'Si vas en feria, entra por el lado del escenario, donde hay menos puestos.'),
 ('Iglesia de San Francisco', 'iglesia',
  'Iglesia colonial con un patio interior, un altar dorado y una torre con campanas.',
  -17.395100, -66.157800, 'Centro histórico de Cochabamba',
  'En el patio se oye una pequeña fuente. Dentro hay silencio, olor a cera y aire fresco.',
  'La puerta principal es de madera clara y está bajo un arco de piedra con una cruz arriba.',
  'piedra', false, false, true, 'bajo',
  'Hay un escalón alto en la puerta; pide ayuda al encargado para entrar.'),
 ('Iglesia de la Merced', 'iglesia',
  'Pequeña iglesia colonial de fachada blanca, con un altar sencillo y ambiente de recogimiento.',
  -17.394400, -66.155300, 'Centro histórico de Cochabamba',
  'Muy silenciosa. Huele a incienso suave. El piso de madera cruje levemente al caminar.',
  'La puerta es de madera con dos hojas y una cruz de hierro sobre el dintel.',
  'madera', false, false, true, 'bajo',
  'Solo hay un escalón bajo en la puerta; la nave es plana.'),
 ('Mirador de San Pedro', 'mirador',
  'Mirador en una colina con vista panorámica de la ciudad y los cerros que la rodean.',
  -17.384500, -66.148600, 'Cerro de San Pedro',
  'Sopla viento fuerte y se oye el ruido lejano de la ciudad. Huele a tierra seca y a eucalipto.',
  'El camino termina en una plazoleta con una baranda de hierro pintada de verde.',
  'tierra', false, false, true, 'bajo',
  'El camino tiene pendiente y tramos de escalones; ve con calzado cómodo y acompañado.'),
 ('Casona Santiváñez', 'museo',
  'Casona colonial restaurada, con patio central de piedra y salas con muebles y pinturas de época.',
  -17.392600, -66.158500, 'Centro histórico de Cochabamba',
  'En el patio se oye el eco de los pasos. Dentro huele a madera y a cera de piso.',
  'La puerta de calle es grande, de madera oscura, con un picaporte de bronce a la derecha.',
  'piedra', false, true, false, 'bajo',
  'Hay escalones irregulares en el patio; pide acompañamiento del personal.'),
 ('Paseo de El Prado', 'paseo',
  'Avenida peatonal con árboles, bancas y esculturas, ideal para caminar y tomar un café.',
  -17.381100, -66.156000, 'Avenida central, zona norte',
  'Se oyen autos a lo lejos y conversaciones en los cafés. Huele a café y a pan recién hecho.',
  'Se reconoce por las hileras de árboles a los lados y los faroles de hierro negro.',
  'baldosa', true, false, true, 'medio',
  'Camina por el centro del paseo, donde la baldosa está más pareja.'),
 ('Laguna Alalay', 'parque',
  'Laguna con un camino alrededor, aves acuáticas y zonas para pasear, correr y descansar.',
  -17.418200, -66.139600, 'Zona sur de la ciudad',
  'Se oyen aves y el viento sobre el agua. Huele a agua y a pasto. Hay poca sombra.',
  'El acceso principal es un portón ancho junto a un puesto de venta de bebidas.',
  'cemento', false, false, true, 'bajo',
  'Lleva agua y gorra; el camino es largo y casi no hay sombra al mediodía.'),
 ('Plaza de las Banderas', 'plaza',
  'Plaza amplia con una fila de mástiles y banderas, un área abierta y espacio para eventos cívicos.',
  -17.369500, -66.144800, 'Zona norte de la ciudad',
  'Se oyen las banderas moviéndose con el viento. Hay poco movimiento de personas y poca sombra.',
  'Se reconoce por los mástiles altos alineados y una plataforma de cemento frente a ellos.',
  'cemento', false, false, true, 'bajo',
  'El espacio es plano y abierto; es fácil de recorrer con bastón.')
) AS d(nombre, tipo, descripcion, latitud, longitud, direccion, sensorial, referencia,
       piso, tactil, braille, perros, ruido, recomendacion)
WHERE NOT EXISTS (SELECT 1 FROM sitios_turisticos s WHERE s.nombre = d.nombre);

INSERT INTO eventos (nombre, descripcion, tipo, fecha_inicio, fecha_fin, zona, creado_por)
SELECT e.nombre, e.descripcion, e.tipo, e.fecha_inicio, e.fecha_fin, e.zona,
       (SELECT id FROM usuarios ORDER BY id LIMIT 1)
FROM (VALUES
 ('Fiesta de Urkupiña', 'DATO DE PRUEBA. Festividad religiosa y cultural con peregrinación y danzas.',
  'festividad', DATE '2026-08-14', DATE '2026-08-16', 'Quillacollo'),
 ('Aniversario de Cochabamba', 'DATO DE PRUEBA. Feriado departamental con actos cívicos y desfiles.',
  'feriado', DATE '2026-09-14', NULL, 'Plaza 14 de Septiembre'),
 ('Feria Gastronómica de la Chicha y el Api', 'DATO DE PRUEBA. Feria de comidas y bebidas tradicionales de los valles.',
  'feria', CURRENT_DATE + 7, CURRENT_DATE + 9, 'Plaza Colón'),
 ('Festival de Música Andina', 'DATO DE PRUEBA. Conciertos de música de los valles y el altiplano.',
  'festividad', CURRENT_DATE + 15, NULL, 'Teatro Achá'),
 ('Feria Navideña de Artesanías', 'DATO DE PRUEBA. Venta de artesanías y adornos de Navidad.',
  'feria', CURRENT_DATE + 30, CURRENT_DATE + 44, 'Plaza 14 de Septiembre'),
 ('Navidad', 'DATO DE PRUEBA. Feriado nacional.',
  'feriado', DATE '2026-12-25', NULL, 'Todo el departamento'),
 ('Entrada Folklórica Universitaria', 'DATO DE PRUEBA. Desfile de danzas y comparsas por la avenida central.',
  'festividad', CURRENT_DATE - 20, NULL, 'Paseo de El Prado')
) AS e(nombre, descripcion, tipo, fecha_inicio, fecha_fin, zona)
WHERE NOT EXISTS (SELECT 1 FROM eventos x WHERE x.nombre = e.nombre);

COMMIT;

SELECT 'sitios de prueba' AS dato, count(*) FROM sitios_turisticos WHERE fuente LIKE 'DATO DE PRUEBA%'
UNION ALL
SELECT 'eventos de prueba', count(*) FROM eventos WHERE descripcion LIKE 'DATO DE PRUEBA%';
