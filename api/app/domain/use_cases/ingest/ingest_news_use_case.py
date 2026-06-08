from __future__ import annotations

import asyncio
import json
import os
import random
from datetime import date, datetime, timedelta
from typing import TypedDict

import httpx

from drivers.db.db_driver import get_admin_pool
from drivers.gdelt_bulk.gdelt_bulk_driver import gdelt_bulk_driver, THEME_FILTERS
from drivers.guardian.guardian_driver import guardian_driver

_GUARDIAN_DELAY  = float(os.environ.get("GUARDIAN_REQUEST_DELAY", "0.5"))
_ALL_SOURCES     = {"gdelt_bulk"}

THEMES = list(THEME_FILTERS.keys())

_INSERT = """
    INSERT INTO news_events
        (published_at, title, url, country, tone, source_lang, topics, source)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    ON CONFLICT (url) DO NOTHING
"""

_SLOT_BATCH    = 48
_CONCURRENCY   = 20
_MAX_PER_DAY   = 30


class Progress(TypedDict):
    running:                    bool
    week_current:               str | None
    slot_current:               str | None
    slots_done:                 int
    slots_total:                int
    weeks_done:                 int
    weeks_total:                int
    weeks_skipped:              int
    articles_inserted_bulk:     int
    articles_inserted_guardian: int
    guardian_requests_today:    int
    guardian_daily_limit:       int
    last_error:                 str | None


