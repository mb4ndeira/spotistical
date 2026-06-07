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
    """
    K-Means audio clustering — per country.

    For every country in the tracks table, loads the distinct tracks that
    charted there, runs a silhouette sweep (k=5–15), fits the best k, projects
    with UMAP, and persists to song_clusters(spotify_id, country).

    The same track will have different cluster IDs in different markets —
    each assignment reflects its role in that country's music landscape.

    Pass include_global=true to also run a global pass (country='GL').

    Safe to re-run — ON CONFLICT DO UPDATE.
    """
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
    """
    Live progress of the audio clustering pipeline.

    country_current   — which market is being processed right now
    countries_done    — markets completed
    countries_total   — total markets found in tracks table
    countries_skipped — markets with too few tracks (< 30 unique)
    k_current         — k being evaluated in the silhouette sweep
    k_best_this       — best k chosen for the current country
    tracks_persisted  — total rows written to song_clusters so far
    """
    return get_progress()
