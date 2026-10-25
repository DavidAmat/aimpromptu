"""`/sheet` — the new piano sheet of a part (implementation 03, Phase 5).

* `GET /sheet/{uuid}?width=N` — the sheet as it is now, drawn for a page `N` staff spaces wide: the SVG (a
  `data-note="<frame>:<midi>"` on every notehead), one row per drawn column (system, frame, x, ms: the cursor map),
  one box per system, the segments of the piece-by-piece view and their state, and the state of Sonnet on the part.
  While Sonnet writes, the answer is the sheet of that moment (`part_sheet.job.LiveRun`).
* `POST /sheet/{uuid}/llm` — start Sonnet on the part (or answer the run already going). The page follows the job
  on `GET /matrix/progress/{jobId}`: an `event: sheet` message each time the sheet changes, then `event: done`.

The sheet is never stale for the page: a sheet stored for older notes is laid again on the current ones
(`part_sheet.build`). What the old Sheet step saved (`sheet.json`, vexflow-v2) is not read here, except the armadura
and the reference figure of a part Sonnet never wrote.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from aitu_backend.audio import store as audio_store
from aitu_backend.auth import context, rights
from aitu_backend.part_sheet import build, job
from aitu_backend.part_sheet import store as new_sheet_store
from aitu_backend.storage import locate
from aitu_backend.transcription import pipeline

router = APIRouter(prefix="/sheet", tags=["sheet"])

#: The staff width a page that sends none is drawn for (the research's, Phase 3).
DEFAULT_WIDTH = 130.0


def _notes_or_404(audio_uuid: str) -> None:
    if not audio_store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")
    if not pipeline.has_events(audio_uuid):
        raise HTTPException(
            status_code=409,
            detail="Transcribe the audio first: the sheet is written from its notes.",
        )


def _llm_state(audio_uuid: str, drawn: build.Drawn, running: Any) -> dict[str, Any]:
    """What the page may do with Sonnet on this part."""
    user = context.current()
    access = rights.part_access(user, audio_uuid) if user is not None else rights.Access.WRITE
    writes = access >= rights.Access.WRITE
    where = locate.part(audio_uuid)
    # The owner's own version of My library changes through Edit: the button opens the copy and starts there.
    via_edit = (
        not writes and user is not None and where.layer == "private" and where.owner_id == user.id
    )
    available = job.available()
    # A new transcription asked for Sonnet (``sheet.pending``); the parts made before Phase 5 never did.
    fresh = drawn.record is None and new_sheet_store.asked(audio_uuid)
    return {
        "state": (
            "running" if running is not None else ("done" if drawn.record is not None else "none")
        ),
        "jobId": running.id if running is not None else None,
        "available": available,
        "auto": available and writes and running is None and fresh,
        # Always offered: **Enhance with AI**, or **Enhance it again with AI** on a sheet it enhanced.
        "canRun": available and writes and running is None,
        "viaEdit": available and via_edit,
        "enhanced": drawn.record is not None and drawn.record.enhanced,
        "runs": drawn.record.runs if drawn.record is not None else 0,
        "usd": drawn.record.usd if drawn.record is not None else None,
        "written": drawn.record.written if drawn.record is not None else None,
    }


@router.get("/{audio_uuid}")
def get_sheet(
    audio_uuid: str, width: float = Query(DEFAULT_WIDTH, ge=build.MIN_WIDTH, le=build.MAX_WIDTH)
) -> dict[str, Any]:
    """The sheet of a part now, drawn for a page of `width` staff spaces."""
    _notes_or_404(audio_uuid)
    stored = pipeline.load_note_events(audio_uuid)
    if stored is None or not any(not event.removed for event in stored.events):
        # A blank sheet (From scratch, Phase 8 of implementation 02): nothing to draw; the page shows the old
        # sheet's empty state, with Record a passage and Paste.
        return {
            "svg": "",
            "columns": [],
            "systems": [],
            "width": width + 8,
            "height": 0,
            "segments": [],
            "source": "algorithm",
            "stale": False,
            "llm": {
                "state": "none",
                "jobId": None,
                "available": job.available(),
                "auto": False,
                "canRun": False,
                "viaEdit": False,
                "enhanced": False,
                "runs": 0,
                "usd": None,
                "written": None,
            },
            "timings": {},
        }
    running = job.job_of(audio_uuid)
    run = job.live(audio_uuid) if running is not None else None
    drawn = build.current(audio_uuid)
    if run is not None:
        text, segments = run.text(), run.segments()
    else:
        text, segments = drawn.text, drawn.windows
    try:
        picture = build.draw(text, width)
    except Exception as exc:  # pragma: no cover - a sheet the engine cannot draw is a bug to see
        raise HTTPException(status_code=500, detail=f"The sheet could not be drawn: {exc}") from exc
    return {
        **picture,
        "segments": [{"start": a, "end": b, "state": s} for a, b, s in segments],
        "source": drawn.source,
        "stale": drawn.stale,
        "llm": _llm_state(audio_uuid, drawn, running),
    }


@router.post("/{audio_uuid}/llm", status_code=202)
def run_llm(audio_uuid: str) -> dict[str, str]:
    """Sonnet writes the sheet of the part in the background (the hands and the reading); the page follows it."""
    _notes_or_404(audio_uuid)
    if not job.available():
        raise HTTPException(status_code=409, detail="The AI is not set up on this machine.")
    started = job.start(audio_uuid)
    return {"jobId": started.id, "status": started.status}
