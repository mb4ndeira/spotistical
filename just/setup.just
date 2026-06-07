# ── First-time setup & replication ─────────────────────────────────────────────

# Full bootstrap for a new machine: start services, wait for DB, run ingest
# Prerequisites: Docker running, .env file populated (copy from .env.example)
bootstrap:
    #!/bin/bash
    set -euo pipefail

    echo ""
    echo "  spotistical · bootstrap"
    echo "  ────────────────────────────────────────────────"

    # 1. Check .env exists
    if [ ! -f "{{ justfile_directory() }}/.env" ]; then
        echo ""
        echo "  ✗  .env not found."
        echo "     Copy and fill in the template first:"
        echo "       cp .env.example .env"
        echo ""
        exit 1
    fi
    echo "  ✓  .env found"

    # 2. Start all services (DB first via depends_on healthcheck)
    echo "  →  Starting services…"
    {{ compose }} up -d
    echo "  ✓  Services up"

    # 3. Wait for API to be ready
    echo "  →  Waiting for API…"
    for i in $(seq 1 30); do
        status=$(curl -s http://localhost:${API_HOST_PORT:-8000}/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('db',''))" 2>/dev/null || true)
        if [ "$status" = "connected" ]; then
            break
        fi
        sleep 2
    done
    if [ "$status" != "connected" ]; then
        echo "  ✗  API did not connect to DB in time. Check: just logs-svc api"
        exit 1
    fi
    echo "  ✓  API + DB connected"

    # 4. Ensure app user exists (idempotent — safe on existing volumes)
    echo "  →  Ensuring app user exists…"
    {{ compose }} exec -T db psql \
        -U "${POSTGRES_USER:-spotify}" \
        -d "${POSTGRES_DB:-spotify}" \
        -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${POSTGRES_APP_USER:-spotify_app}') THEN CREATE ROLE \"${POSTGRES_APP_USER:-spotify_app}\" WITH LOGIN PASSWORD '${POSTGRES_APP_PASSWORD:-spotify_app}'; END IF; END \$\$; GRANT CONNECT ON DATABASE \"${POSTGRES_DB:-spotify}\" TO \"${POSTGRES_APP_USER:-spotify_app}\"; GRANT USAGE ON SCHEMA public TO \"${POSTGRES_APP_USER:-spotify_app}\";" \
        2>/dev/null || true
    echo "  ✓  App user ready"

    # 5. Trigger parquet ingest
    echo "  →  Starting parquet ingest (2.1M rows — this takes ~10 min)…"
    curl -s -X POST http://localhost:${API_HOST_PORT:-8000}/ingest/tracks > /dev/null
    echo "  ✓  Ingest triggered — tail progress with: just logs-svc api"

    echo ""
    echo "  ────────────────────────────────────────────────"
    echo "  Once ingest finishes run:"
    echo "    just ingest-wait                           # blocks until done"
    echo "    just backfill-news 2023-10-18 2025-06-11  # fetch news history"
    echo "    just lock-sources                          # protect source tables"
    echo "    just db-stats                              # verify row counts"
    echo ""

# Wait for ingest to finish and print final row counts
ingest-wait:
    #!/bin/bash
    echo "Waiting for ingest to finish…"
    while true; do
        running=$(curl -s http://localhost:${API_HOST_PORT:-8000}/ingest/tracks/status 2>/dev/null \
            | python3 -c "import sys,json; print(json.load(sys.stdin).get('running',''))" 2>/dev/null || echo "unknown")
        if [ "$running" = "False" ]; then
            break
        fi
        echo "  still running… (check: just logs-svc api)"
        sleep 15
    done
    echo "Ingest complete."
    just db-stats
