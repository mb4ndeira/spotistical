from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from domain.use_cases.lyrics.fetch_lyrics_use_case import fetch_lyrics_uc, get_progress, request_stop

router = APIRouter(prefix="/lyrics", tags=["lyrics"])

_running = False


@router.post("/fetch")
async def fetch_lyrics(
    background_tasks: BackgroundTasks,
    retry_failed: bool = Query(
        False,
        description="Re-attempt tracks that previously returned 404 / timeout.",
    ),
):
    """
    Batch-fetch lyrics from lyrics.ovh for all unique tracks in the DB.

    Ordered by chart appearances DESC — most important tracks first.
    Skips tracks already in track_lyrics (idempotent, safe to re-run).
    Rate: ~2 req/sec (0.5s delay). ~25k tracks ≈ 3.5 hours.

    Watch progress: GET /lyrics/status
    """
    global _running
    if _running:
        raise HTTPException(409, "Lyrics fetch already running")

    async def _run():
        global _running
        _running = True
        try:
            result = await fetch_lyrics_uc.execute(retry_failed=retry_failed)
            print(f"[lyrics/fetch] done — {result}")
        finally:
            _running = False

    background_tasks.add_task(_run)
    return {
        "success": True,
        "message": "Lyrics fetch started — GET /lyrics/status for progress",
        "retry_failed": retry_failed,
    }


@router.get("/status")
async def lyrics_status():
    """
    Live progress of the lyrics fetch pipeline.

    stage         : idle | loading | fetching | done | error
    tracks_total  : tracks to process this run (excludes already-done)
    tracks_done   : processed so far (found + failed)
    tracks_found  : lyrics successfully retrieved
    tracks_failed : 404 / timeout / empty
    tracks_skipped: already in track_lyrics, not re-fetched
    current_track : track being fetched right now
    """
    return get_progress()


@router.post("/stop")
async def stop_lyrics_fetch():
    """Request a graceful stop of the running lyrics fetch."""
    if not get_progress()["running"]:
        raise HTTPException(400, "No fetch running")
    request_stop()
    return {"success": True, "message": "Stop requested — will finish in-flight requests then halt"}


@router.get("/coverage")
async def lyrics_coverage():
    """DB-level coverage summary — total rows, success rate, top fail reasons."""
    import drivers.db.db_driver as db_driver
    try:
        pool = db_driver.get_pool()
        async with pool.acquire() as conn:
            summary = await conn.fetchrow("""
                SELECT
                    count(*)                             AS total,
                    count(*) FILTER (WHERE NOT failed)  AS with_lyrics,
                    count(*) FILTER (WHERE failed)       AS without_lyrics,
                    round(
                        count(*) FILTER (WHERE NOT failed)::numeric
                        / nullif(count(*), 0) * 100, 1
                    )                                    AS coverage_pct
                FROM track_lyrics
            """)
            fail_reasons = await conn.fetch("""
                SELECT fail_reason, count(*) AS n
                FROM   track_lyrics
                WHERE  failed = TRUE
                GROUP  BY fail_reason
                ORDER  BY n DESC
                LIMIT  10
            """)
        return {
            "total":          summary["total"],
            "with_lyrics":    summary["with_lyrics"],
            "without_lyrics": summary["without_lyrics"],
            "coverage_pct":   summary["coverage_pct"],
            "fail_reasons":   [dict(r) for r in fail_reasons],
        }
    except Exception as exc:
        return {"error": str(exc)}
