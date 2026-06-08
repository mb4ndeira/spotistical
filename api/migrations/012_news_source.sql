-- ─────────────────────────────────────────────────────────────────
-- spotistical · rastreabilidade de fonte em news_events
--
-- Adiciona coluna `source` para distinguir artigos por provedor:
--   'guardian' — The Guardian API (primário, cobertura garantida)
--   'gdelt'    — GDELT DOC API (secundário, multilingual)
--   NULL       — artigos anteriores (Alpha Vantage)
--
-- idempotent — safe to re-run.
-- ─────────────────────────────────────────────────────────────────

ALTER TABLE news_events ADD COLUMN IF NOT EXISTS source TEXT;

COMMENT ON COLUMN news_events.source IS
    'Provedor do artigo: ''guardian'', ''gdelt'', ou NULL (legado Alpha Vantage).';
