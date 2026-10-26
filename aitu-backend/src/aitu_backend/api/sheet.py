"""`/sheet` — the new piano sheet of a part (implementation 03, Phase 5).

* `GET /sheet/{uuid}?width=N` — the sheet as it is now, drawn for a page `N` staff spaces wide: the SVG (a
  `data-note="<frame>:<midi>"` on every notehead), one row per drawn column (system, frame, x, ms: the cursor map),
  one box per system, the segments of the piece-by-piece view and their state, and the state of Sonnet on the part.
  While Sonnet writes, the answer is the sheet of that moment (`part_sheet.job.LiveRun`).
* `POST /sheet/{uuid}/llm` — start Sonnet on the part (or answer the run already going). The page follows the job
  on `GET /matrix/progress/{jobId}`: an `event: sheet` message each time the sheet changes, then `event: done`.
* `POST /sheet/{uuid}/hands?width=N` — give notes to one hand (Phase 6: `part_sheet.edits`), and
  `POST /sheet/{uuid}/undo` and `/redo` — walk the steps of the part's log. Each answers the sheet drawn again, as
  `GET` does, so one edit is one request. Refused (409) while the AI writes the sheet: the segments still waiting
  cannot be edited, and its hands would replace the ones moved meanwhile.
* `POST /sheet/{uuid}/reading?width=N` — one reading edit of the toolboxes (Phase 7, `part_sheet.reading`):
  figures, fingers, beams, the grace note switch, ornaments, and the armadura, clefs and 8va of a stretch.
  `POST /sheet/{uuid}/remove` takes notes off the page. A refused edit answers 400 with the reason.
* `GET /sheet/{uuid}/stretch?start=A&end=B` — the armadura in force at a stretch and the one with the fewest signs
  over it. `POST /sheet/{uuid}/llm/stretch` — the AI writes a stretch again with the user's words (one request,
  in the background; the page follows the job as for a whole run).

The sheet is never stale for the page: a sheet stored for older notes is laid again on the current ones
(`part_sheet.build`). What the old Sheet step saved (`sheet.json`, vexflow-v2) is not read here, except the armadura
and the reference figure of a part Sonnet never wrote.
"""

from __future__ import annotations

from typing import Any

from typing import Literal

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import store as audio_store
from aitu_backend.auth import context, rights
from aitu_backend.part_sheet import build, edits, job, reading
from aitu_backend.part_sheet import store as new_sheet_store
from aitu_backend.sheet.engrave import frames as frames_engine
from aitu_backend.sheet.sheet import f1
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


def _writes(audio_uuid: str) -> bool:
    user = context.current()
    access = rights.part_access(user, audio_uuid) if user is not None else rights.Access.WRITE
    return access >= rights.Access.WRITE


def _llm_state(audio_uuid: str, drawn: build.Drawn, running: Any) -> dict[str, Any]:
    """What the page may do with Sonnet on this part."""
    user = context.current()
    writes = _writes(audio_uuid)
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
    return _answer(audio_uuid, width)


def _answer(audio_uuid: str, width: float) -> dict[str, Any]:
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
            "notes": [],
            "reading": {"key": 0, "keyChanges": [], "clefs": {}, "clefChanges": []},
            "titles": {},
            "lyrics": [],
            "quarterMs": None,
            "spaceMs": None,
            "lineSpace": None,
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
            "editable": False,
            "history": {"undo": None, "redo": None},
            "timings": {},
        }
    running = job.job_of(audio_uuid)
    run = job.live(audio_uuid) if running is not None else None
    drawn = build.current(audio_uuid)
    if run is not None:
        text, segments = run.text(), run.segments()
    else:
        # The stretches the AI wrote again (Phase 7) after the windows: the page reveals the one that came back.
        stretches = drawn.record.stretches if drawn.record is not None else []
        text = drawn.text
        segments = list(drawn.windows) + [(int(a), int(b), "llm") for a, b, *_ in stretches]
    try:
        picture = build.draw(text, width)
    except Exception as exc:  # pragma: no cover - a sheet the engine cannot draw is a bug to see
        raise HTTPException(status_code=500, detail=f"The sheet could not be drawn: {exc}") from exc
    ends = edits.note_ends(stored.events)
    for note in picture["notes"]:
        note["end"] = ends.get(note["ref"])
    return {
        **picture,
        "segments": [{"start": a, "end": b, "state": s} for a, b, s in segments],
        "source": drawn.source,
        "stale": drawn.stale,
        "llm": _llm_state(audio_uuid, drawn, running),
        # The notes can be edited by a user who may change the part, when the AI is not writing it (plan 3.7).
        "editable": running is None and _writes(audio_uuid),
        "history": edits.history(audio_uuid),
    }


class HandsRequest(BaseModel):
    #: The notes as their noteheads name them: ``"<frame>:<midi>"`` (``data-note``).
    notes: list[str] = Field(default_factory=list, max_length=20000)
    hand: Literal["right", "left"]


