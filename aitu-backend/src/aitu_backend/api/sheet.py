"""`/sheet` — the new piano sheet of a part (implementation 03, Phase 5).

* `GET /sheet/{uuid}?width=N` — the sheet as it is now, drawn for a page `N` staff spaces wide: the SVG (a
  `data-note="<frame>:<midi>"` on every notehead), one row per drawn column (system, frame, x, ms: the cursor map),
  one box per system, the segments of the piece-by-piece view and their state (with the staff the AI writes, when
  it writes one hand), and the state of Sonnet on the part.
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
* `POST /sheet/{uuid}/paste?width=N` — a copied passage put in at the cursor or over a marked stretch (Phase 8B,
  `part_sheet.edits.paste_passage`): its notes, its sheet and its audio; one step of undo.
* `GET /sheet/{uuid}/stretch?start=A&end=B` — the armadura in force at a stretch and the one with the fewest signs
  over it. `POST /sheet/{uuid}/llm/stretch` — the AI writes a stretch again with the user's words (one request,
  in the background; the page follows the job as for a whole run), of both hands or of one (the other fixed).
* `POST /sheet/{uuid}/llm/simplify` — the AI simplifies one hand, or both, over the whole song, batch after batch
  (implementation 04, Phase 4); one step of undo. `GET /sheet/{uuid}/llm/costs` — what each run of the Enhance with
  AI dialog would cost, about.
* The levels (implementation 04-3, Phase 4): `GET /sheet/levels/catalog` — the catalog of patterns of Enhance with
  AI and the patterns used when none is selected; `GET /sheet/levels/catalog/{hand}/{level}/{number}.svg` — the
  drawing of a pattern's example by the app's engine. `POST /sheet/{uuid}/llm/level` — the AI writes a range again
  at a level, in place (one step of undo); `POST /sheet/{uuid}/llm/level-copy` — a level of the whole sheet, written
  into a new project of My projects (the level copy), whose ids it answers.
* `GET` and `PUT /sheet/{uuid}/words` — the pasted lyrics of the part and its pool of pieces (the Lyrics tab), kept
  in `project.json`, not in the sheet (moved from `/time/{uuid}/lyrics` in implementation 03, Phase 10).

The sheet is never stale for the page: a sheet stored for older notes is laid again on the current ones
(`part_sheet.build`). What the old Sheet step saved (`sheet.json`, vexflow-v2) is not read here, except the armadura
and the reference figure of a part Sonnet never wrote.
"""

from __future__ import annotations

from typing import Any

from typing import Literal

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from fastapi.responses import Response

from aitu_backend.audio import store as audio_store
from aitu_backend.auth import context, rights
from aitu_backend.auth.dependencies import require_part
from aitu_backend.editing import paste as passage_paste
from aitu_backend.part_sheet import build, edits, job, reading
from aitu_backend.sheet.engrave import frames as frames_engine
from aitu_backend.sheet.sheet import f1
from aitu_backend.library import flow
from aitu_backend.sheet.llm import levels
from aitu_backend.storage import bundle, locate
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
    return {
        "state": (
            "running" if running is not None else ("done" if drawn.record is not None else "none")
        ),
        "jobId": running.id if running is not None else None,
        "available": available,
        # The AI never starts by itself: only the button starts it (the user, 2026-10-30; until then a new
        # transcription, marked ``sheet.pending``, went to the AI when its sheet first opened).
        "auto": False,
        # Always offered: **Enhance with AI**, or **Enhance it again with AI** on a sheet it enhanced.
        "canRun": available and writes and running is None,
        "viaEdit": available and via_edit,
        "enhanced": drawn.record is not None and drawn.record.enhanced,
        "runs": drawn.record.runs if drawn.record is not None else 0,
        "usd": drawn.record.usd if drawn.record is not None else None,
        "written": drawn.record.written if drawn.record is not None else None,
    }


# ------------------------------------------------------------------ the catalog of patterns (before /{audio_uuid})


class CatalogPattern(BaseModel):
    ref: str
    hand: str
    level: str
    number: int
    name: str
    line: str
    source: str | None = None
    bars: str | None = None


class CatalogOut(BaseModel):
    patterns: list[CatalogPattern]
    #: ``hand -> level -> refs``: the patterns a run uses for a hand when none is selected.
    defaults: dict[str, dict[str, list[str]]]


