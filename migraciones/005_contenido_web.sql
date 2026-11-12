-- 005: caché de Wikipedia (solo temas culturales), para no pedir lo mismo cada vez.
CREATE TABLE IF NOT EXISTS contenido_web (
    id SERIAL PRIMARY KEY,
    fuente VARCHAR(30) NOT NULL DEFAULT 'wikipedia',
    tema VARCHAR(30) NOT NULL,               -- leyenda / tradicion / comida / danza / historia / personaje
    titulo VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    texto TEXT NOT NULL,
    licencia VARCHAR(50) NOT NULL DEFAULT 'CC BY-SA 4.0',
    obtenido_en TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (fuente, titulo)
);
