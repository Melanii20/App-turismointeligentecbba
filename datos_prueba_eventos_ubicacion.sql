-- Complemento de datos_prueba.sql (también FICTICIO): da coordenadas y horario a los eventos de prueba
-- para ver la tarjeta "Hoy cerca de ti". Usa las coordenadas del sitio de prueba que se llama igual que la
-- zona del evento. Solo toca eventos marcados "DATO DE PRUEBA" que aún no tienen ubicación u hora.
-- Se borra junto con los demás datos de prueba (borrar_datos_prueba.sql borra los eventos completos).
SET client_encoding = 'UTF8';
BEGIN;
UPDATE eventos e
SET latitud = s.latitud, longitud = s.longitud
FROM sitios_turisticos s
WHERE e.descripcion LIKE 'DATO DE PRUEBA%' AND e.latitud IS NULL AND e.zona = s.nombre;
UPDATE eventos
SET hora_inicio = '09:00', hora_fin = '18:00'
WHERE descripcion LIKE 'DATO DE PRUEBA%' AND hora_inicio IS NULL;
COMMIT;
SELECT nombre, zona, latitud, hora_inicio FROM eventos WHERE descripcion LIKE 'DATO DE PRUEBA%' ORDER BY fecha_inicio;
