-- ─────────────────────────────────────────────────────────────────
-- spotistical · per-country song_clusters
-- Replaces the global (spotify_id) PK with a composite
-- (spotify_id, country) PK so the same track can belong to
-- different audio clusters in different markets.
--
-- country = 'GL' is reserved for the optional global pass.
--
-- idempotent — safe to re-run (DROP IF EXISTS + recreate)
-- ─────────────────────────────────────────────────────────────────

DROP TABLE IF EXISTS song_clusters;

CREATE TABLE song_clusters (
    spotify_id          TEXT    NOT NULL,
    country             CHAR(2) NOT NULL,   -- ISO2C  or 'GL' (global)

    -- audio clustering (Task 1)
    audio_cluster_id    INTEGER,
    audio_cluster_label TEXT,
    umap_audio_x        FLOAT4,
    umap_audio_y        FLOAT4,

    -- lyric clustering (Task 2)
    lyric_cluster_id    INTEGER,
    lyric_cluster_label TEXT,
    umap_lyric_x        FLOAT4,
    umap_lyric_y        FLOAT4,

    PRIMARY KEY (spotify_id, country)
);

CREATE INDEX IF NOT EXISTS idx_song_clusters_country
    ON song_clusters (country);

CREATE INDEX IF NOT EXISTS idx_song_clusters_audio_cluster
    ON song_clusters (country, audio_cluster_id);

COMMENT ON TABLE  song_clusters IS
    'Per-country cluster assignments. Each row = one track in one market. '
    'country=''GL'' holds the global (all-markets) clustering for reference.';

COMMENT ON COLUMN song_clusters.country IS
    'ISO2C market code, or ''GL'' for the global clustering pass.';
