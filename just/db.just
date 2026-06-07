# ── Database ───────────────────────────────────────────────────────────────────

pg_user := env_var_or_default("POSTGRES_USER", "spotify")
pg_db   := env_var_or_default("POSTGRES_DB",   "spotify")

# Interactive psql session inside the DB container
psql:
    {{ compose }} exec db psql -U {{ pg_user }} -d {{ pg_db }}

# Apply all migrations manually (the API does this automatically on startup)
migrate:
    #!/bin/bash
    for f in {{ justfile_directory() }}/api/migrations/*.sql; do
        echo "Applying $f …"
        {{ compose }} exec -T db psql -U {{ pg_user }} -d {{ pg_db }} < "$f"
    done

# Row counts for all main tables
db-stats:
    {{ compose }} exec db psql -U {{ pg_user }} -d {{ pg_db }} -x -c \
        "SELECT 'tracks'        AS \"table\", count(*)::text AS rows FROM tracks        UNION ALL \
         SELECT 'news_events',               count(*)::text         FROM news_events   UNION ALL \
         SELECT 'song_clusters',             count(*)::text         FROM song_clusters UNION ALL \
         SELECT 'insights',                  count(*)::text         FROM insights"

# TimescaleDB hypertable chunk info
db-chunks:
    {{ compose }} exec db psql -U {{ pg_user }} -d {{ pg_db }} -c \
        "SELECT hypertable_name, chunk_name, range_start::date, range_end::date, \
                pg_size_pretty(total_bytes) AS size \
         FROM   timescaledb_information.chunks \
         ORDER  BY hypertable_name, range_start"

# Drop all tables — destructive, requires API restart to re-apply migrations
db-reset:
    #!/bin/bash
    echo "WARNING: drops all tables and wipes all data. Ctrl-C to abort."
    sleep 4
    {{ compose }} exec -T db psql -U {{ pg_user }} -d {{ pg_db }} \
        -c "DROP TABLE IF EXISTS insights, song_clusters, news_events, tracks CASCADE"
    echo "Done. Restart the API to re-apply migrations: just restart-svc api"

# ── Notebooks ──────────────────────────────────────────────────────────────────

# Launch Jupyter Lab (auto-installs deps if missing)
notebooks:
    #!/bin/bash
    cd {{ justfile_directory() }}/notebooks
    if ! python3 -c "import jupyter" 2>/dev/null; then
        pip install -r requirements.txt -q
    fi
    jupyter lab --port 8888 --no-browser

# ── Health ─────────────────────────────────────────────────────────────────────

# API health check (includes DB connectivity status)
health:
    curl -s http://localhost:${API_HOST_PORT:-8000}/health | python3 -m json.tool
