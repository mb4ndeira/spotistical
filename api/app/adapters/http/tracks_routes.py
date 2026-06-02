from fastapi import APIRouter, HTTPException, Query

from domain.use_cases.tracks.list_tracks_use_case import list_tracks_uc
from domain.use_cases.tracks.list_snapshot_dates_use_case import list_snapshot_dates_uc
from domain.use_cases.tracks.list_countries_use_case import list_countries_uc

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("/")
def list_tracks(
    date: str | None = Query(None, description="Snapshot date (YYYY-MM-DD)"),
    country: str | None = Query(None, description="2-letter country code, e.g. US"),
    limit: int = Query(50, le=500),
):
    result = list_tracks_uc.execute(date=date, country=country, limit=limit)
    if not result["success"]:
        raise HTTPException(500, result["error"])
    return result["data"]


@router.get("/dates")
def list_snapshot_dates():
    result = list_snapshot_dates_uc.execute()
    if not result["success"]:
        raise HTTPException(500, result["error"])
    return result["data"]


@router.get("/countries")
def list_countries():
    result = list_countries_uc.execute()
    if not result["success"]:
        raise HTTPException(500, result["error"])
    return result["data"]
