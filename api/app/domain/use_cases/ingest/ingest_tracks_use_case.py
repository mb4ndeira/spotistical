from __future__ import annotations

import math
import os
from datetime import date, datetime

import pandas as pd

from drivers.db.db_driver import get_admin_pool

COUNTRY_TO_ISO2: dict[str, str] = {
    "Argentina": "AR", "Australia": "AU", "Austria": "AT",
    "Belarus": "BY", "Belgium": "BE", "Bolivia": "BO",
    "Brazil": "BR", "Bulgaria": "BG", "Canada": "CA",
    "Chile": "CL", "Colombia": "CO", "Costa Rica": "CR",
    "Czechia": "CZ", "Denmark": "DK", "Dominican Republic": "DO",
    "Ecuador": "EC", "Egypt": "EG", "El Salvador": "SV",
    "Estonia": "EE", "Finland": "FI", "France": "FR",
    "Germany": "DE", "Greece": "GR", "Guatemala": "GT",
    "Honduras": "HN", "Hong Kong SAR China": "HK", "Hungary": "HU",
    "Iceland": "IS", "India": "IN", "Indonesia": "ID",
    "Ireland": "IE", "Israel": "IL", "Italy": "IT",
    "Japan": "JP", "Kazakhstan": "KZ", "Latvia": "LV",
    "Lithuania": "LT", "Luxembourg": "LU", "Malaysia": "MY",
    "Mexico": "MX", "Morocco": "MA", "Netherlands": "NL",
    "New Zealand": "NZ", "Nicaragua": "NI", "Nigeria": "NG",
    "Norway": "NO", "Pakistan": "PK", "Panama": "PA",
    "Paraguay": "PY", "Peru": "PE", "Philippines": "PH",
    "Poland": "PL", "Portugal": "PT", "Romania": "RO",
    "Saudi Arabia": "SA", "Singapore": "SG", "Slovakia": "SK",
    "South Africa": "ZA", "South Korea": "KR", "Spain": "ES",
    "Sweden": "SE", "Switzerland": "CH", "Taiwan": "TW",
    "Thailand": "TH", "Turkey": "TR", "Ukraine": "UA",
    "United Arab Emirates": "AE", "United Kingdom": "GB",
    "United States": "US", "Uruguay": "UY", "Venezuela": "VE",
    "Vietnam": "VN",
}

_PARQUET_PATH = os.environ.get("TRACKS_PARQUET_PATH", "/data/tracks.parquet")
_BATCH_SIZE   = 5_000


def _safe_date(val: object) -> date | None:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    try:
        if isinstance(val, (datetime, date)):
            return val if isinstance(val, date) else val.date()
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except Exception:
        return None


def _safe_int(val: object) -> int | None:
    try:
        v = int(val)
        return None if math.isnan(val) else v  # type: ignore[arg-type]
    except Exception:
        return None


def _safe_float(val: object) -> float | None:
    try:
        v = float(val)  # type: ignore[arg-type]
        return None if math.isnan(v) else v
    except Exception:
        return None


class IngestTracksUseCase:

    _INSERT = """
        INSERT INTO tracks (
            snapshot_date, country, spotify_id,
            daily_rank, daily_movement, weekly_movement,
            name, artists, popularity, is_explicit, duration_ms,
            album_name, album_release_date,
            danceability, energy, key, loudness, mode,
            speechiness, acousticness, instrumentalness, liveness,
            valence, tempo, time_signature
        ) VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,
            $14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25
        )
        ON CONFLICT (snapshot_date, country, spotify_id) DO NOTHING
    """

    async def execute(self) -> dict:
        df = pd.read_parquet(_PARQUET_PATH, engine="pyarrow")

        df = df[df["country"].notna()]
        df["country_code"] = df["country"].map(COUNTRY_TO_ISO2)
        df = df[df["country_code"].notna()]

        total   = len(df)
        batches = math.ceil(total / _BATCH_SIZE)
        inserted = 0

        pool = get_admin_pool()
        async with pool.acquire() as conn:
            stmt = await conn.prepare(self._INSERT)
            for i in range(batches):
                chunk = df.iloc[i * _BATCH_SIZE : (i + 1) * _BATCH_SIZE]
                records = [
                    (
                        _safe_date(row.snapshot_date),
                        row.country_code,
                        row.spotify_id,
                        _safe_int(row.daily_rank),
                        _safe_int(row.daily_movement),
                        _safe_int(row.weekly_movement),
                        row.name,
                        row.artists,
                        _safe_int(row.popularity),
                        bool(row.is_explicit) if row.is_explicit is not None else None,
                        _safe_int(row.duration_ms),
                        row.album_name if pd.notna(row.album_name) else None,
                        _safe_date(row.album_release_date),
                        _safe_float(row.danceability),
                        _safe_float(row.energy),
                        _safe_int(row.key),
                        _safe_float(row.loudness),
                        _safe_int(row.mode),
                        _safe_float(row.speechiness),
                        _safe_float(row.acousticness),
                        _safe_float(row.instrumentalness),
                        _safe_float(row.liveness),
                        _safe_float(row.valence),
                        _safe_float(row.tempo),
                        _safe_int(row.time_signature),
                    )
                    for row in chunk.itertuples(index=False)
                ]
                await stmt.executemany(records)
                inserted += len(records)
                print(f"[ingest] batch {i+1}/{batches} — {inserted:,}/{total:,} rows")

        return {"success": True, "rows_processed": total, "rows_inserted": inserted}


ingest_tracks_uc = IngestTracksUseCase()
