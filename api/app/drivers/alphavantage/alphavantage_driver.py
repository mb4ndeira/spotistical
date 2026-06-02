from __future__ import annotations

import json
import logging
import os
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.alphavantage.co/query"
_AV_FMT = "%Y%m%dT%H%M%S"


class AlphaVantageDriver:
    def _api_key(self) -> str:
        key = os.environ.get("ALPHA_VANTAGE_API_KEY", "")
        if not key:
            raise RuntimeError("ALPHA_VANTAGE_API_KEY env var is not set")
        return key

    def fetch_news(
        self,
        *,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
        topics: list[str] | None = None,
        limit: int = 200,
    ) -> list[dict]:
        params: dict = {
            "function": "NEWS_SENTIMENT",
            "sort": "LATEST",
            "limit": min(limit, 1000),
            "apikey": self._api_key(),
        }
        if time_from:
            params["time_from"] = time_from.strftime(_AV_FMT)
        if time_to:
            params["time_to"] = time_to.strftime(_AV_FMT)
        if topics:
            params["topics"] = ",".join(topics)

        logger.info("AlphaVantageDriver: fetching news (limit=%d, topics=%s)", limit, topics)

        with httpx.Client(timeout=30) as client:
            resp = client.get(_BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        feed = data.get("feed", [])
        results = []
        for item in feed:
            results.append({
                "published_at": datetime.strptime(item["time_published"], _AV_FMT),
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "summary": item.get("summary"),
                "source": item.get("source", ""),
                "source_domain": item.get("source_domain", ""),
                "topics": json.dumps(item.get("topics", [])),
                "overall_sentiment_score": item.get("overall_sentiment_score"),
                "overall_sentiment_label": item.get("overall_sentiment_label"),
            })

        logger.info("AlphaVantageDriver: received %d articles", len(results))
        return results


alphavantage_driver = AlphaVantageDriver()
