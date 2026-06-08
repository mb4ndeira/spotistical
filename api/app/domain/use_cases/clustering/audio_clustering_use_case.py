from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TypedDict, Optional

import numpy as np

import drivers.db.db_driver as db_driver

AUDIO_FEATURES: list[str] = [
    "danceability", "energy", "key", "loudness", "mode",
    "speechiness", "acousticness", "instrumentalness",
    "liveness", "valence", "tempo", "time_signature",
]

K_MIN_C = 5
K_MAX_C = 15

K_MIN_GL = 10
K_MAX_GL = 30

MIN_TRACKS = 30

UMAP_N_NEIGHBORS = 15
UMAP_MIN_DIST    = 0.1

BATCH_SIZE = 2_000


class ClusteringProgress(TypedDict):
    running:            bool
    stage:              str
    run_id:             Optional[str]
    country_current:    Optional[str]
    countries_done:     int
    countries_total:    int
    countries_skipped:  int
    k_current:          Optional[int]
    k_best_this:        Optional[int]
    tracks_this:        int
    tracks_persisted:   int
    last_error:         Optional[str]


_progress: ClusteringProgress = {
    "running":           False,
    "stage":             "idle",
    "run_id":            None,
    "country_current":   None,
    "countries_done":    0,
    "countries_total":   0,
    "countries_skipped": 0,
    "k_current":         None,
    "k_best_this":       None,
    "tracks_this":       0,
    "tracks_persisted":  0,
    "last_error":        None,
}


def get_progress() -> ClusteringProgress:
    return dict(_progress)


def _set(**kwargs) -> None:
    _progress.update(kwargs)


class AudioClusteringUseCase:

    async def execute(self, include_global: bool = False) -> dict:
        run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        _set(
            running=True, stage="loading_countries", run_id=run_id,
            country_current=None, countries_done=0, countries_total=0,
            countries_skipped=0, k_current=None, k_best_this=None,
            tracks_this=0, tracks_persisted=0, last_error=None,
        )
        print(f"[clustering/audio] run_id={run_id}")
        try:
            return await self._pipeline(include_global, run_id)
        except Exception as exc:
            _set(stage="error", last_error=str(exc))
            print(f"[clustering/audio] ERROR: {exc}")
            raise
        finally:
            _set(running=False)

    async def _pipeline(self, include_global: bool, run_id: str) -> dict:

        pool = db_driver.get_admin_pool()

        async with pool.acquire() as conn:
            country_rows = await conn.fetch(
                "SELECT DISTINCT country FROM tracks ORDER BY country"
            )
        countries = [r["country"].strip() for r in country_rows]
        _set(countries_total=len(countries), stage="clustering")
        print(f"[clustering/audio] {len(countries)} countries to cluster")

        total_persisted = 0
        skipped         = 0

        for country in countries:
            _set(country_current=country, k_current=None, k_best_this=None)

            rows = await self._load_country(pool, country)
            if len(rows) < MIN_TRACKS:
                print(f"[clustering/audio] {country}: only {len(rows)} tracks — skipping")
                skipped += 1
                _set(countries_skipped=skipped)
                continue

            spotify_ids = [r["spotify_id"] for r in rows]
            X_raw = np.array(
                [[r[f] for f in AUDIO_FEATURES] for r in rows], dtype=np.float32
            )
            _set(tracks_this=len(spotify_ids))
            print(f"[clustering/audio] {country}: {len(spotify_ids)} tracks")

            loop       = asyncio.get_event_loop()
            cpu_result = await loop.run_in_executor(
                None, _cpu_work, spotify_ids, X_raw, K_MIN_C, K_MAX_C
            )

            n = await self._persist(cpu_result, country, run_id, pool)
            total_persisted += n

            done = _progress["countries_done"] + 1
            _set(countries_done=done, tracks_persisted=total_persisted,
                 k_best_this=cpu_result["best_k"])

        if include_global:
            _set(stage="global_pass", country_current="GL")
            print("[clustering/audio] running global pass (country=GL) …")
            rows = await self._load_global(pool)
            if len(rows) >= MIN_TRACKS:
                spotify_ids = [r["spotify_id"] for r in rows]
                X_raw       = np.array(
                    [[r[f] for f in AUDIO_FEATURES] for r in rows], dtype=np.float32
                )
                _set(tracks_this=len(spotify_ids))
                loop       = asyncio.get_event_loop()
                cpu_result = await loop.run_in_executor(
                    None, _cpu_work, spotify_ids, X_raw, K_MIN_GL, K_MAX_GL
                )
                n = await self._persist(cpu_result, "GL", run_id, pool)
                total_persisted += n

        await self._invalidate_stale_insights(run_id, pool)

        summary = {
            "run_id":              run_id,
            "countries_clustered": _progress["countries_done"],
            "countries_skipped":   skipped,
            "tracks_persisted":    total_persisted,
        }
        _set(stage="done", tracks_persisted=total_persisted)
        print(f"[clustering/audio] complete — {summary}")
        return summary

    async def _load_country(self, pool, country: str) -> list:
        feature_cols = ", ".join(f"AVG({f})::float4 AS {f}" for f in AUDIO_FEATURES)
        not_null     = " AND ".join(f"AVG({f}) IS NOT NULL" for f in AUDIO_FEATURES)
        async with pool.acquire() as conn:
            return await conn.fetch(f"""
                SELECT spotify_id, {feature_cols}
                FROM   tracks
                WHERE  country = $1
                GROUP  BY spotify_id
                HAVING {not_null}
            """, country)

    async def _load_global(self, pool) -> list:
        feature_cols = ", ".join(f"AVG({f})::float4 AS {f}" for f in AUDIO_FEATURES)
        not_null     = " AND ".join(f"AVG({f}) IS NOT NULL" for f in AUDIO_FEATURES)
        async with pool.acquire() as conn:
            return await conn.fetch(f"""
                SELECT spotify_id, {feature_cols}
                FROM   tracks
                GROUP  BY spotify_id
                HAVING {not_null}
            """)

    async def _persist(self, result: dict, country: str, run_id: str, pool) -> int:
        rows = [
            (sid, country, int(lbl), float(x), float(y), run_id)
            for sid, lbl, x, y in zip(
                result["spotify_ids"], result["labels"],
                result["umap_x"],      result["umap_y"],
            )
        ]
        sql = """
            INSERT INTO song_clusters
                (spotify_id, country, audio_cluster_id, umap_audio_x, umap_audio_y,
                 clustering_run_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (spotify_id, country) DO UPDATE SET
                audio_cluster_id  = EXCLUDED.audio_cluster_id,
                umap_audio_x      = EXCLUDED.umap_audio_x,
                umap_audio_y      = EXCLUDED.umap_audio_y,
                clustering_run_id = EXCLUDED.clustering_run_id
        """
        async with pool.acquire() as conn:
            for i in range(0, len(rows), BATCH_SIZE):
                await conn.executemany(sql, rows[i : i + BATCH_SIZE])
        return len(rows)

    async def _invalidate_stale_insights(self, run_id: str, pool) -> None:
        async with pool.acquire() as conn:
            deleted = await conn.fetchval("""
                WITH del AS (
                    DELETE FROM insights
                    WHERE  clustering_run_id IS NOT NULL
                      AND  clustering_run_id != $1
                    RETURNING 1
                )
                SELECT count(*) FROM del
            """, run_id)
        if deleted:
            print(f"[clustering/audio] invalidated {deleted} stale insights "
                  f"(clustering_run_id != {run_id})")


