from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from drivers.alphavantage.alphavantage_driver import alphavantage_driver

logger = logging.getLogger(__name__)


class ListNewsUseCase:
    def execute(
        self,
        time_from: Optional[datetime] = None,
        time_to: Optional[datetime] = None,
        topics: Optional[list] = None,
        limit: int = 50,
    ) -> dict:
        try:
            data = alphavantage_driver.fetch_news(
                time_from=time_from,
                time_to=time_to,
                topics=topics,
                limit=limit,
            )
            return {"success": True, "data": data}
        except RuntimeError as e:
            return {"success": False, "error": str(e)}
        except Exception:
            logger.exception("Error fetching news from Alpha Vantage")
            return {"success": False, "error": "Failed to fetch news"}


list_news_uc = ListNewsUseCase()
