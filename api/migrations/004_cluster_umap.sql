-- ─────────────────────────────────────────────────────────────────
-- spotistical · cluster UMAP coordinates
-- Adds 2D projection columns to song_clusters for audio (Task 1)
-- and lyric (Task 2) UMAP embeddings.
-- idempotent — uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS
-- ─────────────────────────────────────────────────────────────────

ALTER TABLE song_clusters
    ADD COLUMN IF NOT EXISTS umap_audio_x  FLOAT4,
    ADD COLUMN IF NOT EXISTS umap_audio_y  FLOAT4,
    ADD COLUMN IF NOT EXISTS umap_lyric_x  FLOAT4,
    ADD COLUMN IF NOT EXISTS umap_lyric_y  FLOAT4;

COMMENT ON COLUMN song_clusters.umap_audio_x IS '2-D UMAP projection of audio features (x axis)';
COMMENT ON COLUMN song_clusters.umap_audio_y IS '2-D UMAP projection of audio features (y axis)';
COMMENT ON COLUMN song_clusters.umap_lyric_x IS '2-D UMAP projection of lyric embeddings (x axis)';
COMMENT ON COLUMN song_clusters.umap_lyric_y IS '2-D UMAP projection of lyric embeddings (y axis)';
