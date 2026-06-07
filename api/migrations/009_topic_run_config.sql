-- ─────────────────────────────────────────────────────────────────
-- spotistical · configuração do run BERTopic
--
-- Problema que isso resolve:
-- O modelo de embedding é multilingual mas o CountVectorizer usa
-- stop_words='english' porque o corpus Alpha Vantage é majoritariamente
-- em inglês (feeds financeiros anglófonos, mesmo para mercados emergentes).
-- Quando o corpus for substituído por uma fonte multilingual, o run
-- passará a usar um vectorizer diferente — e essa distinção precisa ser
-- rastreável para que comparações entre runs façam sentido.
--
-- idempotent — safe to re-run.
-- ─────────────────────────────────────────────────────────────────

ALTER TABLE news_topic_definitions
    ADD COLUMN IF NOT EXISTS config JSONB;

COMMENT ON COLUMN news_topic_definitions.config IS
    'Configuração do run BERTopic. Campos esperados:
     embedding_model  TEXT  — nome do modelo sentence-transformers
     news_lang        TEXT  — idioma dominante do corpus ("en", "multilingual", ...)
     stop_words       TEXT  — valor passado ao CountVectorizer stop_words
     corpus_size      INT   — número de artigos usados no run
    Permite distinguir runs monolingual (corpus atual, Alpha Vantage em inglês)
    de runs multilingual futuros sem quebrar a chave run_id.';
