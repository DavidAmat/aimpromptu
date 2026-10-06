"""FastAPI app factory.

Thin by design: it builds the app, installs CORS and gzip, opens ``.database/`` (the tables,
the folders, the master user) and includes every router from :mod:`aitu_backend.api`. All logic
lives in the feature packages (`matrix/`, `audio/`, `transcription/`,
`storage/`, `notation/`).
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aitu_backend import config
from aitu_backend.api import ALL_ROUTERS
from aitu_backend.compression import JsonGZipMiddleware
from aitu_backend.db.database import engine
from aitu_backend.db.users import ensure_master_user
from aitu_backend.storage.paths import ensure_database_tree
from aitu_backend.transcription import models


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open ``.database/`` before serving the first request, and start loading the model.

    The tables are brought to the newest Alembic revision, the top folders are made, and the master
    user is made from ``AITU_MASTER_USERNAME`` when the database has none (plan section 9.1).

    With ``AITU_PRELOAD_ENGINE=muscriptor-large`` the model loads on a background thread, so the
    server answers at once and the first transcription does not pay the load. A failure (no token,
    licence not accepted) is reported by ``GET /matrix/engine``.
    """
    engine()
    ensure_database_tree()
    ensure_master_user()
    spec = config.preload_engine()
    if spec:
        models.preload_in_background(spec)
    yield


def create_app() -> FastAPI:
    """Build the ASGI application."""
    application = FastAPI(
        title="AImpromptu Backend API",
        description="Piano matrix engine, audio ingestion and score documents for aitu-frontend.",
        version="0.1.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # JSON only: the piano sheet answer is about 12 times smaller, and the audio is left alone.
    application.add_middleware(JsonGZipMiddleware)

    @application.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in ALL_ROUTERS:
        application.include_router(router)

    return application


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "aitu_backend.main:app",
        host=config.host(),
        port=config.port(),
        reload=True,
    )


if __name__ == "__main__":
    run()
