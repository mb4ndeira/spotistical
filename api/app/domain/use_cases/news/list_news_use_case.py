from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from adapters.repositories.news_repository import news_repository

logger = logging.getLogger(__name__)


class ListNewsUseCase:
    def execute(
        self,
        time_from: Optional[datetime] = None,
        time_to: Optional[datetime] = None,
        country: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        try:
            data = news_repository.list(
                time_from=time_from,
                time_to=time_to,
                country=country,
                limit=limit,
            )
            return {"success": True, "data": data}
        except Exception:
            logger.exception("Error fetching news from DB")
            return {"success": False, "error": "Failed to fetch news"}


list_news_uc = ListNewsUseCase()
