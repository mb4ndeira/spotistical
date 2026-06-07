-- ─────────────────────────────────────────────────────────────────
-- spotistical · migração de Alpha Vantage → GDELT
--
-- Remove colunas de sentimento financeiro do AV (não usadas nos tiers).
-- Adiciona colunas nativas do GDELT:
--   tone        — AvgTone do artigo (-10 negativo … +10 positivo)
--   source_lang — idioma do artigo (e.g. 'English', 'Spanish', 'Portuguese')
--
-- Os 7.788 artigos existentes perdem overall_sentiment_* mas mantêm
-- todos os outros campos. tone e source_lang ficarão NULL nesses registros
-- — o que é correto, pois vieram de uma fonte diferente.
--
-- idempotent — safe to re-run.
-- ─────────────────────────────────────────────────────────────────

ALTER TABLE news_events DROP COLUMN IF EXISTS overall_sentiment_score;
ALTER TABLE news_events DROP COLUMN IF EXISTS overall_sentiment_label;

ALTER TABLE news_events ADD COLUMN IF NOT EXISTS tone        REAL;
ALTER TABLE news_events ADD COLUMN IF NOT EXISTS source_lang TEXT;

COMMENT ON COLUMN news_events.tone IS
    'GDELT AvgTone: sentimento médio do artigo. Escala aproximada -10 (muito negativo) a +10 (muito positivo).';

COMMENT ON COLUMN news_events.source_lang IS
    'Idioma do artigo conforme GDELT (e.g. ''English'', ''Spanish'', ''Portuguese'').';
