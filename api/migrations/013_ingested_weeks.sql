CREATE TABLE IF NOT EXISTS news_ingested_weeks (
    week_start  DATE PRIMARY KEY,
    source      TEXT NOT NULL DEFAULT 'gdelt_bulk',
    articles_before_curation INT,
    articles_after_curation  INT,
    completed_at TIMESTAMPTZ DEFAULT now()
);
