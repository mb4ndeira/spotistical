"""
lyrics_driver.py
────────────────
Cascade de providers de letras:

  1. lyrics.ovh  — primeira tentativa
  2. lrclib.net  — fallback apenas quando lyrics.ovh retorna 404 (música não encontrada)

Política de retry:
  - Erros de conexão / timeout → retry na mesma fonte até MAX_RETRIES vezes,
    com backoff exponencial. Não cascateia — connection error não diz nada sobre
    se a música existe em outro provider.
  - 404 → cascateia imediatamente para o próximo provider.

Cada worker é independente — retry e cascade acontecem dentro do worker sem
bloquear os demais (concorrência preservada).
"""
from __future__ import annotations

import ast
import asyncio
import os
import re
import urllib.parse

import httpx

TIMEOUT     = float(os.environ.get("LYRICS_TIMEOUT",    "10"))
MAX_RETRIES = int(os.environ.get("LYRICS_MAX_RETRIES",  "2"))

# fail_reasons que indicam "música não existe nesta fonte" → cascateia
_NOT_FOUND_REASONS = {"404", "empty_response", "not_found"}

# fail_reasons que indicam problema de rede → retry, não cascateia
_RETRYABLE_REASONS = {"timeout", "connection_error"}


# ── helpers ────────────────────────────────────────────────────────────────────

def parse_first_artist(artists_str: str) -> str:
    if not artists_str:
        return ""
    s = artists_str.strip()
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list) and parsed:
            return str(parsed[0]).strip()
    except Exception:
        pass
    return s.split(",")[0].strip().strip("'\"[]")


def clean_title(title: str) -> str:
    title = re.sub(r"\s*[\(\[].*?[\)\]]", "", title)
    title = re.sub(r"\s*-\s*(remaster|remix|radio edit|live|acoustic).*$",
                   "", title, flags=re.IGNORECASE)
    return title.strip()


# ── provider 1: lyrics.ovh ────────────────────────────────────────────────────

async def _lyricsovh(client: httpx.AsyncClient, artist: str, title: str) -> tuple[str | None, str | None]:
    url = f"https://api.lyrics.ovh/v1/{urllib.parse.quote(artist)}/{urllib.parse.quote(title)}"
    try:
        resp = await client.get(url, timeout=TIMEOUT)
        if resp.status_code == 404:
            return None, "404"
        if resp.status_code == 429:
            return None, "429_rate_limited"
        resp.raise_for_status()
        lyrics = resp.json().get("lyrics", "").strip()
        return (lyrics, None) if lyrics else (None, "empty_response")
    except httpx.TimeoutException:
        return None, "timeout"
    except httpx.ConnectError:
        return None, "connection_error"
    except Exception as exc:
        return None, f"connection_error:{exc}"


# ── provider 2: lrclib.net ────────────────────────────────────────────────────

async def _lrclib(client: httpx.AsyncClient, artist: str, title: str) -> tuple[str | None, str | None]:
    """lrclib.net — open source, sem key, boa cobertura multilingual (K-pop, J-pop, Latin)."""
    params = {"artist_name": artist, "track_name": title}
    try:
        resp = await client.get("https://lrclib.net/api/get", params=params, timeout=TIMEOUT)
        if resp.status_code == 404:
            return None, "404"
        resp.raise_for_status()
        data = resp.json()
        # prefere plainLyrics; fallback para syncedLyrics sem timestamps
        lyrics = data.get("plainLyrics") or ""
        if not lyrics:
            synced = data.get("syncedLyrics") or ""
            # remove timestamps "[mm:ss.xx] "
            lyrics = re.sub(r"\[\d+:\d+\.\d+\]\s*", "", synced).strip()
        return (lyrics, None) if lyrics else (None, "empty_response")
    except httpx.TimeoutException:
        return None, "timeout"
    except httpx.ConnectError:
        return None, "connection_error"
    except Exception as exc:
        return None, f"connection_error:{exc}"


# ── cascade com retry ─────────────────────────────────────────────────────────

_PROVIDERS = [
    ("lyrics.ovh", _lyricsovh),
    ("lrclib",     _lrclib),
]


async def fetch_lyrics(
    client: httpx.AsyncClient,
    artist: str,
    title: str,
) -> tuple[str | None, str | None, str | None]:
    """
    Returns (lyrics, source, fail_reason).
      - Se encontrou: (text, "lyrics.ovh"|"lrclib", None)
      - Se não encontrou em nenhum: (None, None, "not_found")
      - Se falhou por rede após retries: (None, None, "connection_failed")
    """
    artist_clean = parse_first_artist(artist)
    title_clean  = clean_title(title)

    if not artist_clean or not title_clean:
        return None, None, "missing_artist_or_title"

    last_reason: str | None = None

    for source_name, provider_fn in _PROVIDERS:
        # tenta com retry para erros de rede
        for attempt in range(MAX_RETRIES + 1):
            lyrics, reason = await provider_fn(client, artist_clean, title_clean)

            if lyrics:
                return lyrics, source_name, None

            if reason in _NOT_FOUND_REASONS:
                last_reason = reason
                break  # não tem neste provider → tenta o próximo

            if reason in _RETRYABLE_REASONS or (reason or "").startswith("connection_error"):
                last_reason = "connection_failed"
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)  # backoff: 1s, 2s
                    continue
                break  # esgotou retries → não cascateia, vai para próximo provider

            # outro erro desconhecido → não cascateia
            last_reason = reason
            break

    return None, None, last_reason or "not_found"
