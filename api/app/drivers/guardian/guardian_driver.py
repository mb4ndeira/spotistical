from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE_URL  = "https://content.guardianapi.com/search"
_PAGE_SIZE = 200

THEME_SECTIONS: dict[str, list[str]] = {
    "music":   ["music", "culture", "film", "tv-and-radio"],
    "sports":  ["sport"],
    "economy": ["business", "money", "world"],
}


class GuardianDriver:

    def _api_key(self) -> str:
        key = os.environ.get("GUARDIAN_API_KEY", "")
        if not key:
            raise RuntimeError("GUARDIAN_API_KEY env var is not set")
        return key

    async def fetch_articles(
        self,
        *,
        date_from: date,
        date_to: date,
        theme: str,
        client: httpx.AsyncClient,
        request_counter: list[int] | None = None,
        daily_limit: int = 490,
    ) -> list[dict[str, Any]]:
        sections = THEME_SECTIONS.get(theme, [theme])
        results: list[dict[str, Any]] = []

        for section in sections:
            page = 1
            while True:
                if request_counter is not None and request_counter[0] >= daily_limit:
                    logger.warning(
                        "GuardianDriver: limite diário atingido (%d req) — parando fetch",
                        daily_limit,
                    )
                    return results

                params = {
                    "section":     section,
                    "from-date":   date_from.isoformat(),
                    "to-date":     date_to.isoformat(),
                    "page-size":   str(_PAGE_SIZE),
                    "page":        str(page),
                    "order-by":    "newest",
                    "api-key":     self._api_key(),
                }
                try:
                    resp = await client.get(_BASE_URL, params=params, timeout=15)
                    if request_counter is not None:
                        request_counter[0] += 1
                    resp.raise_for_status()
                    data = resp.json().get("response", {})
                except Exception as exc:
                    logger.warning("GuardianDriver: %s/%s p%d — %s", theme, section, page, exc)
                    break

                for item in data.get("results", []):
                    pub = item.get("webPublicationDate", "")
                    results.append({
                        "published_at": pub[:19].replace("T", " ") if pub else None,
                        "title":        (item.get("webTitle") or "")[:1024],
                        "url":          (item.get("webUrl")   or "")[:2048],
                        "country":      None,
                        "tone":         None,
                        "source_lang":  "English",
                        "source":       "guardian",
                    })

                total_pages = data.get("pages", 1)
                logger.info(
                    "GuardianDriver: %s/%s p%d/%d — %d artigos  (req total: %d)",
                    theme, section, page, total_pages, len(data.get("results", [])),
                    request_counter[0] if request_counter else -1,
                )
                if page >= total_pages:
                    break
                page += 1

        return results


guardian_driver = GuardianDriver()