def _not_running(audio_uuid: str) -> None:
    if job.job_of(audio_uuid) is not None:
        raise HTTPException(
            status_code=409, detail="The AI is enhancing this sheet: wait until it is done."
        )


@router.post("/{audio_uuid}/hands")
def move_hands(
    audio_uuid: str,
    body: HandsRequest = Body(...),
    width: float = Query(DEFAULT_WIDTH, ge=build.MIN_WIDTH, le=build.MAX_WIDTH),
) -> dict[str, Any]:
    """Give the notes to one hand, in `notes.pmn` (one step of undo); the sheet drawn again."""
    _notes_or_404(audio_uuid)
    _not_running(audio_uuid)
    done = edits.move_hands(audio_uuid, body.notes, body.hand)
    return {**_answer(audio_uuid, width), "moved": done.moved, "unmatched": done.unmatched}


class ReadingRequest(BaseModel):
    action: Literal[reading.ACTIONS]  # type: ignore[valid-type]
    #: The notes picked, as their noteheads name them (the note toolbox).
    notes: list[str] = Field(default_factory=list, max_length=20000)
    #: The stretch marked, in frames, ``end`` excluded (the range toolbox).
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)
    staff: Literal["both", "right", "left"] = "both"
    #: The figure (``8``), the fingers (``[1, 3, 5]``), the grace switch (``"on"``, ``"off"``), the ornament
    #: (``"trill"``), the armadura (fifths), the clef (``"treble"``), the octave line (``1``, ``2``, ``-1``,
    #: ``-2``, ``0``); ``null`` gives the notes back to the rule (or the stretch its piece's armadura, the hand's
    #: own clef).
    value: Any = None


@router.post("/{audio_uuid}/reading")
def edit_reading(
    audio_uuid: str,
    body: ReadingRequest = Body(...),
    width: float = Query(DEFAULT_WIDTH, ge=build.MIN_WIDTH, le=build.MAX_WIDTH),
    preview: bool = Query(False),
) -> dict[str, Any]:
    """One reading edit of the toolboxes (one step of undo); the sheet drawn again. ``preview`` stores nothing and
    answers the sheet as the edit would leave it (Transpose figures, Phase 8)."""
    _notes_or_404(audio_uuid)
    _not_running(audio_uuid)
    try:
        change, holds = reading.plan(
            body.action,
            notes=body.notes,
            start=body.start,
            end=body.end,
            staff=body.staff,
            value=body.value,
        )
        if preview:
            label, text = edits.preview_reading(audio_uuid, change, holds)
            return {**build.draw(text, width), "edited": label}
        label = edits.edit_reading(audio_uuid, change, holds)
    except (reading.Refused, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**_answer(audio_uuid, width), "edited": label}


class TransposeRequest(BaseModel):
    semitones: int = Field(ge=-48, le=48)


@router.post("/{audio_uuid}/transpose")
def transpose(
    audio_uuid: str,
    body: TransposeRequest = Body(...),
    width: float = Query(DEFAULT_WIDTH, ge=build.MIN_WIDTH, le=build.MAX_WIDTH),
    preview: bool = Query(False),
) -> dict[str, Any]:
    """Transpose notes (Phase 8): every note of the part moved, the stored sheet with it (one step of undo).
    ``preview`` writes nothing and answers the sheet as it would be."""
    _notes_or_404(audio_uuid)
    _not_running(audio_uuid)
    try:
        done = edits.transpose_notes(audio_uuid, body.semitones, preview=preview)
    except reading.Refused as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    facts = {"edited": done.label, "moved": done.moved, "outside": done.outside}
    if preview:
        return {**build.draw(done.text, width), **facts}
    return {**_answer(audio_uuid, width), **facts}


class AddNoteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    frame: int = Field(ge=0)
    midi: int = Field(ge=0, le=127)
    hand: Literal["right", "left"]
    #: How long it sounds; absent: a negra of the sheet's reference figure.
    length_ms: float | None = Field(default=None, alias="lengthMs", gt=0)


@router.post("/{audio_uuid}/add")
def add_note(
    audio_uuid: str,
    body: AddNoteRequest = Body(...),
    width: float = Query(DEFAULT_WIDTH, ge=build.MIN_WIDTH, le=build.MAX_WIDTH),
) -> dict[str, Any]:
    """A note added on the keyboard panel (Phase 8), into `notes.pmn` (one step of undo); the sheet drawn again."""
    _notes_or_404(audio_uuid)
    _not_running(audio_uuid)
    try:
        label = edits.add_note(audio_uuid, body.frame, body.midi, body.hand, body.length_ms)
    except (reading.Refused, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**_answer(audio_uuid, width), "edited": label}


