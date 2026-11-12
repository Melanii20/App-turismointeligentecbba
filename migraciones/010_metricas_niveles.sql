ALTER TABLE metricas_consulta
  ADD COLUMN nivel_fuente VARCHAR(20),      -- base / documento / cache_web / web / ninguna
  ADD COLUMN eje_dato VARCHAR(20),          -- operativo / narrativo
  ADD COLUMN creditos_tavily SMALLINT NOT NULL DEFAULT 0,
  ADD COLUMN motivo_sin_llm VARCHAR(50);
