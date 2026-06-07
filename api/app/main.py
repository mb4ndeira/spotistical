from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.http.tracks_routes import router as tracks_router
from adapters.http.news_routes   import router as news_router
from adapters.http.ingest_routes import router as ingest_router
import drivers.db.db_driver as db_driver


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──────────────────────────────────────────────────
    try:
        await db_driver.init()
        print("[startup] DB pool ready, migrations applied")
    except Exception as exc:
        # Don't crash the API if DB is unreachable at startup —
        # allows running without a DB for parquet-only dev mode.
        print(f"[startup] DB unavailable ({exc}) — running in parquet-only mode")
    yield
    # ── shutdown ─────────────────────────────────────────────────
    await db_driver.close()


app = FastAPI(title="Spotify × Events API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tracks_router)
app.include_router(news_router)
app.include_router(ingest_router)


@app.get("/health")
async def health():
    db_ok = db_driver._app_pool is not None
    return {"status": "ok", "db": "connected" if db_ok else "unavailable"}
