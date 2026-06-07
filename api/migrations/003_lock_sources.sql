-- ─────────────────────────────────────────────────────────────────
-- Task 0 · Source table protection
--
-- Run ONCE after initial ingest (tracks) and backfill (news_events)
-- are complete.  Call via: just lock-sources
--
-- What this does:
--   1. Installs triggers that prevent UPDATE/DELETE on source tables
--      for ALL users — including the admin.  INSERTs remain allowed
--      so incremental news fetches can add new articles safely.
--   2. Grants the app user read-only access to source tables and
--      read-write access to derived tables (song_clusters, insights).
--
-- Safe to re-run — all statements are idempotent.
-- ─────────────────────────────────────────────────────────────────

-- ── 1. Trigger function ───────────────────────────────────────────

CREATE OR REPLACE FUNCTION prevent_source_modification()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION
        '% is a read-only source table. UPDATE and DELETE are not permitted. '
        'To reload data use just db-reset followed by just ingest / just backfill-news.',
        TG_TABLE_NAME;
END;
$$;

-- ── 2. Attach triggers ────────────────────────────────────────────

DROP TRIGGER IF EXISTS tracks_readonly      ON tracks;
DROP TRIGGER IF EXISTS news_events_readonly ON news_events;

CREATE TRIGGER tracks_readonly
    BEFORE UPDATE OR DELETE ON tracks
    FOR EACH ROW EXECUTE FUNCTION prevent_source_modification();

CREATE TRIGGER news_events_readonly
    BEFORE UPDATE OR DELETE ON news_events
    FOR EACH ROW EXECUTE FUNCTION prevent_source_modification();

-- ── 3. App-user permissions ───────────────────────────────────────
-- (No-op if POSTGRES_APP_USER was not created; the DO block is safe.)

DO $$
DECLARE
    app TEXT := current_setting('spotistical.app_user', true);
BEGIN
    IF app IS NULL OR app = '' THEN
        RAISE NOTICE 'spotistical.app_user not set — skipping GRANT/REVOKE';
        RETURN;
    END IF;

    -- Source tables: SELECT only
    EXECUTE format('GRANT  SELECT                          ON tracks       TO %I', app);
    EXECUTE format('REVOKE INSERT, UPDATE, DELETE          ON tracks       FROM %I', app);
    EXECUTE format('GRANT  SELECT                          ON news_events  TO %I', app);
    EXECUTE format('REVOKE INSERT, UPDATE, DELETE          ON news_events  FROM %I', app);

    -- Derived tables: full read-write
    EXECUTE format('GRANT  SELECT, INSERT, UPDATE, DELETE  ON song_clusters TO %I', app);
    EXECUTE format('GRANT  SELECT, INSERT, UPDATE, DELETE  ON insights       TO %I', app);
    EXECUTE format('GRANT  USAGE, SELECT ON SEQUENCE insights_id_seq         TO %I', app);
    EXECUTE format('GRANT  USAGE, SELECT ON SEQUENCE news_events_id_seq      TO %I', app);

    RAISE NOTICE 'Permissions applied for app user: %', app;
END;
$$;
