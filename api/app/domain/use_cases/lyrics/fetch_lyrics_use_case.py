from __future__ import annotations

import asyncio
import os
from typing import Optional, TypedDict

import httpx

import drivers.db.db_driver as db_driver
from drivers.lyrics.lyrics_driver import fetch_lyrics

CONCURRENCY   = int(os.environ.get("LYRICS_CONCURRENCY",   "15"))
BATCH_SIZE    = int(os.environ.get("LYRICS_BATCH_SIZE",   "100"))


class LyricsProgress(TypedDict):
    running:        bool
    stage:          str
    tracks_total:   int
    tracks_done:    int
    tracks_found:   int
    tracks_failed:  int
    tracks_skipped: int
    current_track:  Optional[str]
    last_error:     Optional[str]


_progress: LyricsProgress = {
    "running":        False,
    "stage":          "idle",
    "tracks_total":   0,
    "tracks_done":    0,
    "tracks_found":   0,
    "tracks_failed":  0,
    "tracks_skipped": 0,
    "current_track":  None,
    "last_error":     None,
}

_stop_requested = False


def get_progress() -> LyricsProgress:
    return dict(_progress)


def request_stop() -> None:
    global _stop_requested
    _stop_requested = True


def _set(**kwargs) -> None:
    _progress.update(kwargs)


class FetchLyricsUseCase:

    async def execute(self, retry_failed: bool = False) -> dict:
        global _stop_requested
        _stop_requested = False
        _set(
            running=True, stage="loading", tracks_total=0, tracks_done=0,
            tracks_found=0, tracks_failed=0, tracks_skipped=0,
            current_track=None, last_error=None,
        )
        try:
            return await self._pipeline(retry_failed)
        except Exception as exc:
            _set(stage="error", last_error=str(exc))
            print(f"[lyrics/fetch] ERROR: {exc}")
            raise
        finally:
            _set(running=False, current_track=None)

    async def _pipeline(self, retry_failed: bool) -> dict:
        pool = db_driver.get_admin_pool()

        _set(stage="loading")
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT spotify_id, name, artists, appearances
                FROM (
                    SELECT spotify_id,
                           MIN(name)    AS name,
                           MIN(artists) AS artists,
                           COUNT(*)     AS appearances
                    FROM   tracks
                    GROUP  BY spotify_id
                ) t
                ORDER BY appearances DESC
            """)

        async with pool.acquire() as conn:
            done_rows = await conn.fetch("SELECT spotify_id, failed, fail_reason FROM track_lyrics")
        done = {r["spotify_id"]: (r["failed"], r["fail_reason"]) for r in done_rows}

        to_fetch, skipped = [], 0
        for r in rows:
            sid = r["spotify_id"]
            if sid in done:
                failed, reason = done[sid]
                if failed and reason == "connection_failed":
                    to_fetch.append(r)
                elif failed and retry_failed:
                    to_fetch.append(r)
                else:
                    skipped += 1
            else:
                to_fetch.append(r)

        _set(stage="fetching", tracks_total=len(to_fetch), tracks_skipped=skipped)
        print(f"[lyrics/fetch] {len(to_fetch):,} to fetch  ·  {skipped:,} skipped"
              f"  ·  concurrency={CONCURRENCY}")

        queue   = asyncio.Queue()
        for row in to_fetch:
            await queue.put(row)

        results: list[tuple] = []
        lock    = asyncio.Lock()

        async def worker(client: httpx.AsyncClient) -> None:
            while True:
                if _stop_requested:
                    return
                try:
                    row = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return

                sid     = row["spotify_id"]
                name    = row["name"]    or ""
                artists = row["artists"] or ""

                lyrics, source, fail_reason = await fetch_lyrics(client, artists, name)
                record = (sid, lyrics, None, source or "none", lyrics is None, fail_reason)

                async with lock:
                    results.append(record)
                    _set(
                        tracks_done    = _progress["tracks_done"] + 1,
                        tracks_found   = _progress["tracks_found"]  + (0 if lyrics is None else 1),
                        tracks_failed  = _progress["tracks_failed"] + (1 if lyrics is None else 0),
                        current_track  = f"{artists[:25]} — {name[:25]}",
                    )
                    if len(results) >= BATCH_SIZE:
                        to_flush = list(results)
                        results.clear()
                        await self._flush(to_flush, pool)
                        print(f"[lyrics/fetch] {_progress['tracks_done']:,}/{len(to_fetch):,}"
                              f"  found={_progress['tracks_found']:,}"
                              f"  failed={_progress['tracks_failed']:,}")

        async with httpx.AsyncClient(timeout=10) as client:
            workers = [asyncio.create_task(worker(client)) for _ in range(CONCURRENCY)]
            await asyncio.gather(*workers)

        if results:
            await self._flush(results, pool)

        summary = {
            "tracks_fetched": _progress["tracks_done"],
            "found":          _progress["tracks_found"],
            "failed":         _progress["tracks_failed"],
            "skipped":        skipped,
            "coverage_pct":   round(
                _progress["tracks_found"] / max(_progress["tracks_done"], 1) * 100, 1
            ),
            "stopped_early":  _stop_requested,
        }
        _set(stage="stopped" if _stop_requested else "done")
        print(f"[lyrics/fetch] complete — {summary}")
        return summary

    async def _flush(self, rows: list[tuple], pool) -> None:
        sql = """
            INSERT INTO track_lyrics
                (spotify_id, lyrics_raw, language, source, failed, fail_reason)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (spotify_id) DO UPDATE SET
                lyrics_raw  = EXCLUDED.lyrics_raw,
                language    = EXCLUDED.language,
                source      = EXCLUDED.source,
                failed      = EXCLUDED.failed,
                fail_reason = EXCLUDED.fail_reason,
                fetched_at  = NOW()
        """
        async with pool.acquire() as conn:
            await conn.executemany(sql, rows)


fetch_lyrics_uc = FetchLyricsUseCase()
