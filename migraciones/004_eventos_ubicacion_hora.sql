-- 004: ubicación y hora de los eventos (tarjeta "Hoy cerca de ti").
ALTER TABLE eventos
  ADD COLUMN IF NOT EXISTS latitud DECIMAL(9,6),
  ADD COLUMN IF NOT EXISTS longitud DECIMAL(9,6),
  ADD COLUMN IF NOT EXISTS hora_inicio TIME,
  ADD COLUMN IF NOT EXISTS hora_fin TIME;
