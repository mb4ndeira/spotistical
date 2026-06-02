from __future__ import annotations

import logging
from typing import Optional

from drivers.parquet.parquet_driver import parquet_driver

logger = logging.getLogger(__name__)


class TracksRepository:
    def _load(self) -> list[dict]:
        return parquet_driver.read_all()

    def list(
        self,
        date: Optional[str] = None,
        country: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        rows = self._load()

        if date:
            rows = [r for r in rows if str(r.get("snapshot_date", "")) == date]
        if country:
            rows = [r for r in rows if str(r.get("country", "")).upper() == country.upper()]

        rows.sort(key=lambda r: (str(r.get("snapshot_date", "")), r.get("daily_rank", 0)))
        return rows[:limit]

    def list_snapshot_dates(self) -> list[str]:
        rows = self._load()
        dates = sorted(
            {str(r["snapshot_date"]) for r in rows if r.get("snapshot_date")},
            reverse=True,
        )
        return dates

    def list_countries(self) -> list[str]:
        rows = self._load()
        return sorted({str(r["country"]) for r in rows if r.get("country")})


tracks_repository = TracksRepository()
