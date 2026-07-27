"""FastAPI app factory.

Thin by design: it builds the app, installs CORS, ensures the storage tree
exists and includes every router from :mod:`aitu_backend.api`. All logic
lives in the feature packages (`matrix/`, `audio/`, `transcription/`,
`storage/`, `notation/`).
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aitu_backend.api import ALL_ROUTERS
from aitu_backend.storage.paths import ensure_data_tree


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the `data/` tree before serving the first request."""
    ensure_data_tree()
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
        host="127.0.0.1",
        port=8765,
        reload=True,
    )


if __name__ == "__main__":
    run()
