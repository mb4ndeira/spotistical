from __future__ import annotations

import logging
from datetime import date
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_DATE_FMT = "%Y%m%d%H%M%S"

# Queries temáticas que cobrem os 3 drivers de charts:
#   1. entretenimento/música — causa direta de movimentação
#   2. esportes              — eventos correlacionam com comportamento de escuta
#   3. macro-economia        — driver de humor coletivo (Tier 3)
THEMES = [
    ("music",   "(music OR concert OR album OR singer OR band OR spotify OR streaming)"),
    ("sports",  "theme:SPORTS"),
    ("economy", "theme:ECON"),
]


class GdeltDriver:
    """Acessa o GDELT DOC API 2.0 — sem autenticação, sem limites publicados.

    Retorna até 250 artigos por request. Para backfill usa janelas semanais
    × 3 queries temáticas, com delay configurável entre requests.
    """

    async def fetch_articles(
        self,
        *,
        date_from: date,
        date_to: date,
        query: str,
        client: httpx.AsyncClient,
        max_records: int = 250,
    ) -> list[dict[str, Any]]:
        params = {
            "query":         query,
            "mode":          "ArtList",
            "maxrecords":    str(max_records),
            "format":        "json",
            "sort":          "DateDesc",
            "startdatetime": date_from.strftime(_DATE_FMT).replace(
                date_from.strftime("%H%M%S"), "000000"
            ),
            "enddatetime":   date_to.strftime(_DATE_FMT).replace(
                date_to.strftime("%H%M%S"), "235959"
            ),
        }

        logger.info("GdeltDriver: %s  %s → %s", query[:40], date_from, date_to)

        resp = await client.get(_BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        articles = data.get("articles") or []
        results = []
        for a in articles:
            seendate = a.get("seendate", "")
            try:
                from datetime import datetime
                pub = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ")
            except (ValueError, TypeError):
                continue
            results.append({
                "published_at": pub,
                "title":        (a.get("title") or "")[:1024],
                "url":          (a.get("url")   or "")[:2048],
                "country":      (a.get("sourcecountry") or "")[:2] or None,
                "tone":         float(a["tone"]) if a.get("tone") is not None else None,
                "source_lang":  a.get("language") or None,
            })

        logger.info("GdeltDriver: %d artigos recebidos", len(results))
        return results


gdelt_driver = GdeltDriver()