@router.get("/levels/catalog", response_model=CatalogOut)
def level_catalog() -> CatalogOut:
    """The catalog of patterns of Enhance with AI (the gallery of patterns, numbered inside each hand and level)."""
    patterns, defaults = levels.catalog_rows()
    return CatalogOut(patterns=[CatalogPattern(**p) for p in patterns], defaults=defaults)


_drawings: dict[str, str] = {}


@router.get("/levels/catalog/{hand}/{level}/{number}.svg")
def level_drawing(hand: Literal["left", "right"], level: str, number: int) -> Response:
    """A pattern's example drawn by the app's engine (``super-hard`` for super hard), kept in memory once drawn."""
    ref = f"{hand} {level.replace('-', ' ')} {number}"
    pattern = levels.catalog().get(ref)
    if pattern is None:
        raise HTTPException(status_code=404, detail=f"No pattern '{ref}'")
    if ref not in _drawings:
        _drawings[ref] = frames_engine.render_frames(pattern.example, px_per_space=10.0, note_ids=False).svg
    return Response(
        _drawings[ref], media_type="image/svg+xml", headers={"Cache-Control": "max-age=86400"}
    )


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
        # A blank sheet (From scratch, Phase 8 of implementation 02): nothing to draw; the page shows its empty
        # state, with Record a passage and Paste (Phase 8B), and Undo after a paste.
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
            "editable": job.job_of(audio_uuid) is None and _writes(audio_uuid),
            "history": edits.history(audio_uuid),
            "audioRevision": stored.header.audio_revision if stored is not None else 0,
            "timings": {},
        }
    running = job.job_of(audio_uuid)
    run = job.live(audio_uuid) if running is not None else None
    drawn = build.current(audio_uuid)
    # The staff of a run of one hand: the page veils only that staff of the segment at the AI.
    staff = run.staff if run is not None else None
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
        "segments": [
            {"start": a, "end": b, "state": s, **({"staff": staff} if staff is not None else {})}
            for a, b, s in segments
        ],
        "source": drawn.source,
        "stale": drawn.stale,
        "llm": _llm_state(audio_uuid, drawn, running),
        # The notes can be edited by a user who may change the part, when the AI is not writing it (plan 3.7).
        "editable": running is None and _writes(audio_uuid),
        "history": edits.history(audio_uuid),
        # A paste and its undo change the audio too: the page's player loads it again when this changes.
        "audioRevision": stored.header.audio_revision,
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


class DuplicateRequest(BaseModel):
    notes: list[str] = Field(min_length=1, max_length=200)
    #: The figure of the copies: 2 blanca ... 32 fusa; shorter than each note's own.
    figure: int = Field(ge=2, le=64)


@router.post("/{audio_uuid}/duplicate")
def duplicate_notes(
    audio_uuid: str,
    body: DuplicateRequest = Body(...),
    width: float = Query(DEFAULT_WIDTH, ge=build.MIN_WIDTH, le=build.MAX_WIDTH),
) -> dict[str, Any]:
    """**Duplicate** of the note toolbox: each picked note played again at a shorter figure, filling its own time
    (a negra into two corcheas), into `notes.pmn` (one step of undo); the sheet drawn again."""
    _notes_or_404(audio_uuid)
    _not_running(audio_uuid)
    try:
        label = edits.duplicate_notes(audio_uuid, body.notes, body.figure)
    except (reading.Refused, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**_answer(audio_uuid, width), "edited": label}


@router.post("/{audio_uuid}/unite")
def unite_notes(
    audio_uuid: str,
    body: NotesRequest = Body(...),
    width: float = Query(DEFAULT_WIDTH, ge=build.MIN_WIDTH, le=build.MAX_WIDTH),
) -> dict[str, Any]:
    """**Unite** of the note toolbox: consecutive chords of the same keys and figure become one chord of the figure
    that fills their time (two semicorcheas into a corchea), in `notes.pmn` (one step of undo); the sheet drawn
    again."""
    _notes_or_404(audio_uuid)
    _not_running(audio_uuid)
    try:
        label = edits.unite_notes(audio_uuid, body.notes)
    except (reading.Refused, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**_answer(audio_uuid, width), "edited": label}


