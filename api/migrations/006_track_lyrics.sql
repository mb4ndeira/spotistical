-- ─────────────────────────────────────────────────────────────────
-- spotistical · track lyrics
-- One row per unique spotify_id.
-- failed = TRUE means we tried and got nothing — skip on future runs.
-- idempotent — safe to re-run.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS track_lyrics (
    spotify_id   TEXT        PRIMARY KEY,
    lyrics_raw   TEXT,                        -- NULL if fetch failed
    language     TEXT,                        -- ISO 639-1, detected by use case
    source       TEXT        DEFAULT 'lyrics.ovh',
    fetched_at   TIMESTAMPTZ DEFAULT NOW(),
    failed       BOOLEAN     DEFAULT FALSE,   -- TRUE = tried, no lyrics found
    fail_reason  TEXT                         -- e.g. '404', 'timeout', 'empty'
);

COMMENT ON TABLE  track_lyrics IS
    'Raw lyrics per unique track. failed=TRUE rows are skipped on re-runs '
    'unless retry_failed=true is passed. Source tables (tracks) are never modified.';

CREATE INDEX IF NOT EXISTS idx_track_lyrics_failed
    ON track_lyrics (failed)
    WHERE failed = FALSE;
