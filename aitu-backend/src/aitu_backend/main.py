"""FastAPI app factory.

Thin by design: it builds the app, installs CORS and gzip, opens ``.database/`` (the tables,
the folders, the master user) and includes every router from :mod:`aitu_backend.api`. All logic
lives in the feature packages (`matrix/`, `audio/`, `transcription/`,
`storage/`, `notation/`).
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aitu_backend import config
from aitu_backend.api import MASTER_ROUTERS, OPEN_ROUTERS, USER_ROUTERS
from aitu_backend.auth.dependencies import master_only, project_rights, signed_in
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

    # The page reaches the backend through its own server (`/api`), on the same origin, so the
    # browser sends the session cookie by itself. CORS stays open for scripts, without credentials:
    # a page of another origin can never send the cookie (context/08-security.md).
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

    # Every route but signing in and /health needs a session, and checks the rights of the
    # project it names before anything else (implementation 02, plan sections 9.2 and 9.3).
    for router in OPEN_ROUTERS:
        application.include_router(router)
    for router in USER_ROUTERS:
        application.include_router(
            router, dependencies=[Depends(signed_in), Depends(project_rights)]
        )
    for router in MASTER_ROUTERS:
        application.include_router(router, dependencies=[Depends(signed_in), Depends(master_only)])

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
