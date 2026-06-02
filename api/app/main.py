from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.http.tracks_routes import router as tracks_router
from adapters.http.news_routes import router as news_router

app = FastAPI(title="Spotify × Events API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tracks_router)
app.include_router(news_router)


@app.get("/health")
def health():
    return {"status": "ok"}
