# ── First-time setup ────────────────────────────────────────────────────────────

# Start services and wait for the API to be ready.
# Then open notebooks/00_pipeline.ipynb to ingest data and lock sources.
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
        echo "     Copy and fill in the template:"
        echo "       cp .env.example .env"
        echo ""
        exit 1
    fi
    echo "  ✓  .env found"

    # 2. Start services (DB first via depends_on healthcheck)
    echo "  →  Starting services…"
    {{ compose }} up -d
    echo "  ✓  Services started"

    # 3. Wait for API + DB
    echo "  →  Waiting for API…"
    for i in $(seq 1 30); do
        status=$(curl -s http://localhost:${API_HOST_PORT:-8000}/health 2>/dev/null \
            | python3 -c "import sys,json; print(json.load(sys.stdin).get('db',''))" 2>/dev/null || true)
        [ "$status" = "connected" ] && break
        sleep 2
    done
    if [ "$status" != "connected" ]; then
        echo "  ✗  API did not connect to DB — check: just logs api"
        exit 1
    fi
    echo "  ✓  API + DB connected"

    # 4. Ensure app user exists (idempotent)
    echo "  →  Ensuring app user…"
    {{ compose }} exec -T db psql \
        -U "${POSTGRES_USER:-spotify}" \
        -d "${POSTGRES_DB:-spotify}" \
        -c "DO \$\$ BEGIN
              IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${POSTGRES_APP_USER:-spotify_app}')
              THEN CREATE ROLE \"${POSTGRES_APP_USER:-spotify_app}\"
                   WITH LOGIN PASSWORD '${POSTGRES_APP_PASSWORD:-spotify_app}';
              END IF;
            END \$\$;
            GRANT CONNECT ON DATABASE \"${POSTGRES_DB:-spotify}\" TO \"${POSTGRES_APP_USER:-spotify_app}\";
            GRANT USAGE  ON SCHEMA public TO \"${POSTGRES_APP_USER:-spotify_app}\";" \
        2>/dev/null || true
    echo "  ✓  App user ready"

    echo ""
    echo "  ────────────────────────────────────────────────"
    echo "  Services are up. Continue in the notebook:"
    echo ""
    echo "    just notebooks"
    echo "    → open  00_pipeline.ipynb   (ingest, backfill, lock sources)"
    echo "    → open  01_audio_clustering.ipynb"
    echo ""
