-- 003: sin valor por defecto en los campos de accesibilidad: NULL = "sin información".
-- Solo cambia los DEFAULT de las columnas; NO modifica ninguna fila existente.
-- Pendiente (a mano, por la administradora): revisar los sitios que ya existían; si un dato
-- (piso táctil, braille, perros guía) no fue verificado, dejarlo en NULL.
ALTER TABLE sitios_turisticos
  ALTER COLUMN acceso_piso_tactil DROP DEFAULT,
  ALTER COLUMN "acceso_señalizacion_braille" DROP DEFAULT,
  ALTER COLUMN acceso_permite_perros_guia DROP DEFAULT;
