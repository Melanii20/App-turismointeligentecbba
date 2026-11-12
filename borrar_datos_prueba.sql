-- Borra TODOS los datos de prueba cargados con datos_prueba.sql, y solo esos
-- (los sitios cuya fuente empieza con 'DATO DE PRUEBA', los eventos y documentos que empiezan igual).
-- No toca los datos reales ni los 3 sitios de prueba originales.
SET client_encoding = 'UTF8';
BEGIN;
DELETE FROM sitios_turisticos WHERE fuente LIKE 'DATO DE PRUEBA%';
DELETE FROM eventos WHERE descripcion LIKE 'DATO DE PRUEBA%';
-- Documento ficticio (sus fragmentos se borran en cascada)
DELETE FROM documentos WHERE permiso_uso LIKE 'DATO DE PRUEBA%';
COMMIT;
SELECT (SELECT count(*) FROM sitios_turisticos) AS sitios_restantes,
       (SELECT count(*) FROM eventos) AS eventos_restantes;