@router.get("/{audio_uuid}/pages")
def pages(
    audio_uuid: str,
    width: float = Query(..., ge=40.0, le=build.MAX_WIDTH),
    height: float = Query(..., ge=20.0, le=1000.0),
    first: float | None = Query(None, ge=10.0, le=1000.0),
    gap: float | None = Query(None, ge=0.0, le=40.0),
) -> dict[str, Any]:
    """The sheet on paper (Print to PDF, Phase 8): whole lines dealt onto pages ``height`` staff spaces high (the
    first one ``first``, under its title), drawn ``width`` staff spaces wide; ``gap`` between two lines.
    """
    _notes_or_404(audio_uuid)
    stored = pipeline.load_note_events(audio_uuid)
    if stored is None or not any(not event.removed for event in stored.events):
        return {"pages": []}
    text = build.current(audio_uuid).text
    sheet = f1.read(text)
    return {
        "pages": frames_engine.render_pages(
            sheet,
            frames_engine.Options(width=width),
            page_height=height,
            first_height=first,
            gap=gap,
        ),
        **build.sheet_settings(sheet),
    }


class NotesRequest(BaseModel):
    notes: list[str] = Field(default_factory=list, max_length=20000)


@router.post("/{audio_uuid}/remove")
def remove_notes(
    audio_uuid: str,
    body: NotesRequest = Body(...),
    width: float = Query(DEFAULT_WIDTH, ge=build.MIN_WIDTH, le=build.MAX_WIDTH),
) -> dict[str, Any]:
    """Take notes off the page: marked removed in `notes.pmn` (one step of undo); the sheet drawn again."""
    _notes_or_404(audio_uuid)
    _not_running(audio_uuid)
    done = edits.remove_notes(audio_uuid, body.notes)
    return {**_answer(audio_uuid, width), "moved": done.moved, "unmatched": done.unmatched}


@router.get("/{audio_uuid}/stretch")
def stretch_keys(
    audio_uuid: str, start: int = Query(..., ge=0), end: int = Query(..., ge=0)
) -> dict[str, int]:
    """The armadura in force at the start of a stretch and the one that prints the fewest signs over it."""
    _notes_or_404(audio_uuid)
    return reading.fewest_signs(f1.read(build.current(audio_uuid).text), start, end)


class StretchRequest(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    staff: Literal["both", "right", "left"] = "both"
    #: The notes picked, when the stretch comes from the note toolbox.
    notes: list[str] = Field(default_factory=list, max_length=2000)
    instruction: str = Field(default="", max_length=1000)


@router.post("/{audio_uuid}/llm/stretch", status_code=202)
def run_llm_stretch(audio_uuid: str, body: StretchRequest = Body(...)) -> dict[str, str]:
    """The AI writes the stretch again with the user's words, in the background; the page follows the job."""
    _notes_or_404(audio_uuid)
    if not job.available():
        raise HTTPException(status_code=409, detail="The AI is not set up on this machine.")
    if body.end <= body.start:
        raise HTTPException(status_code=400, detail="The stretch is empty.")
    if not _writes(audio_uuid):
        raise HTTPException(status_code=403, detail="This sheet cannot be changed here.")
    try:
        started = job.start_stretch(
            audio_uuid,
            start=body.start,
            end=body.end,
            instruction=body.instruction,
            staff={"right": 1, "left": 2}.get(body.staff),
            picked=body.notes or None,
        )
    except job.Busy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"jobId": started.id, "status": started.status}


@router.post("/{audio_uuid}/undo")
def undo(
    audio_uuid: str, width: float = Query(DEFAULT_WIDTH, ge=build.MIN_WIDTH, le=build.MAX_WIDTH)
) -> dict[str, Any]:
    """Take the last step of the part's log back; the sheet drawn again."""
    _notes_or_404(audio_uuid)
    _not_running(audio_uuid)
    label = edits.undo(audio_uuid)
    return {**_answer(audio_uuid, width), "walked": label}


@router.post("/{audio_uuid}/redo")
def redo(
    audio_uuid: str, width: float = Query(DEFAULT_WIDTH, ge=build.MIN_WIDTH, le=build.MAX_WIDTH)
) -> dict[str, Any]:
    """Put the last step taken back again; the sheet drawn again."""
    _notes_or_404(audio_uuid)
    _not_running(audio_uuid)
    label = edits.redo(audio_uuid)
    return {**_answer(audio_uuid, width), "walked": label}


@router.post("/{audio_uuid}/llm", status_code=202)
def run_llm(audio_uuid: str) -> dict[str, str]:
    """Sonnet writes the sheet of the part in the background (the hands and the reading); the page follows it."""
    _notes_or_404(audio_uuid)
    if not job.available():
        raise HTTPException(status_code=409, detail="The AI is not set up on this machine.")
    started = job.start(audio_uuid)
    return {"jobId": started.id, "status": started.status}
