-- 002: capa general del sitio (la llena el administrador; nunca desde Wikipedia).
ALTER TABLE sitios_turisticos
  ADD COLUMN IF NOT EXISTS relato TEXT,
  ADD COLUMN IF NOT EXISTS que_ver TEXT,
  ADD COLUMN IF NOT EXISTS horario VARCHAR(150),
  ADD COLUMN IF NOT EXISTS costo_ingreso VARCHAR(100),
  ADD COLUMN IF NOT EXISTS duracion_visita VARCHAR(50),
  ADD COLUMN IF NOT EXISTS servicios TEXT;
