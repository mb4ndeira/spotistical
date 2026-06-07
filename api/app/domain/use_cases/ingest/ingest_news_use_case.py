from __future__ import annotations

import asyncio
import json
import os
from datetime import date, datetime, timedelta
from typing import TypedDict

import httpx

from drivers.db.db_driver import get_admin_pool

_API_KEY  = lambda: os.environ.get("ALPHA_VANTAGE_API_KEY", "")
_BASE_URL = "https://www.alphavantage.co/query"
_DELAY    = float(os.environ.get("AV_REQUEST_DELAY", "13"))  # seconds between requests

# 3 topics most predictive of chart movement (trimmed from 7)
TOPICS = [
    "entertainment",   # concerts, album drops, film releases — direct cause
    "sports",          # major events correlate with listening behaviour
    "economy_macro",   # collective mood driver for Tier 3
]

_INSERT = """
    INSERT INTO news_events (published_at, title, url, overall_sentiment_score, overall_sentiment_label, topics)
    VALUES ($1, $2, $3, $4, $5, $6)
    ON CONFLICT (url) DO NOTHING
"""


class Progress(TypedDict):
    running:           bool
    week_current:      str | None   # ISO week start date
    weeks_done:        int
    weeks_total:       int
    weeks_skipped:     int          # already had data
    articles_inserted: int
    last_error:        str | None


# Module-level state — read by the status endpoint at any time
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
    """Return the Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


def _week_end(week_monday: date) -> date:
    return week_monday + timedelta(days=6)


def _weeks_in_range(date_from: date, date_to: date) -> list[date]:
    """All week-start Mondays whose window overlaps [date_from, date_to]."""
    weeks = []
    w = _week_start(date_from)
    while w <= date_to:
        weeks.append(w)
        w += timedelta(weeks=1)
    return weeks


class IngestNewsUseCase:
    """Backfill news_events from Alpha Vantage NEWS_SENTIMENT API.

    Granularity : weekly windows (Mon–Sun), 3 topics per week.
    Incremental : skips weeks that already have any articles in the DB.
    Idempotent  : ON CONFLICT (url) DO NOTHING — safe to re-run at any time.
    Observable  : module-level _progress dict updated continuously.
    Non-blocking: runs as a FastAPI BackgroundTask; pipeline can use
                  whatever is already in news_events while this runs.
    """

    async def execute(self, date_from: date, date_to: date) -> dict:
        global _progress

        key = _API_KEY()
        if not key:
            _progress["last_error"] = "ALPHA_VANTAGE_API_KEY not set"
            return {"success": False, "error": _progress["last_error"]}

        pool  = get_admin_pool()
        weeks = _weeks_in_range(date_from, date_to)

        # Which weeks already have at least one article?
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

                time_from = week.strftime("%Y%m%dT0000")
                time_to   = w_end.strftime("%Y%m%dT2359")

                for topic in TOPICS:
                    params = {
                        "function":  "NEWS_SENTIMENT",
                        "apikey":    key,
                        "topics":    topic,
                        "time_from": time_from,
                        "time_to":   time_to,
                        "limit":     "1000",
                        "sort":      "RELEVANCE",
                    }
                    try:
                        resp = await client.get(_BASE_URL, params=params)
                        resp.raise_for_status()
                        data = resp.json()
                    except Exception as exc:
                        msg = f"{week} / {topic}: {exc}"
                        print(f"[news-ingest] request failed — {msg}")
                        _progress["last_error"] = msg
                        await asyncio.sleep(_DELAY)
                        continue

                    records = []
                    for a in data.get("feed", []):
                        try:
                            pub_dt = datetime.strptime(a["time_published"], "%Y%m%dT%H%M%S")
                            records.append((
                                pub_dt,
                                a.get("title", "")[:1024],
                                a.get("url",   "")[:2048],
                                float(a.get("overall_sentiment_score", 0) or 0),
                                a.get("overall_sentiment_label", ""),
                                json.dumps(a.get("topics", [])),
                            ))
                        except Exception:
                            continue

                    if records:
                        async with pool.acquire() as conn:
                            await conn.executemany(_INSERT, records)
                        _progress["articles_inserted"] += len(records)
                        print(
                            f"[news-ingest] {week} / {topic}"
                            f" — {len(records)} articles"
                            f" (total: {_progress['articles_inserted']:,})"
                        )

                    await asyncio.sleep(_DELAY)

                _progress["weeks_done"] += 1

        _progress.update({"running": False, "week_current": None})
        return {
            "success":         True,
            "date_from":       str(date_from),
            "date_to":         str(date_to),
            "weeks_processed": _progress["weeks_done"],
            "weeks_skipped":   _progress["weeks_skipped"],
            "articles_inserted": _progress["articles_inserted"],
        }


ingest_news_uc = IngestNewsUseCase()