_progress: Progress = {
    "running":                    False,
    "week_current":               None,
    "slot_current":               None,
    "slots_done":                 0,
    "slots_total":                0,
    "weeks_done":                 0,
    "weeks_total":                0,
    "weeks_skipped":              0,
    "articles_inserted_bulk":     0,
    "articles_inserted_guardian": 0,
    "guardian_requests_today":    0,
    "guardian_daily_limit":       490,
    "last_error":                 None,
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


def _parse_pub(a: dict) -> datetime | None:
    pub = a.get("published_at")
    if isinstance(pub, str):
        try:
            return datetime.fromisoformat(pub.replace("Z", "+00:00"))
        except ValueError:
            return None
    return pub


def _make_record(a: dict, theme_key: str, pub: datetime) -> tuple:
    return (
        pub,
        a["title"],
        a["url"],
        a.get("country"),
        a.get("tone"),
        a.get("source_lang"),
        json.dumps([theme_key]),
        a.get("source"),
    )


def _sample_into_reservoir(
    articles: list[dict],
    theme_key: str,
    reservoir: dict,
    seen: dict,
) -> None:
    for a in articles:
        pub = _parse_pub(a)
        if pub is None:
            continue
        key = (a.get("country"), theme_key, pub.date())
        seen[key] = seen.get(key, 0) + 1
        n = seen[key]
        record = _make_record(a, theme_key, pub)
        bucket = reservoir.setdefault(key, [])
        if len(bucket) < _MAX_PER_DAY:
            bucket.append(record)
        else:
            j = random.randint(0, n - 1)
            if j < _MAX_PER_DAY:
                bucket[j] = record


async def _flush_reservoir(reservoir: dict, pool) -> int:
    records = [r for bucket in reservoir.values() for r in bucket]
    if not records:
        return 0
    async with pool.acquire() as conn:
        await conn.executemany(_INSERT, records)
    return len(records)


async def _insert_articles(articles: list[dict], theme_key: str, pool) -> int:
    if not articles:
        return 0
    records = []
    for a in articles:
        pub = _parse_pub(a)
        if pub is None:
            continue
        records.append(_make_record(a, theme_key, pub))
    if not records:
        return 0
    async with pool.acquire() as conn:
        await conn.executemany(_INSERT, records)
    return len(records)


class IngestNewsUseCase:

    async def execute(
        self,
        date_from: date,
        date_to: date,
        sources: set[str] | None = None,
        guardian_daily_limit: int = 490,
    ) -> dict:
        global _progress

        active_sources = sources if sources is not None else _ALL_SOURCES
        pool  = get_admin_pool()
        weeks = _weeks_in_range(date_from, date_to)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT week_start FROM news_ingested_weeks
                   WHERE week_start BETWEEN $1 AND $2""",
                date_from, date_to,
            )
        covered_weeks = {r["week_start"] for r in rows}

        guardian_req_counter: list[int] = [0]

        all_slots = (
            gdelt_bulk_driver.slot_timestamps(date_from, date_to)
            if "gdelt_bulk" in active_sources else []
        )

        _progress.update({
            "running":                    True,
            "weeks_total":                len(weeks),
            "weeks_done":                 0,
            "weeks_skipped":              len([w for w in weeks if w in covered_weeks]),
            "slots_total":                len(all_slots),
            "slots_done":                 0,
            "articles_inserted_bulk":     0,
            "articles_inserted_guardian": 0,
            "guardian_requests_today":    0,
            "guardian_daily_limit":       guardian_daily_limit,
            "week_current":               None,
            "slot_current":               None,
            "last_error":                 None,
        })

        sem = asyncio.Semaphore(_CONCURRENCY)

        limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
        async with httpx.AsyncClient(timeout=30, limits=limits) as client:
            for week in weeks:
                if week in covered_weeks:
                    _progress["weeks_done"] += 1
                    continue

                w_end = min(_week_end(week), date_to)
                _progress["week_current"] = str(week)

                if "gdelt_bulk" in active_sources:
                    await self._fetch_bulk_week(week, w_end, client, pool, sem, include_translations=True)

                if (
                    "guardian" in active_sources
                    and guardian_req_counter[0] < guardian_daily_limit
                ):
                    guardian_tasks = [
                        self._fetch_guardian(
                            week, w_end, theme_key, client, pool,
                            guardian_req_counter, guardian_daily_limit,
                        )
                        for theme_key in THEMES
                    ]
                    results = await asyncio.gather(*guardian_tasks, return_exceptions=True)
                    for r in results:
                        if isinstance(r, Exception):
                            _progress["last_error"] = str(r)
                    _progress["guardian_requests_today"] = guardian_req_counter[0]

                await self._register_week(week, w_end, pool)

                _progress["weeks_done"] += 1

        _progress.update({"running": False, "week_current": None})
        return {
            "success":                    True,
            "date_from":                  str(date_from),
            "date_to":                    str(date_to),
            "sources":                    sorted(active_sources),
            "weeks_processed":            _progress["weeks_done"],
            "weeks_skipped":              _progress["weeks_skipped"],
            "articles_inserted_bulk":     _progress["articles_inserted_bulk"],
            "articles_inserted_guardian": _progress["articles_inserted_guardian"],
            "guardian_requests_today":    _progress["guardian_requests_today"],
        }

    async def _register_week(self, week: date, w_end: date, pool) -> None:
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT count(*) FROM news_events WHERE published_at::date BETWEEN $1 AND $2",
                week, w_end,
            )
            await conn.execute("""
                INSERT INTO news_ingested_weeks
                    (week_start, articles_before_curation, articles_after_curation)
                VALUES ($1, $2, $2)
                ON CONFLICT (week_start) DO NOTHING
            """, week, count)

    async def _fetch_bulk_week(
        self, week: date, w_end: date,
        client: httpx.AsyncClient, pool,
        sem: asyncio.Semaphore,
        include_translations: bool = False,
    ) -> None:
        slots = gdelt_bulk_driver.slot_timestamps(week, w_end)

        slots_by_day: dict[date, list[str]] = {}
        for s in slots:
            d = date(int(s[:4]), int(s[4:6]), int(s[6:8]))
            slots_by_day.setdefault(d, []).append(s)

        for day, day_slots in sorted(slots_by_day.items()):
            reservoir: dict = {}
            seen: dict = {}

            for i in range(0, len(day_slots), _SLOT_BATCH):
                batch = day_slots[i : i + _SLOT_BATCH]
                _progress["slot_current"] = batch[0]

                theme_tasks = [
                    gdelt_bulk_driver.fetch_slot_batch(
                        slots=batch, theme_key=tk,
                        client=client, sem=sem,
                        include_translations=include_translations,
                    )
                    for tk in THEMES
                ]
                try:
                    per_theme = await asyncio.gather(*theme_tasks, return_exceptions=True)
                except Exception as exc:
                    _progress["last_error"] = f"gdelt_bulk batch {batch[0]}: {exc}"
                    await asyncio.sleep(0)
                    continue

                for tk, result in zip(THEMES, per_theme):
                    if isinstance(result, Exception):
                        _progress["last_error"] = f"gdelt_bulk {tk} {batch[0]}: {result}"
                        continue
                    _sample_into_reservoir(result, tk, reservoir, seen)

                _progress["slots_done"] += len(batch)
                buffered = sum(len(v) for v in reservoir.values())
                print(
                    f"[news-ingest] {day}  slots {i+len(batch)}/{len(day_slots)}"
                    f"  buffered={buffered:,}"
                )
                await asyncio.sleep(0)

            n = await _flush_reservoir(reservoir, pool)
            _progress["articles_inserted_bulk"] += n
            print(f"[news-ingest] {day} — inserted {n:,} articles")

    async def _fetch_guardian(
        self, week: date, w_end: date, theme_key: str,
        client: httpx.AsyncClient, pool,
        request_counter: list[int] | None = None,
        daily_limit: int = 490,
    ) -> None:
        try:
            articles = await guardian_driver.fetch_articles(
                date_from=week, date_to=w_end, theme=theme_key, client=client,
                request_counter=request_counter, daily_limit=daily_limit,
            )
            n = await _insert_articles(articles, theme_key, pool)
            _progress["articles_inserted_guardian"] += n
            if n:
                print(f"[news-ingest] guardian   {week} / {theme_key} — {n} artigos")
        except RuntimeError as exc:
            _progress["last_error"] = str(exc)
        except Exception as exc:
            _progress["last_error"] = f"guardian {week}/{theme_key}: {exc}"
        finally:
            await asyncio.sleep(_GUARDIAN_DELAY + random.uniform(0, 0.5))


ingest_news_uc = IngestNewsUseCase()