class PasteSource(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    part: str
    from_ms: float = Field(alias="fromMs", ge=0)
    to_ms: float = Field(alias="toMs", gt=0)


class PasteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: PasteSource
    #: Where the passage goes, in ms of this part: the cursor, or the start of the marked stretch it replaces.
    at_ms: float = Field(alias="atMs", ge=0)
    #: The end of the marked stretch the passage replaces; absent to put it in at ``atMs``.
    replace_to_ms: float | None = Field(default=None, alias="replaceToMs", gt=0)


@router.post("/{audio_uuid}/paste")
def paste_passage(
    audio_uuid: str,
    body: PasteRequest = Body(...),
    width: float = Query(DEFAULT_WIDTH, ge=build.MIN_WIDTH, le=build.MAX_WIDTH),
) -> dict[str, Any]:
    """Paste a copied passage (Phase 8B): its notes, its sheet and its audio, at ``atMs`` or over ``[atMs,
    replaceToMs)``; everything after moves by its length. One step of undo; the sheet drawn again. The source is any
    part the user may read; another one answers 404."""
    if not audio_store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")
    _not_running(audio_uuid)
    require_part(body.source.part, write=False)
    try:
        done = edits.paste_passage(
            audio_uuid,
            body.source.part,
            body.source.from_ms,
            body.source.to_ms,
            at_ms=body.at_ms,
            replace_to_ms=body.replace_to_ms,
        )
    except locate.NotFound:
        raise HTTPException(status_code=404, detail="The copied passage is not there any more.")
    except passage_paste.PasteError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        **_answer(audio_uuid, width),
        "edited": done.label,
        "atMs": done.at_ms,
        "lengthMs": done.length_ms,
        "notesIn": done.notes_in,
        "notesMoved": done.notes_moved,
        "notesRemoved": done.notes_removed,
    }


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


class SimplifyRequest(BaseModel):
    hand: Literal["both", "right", "left"]


@router.post("/{audio_uuid}/llm/simplify", status_code=202)
def run_llm_simplify(audio_uuid: str, body: SimplifyRequest = Body(...)) -> dict[str, str]:
    """The AI simplifies one hand, or both, over the whole song, in the background; the page follows the job."""
    _notes_or_404(audio_uuid)
    if not job.available():
        raise HTTPException(status_code=409, detail="The AI is not set up on this machine.")
    if not _writes(audio_uuid):
        raise HTTPException(status_code=403, detail="This sheet cannot be changed here.")
    try:
        started = job.start_simplify(audio_uuid, hand=body.hand)
    except job.Busy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"jobId": started.id, "status": started.status}


Level = Literal["easy", "medium", "hard"]


class LevelRequest(BaseModel):
    #: The level of each hand (the same for both by default).
    right: Level = "easy"
    left: Level = "easy"
    hand: Literal["both", "right", "left"] = "both"
    #: A range (``POST .../llm/level``): its first frame and its end; none for a level of the whole sheet.
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=1)
    #: The refs selected in the catalog ("left medium 2").
    patterns: list[str] = Field(default_factory=list, max_length=200)
    words: str = Field(default="", max_length=1000)

    def level(self) -> str | dict[str, str]:
        if self.hand == "right":
            return self.right
        if self.hand == "left":
            return self.left
        return self.right if self.right == self.left else {"right": self.right, "left": self.left}


LEVEL_TITLES = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}


def level_title(body: LevelRequest) -> str:
    """The name of a level copy after its song's: ``Easy``, ``Right hard, left medium``, ``Easy, left hand``."""
    level = body.level()
    if isinstance(level, dict):
        return f"Right {level['right']}, left {level['left']}"
    name = LEVEL_TITLES[level]
    return name if body.hand == "both" else f"{name}, {body.hand} hand"


def _start_level(part_id: str, body: LevelRequest, start: int | None, end: int | None) -> Any:
    try:
        return job.start_level(
            part_id,
            level=body.level(),
            hand=body.hand,
            start=start,
            end=end,
            patterns=body.patterns,
            words=body.words,
        )
    except job.Busy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{audio_uuid}/llm/level", status_code=202)
def run_llm_level(audio_uuid: str, body: LevelRequest = Body(...)) -> dict[str, str]:
    """The AI writes a range of the sheet again at a level, in place, in the background (one step of undo)."""
    _notes_or_404(audio_uuid)
    if not job.level_available():
        raise HTTPException(status_code=409, detail="The AI is not set up on this machine.")
    if body.start is None or body.end is None or body.end <= body.start:
        raise HTTPException(status_code=400, detail="Select a range first.")
    if not _writes(audio_uuid):
        raise HTTPException(status_code=403, detail="This sheet cannot be changed here.")
    started = _start_level(audio_uuid, body, body.start, body.end)
    return {"jobId": started.id, "status": started.status}


class LevelCopyOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(alias="jobId")
    project_id: str = Field(alias="projectId")
    part_id: str = Field(alias="partId")
    title: str


@router.post("/{audio_uuid}/llm/level-copy", status_code=202, response_model=LevelCopyOut, response_model_by_alias=True)
def run_llm_level_copy(audio_uuid: str, body: LevelRequest = Body(...)) -> LevelCopyOut:
    """A level of the whole sheet (plan section 5.8): a new project of My projects, a copy of the song named with the
    level ("99 Red Balloons · Easy"), where the AI writes the level in the background. The original does not
    change. The user's own projects and versions of My Library only."""
    user = context.current()
    where = locate.part(audio_uuid)
    if user is not None and (where.owner_id != user.id or where.layer not in ("vault", "private")):
        raise HTTPException(status_code=403, detail="Only your own songs can have a level.")
    _notes_or_404(audio_uuid)
    if not job.level_available():
        raise HTTPException(status_code=409, detail="The AI is not set up on this machine.")
    current = f1.read(build.current(audio_uuid).text)
    staffs = (1, 2) if body.hand == "both" else ((1,) if body.hand == "right" else (2,))
    if not levels.level_windows(current, staffs):
        raise HTTPException(status_code=400, detail="This hand has no notes.")
    source = bundle.read_project(where.project_id)
    title = f"{source.title} · {level_title(body)}"
    try:
        copy_id, parts = flow.level_copy(
            where.project_id, owner=user.id if user is not None else where.owner_id, title=title
        )
    except flow.Refused as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    part_id = parts[audio_uuid]
    started = _start_level(part_id, body, None, None)
    return LevelCopyOut(job_id=started.id, project_id=copy_id, part_id=part_id, title=title)


@router.get("/{audio_uuid}/llm/costs")
def llm_costs(
    audio_uuid: str,
    start: int | None = Query(None, ge=0),
    end: int | None = Query(None, ge=1),
) -> dict[str, Any]:
    """What each run of the Enhance with AI dialog would cost, about: requests and US dollars. With a range
    (``start``, ``end``), also a level of that range for each hand (``level-stretch-both`` ...)."""
    _notes_or_404(audio_uuid)
    out = job.costs(audio_uuid)
    if start is not None and end is not None and end > start:
        current = f1.read(build.current(audio_uuid).text)
        for hand in job.HANDS:
            out[f"level-stretch-{hand}"] = job.level_cost(current, hand, start, end)
    return out


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


class PartWords(BaseModel):
    """The words of the song attached to a part (the sheet toolbox's Lyrics tab)."""

    model_config = ConfigDict(populate_by_name=True)

    #: ``None`` or an empty text: no lyrics saved.
    text: str | None = Field(None, max_length=20000)
    #: The lyrics pieces of the pool, in order. ``None``: never saved here; on a ``PUT``, absent leaves the saved pool
    #: as it is.
    pool: list[str] | None = None


def _project_of_part(audio_uuid: str):
    if not audio_store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")
    try:
        return bundle.read_project(locate.part(audio_uuid).project_id)
    except locate.NotFound:
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'") from None


@router.get("/{audio_uuid}/words", response_model=PartWords, response_model_by_alias=True)
def get_words(audio_uuid: str) -> PartWords:
    """The lyrics and the pool saved with this part, so the Lyrics tab opens with them."""
    part = _project_of_part(audio_uuid).part(audio_uuid)
    return PartWords(text=part.lyrics, pool=part.lyrics_pool)


@router.put("/{audio_uuid}/words", response_model=PartWords, response_model_by_alias=True)
def put_words(audio_uuid: str, body: PartWords = Body(...)) -> PartWords:
    """Save the pasted lyrics and the pool with the part, in ``project.json``: **Save lyrics**.

    The song's words, not a reading of the page, so they are kept apart from the sheet and outlive a new
    transcription. Nothing else of the project changes. A version of My library answers ``403``.
    """
    text = (body.text or "").strip() or None
    project = _project_of_part(audio_uuid)
    with bundle.project_lock(project.id):
        project = bundle.read_project(project.id)
        part = project.part(audio_uuid)
        part.lyrics = text
        if "pool" in body.model_fields_set:
            part.lyrics_pool = [piece.strip() for piece in body.pool or [] if piece.strip()]
        bundle.write_project(project)
    return PartWords(text=text, pool=part.lyrics_pool)
