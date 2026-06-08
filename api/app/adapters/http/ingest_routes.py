from __future__ import annotations

from datetime import date

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from domain.use_cases.ingest.ingest_tracks_use_case import ingest_tracks_uc
from domain.use_cases.ingest.ingest_news_use_case   import ingest_news_uc, get_progress
import drivers.db.db_driver as db_driver

router = APIRouter(prefix="/ingest", tags=["ingest"])

_tracks_running = False
_news_running   = False


# ── Tracks ────────────────────────────────────────────────────────

@router.post("/tracks")
async def ingest_tracks(background_tasks: BackgroundTasks):
    """Load spotify_processed.parquet → tracks hypertable.

    Runs in the background. Safe to re-run (ON CONFLICT DO NOTHING).
    Source table — no modifications allowed after just lock-sources is run.
    """
    global _tracks_running
    if _tracks_running:
        raise HTTPException(409, "Tracks ingest already running")

    async def _run():
        global _tracks_running
        _tracks_running = True
        try:
            result = await ingest_tracks_uc.execute()
            print(f"[ingest/tracks] complete — {result}")
        finally:
            _tracks_running = False

    background_tasks.add_task(_run)
    return {"success": True, "message": "Tracks ingest started — watch logs with: just logs-svc api"}


@router.get("/tracks/status")
async def tracks_status():
    return {"running": _tracks_running}


# ── News ──────────────────────────────────────────────────────────

_VALID_SOURCES = {"gdelt_bulk", "guardian"}


@router.post("/news")
async def ingest_news(
    background_tasks: BackgroundTasks,
    date_from:             date      = Query(...,  description="Start date YYYY-MM-DD"),
    date_to:               date      = Query(...,  description="End date   YYYY-MM-DD"),
    sources:               list[str] = Query(default=["gdelt_bulk"],
                                             description="Fontes: gdelt_bulk (padrão), guardian (opcional)"),
    guardian_daily_limit:  int       = Query(default=490,
                                             description="Máx. requests Guardian por dia (teto free tier: 500)"),
):
    """Backfill news_events via fontes configuráveis.

    - **gdelt_bulk** (primário, padrão): arquivos GKG brutos, sem rate limit, multilingual, tone nativo.
    - **guardian** (secundário, padrão): inglês, alta qualidade, 500 req/dia. Requer GUARDIAN_API_KEY.

    Incremental — semanas com gdelt_bulk já no banco são puladas.
    Safe to re-run (ON CONFLICT (url) DO NOTHING).
    """
    global _news_running
    if _news_running:
        raise HTTPException(409, "News ingest already running")
    if date_from > date_to:
        raise HTTPException(400, "date_from must be <= date_to")

    invalid = set(sources) - _VALID_SOURCES
    if invalid:
        raise HTTPException(400, f"Fontes inválidas: {sorted(invalid)}. Válidas: {sorted(_VALID_SOURCES)}")

    active = set(sources)

    async def _run():
        global _news_running
        _news_running = True
        try:
            result = await ingest_news_uc.execute(
                date_from, date_to,
                sources=active,
                guardian_daily_limit=guardian_daily_limit,
            )
            print(f"[ingest/news] complete — {result}")
        finally:
            _news_running = False

    background_tasks.add_task(_run)
    return {
        "success": True,
        "sources": sorted(active),
        "message": f"News backfill started ({date_from} → {date_to}) — watch logs with: just logs-svc api",
    }


@router.get("/news/status")
async def news_status():
    """Live progress + DB coverage summary."""
    progress = get_progress()

    # Coverage summary straight from the DB
    try:
        pool = db_driver.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT
                       count(*)                          AS total_articles,
                       count(DISTINCT published_at::date) AS days_covered,
                       min(published_at)::date           AS earliest,
                       max(published_at)::date           AS latest
                   FROM news_events"""
            )
        coverage = {
            "total_articles": row["total_articles"],
            "days_covered":   row["days_covered"],
            "earliest":       str(row["earliest"]) if row["earliest"] else None,
            "latest":         str(row["latest"])   if row["latest"]   else None,
        }
    except Exception:
        coverage = None

    return {**progress, "db_coverage": coverage}


# ── Lock ──────────────────────────────────────────────────────────

@router.post("/lock-sources")
async def lock_sources():
    """Apply source table protection after ingest is complete.

    Installs DB triggers that block UPDATE/DELETE on tracks and news_events
    for all users, and restricts the app user to SELECT-only on those tables.

    Run once after both ingest/tracks and ingest/news are finished.
    Idempotent — safe to call multiple times.
    """
    if _tracks_running or _news_running:
        raise HTTPException(409, "Cannot lock while an ingest is running")
    await db_driver.lock_source_tables()
    return {"success": True, "message": "Source tables locked — tracks and news_events are now read-only"}
