"""FastAPI routers, one module per product section.

Each module exposes a single ``router`` (an ``APIRouter`` with its URL prefix and
tag) that :mod:`aitu_backend.main` includes.

The text-notation MVP (``/scores`` and ``/sequence``) was deleted in implementation 02,
Phase 1 (Q-4), and the old Piano Library router (``/library``: playground, ``.npz``, promotions) in
Phase 3.
``/projects`` is the Personal Vault (Phase 3: duplicate; Phase 5: the rest). ``/auth`` signs in
and ``/admin`` is the master user's (Phase 4).

``/video`` brings a Synthesia video in, samples its frames and reads the
falling rectangles off them; ``/frame-examples`` is where a detection rule earns
its place before it is trusted on one.

``/matrix`` runs the model and serves the notes it heard. ``/time`` turns those
notes into peaks, a ladder and a drawable score. ``/pieces`` is the flow page's
view of a piece: the state of each step, the notes as columns, their edits and
the hand prediction (implementation 08, Phase 5). The ``/notation`` router, which
built a beats-based score document, was deleted in P4.2 together with the tab
that read it.
"""

from aitu_backend.api.admin import router as admin_router
from aitu_backend.api.audio import router as audio_router
from aitu_backend.api.auth import router as auth_router
from aitu_backend.api.editing import router as editing_router
from aitu_backend.api.frame_examples import router as frame_examples_router
from aitu_backend.api.matrix import router as matrix_router
from aitu_backend.api.pieces import router as pieces_router
from aitu_backend.api.projects import router as projects_router
from aitu_backend.api.time_score import router as time_score_router
from aitu_backend.api.video import router as video_router
from aitu_backend.api.youtube import router as youtube_router

#: Answer without a session: signing in (implementation 02, plan section 9.2).
OPEN_ROUTERS = [auth_router]
#: A session, then the rights of the project the route names (section 9.3).
USER_ROUTERS = [
    audio_router,
    editing_router,
    matrix_router,
    pieces_router,
    projects_router,
    youtube_router,
    time_score_router,
    video_router,
]
#: A session of the master user: Lab's examples and Admin.
MASTER_ROUTERS = [frame_examples_router, admin_router]

#: Included by the app factory in this order.
ALL_ROUTERS = OPEN_ROUTERS + USER_ROUTERS + MASTER_ROUTERS

__all__ = [
    "ALL_ROUTERS",
    "MASTER_ROUTERS",
    "OPEN_ROUTERS",
    "USER_ROUTERS",
    "admin_router",
    "audio_router",
    "auth_router",
    "editing_router",
    "frame_examples_router",
    "matrix_router",
    "pieces_router",
    "projects_router",
    "time_score_router",
    "video_router",
    "youtube_router",
]
