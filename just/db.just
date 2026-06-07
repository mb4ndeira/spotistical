# ── Database ───────────────────────────────────────────────────────────────────

# Default DB connection vars (overridden by .env)
pg_user := env_var_or_default("POSTGRES_USER", "spotify")
pg_pass := env_var_or_default("POSTGRES_PASSWORD", "spotify")
pg_db   := env_var_or_default("POSTGRES_DB", "spotistical")

# Open an interactive psql session inside the DB container
psql:
    {{ compose }} exec db psql -U {{ pg_user }} -d {{ pg_db }}

# Apply migrations manually (normally run automatically by the API on startup)
migrate:
    #!/bin/bash
    for f in {{ justfile_directory() }}/api/migrations/*.sql; do
        echo "Applying $f …"
        {{ compose }} exec -T db psql -U {{ pg_user }} -d {{ pg_db }} < "$f"
    done

# Quick row counts for all main tables
db-stats:
    {{ compose }} exec db psql -U {{ pg_user }} -d {{ pg_db }} -x \
        -c "SELECT 'tracks'        AS \"table\", count(*)::text AS rows FROM tracks        UNION ALL \
            SELECT 'news_events'   AS \"table\", count(*)::text AS rows FROM news_events   UNION ALL \
            SELECT 'song_clusters' AS \"table\", count(*)::text AS rows FROM song_clusters UNION ALL \
            SELECT 'insights'      AS \"table\", count(*)::text AS rows FROM insights"

# Hypertable chunk info
db-chunks:
    {{ compose }} exec db psql -U {{ pg_user }} -d {{ pg_db }} \
        -c "SELECT hypertable_name, chunk_name, range_start::date, range_end::date, \
                   pg_size_pretty(total_bytes) AS size \
            FROM   timescaledb_information.chunks \
            ORDER  BY hypertable_name, range_start"

# Drop and recreate the entire schema — destructive, wipes all data
db-reset:
    #!/bin/bash
    echo "WARNING: this drops all tables and re-runs migrations. Ctrl-C to abort."
    sleep 4
    {{ compose }} exec -T db psql -U {{ pg_user }} -d {{ pg_db }} \
        -c "DROP TABLE IF EXISTS insights, song_clusters, news_events, tracks CASCADE"
    echo "Tables dropped. Restart the API to re-apply migrations:"
    echo "  just restart-svc api"

# ── Ingest ─────────────────────────────────────────────────────────────────────

# Trigger the parquet → TimescaleDB ingest (runs in background, watch logs)
ingest:
    #!/bin/bash
    echo "Triggering ingest…"
    curl -s -X POST http://localhost:${API_HOST_PORT:-8000}/ingest/tracks | python3 -m json.tool
    echo ""
    echo "Watch progress with: just logs-svc api"

# Poll ingest status
ingest-status:
    curl -s http://localhost:${API_HOST_PORT:-8000}/ingest/tracks/status | python3 -m json.tool

# Lock source tables (run once after ingest + backfill are both complete)
lock-sources:
    #!/bin/bash
    echo "Locking source tables…"
    curl -s -X POST http://localhost:${API_HOST_PORT:-8000}/ingest/lock-sources | python3 -m json.tool

# Backfill Alpha Vantage news: just backfill-news 2023-10-18 2025-06-11
backfill-news date_from date_to:
    #!/bin/bash
    echo "Starting news backfill {{ date_from }} → {{ date_to }}…"
    curl -s -X POST \
        "http://localhost:${API_HOST_PORT:-8000}/ingest/news?date_from={{ date_from }}&date_to={{ date_to }}" \
        | python3 -m json.tool
    echo ""
    echo "Watch progress with: just logs-svc api"

# Live progress + DB coverage: weeks done, articles in DB, date range covered
backfill-news-status:
    curl -s http://localhost:${API_HOST_PORT:-8000}/ingest/news/status \
        | python3 {{ justfile_directory() }}/scripts/news_status.py

# ── Health ─────────────────────────────────────────────────────────────────────

# Check API health (includes DB connectivity)
health:
    curl -s http://localhost:${API_HOST_PORT:-8000}/health | python3 -m json.tool
