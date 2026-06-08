from __future__ import annotations

import asyncio
import json
import os
import random
from datetime import date, timedelta
from typing import TypedDict

import httpx

from drivers.db.db_driver import get_admin_pool
from drivers.gdelt_bulk.gdelt_bulk_driver import gdelt_bulk_driver, THEME_FILTERS
from drivers.guardian.guardian_driver import guardian_driver

_GUARDIAN_DELAY  = float(os.environ.get("GUARDIAN_REQUEST_DELAY", "0.5"))
_ALL_SOURCES     = {"gdelt_bulk"}

# Temas a ingerir — chaves têm que existir em THEME_FILTERS e THEME_SECTIONS
THEMES = list(THEME_FILTERS.keys())  # ["music", "sports", "economy"]

_INSERT = """
    INSERT INTO news_events
        (published_at, title, url, country, tone, source_lang, topics, source)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    ON CONFLICT (url) DO NOTHING
"""


_SLOT_BATCH   = 48   # slots por batch (~12h de dados)
_CONCURRENCY  = 20   # downloads paralelos — dentro do pool de conexões httpx


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


async def _insert_articles(articles: list[dict], theme_key: str, pool) -> int:
    if not articles:
        return 0
    from datetime import datetime
    records = []
    for a in articles:
        pub = a.get("published_at")
        if isinstance(pub, str):
            try:
                pub = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            except ValueError:
                continue
        if pub is None:
            continue
        records.append((
            pub,
            a["title"],
            a["url"],
            a.get("country"),
            a.get("tone"),
            a.get("source_lang"),
            json.dumps([theme_key]),
            a.get("source"),
        ))
    if not records:
        return 0
    async with pool.acquire() as conn:
        await conn.executemany(_INSERT, records)
    return len(records)


class IngestNewsUseCase:
    """Backfill news_events via GDELT Bulk (primário) + Guardian (secundário).

    GDELT Bulk:
    - Sem rate limit — baixa arquivos GKG de 15 em 15 minutos diretamente
    - Multilingual (inglês + arquivos de tradução)
    - Tone nativo, cobertura global

    Guardian:
    - Inglês, alta qualidade editorial
    - 500 req/dia free — para graciosamente ao atingir guardian_daily_limit
    - Complementa GDELT com publicações premium não indexadas

    Semanas com GDELT bulk já no banco são puladas.
    ON CONFLICT (url) DO NOTHING — sem duplicatas entre fontes.
    """

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

        # semana coberta = GDELT bulk já passou por ela (quando gdelt_bulk ativo)
        if "gdelt_bulk" in active_sources:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT DISTINCT date_trunc('week', published_at)::date AS w
                       FROM news_events
                       WHERE published_at::date BETWEEN $1 AND $2
                         AND source = 'gdelt_bulk'""",
                    date_from, date_to,
                )
            covered_weeks = {r["w"] for r in rows}
        else:
            covered_weeks = set()

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

                # GDELT Bulk — processa em batches de slots, insere e atualiza progresso a cada batch
                if "gdelt_bulk" in active_sources:
                    await self._fetch_bulk_week(week, w_end, client, pool, sem, include_translations=True)

                # Guardian — por tema, para se atingiu o limite
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

                # Curadoria pós-semana: mantém até 200 artigos por (country, theme)
                # distribuídos proporcionalmente por dia via amostragem estratificada
                deleted = await self._curate_week(week, w_end, pool)
                if deleted:
                    print(f"[news-ingest] curadoria {week} — {deleted:,} artigos removidos")

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

    async def _curate_week(self, week: date, w_end: date, pool, max_per_group: int = 200) -> int:
        """Amostragem estratificada por dia: mantém até max_per_group artigos por (country, theme).

        Cada dia recebe floor(200 * day_count / week_count) slots — proporcional ao volume.
        Dentro de cada dia a seleção é aleatória (ORDER BY random()).
        Artigos sem country são descartados integralmente (não há como associar ao Spotify).
        """
        async with pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM news_events
                WHERE published_at::date BETWEEN $1 AND $2
                  AND id IN (
                    SELECT id FROM (
                      SELECT id,
                             ROW_NUMBER() OVER (
                               PARTITION BY country,
                                            topics::text,
                                            published_at::date
                               ORDER BY random()
                             )                              AS rn_day,
                             COUNT(*) OVER (
                               PARTITION BY country, topics::text, published_at::date
                             )                              AS day_count,
                             COUNT(*) OVER (
                               PARTITION BY country, topics::text
                             )                              AS week_count
                      FROM news_events
                      WHERE published_at::date BETWEEN $1 AND $2
                        AND country IS NOT NULL
                    ) ranked
                    WHERE rn_day > CEIL($3::numeric * day_count::numeric / week_count::numeric)

                    UNION ALL

                    -- artigos sem país: descarta todos
                    SELECT id FROM news_events
                    WHERE published_at::date BETWEEN $1 AND $2
                      AND country IS NULL
                  )
            """, week, w_end, max_per_group)
        # result é string "DELETE N"
        try:
            return int(result.split()[-1])
        except (ValueError, IndexError):
            return 0

    async def _fetch_bulk_week(
        self, week: date, w_end: date,
        client: httpx.AsyncClient, pool,
        sem: asyncio.Semaphore,
        include_translations: bool = False,
    ) -> None:
        """Processa uma semana em batches de slots — insere e reporta progresso a cada batch."""
        slots = gdelt_bulk_driver.slot_timestamps(week, w_end)

        for i in range(0, len(slots), _SLOT_BATCH):
            batch = slots[i : i + _SLOT_BATCH]
            _progress["slot_current"] = batch[0]

            # todos os temas em paralelo dentro do batch
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
                continue

            for tk, result in zip(THEMES, per_theme):
                if isinstance(result, Exception):
                    _progress["last_error"] = f"gdelt_bulk {tk} {batch[0]}: {result}"
                    continue
                n = await _insert_articles(result, tk, pool)
                _progress["articles_inserted_bulk"] += n

            _progress["slots_done"] += len(batch)
            print(
                f"[news-ingest] gdelt_bulk {week}  slots {i+len(batch)}/{len(slots)}"
                f"  total={_progress['articles_inserted_bulk']:,}"
            )

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
