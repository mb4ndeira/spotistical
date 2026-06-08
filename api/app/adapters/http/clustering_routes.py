from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from domain.use_cases.clustering.audio_clustering_use_case import (
    audio_clustering_uc,
    get_progress,
)

router = APIRouter(prefix="/clustering", tags=["clustering"])

_running = False


@router.post("/audio")
async def run_audio_clustering(
    background_tasks: BackgroundTasks,
    include_global: bool = Query(
        False,
        description="Also run a global pass (country='GL') after all per-country passes.",
    ),
):
    global _running
    if _running:
        raise HTTPException(409, "Audio clustering already running")

    async def _run():
        global _running
        _running = True
        try:
            result = await audio_clustering_uc.execute(include_global=include_global)
            print(f"[clustering/audio] done — {result}")
        finally:
            _running = False

    background_tasks.add_task(_run)
    return {
        "success": True,
        "message": "Per-country audio clustering started — GET /clustering/audio/status",
        "include_global": include_global,
    }


@router.get("/audio/status")
async def audio_clustering_status():
    return get_progress()
