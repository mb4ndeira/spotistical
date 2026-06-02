import logging
from typing import Optional

from adapters.repositories.tracks_repository import tracks_repository

logger = logging.getLogger(__name__)


class ListTracksUseCase:
    def execute(
        self,
        date: Optional[str] = None,
        country: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        try:
            data = tracks_repository.list(date=date, country=country, limit=limit)
            return {"success": True, "data": data}
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}
        except Exception:
            logger.exception("Error listing tracks")
            return {"success": False, "error": "Failed to list tracks"}


list_tracks_uc = ListTracksUseCase()
