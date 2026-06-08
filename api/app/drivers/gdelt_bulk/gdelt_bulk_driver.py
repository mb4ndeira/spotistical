from __future__ import annotations

import asyncio
import concurrent.futures
import csv
import io
import logging
import re
import sys
import zipfile
from datetime import date, datetime, timedelta
from typing import Any

import httpx

csv.field_size_limit(min(sys.maxsize, 10_000_000))

logger = logging.getLogger(__name__)

_BASE = "http://data.gdeltproject.org/gdeltv2"

THEME_FILTERS: dict[str, list[str]] = {
    "music":   ["TAX_FNCACT_MUSIC", "ARTS_MUSIC", "SOC_MUSIC",
                "TAX_FNCACT_SINGER", "TAX_FNCACT_BAND", "ARTS_PERFORMING_ARTS"],
    "sports":  ["SPORTS"],
    "economy": ["ECON_", "EPU_CATS", "BUS_MARKET", "BUS_STOCK"],
}

SPOTIFY_COUNTRIES: frozenset[str] = frozenset({
    "AE", "AR", "AT", "AU", "BE", "BG", "BO", "BR", "BY", "CA",
    "CH", "CL", "CO", "CR", "CZ", "DE", "DK", "DO", "EC", "EE",
    "EG", "ES", "FI", "FR", "GB", "GR", "GT", "HK", "HN", "HU",
    "ID", "IE", "IL", "IN", "IS", "IT", "JP", "KR", "KZ", "LT",
    "LU", "LV", "MA", "MX", "MY", "NG", "NI", "NL", "NO", "NZ",
    "PA", "PE", "PH", "PK", "PL", "PT", "PY", "RO", "SA", "SE",
    "SG", "SK", "SV", "TH", "TR", "TW", "UA", "US", "UY", "VE",
    "VN", "ZA",
})

_executor = concurrent.futures.ProcessPoolExecutor(max_workers=6)


def _slot_timestamps(date_from: date, date_to: date) -> list[str]:
    slots: list[str] = []
    cur = datetime(date_from.year, date_from.month, date_from.day, 0, 0, 0)
    end = datetime(date_to.year, date_to.month, date_to.day, 23, 45, 0)
    while cur <= end:
        slots.append(cur.strftime("%Y%m%d%H%M%S"))
        cur += timedelta(minutes=15)
    return slots


def _parse_tone(tone_str: str) -> float | None:
    try:
        return float(tone_str.split(",")[0])
    except (ValueError, IndexError):
        return None


def _parse_country(v2locations: str) -> str | None:
    for loc in v2locations.split(";"):
        parts = loc.split("#")
        if len(parts) >= 3 and parts[2]:
            cc = parts[2].upper()
            if cc in SPOTIFY_COUNTRIES:
                return cc
    return None


def _parse_gkg_row_all_themes(
    row: list[str],
    source_lang: str | None,
) -> dict[str, dict[str, Any]]:
    if len(row) < 16:
        return {}

    country = _parse_country(row[9]) if len(row) > 9 else None
    if country is None:
        return {}

    title_m = re.search(r'<PAGE_TITLE>(.*?)</PAGE_TITLE>', row[-1])
    if not title_m:
        return {}
    title = title_m.group(1).strip()[:1024]
    if not title:
        return {}

    try:
        pub = datetime.strptime(row[1][:14], "%Y%m%d%H%M%S")
    except (ValueError, TypeError):
        return {}

    url = (row[4] or "").strip()[:2048]
    if not url:
        return {}

    themes_str = row[7]
    article = {
        "published_at": pub,
        "title":        title,
        "url":          url,
        "country":      country,
        "tone":         _parse_tone(row[15]),
        "source_lang":  source_lang,
        "source":       "gdelt_bulk",
    }

    matched: dict[str, dict[str, Any]] = {}
    for theme_key, codes in THEME_FILTERS.items():
        if any(f in themes_str for f in codes):
            matched[theme_key] = article
    return matched


def _parse_zip_bytes(content: bytes, source_lang: str | None) -> dict[str, list[dict]]:
    try:
        zf  = zipfile.ZipFile(io.BytesIO(content))
        raw = zf.read(zf.namelist()[0]).decode("utf-8", errors="replace")
    except Exception:
        return {}

    results: dict[str, list] = {k: [] for k in THEME_FILTERS}
    lang = source_lang
    for row in csv.reader(io.StringIO(raw), delimiter="\t"):
        if source_lang is None and len(row) > 25 and row[25]:
            m = re.search(r'srclang:([a-z]{2,3})', row[25])
            lang = m.group(1) if m else None
        for theme_key, article in _parse_gkg_row_all_themes(row, lang).items():
            results[theme_key].append(article)
    return results


async def _download_and_parse_all(
    url: str,
    source_lang: str | None,
    client: httpx.AsyncClient,
    timeout: float = 15,
) -> dict[str, list[dict[str, Any]]]:
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
    except httpx.TimeoutException:
        logger.warning("GdeltBulk timeout: %s", url[-50:])
        return {}
    except Exception as exc:
        logger.debug("GdeltBulk error: %s — %s", url[-50:], exc)
        return {}

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _parse_zip_bytes, resp.content, source_lang)


class GdeltBulkDriver:

    async def fetch_slot_batch(
        self,
        *,
        slots: list[str],
        client: httpx.AsyncClient,
        include_translations: bool = True,
        sem: asyncio.Semaphore,
    ) -> dict[str, list[dict[str, Any]]]:

        async def _one(ts: str) -> dict[str, list[dict[str, Any]]]:
            english_url = f"{_BASE}/{ts}.gkg.csv.zip"
            tasks = [_download_and_parse_all(english_url, "English", client, timeout=15)]
            if include_translations:
                trans_url = f"{_BASE}/{ts}.translation.gkg.csv.zip"
                tasks.append(_download_and_parse_all(trans_url, None, client, timeout=8))
            async with sem:
                parts = await asyncio.gather(*tasks, return_exceptions=True)
            merged: dict[str, list] = {k: [] for k in THEME_FILTERS}
            for p in parts:
                if isinstance(p, dict):
                    for k, articles in p.items():
                        merged[k].extend(articles)
            return merged

        slot_results = await asyncio.gather(*[_one(ts) for ts in slots])

        combined: dict[str, list] = {k: [] for k in THEME_FILTERS}
        for slot_result in slot_results:
            for k, articles in slot_result.items():
                combined[k].extend(articles)
        return combined

    def slot_timestamps(self, date_from: date, date_to: date) -> list[str]:
        return _slot_timestamps(date_from, date_to)


gdelt_bulk_driver = GdeltBulkDriver()
