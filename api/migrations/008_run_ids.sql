-- ─────────────────────────────────────────────────────────────────
-- spotistical · run isolation for derived tables
--
-- Problema que isso resolve:
-- K-Means e BERTopic renumeram IDs a cada re-run. Sem versioning,
-- um insight que diz "cluster 3 = alta energia" pode estar apontando
-- para o que hoje seria "cluster 7 = acústico" depois de re-rodar.
--
-- Solução:
-- song_clusters.clustering_run_id  — identifica o run que gerou cada assignment
-- insights.clustering_run_id       — run de clusters usado para gerar o insight
-- insights.topic_run               — run BERTopic usado para gerar o insight
--
-- Contrato:
-- Qualquer query que una insights com song_clusters ou news_topic_definitions
-- DEVE filtrar pelo run_id correspondente. O insight engine escreve sempre
-- com os run IDs ativos. Re-rodar clustering/BERTopic + insight engine
-- limpa automaticamente os insights do run anterior.
--
-- idempotent — safe to re-run.
-- ─────────────────────────────────────────────────────────────────

-- clustering_run_id em song_clusters
-- Formato: ISO8601 timestamp do início do run  ex: '2024-01-15T10:00:00'
ALTER TABLE song_clusters
    ADD COLUMN IF NOT EXISTS clustering_run_id TEXT;

COMMENT ON COLUMN song_clusters.clustering_run_id IS
    'Timestamp do run de K-Means que gerou este assignment. '
    'Cluster IDs só são comparáveis dentro do mesmo clustering_run_id.';

-- run IDs em insights para rastreabilidade
ALTER TABLE insights
    ADD COLUMN IF NOT EXISTS clustering_run_id TEXT,
    ADD COLUMN IF NOT EXISTS topic_run         TEXT;

COMMENT ON COLUMN insights.clustering_run_id IS
    'Run de clustering (song_clusters) ativo quando o insight foi gerado.';

COMMENT ON COLUMN insights.topic_run IS
    'Run BERTopic (news_topic_definitions) ativo quando o insight foi gerado.';

-- índice para limpeza rápida de insights de runs antigos
CREATE INDEX IF NOT EXISTS idx_insights_clustering_run
    ON insights (clustering_run_id)
    WHERE clustering_run_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_insights_topic_run
    ON insights (topic_run)
    WHERE topic_run IS NOT NULL;
