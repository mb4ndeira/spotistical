from __future__ import annotations

import os
import pathlib
import asyncpg

# ── Two pools ─────────────────────────────────────────────────────
# _app_pool   — app user, read-only on source tables (tracks, news_events)
#               used by all normal API routes
# _admin_pool — admin user (POSTGRES_USER), full write access
#               used only by ingest routes

_app_pool:   asyncpg.Pool | None = None
_admin_pool: asyncpg.Pool | None = None

_MIGRATIONS_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "migrations"


def _admin_kwargs() -> dict:
    """Connection kwargs for the admin/ingest user."""
    user     = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    database = os.environ.get("POSTGRES_DB")
    missing  = [k for k, v in {"POSTGRES_USER": user, "POSTGRES_PASSWORD": password, "POSTGRES_DB": database}.items() if not v]
    if missing:
        raise RuntimeError(f"Missing DB env vars: {', '.join(missing)}")
    return dict(
        host=os.environ.get("POSTGRES_HOST", "db"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=user, password=password, database=database,
    )


def _app_kwargs() -> dict | None:
    """Connection kwargs for the app user. Returns None if not configured."""
    user     = os.environ.get("POSTGRES_APP_USER")
    password = os.environ.get("POSTGRES_APP_PASSWORD")
    database = os.environ.get("POSTGRES_DB")
    if not (user and password and database):
        return None
    return dict(
        host=os.environ.get("POSTGRES_HOST", "db"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=user, password=password, database=database,
    )


async def init() -> None:
    """Create both pools and run pending migrations (as admin)."""
    global _app_pool, _admin_pool

    _admin_pool = await asyncpg.create_pool(**_admin_kwargs(), min_size=2, max_size=5, command_timeout=60)
    print("[db] admin pool ready")

    app_kw = _app_kwargs()
    if app_kw:
        _app_pool = await asyncpg.create_pool(**app_kw, min_size=2, max_size=10, command_timeout=60)
        print("[db] app pool ready")
    else:
        print("[db] POSTGRES_APP_USER not set — app pool using admin credentials")
        _app_pool = _admin_pool

    await _run_migrations()
    await _grant_app_user()


async def close() -> None:
    global _app_pool, _admin_pool
    if _admin_pool:
        await _admin_pool.close()
    if _app_pool and _app_pool is not _admin_pool:
        await _app_pool.close()
    _app_pool = _admin_pool = None


def get_pool() -> asyncpg.Pool:
    """App pool — read-only on source tables. Use for all normal queries."""
    if _app_pool is None:
        raise RuntimeError("DB pool not initialised — ensure startup completed")
    return _app_pool


def get_admin_pool() -> asyncpg.Pool:
    """Admin pool — full write access. Use only for ingest operations."""
    if _admin_pool is None:
        raise RuntimeError("Admin pool not initialised — ensure startup completed")
    return _admin_pool


async def lock_source_tables() -> None:
    """Apply 003_lock_sources.sql using the app user name from env."""
    app_user = os.environ.get("POSTGRES_APP_USER", "")
    sql_path = _MIGRATIONS_DIR / "003_lock_sources.sql"
    sql      = sql_path.read_text()

    pool = get_admin_pool()
    async with pool.acquire() as conn:
        # Set the session variable so the DO block inside the migration can read it
        await conn.execute(f"SET LOCAL spotistical.app_user = '{app_user}'")
        await conn.execute(sql)
    print(f"[db] source tables locked — app user '{app_user}' is now read-only on tracks + news_events")


async def _grant_app_user() -> None:
    """Grant the app user read access to source tables and read-write to derived tables.

    Runs on every startup — idempotent (GRANT is a no-op if already granted).
    Derived tables (song_clusters, insights) must be readable by the app user
    so notebooks and API routes can query them without admin credentials.
    Source table write protection is a separate concern handled by 003_lock_sources.sql.
    """
    app_user = os.environ.get("POSTGRES_APP_USER")
    if not app_user:
        return
    pool = get_admin_pool()
    async with pool.acquire() as conn:
        # source tables — read only
        await conn.execute(f'GRANT SELECT ON tracks, news_events TO "{app_user}"')
        # derived tables — full read-write (pipeline owns these)
        await conn.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON song_clusters, insights TO "{app_user}"')
        # sequences needed for INSERT on tables with bigserial PKs
        await conn.execute(f'GRANT USAGE, SELECT ON SEQUENCE insights_id_seq, news_events_id_seq TO "{app_user}"')
    print(f"[db] app user '{app_user}' grants refreshed")


async def _run_migrations() -> None:
    """Run 001 and 002 migrations (schema). 003 is run explicitly via lock_source_tables()."""
    pool     = get_admin_pool()
    sql_files = sorted(f for f in _MIGRATIONS_DIR.glob("*.sql") if not f.name.startswith("003"))
    async with pool.acquire() as conn:
        for path in sql_files:
            try:
                await conn.execute(path.read_text())
                print(f"[db] migration applied: {path.name}")
            except Exception as exc:
                print(f"[db] migration skipped ({path.name}): {exc}")
