#!/bin/bash
# Runs once on first DB volume creation (Docker entrypoint behaviour).
# Creates the app user with read-only access to source tables.
set -e

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname   "$POSTGRES_DB"   \
<<-SQL
    -- App user (read-only on source tables, write on derived tables)
    DO \$\$
    BEGIN
        IF NOT EXISTS (
            SELECT FROM pg_catalog.pg_roles WHERE rolname = '${POSTGRES_APP_USER}'
        ) THEN
            CREATE ROLE "${POSTGRES_APP_USER}"
                WITH LOGIN PASSWORD '${POSTGRES_APP_PASSWORD}';
        END IF;
    END \$\$;

    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO "${POSTGRES_APP_USER}";
    GRANT USAGE   ON SCHEMA public             TO "${POSTGRES_APP_USER}";
SQL

echo "[init] app user '${POSTGRES_APP_USER}' ready."
