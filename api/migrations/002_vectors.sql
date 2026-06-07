-- ─────────────────────────────────────────────────────────────────
-- Task 3 · pgvector — run after installing pgvector extension
-- Requires: timescale/timescaledb image with pgvector, or a custom
--           Dockerfile that installs postgresql-16-pgvector
-- ─────────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE news_events
    ADD COLUMN IF NOT EXISTS embedding VECTOR(768);

CREATE INDEX IF NOT EXISTS idx_news_embedding
    ON news_events USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;
