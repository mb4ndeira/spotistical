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
-- Only revoke write access on source tables from the app user.
-- Read grants on all tables are applied automatically on every API
-- startup via db_driver._grant_app_user() — no need to duplicate here.

DO $$
DECLARE
    app TEXT := current_setting('spotistical.app_user', true);
BEGIN
    IF app IS NULL OR app = '' THEN
        RAISE NOTICE 'spotistical.app_user not set — skipping REVOKE';
        RETURN;
    END IF;

    EXECUTE format('REVOKE INSERT, UPDATE, DELETE ON tracks      FROM %I', app);
    EXECUTE format('REVOKE INSERT, UPDATE, DELETE ON news_events FROM %I', app);

    RAISE NOTICE 'Source table writes revoked for app user: %', app;
END;
$$;
