-- Los campos de accesibilidad de sitios sin verificar quedan en NULL ("sin información").
-- Solo toca sitios sin fecha_verificacion. (Antes de aplicar, 0 de las 3 filas tenían valor distinto de NULL.)
UPDATE sitios_turisticos
SET acceso_piso_tactil = NULL,
    acceso_señalizacion_braille = NULL,
    acceso_permite_perros_guia = NULL
WHERE fecha_verificacion IS NULL;
