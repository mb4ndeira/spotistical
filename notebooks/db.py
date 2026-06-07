"""
db.py — shared DB helper for all spotistical notebooks.

Reads the same .env as the API.  Two engines:
  engine       → app user  (SELECT only on source tables)
  admin_engine → admin user (full access, use only for writing derived tables)

Usage:
    from db import engine
    df = pd.read_sql("SELECT * FROM song_clusters LIMIT 1000", engine)
"""
from __future__ import annotations

import os
import pathlib

from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine

# load root .env (one directory up from notebooks/)
_root = pathlib.Path(__file__).parent.parent
load_dotenv(_root / ".env", override=False)


def _url(user_env: str, pass_env: str) -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db   = os.environ["POSTGRES_DB"]
    user = os.environ[user_env]
    pw   = os.environ[pass_env]
    # use psycopg2 (sync) for notebook compatibility
    # quote the password to handle special characters
    from urllib.parse import quote_plus
    return f"postgresql+psycopg2://{user}:{quote_plus(pw)}@{host}:{port}/{db}"


def _make_engine(user_env: str, pass_env: str) -> Engine:
    return create_engine(_url(user_env, pass_env), pool_pre_ping=True)


# app user — read-only on tracks / news_events
engine = _make_engine("POSTGRES_APP_USER", "POSTGRES_APP_PASSWORD")

# admin user — full write, use only for writing derived tables in notebooks
admin_engine = _make_engine("POSTGRES_USER", "POSTGRES_PASSWORD")


if __name__ == "__main__":
    import pandas as pd
    df = pd.read_sql("SELECT count(*) AS rows FROM tracks", engine)
    print(df)
