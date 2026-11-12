-- La columna "tema" ya existía desde la migración 005, por eso se omite aquí.
ALTER TABLE contenido_web
  ADD COLUMN dominio VARCHAR(150),
  ADD COLUMN estado_revision VARCHAR(20) NOT NULL DEFAULT 'pendiente';  -- pendiente / convertido / descartado
UPDATE contenido_web SET dominio = 'es.wikipedia.org' WHERE dominio IS NULL AND fuente = 'wikipedia';
