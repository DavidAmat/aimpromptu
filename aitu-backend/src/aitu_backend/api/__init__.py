"""FastAPI routers, one module per product section.

Each module exposes a single ``router`` (an ``APIRouter`` with its URL prefix and
tag) that :mod:`aitu_backend.main` includes.

``/video`` brings a Synthesia video in, samples its frames and reads the
falling rectangles off them; ``/frame-examples`` is where a detection rule earns
its place before it is trusted on one.

``/matrix`` runs the model and serves the notes it heard. ``/time`` turns those
notes into peaks, a ladder and a drawable score. The ``/notation`` router, which
built a beats-based score document, was deleted in P4.2 together with the tab
that read it.
"""

from aitu_backend.api.audio import router as audio_router
from aitu_backend.api.editing import router as editing_router
from aitu_backend.api.frame_examples import router as frame_examples_router
from aitu_backend.api.library import router as library_router
from aitu_backend.api.matrix import router as matrix_router
from aitu_backend.api.scores import router as scores_router
from aitu_backend.api.time_score import router as time_score_router
from aitu_backend.api.video import router as video_router
from aitu_backend.api.youtube import router as youtube_router

#: Included by the app factory in this order.
ALL_ROUTERS = [
    scores_router,
    audio_router,
    editing_router,
    matrix_router,
    library_router,
    youtube_router,
    time_score_router,
    frame_examples_router,
    video_router,
]

__all__ = [
    "ALL_ROUTERS",
    "audio_router",
    "editing_router",
    "frame_examples_router",
    "library_router",
    "matrix_router",
    "scores_router",
    "time_score_router",
    "video_router",
    "youtube_router",
]
