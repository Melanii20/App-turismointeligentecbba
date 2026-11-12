-- Documentos de turismo (manuales, guías, folletos...) que entran al RAG solo cuando están verificados.
CREATE TABLE documentos (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    institucion_autor VARCHAR(255),
    tipo VARCHAR(50) NOT NULL,          -- manual / guia / folleto / libro / web_revisado / otro
    tema VARCHAR(50),                   -- general / gastronomia / tradiciones / fiestas / leyendas / historia / ...
    archivo VARCHAR(255),               -- ruta del archivo (NULL si viene de contenido web)
    url_origen TEXT,                    -- si viene de internet
    anio INTEGER,
    permiso_uso TEXT NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'borrador',
    subido_por INTEGER REFERENCES usuarios(id),
    verificado_por INTEGER REFERENCES usuarios(id),
    fecha_verificacion TIMESTAMP,
    creado_en TIMESTAMP DEFAULT now()
);
CREATE TABLE fragmentos_documento (
    id SERIAL PRIMARY KEY,
    documento_id INTEGER NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    numero INTEGER NOT NULL,
    pagina INTEGER,
    texto TEXT NOT NULL,
    embedding VECTOR(768)
);
CREATE INDEX fragmentos_documento_embedding_hnsw
    ON fragmentos_documento USING hnsw (embedding vector_cosine_ops);
CREATE INDEX fragmentos_documento_documento ON fragmentos_documento (documento_id);
