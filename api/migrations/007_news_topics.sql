-- ─────────────────────────────────────────────────────────────────
-- spotistical · BERTopic results
-- Stores topic definitions and per-article assignments from Task 3.
-- Re-running BERTopic creates a new run_id row set, keeping history.
-- idempotent — safe to re-run.
-- ─────────────────────────────────────────────────────────────────

-- topic definitions (one row per topic per run)
CREATE TABLE IF NOT EXISTS news_topic_definitions (
    id           BIGSERIAL   PRIMARY KEY,
    run_id       TEXT        NOT NULL,          -- e.g. '2024-01-15T10:00'
    topic_id     INTEGER     NOT NULL,          -- BERTopic topic ID (-1 = outlier)
    label        TEXT,                          -- auto-generated label
    top_words    JSONB,                         -- [{"word": "...", "score": 0.9}, ...]
    article_count INTEGER,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (run_id, topic_id)
);

-- per-article topic assignment
ALTER TABLE news_events
    ADD COLUMN IF NOT EXISTS topic_id    INTEGER,   -- FK to news_topic_definitions.topic_id
    ADD COLUMN IF NOT EXISTS topic_run   TEXT;      -- which BERTopic run assigned this

CREATE INDEX IF NOT EXISTS idx_news_topic
    ON news_events (topic_id)
    WHERE topic_id IS NOT NULL;
