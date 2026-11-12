-- 006: métricas de uso sin datos personales (para el Capítulo VI).
-- Sin texto de la pregunta, sin ubicación, sin identificador de la persona.
CREATE TABLE IF NOT EXISTS metricas_consulta (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP NOT NULL DEFAULT now(),
    canal VARCHAR(20) NOT NULL,              -- app / telegram
    intencion VARCHAR(30) NOT NULL,
    uso_llm BOOLEAN NOT NULL,
    fuente VARCHAR(30),                      -- base_verificada / wikipedia / sistema
    sitio_id INTEGER REFERENCES sitios_turisticos(id) ON DELETE SET NULL,
    similitud_maxima REAL,
    tiempo_ms INTEGER
);
