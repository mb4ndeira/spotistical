import logging

from adapters.repositories.tracks_repository import tracks_repository

logger = logging.getLogger(__name__)


class ListSnapshotDatesUseCase:
    def execute(self) -> dict:
        try:
            return {"success": True, "data": tracks_repository.list_snapshot_dates()}
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}
        except Exception:
            logger.exception("Error listing snapshot dates")
            return {"success": False, "error": "Failed to list snapshot dates"}


list_snapshot_dates_uc = ListSnapshotDatesUseCase()
