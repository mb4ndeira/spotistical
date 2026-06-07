from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from domain.use_cases.news.list_news_use_case import list_news_uc

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/")
def list_news(
    time_from: str | None = Query(None, description="ISO datetime: 2023-10-01T00:00:00"),
    time_to:   str | None = Query(None, description="ISO datetime: 2023-12-31T23:59:59"),
    country:   str | None = Query(None, description="Código ISO 2 letras: BR, CL, US..."),
    limit:     int        = Query(50, le=1000),
):
    try:
        parsed_from = datetime.fromisoformat(time_from) if time_from else None
        parsed_to   = datetime.fromisoformat(time_to)   if time_to   else None
    except ValueError as e:
        raise HTTPException(400, f"Invalid datetime format: {e}")

    result = list_news_uc.execute(
        time_from=parsed_from,
        time_to=parsed_to,
        country=country,
        limit=limit,
    )

    if not result["success"]:
        raise HTTPException(502, result["error"])
    return result["data"]
