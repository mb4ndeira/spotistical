-- ─────────────────────────────────────────────────────────────────
-- spotistical · initial schema
-- idempotent: safe to run multiple times
-- requires: TimescaleDB, pgvector (both in timescale/timescaledb-ha)
-- ─────────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ── tracks ────────────────────────────────────────────────────────
-- One row per (date, country, track). Primary source of truth.
-- Partitioned by snapshot_date as a TimescaleDB hypertable.

CREATE TABLE IF NOT EXISTS tracks (
    snapshot_date       DATE        NOT NULL,
    country             CHAR(2)     NOT NULL,   -- ISO2C
    spotify_id          TEXT        NOT NULL,
    daily_rank          SMALLINT    NOT NULL,
    daily_movement      SMALLINT,
    weekly_movement     SMALLINT,
    name                TEXT        NOT NULL,
    artists             TEXT,
    popularity          SMALLINT,
    is_explicit         BOOLEAN,
    duration_ms         INTEGER,
    album_name          TEXT,
    album_release_date  DATE,
    -- audio features (all 0–1 normalised except loudness/tempo/key)
    danceability        FLOAT4,
    energy              FLOAT4,
    key                 SMALLINT,
    loudness            FLOAT4,
    mode                SMALLINT,
    speechiness         FLOAT4,
    acousticness        FLOAT4,
    instrumentalness    FLOAT4,
    liveness            FLOAT4,
    valence             FLOAT4,
    tempo               FLOAT4,
    time_signature      SMALLINT,

    PRIMARY KEY (snapshot_date, country, spotify_id)
);

SELECT create_hypertable(
    'tracks', 'snapshot_date',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists       => TRUE
);

CREATE INDEX IF NOT EXISTS idx_tracks_country_date
    ON tracks (country, snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_tracks_spotify_id
    ON tracks (spotify_id);


-- ── news_events ───────────────────────────────────────────────────
-- Alpha Vantage articles. embedding filled by Task 3.
-- country is nullable — filled by NER entity-extraction (Task 4).

CREATE TABLE IF NOT EXISTS news_events (
    id                          BIGSERIAL   PRIMARY KEY,
    published_at                TIMESTAMPTZ NOT NULL,
    title                       TEXT        NOT NULL,
    url                         TEXT        UNIQUE NOT NULL,
    overall_sentiment_score     FLOAT4,
    overall_sentiment_label     TEXT,
    topics                      JSONB,
    country                     CHAR(2)     -- nullable; filled by Task 4
    -- embedding column added by 002_vectors.sql (Task 3, requires pgvector)
);

CREATE INDEX IF NOT EXISTS idx_news_published
    ON news_events (published_at DESC);

CREATE INDEX IF NOT EXISTS idx_news_country_date
    ON news_events (country, published_at DESC)
    WHERE country IS NOT NULL;

-- ── song_clusters ─────────────────────────────────────────────────
-- One row per unique spotify_id. Cluster assignments from Tasks 1 & 2.5.

CREATE TABLE IF NOT EXISTS song_clusters (
    spotify_id          TEXT    PRIMARY KEY,
    audio_cluster_id    INTEGER,
    audio_cluster_label TEXT,
    lyric_cluster_id    INTEGER,
    lyric_cluster_label TEXT
);

-- ── insights ──────────────────────────────────────────────────────
-- Output of the insight engine (Tasks 4–7).
-- One row per (date, country, track, tier signal).

CREATE TABLE IF NOT EXISTS insights (
    id              BIGSERIAL   PRIMARY KEY,
    snapshot_date   DATE        NOT NULL,
    country         CHAR(2)     NOT NULL,
    spotify_id      TEXT        NOT NULL,
    tier            SMALLINT    NOT NULL,   -- 1, 2, or 3
    score           FLOAT4      NOT NULL,
    score_entity    FLOAT4,
    score_thematic  FLOAT4,
    score_macro     FLOAT4,
    label           TEXT,
    description     TEXT,
    contradiction   TEXT,
    narrative       TEXT,
    null_result     BOOLEAN     DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insights_date_country
    ON insights (snapshot_date, country);

CREATE INDEX IF NOT EXISTS idx_insights_spotify
    ON insights (spotify_id, snapshot_date DESC);
