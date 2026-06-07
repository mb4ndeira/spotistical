from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from drivers.db.db_driver import get_pool

logger = logging.getLogger(__name__)


class NewsRepository:
    def list(
        self,
        time_from: Optional[datetime] = None,
        time_to: Optional[datetime] = None,
        country: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._list_async(time_from=time_from, time_to=time_to, country=country, limit=limit)
        )

    async def _list_async(
        self,
        time_from: Optional[datetime],
        time_to: Optional[datetime],
        country: Optional[str],
        limit: int,
    ) -> list[dict]:
        pool = get_pool()
        conditions = []
        params: list = []

        if time_from:
            params.append(time_from)
            conditions.append(f"published_at >= ${len(params)}")
        if time_to:
            params.append(time_to)
            conditions.append(f"published_at <= ${len(params)}")
        if country:
            params.append(country.upper())
            conditions.append(f"country = ${len(params)}")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""SELECT id, published_at, title, url, country,
                           tone, source_lang, topic_id, topic_run
                    FROM news_events
                    {where}
                    ORDER BY published_at DESC
                    LIMIT ${len(params)}""",
                *params,
            )

        return [dict(r) for r in rows]


news_repository = NewsRepository()
