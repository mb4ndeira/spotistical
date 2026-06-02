from __future__ import annotations

import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)

_PARQUET_PATH = os.getenv("TRACKS_PARQUET_PATH", "/data/tracks.parquet")

_KNOWN_COLUMNS = {
    "spotify_id", "name", "artists", "daily_rank", "daily_movement",
    "weekly_movement", "country", "snapshot_date", "popularity", "is_explicit",
    "duration_ms", "album_name", "album_release_date", "danceability", "energy",
    "key", "loudness", "mode", "speechiness", "acousticness", "instrumentalness",
    "liveness", "valence", "tempo", "time_signature",
}

_INT_COLS = {
    "daily_rank", "daily_movement", "weekly_movement", "popularity",
    "duration_ms", "key", "mode", "time_signature",
}


class ParquetDriver:
    def read_all(self) -> list[dict]:
        if not os.path.exists(_PARQUET_PATH):
            raise FileNotFoundError(f"Parquet file not found at {_PARQUET_PATH!r}")

        df = pd.read_parquet(_PARQUET_PATH, engine="pyarrow")

        present = [c for c in _KNOWN_COLUMNS if c in df.columns]
        if not present:
            raise ValueError("Parquet file contains none of the expected track columns.")

        df = df[present].copy()

        if "snapshot_date" in df.columns:
            df["snapshot_date"] = pd.to_datetime(df["snapshot_date"]).dt.strftime("%Y-%m-%d")

        for col in _INT_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.where(pd.notna(df), None)

        logger.info("ParquetDriver: read %d rows from %s", len(df), _PARQUET_PATH)
        return df.to_dict(orient="records")


parquet_driver = ParquetDriver()
