"""
lyrics_driver.py
────────────────
lyrics.ovh HTTP driver.

API: GET https://api.lyrics.ovh/v1/{artist}/{title}
- Free, no key, no hard rate limit
- Returns {"lyrics": "..."} on success
- Returns 404 when not found
- Conservative delay: 0.5s between requests (~2 req/sec)

Artist name parsing handles the formats present in the tracks table:
    "['Taylor Swift']"          → "Taylor Swift"
    "['Bad Bunny', 'Jhay Cortez']" → "Bad Bunny"
    "Taylor Swift"              → "Taylor Swift"
"""
from __future__ import annotations

import ast
import os
import re
import urllib.parse

import httpx

BASE_URL = "https://api.lyrics.ovh/v1"
TIMEOUT  = float(os.environ.get("LYRICS_TIMEOUT", "10"))


def parse_first_artist(artists_str: str) -> str:
    """Extract the first artist name from whatever format the DB stores."""
    if not artists_str:
        return ""
    s = artists_str.strip()
    # Python list repr: ['Artist1', 'Artist2']
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list) and parsed:
            return str(parsed[0]).strip()
    except Exception:
        pass
    # Comma-separated plain text
    return s.split(",")[0].strip().strip("'\"[]")


def clean_title(title: str) -> str:
    """Strip common suffixes that confuse lyrics.ovh."""
    # remove "(feat. ...)", "(with ...)", "(prod. ...)", "- Remaster", etc.
    title = re.sub(r"\s*[\(\[].*?[\)\]]", "", title)
    title = re.sub(r"\s*-\s*(remaster|remix|radio edit|live|acoustic).*$",
                   "", title, flags=re.IGNORECASE)
    return title.strip()


async def fetch_lyrics(client: httpx.AsyncClient, artist: str, title: str) -> tuple[str | None, str | None]:
    """
    Returns (lyrics_text, None) on success or (None, fail_reason) on failure.
    Never raises — all errors are returned as fail_reason strings.
    """
    artist_clean = parse_first_artist(artist)
    title_clean  = clean_title(title)

    if not artist_clean or not title_clean:
        return None, "missing_artist_or_title"

    # lyrics.ovh encodes the path segments
    url = f"{BASE_URL}/{urllib.parse.quote(artist_clean)}/{urllib.parse.quote(title_clean)}"
    try:
        resp = await client.get(url, timeout=TIMEOUT)
        if resp.status_code == 404:
            return None, "404"
        if resp.status_code == 429:
            return None, "429_rate_limited"
        resp.raise_for_status()
        data = resp.json()
        lyrics = data.get("lyrics", "").strip()
        if not lyrics:
            return None, "empty_response"
        return lyrics, None
    except httpx.TimeoutException:
        return None, "timeout"
    except Exception as exc:
        return None, f"error:{exc}"
