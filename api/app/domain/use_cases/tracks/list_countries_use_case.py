import logging

from adapters.repositories.tracks_repository import tracks_repository

logger = logging.getLogger(__name__)


class ListCountriesUseCase:
    def execute(self) -> dict:
        try:
            return {"success": True, "data": tracks_repository.list_countries()}
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}
        except Exception:
            logger.exception("Error listing countries")
            return {"success": False, "error": "Failed to list countries"}


list_countries_uc = ListCountriesUseCase()
