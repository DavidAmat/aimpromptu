"""FastAPI routers, one module per product section.

Each module exposes a single ``router`` (an ``APIRouter`` with its URL
prefix and tag) that :mod:`aitu_backend.main` includes. Endpoints whose
implementation belongs to a later epic already exist here and answer
``501 Not Implemented`` so the frontend shell can be wired against real
routes from day one.
"""

from aitu_backend.api.audio import router as audio_router
from aitu_backend.api.library import router as library_router
from aitu_backend.api.matrix import router as matrix_router
from aitu_backend.api.notation import router as notation_router
from aitu_backend.api.scores import router as scores_router
from aitu_backend.api.youtube import router as youtube_router

#: Included by the app factory in this order.
ALL_ROUTERS = [
    scores_router,
    audio_router,
    matrix_router,
    notation_router,
    library_router,
    youtube_router,
]

__all__ = [
    "ALL_ROUTERS",
    "audio_router",
    "library_router",
    "matrix_router",
    "notation_router",
    "scores_router",
    "youtube_router",
]