def _cpu_work(
    spotify_ids: list[str],
    X_raw: np.ndarray,
    k_min: int,
    k_max: int,
) -> dict:
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    import umap as umap_lib

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    rng    = np.random.default_rng(42)
    n      = len(X_scaled)
    sample = min(n, 5_000)
    scores: dict[int, float] = {}

    k_max_eff = min(k_max, n - 1)
    k_min_eff = min(k_min, k_max_eff)

    for k in range(k_min_eff, k_max_eff + 1):
        _set(k_current=k)
        km     = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = km.fit_predict(X_scaled)
        idx    = rng.choice(n, sample, replace=False) if n > sample else None
        X_s    = X_scaled[idx] if idx is not None else X_scaled
        L_s    = labels[idx]   if idx is not None else labels
        scores[k] = float(silhouette_score(X_s, L_s, metric="euclidean"))

    best_k   = max(scores, key=lambda k: scores[k])
    _set(k_best_this=best_k)

    km_final = KMeans(n_clusters=best_k, random_state=42, n_init="auto")
    labels   = km_final.fit_predict(X_scaled)

    n_neighbors = min(UMAP_N_NEIGHBORS, n - 1)
    reducer  = umap_lib.UMAP(
        n_components = 2,
        n_neighbors  = n_neighbors,
        min_dist     = UMAP_MIN_DIST,
        metric       = "euclidean",
        random_state = 42,
        low_memory   = True,
    )
    embedding = reducer.fit_transform(X_scaled)

    return {
        "spotify_ids": spotify_ids,
        "labels":      labels.tolist(),
        "umap_x":      embedding[:, 0].tolist(),
        "umap_y":      embedding[:, 1].tolist(),
        "best_k":      best_k,
        "scores":      scores,
    }


audio_clustering_uc = AudioClusteringUseCase()
