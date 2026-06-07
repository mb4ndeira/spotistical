from __future__ import annotations

import asyncio
import json
import os
from datetime import date, timedelta
from typing import TypedDict

import httpx

from drivers.db.db_driver import get_admin_pool
from drivers.gdelt.gdelt_driver import THEMES, gdelt_driver

_DELAY = float(os.environ.get("GDELT_REQUEST_DELAY", "5"))  # GDELT: 1 req/5s documentado

_INSERT = """
    INSERT INTO news_events (published_at, title, url, country, tone, source_lang, topics)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    ON CONFLICT (url) DO NOTHING
"""


class Progress(TypedDict):
    running:           bool
    week_current:      str | None
    weeks_done:        int
    weeks_total:       int
    weeks_skipped:     int
    articles_inserted: int
    last_error:        str | None


_progress: Progress = {
    "running":           False,
    "week_current":      None,
    "weeks_done":        0,
    "weeks_total":       0,
    "weeks_skipped":     0,
    "articles_inserted": 0,
    "last_error":        None,
}


def get_progress() -> Progress:
    return dict(_progress)  # type: ignore[return-value]


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _week_end(w: date) -> date:
    return w + timedelta(days=6)


def _weeks_in_range(date_from: date, date_to: date) -> list[date]:
    weeks, w = [], _week_start(date_from)
    while w <= date_to:
        weeks.append(w)
        w += timedelta(weeks=1)
    return weeks


class IngestNewsUseCase:
    """Backfill news_events via GDELT DOC API 2.0.

    Granularity : weekly windows (Mon–Sun), 3 queries temáticas por semana.
    Incremental : pula semanas que já têm artigos no banco.
    Idempotent  : ON CONFLICT (url) DO NOTHING.
    Observable  : _progress dict atualizado continuamente.
    """

    async def execute(self, date_from: date, date_to: date) -> dict:
        global _progress

        pool  = get_admin_pool()
        weeks = _weeks_in_range(date_from, date_to)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT DISTINCT date_trunc('week', published_at)::date AS w
                   FROM news_events
                   WHERE published_at::date BETWEEN $1 AND $2""",
                date_from, date_to,
            )
        covered_weeks = {r["w"] for r in rows}

        _progress.update({
            "running":           True,
            "weeks_total":       len(weeks),
            "weeks_done":        0,
            "weeks_skipped":     len([w for w in weeks if w in covered_weeks]),
            "articles_inserted": 0,
            "week_current":      None,
            "last_error":        None,
        })

        async with httpx.AsyncClient(timeout=30) as client:
            for week in weeks:
                if week in covered_weeks:
                    _progress["weeks_done"] += 1
                    continue

                w_end = min(_week_end(week), date_to)
                _progress["week_current"] = str(week)

                for theme_key, theme_query in THEMES:
                    try:
                        articles = await gdelt_driver.fetch_articles(
                            date_from=week,
                            date_to=w_end,
                            query=theme_query,
                            client=client,
                        )
                    except Exception as exc:
                        msg = f"{week} / {theme_key}: {exc}"
                        print(f"[news-ingest] request failed — {msg}")
                        _progress["last_error"] = msg
                        await asyncio.sleep(_DELAY)
                        continue

                    records = [
                        (
                            a["published_at"],
                            a["title"],
                            a["url"],
                            a["country"],
                            a["tone"],
                            a["source_lang"],
                            json.dumps([theme_key]),
                        )
                        for a in articles
                    ]

                    if records:
                        async with pool.acquire() as conn:
                            await conn.executemany(_INSERT, records)
                        _progress["articles_inserted"] += len(records)
                        print(
                            f"[news-ingest] {week} / {theme_key}"
                            f" — {len(records)} artigos"
                            f" (total: {_progress['articles_inserted']:,})"
                        )

                    await asyncio.sleep(_DELAY)

                _progress["weeks_done"] += 1

        _progress.update({"running": False, "week_current": None})
        return {
            "success":           True,
            "date_from":         str(date_from),
            "date_to":           str(date_to),
            "weeks_processed":   _progress["weeks_done"],
            "weeks_skipped":     _progress["weeks_skipped"],
            "articles_inserted": _progress["articles_inserted"],
        }


ingest_news_uc = IngestNewsUseCase()
