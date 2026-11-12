-- 001: estado del sitio (borrador / verificado). Ya estaba aplicada en la base; se guarda por trazabilidad.
ALTER TABLE sitios_turisticos
  ADD COLUMN IF NOT EXISTS estado VARCHAR(20) NOT NULL DEFAULT 'borrador';
