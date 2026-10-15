"""`/passages` — Recording in Sheet (implementation 02, plan section 13, Phase 9).

**Record this passage** opens a passage of a part: a copy of the marked frames (the *Current*),
and the takes recorded for it (each a *Proposal* once it is read). A passage and its takes are
projects of the user's Personal Vault, hidden from every list; their parts answer the routes of
any part (`/audio`, `/time`, `/pieces`), which is how the page draws and edits them.

The path names the passage's project (`project_id`), so the rights of section 9.3 apply to it as to
any project; opening one checks the user may write the part it is about. **Promote** writes the
take into that part in one write and closes the passage; the part keeps its earlier state for the
undo (`POST /time/{uuid}/versions/{n}/restore`).
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio.formats import ConversionFailed, FfmpegMissing
from aitu_backend.auth.dependencies import require_part
from aitu_backend.editing import passages
from aitu_backend.editing.paste import PasteError
from aitu_backend.schemas.rhythm import SavedRhythm
from aitu_backend.storage import locate
from aitu_backend.transcription import jobs

router = APIRouter(prefix="/passages", tags=["passages"])


class OpenIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    #: The part the passage is of.
    part: str
    #: The stretch, in ms of the part; ``toMs`` equal to ``fromMs`` is a moment (a new passage).
    from_ms: float = Field(..., alias="fromMs", ge=0)
    to_ms: float = Field(..., alias="toMs", ge=0)


class PatchIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    take: str | None = None
    speed: float | None = Field(None, gt=0)
    window_ms: float | None = Field(None, alias="windowMs", ge=0)


class ReadIn(BaseModel):
    """The stretch of the take to keep, in seconds of the recording."""

    model_config = ConfigDict(populate_by_name=True)

    from_seconds: float = Field(..., alias="fromSeconds", ge=0)
    to_seconds: float = Field(..., alias="toSeconds", gt=0)


class PromoteIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    #: ``window``: the stretch of the take under the window, fitted into the passage (the song
    #: keeps its length); ``whole``: the whole take in place of the passage.
    mode: Literal["window", "whole"]
    #: ``original`` (a window only): only the notes change; ``recording``: the take's audio too.
    audio: Literal["original", "recording"] = "recording"
    #: The Proposal's sheet as the page holds it; absent: the take's saved sheet.
    sheet: SavedRhythm | None = None


class FactsOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: str
    audio: str
    notes_out: int = Field(..., alias="notesOut")
    notes_in: int = Field(..., alias="notesIn")
    #: The marks of the passage that go, by their field in ``sheet.json`` (``fingers``,
    #: ``ottavas`` ...); kinds with none are left out.
    marks_dropped: dict[str, int] = Field(..., alias="marksDropped")
    #: How much longer (or, below zero, shorter) the song gets, in ms.
    length_change_ms: float = Field(..., alias="lengthChangeMs")
    duration_seconds: float = Field(..., alias="durationSeconds")


class PromotedOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    part: str
    project_id: str = Field(..., alias="projectId")
    #: The earlier state of the part: ``POST /time/{part}/versions/{n}/restore`` is the undo.
    before_version: int = Field(..., alias="beforeVersion")
    at_ms: float = Field(..., alias="atMs")
    length_ms: float = Field(..., alias="lengthMs")
    sheet: SavedRhythm | None = None


class JobHandle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(..., alias="jobId")
    status: str


def _refused(exc: Exception) -> HTTPException:
    if isinstance(exc, locate.NotFound):
        return HTTPException(status_code=404, detail="That passage or take is not there any more.")
    if isinstance(exc, (passages.PassageError, PasteError)):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, FfmpegMissing):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, ConversionFailed):
        return HTTPException(status_code=422, detail=str(exc))
    raise exc


def _answer(passage_id: str, status_code: int = 200) -> Response:
    try:
        body = passages.describe(passage_id)
    except locate.NotFound as exc:
        raise _refused(exc) from exc
    return JSONResponse(body, status_code=status_code)


def _take_of(project_id: str, take: str) -> None:
    try:
        if take not in passages.load(project_id).takes:
            raise locate.NotFound("take", take)
    except locate.NotFound as exc:
        raise _refused(exc) from exc


@router.post("", status_code=201)
def open_passage(body: OpenIn = Body(...)) -> Response:
    """**Record this passage**: a passage of a part the user may write (a version of the library
    answers `403`). Answers the passage."""
    require_part(body.part, write=True)
    try:
        passage_id = passages.open_passage(body.part, body.from_ms, body.to_ms)
    except (locate.NotFound, passages.PassageError, PasteError) as exc:
        raise _refused(exc) from exc
    return _answer(passage_id, 201)


@router.get("/{project_id}")
def get_passage(project_id: str) -> Response:
    """The passage: the part and the stretch, the Current (`current`, a part), what a figure lasts
    there, the takes and their state, the take on show, the speed and the window."""
    return _answer(project_id)


@router.patch("/{project_id}")
def patch_passage(project_id: str, body: PatchIn = Body(...)) -> Response:
    """The take on show, the speed (×0.25 to ×4) and where the window lies."""
    try:
        passages.update(project_id, take=body.take, speed=body.speed, window_ms=body.window_ms)
    except (locate.NotFound, passages.PassageError) as exc:
        raise _refused(exc) from exc
    return _answer(project_id)


@router.delete("/{project_id}", status_code=204)
def discard_passage(project_id: str) -> Response:
    """The passage and its takes deleted; the part is not touched."""
    try:
        passages.discard(project_id)
    except locate.NotFound as exc:
        raise _refused(exc) from exc
    return Response(status_code=204)


@router.post("/{project_id}/takes", status_code=201)
def add_take(
    project_id: str,
    file: Annotated[UploadFile | None, File()] = None,
    notes: Annotated[str | None, Form()] = None,
) -> Response:
    """A take of the passage, the one on show: a recording (multipart ``file``), the keys played on
    a MIDI piano (``notes``, a JSON list of ``{midiNote, start, end, velocity}`` in seconds from the
    start of the recording), or both."""
    if file is not None and not file.filename:
        raise HTTPException(status_code=422, detail="The uploaded file has no name")
    try:
        played = (
            [passages.MidiNote.model_validate(item) for item in json.loads(notes)]
            if notes
            else None
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"The notes are not readable: {exc}") from exc
    try:
        passages.add_take(
            project_id,
            file.file if file is not None else None,
            file.filename if file is not None else None,
            played,
        )
    except (locate.NotFound, passages.PassageError, FfmpegMissing, ConversionFailed) as exc:
        raise _refused(exc) from exc
    return _answer(project_id, 201)


@router.delete("/{project_id}/takes/{take}")
def delete_take(project_id: str, take: str) -> Response:
    _take_of(project_id, take)
    try:
        passages.delete_take(project_id, take)
    except locate.NotFound as exc:
        raise _refused(exc) from exc
    return _answer(project_id)


@router.post("/{project_id}/takes/{take}/read", status_code=202, response_model=JobHandle)
def read_take(project_id: str, take: str, body: ReadIn = Body(...)) -> JobHandle:
    """**Write the proposal**: keep the stretch of the take, transcribe it, split the hands and
    write its first sheet with the passage's key and figure, as one job on the GPU queue. Followed
    on `GET /matrix/progress/{jobId}` (the live notes of the transcription included)."""
    _take_of(project_id, take)
    if body.to_seconds <= body.from_seconds:
        raise HTTPException(status_code=422, detail="The end of the take is before its start.")

    def work(reporter: Any) -> dict[str, str]:
        passages.read_take(project_id, take, body.from_seconds, body.to_seconds, reporter=reporter)
        return {"take": take}

    job = jobs.submit(
        work, gpu=True, key=passages.take_job_key(take), describe=lambda result: result
    )
    return JobHandle(job_id=job.id, status=job.status)


@router.post("/{project_id}/promotion", response_model=FactsOut, response_model_by_alias=True)
def promotion_facts(project_id: str, body: PromoteIn = Body(...)) -> FactsOut:
    """What **Promote** would do, without writing: the notes out and in, the marks that go, and
    how much longer or shorter the song gets."""
    try:
        found = passages.facts(project_id, body.mode, body.audio, body.sheet)
    except (locate.NotFound, passages.PassageError, PasteError) as exc:
        raise _refused(exc) from exc
    return FactsOut(
        mode=found.mode,
        audio=found.audio,
        notes_out=found.notes_out,
        notes_in=found.notes_in,
        marks_dropped=found.marks_dropped,
        length_change_ms=found.length_change_ms,
        duration_seconds=found.duration_seconds,
    )


@router.post("/{project_id}/promote", response_model=PromotedOut, response_model_by_alias=True)
def promote(project_id: str, body: PromoteIn = Body(...)) -> PromotedOut:
    """**Promote**: the take into the part in place of the passage, notes, marks and audio in one
    write; the passage is closed. The part keeps its earlier state (`beforeVersion`)."""
    try:
        require_part(passages.load(project_id).passage_of, write=True)
        done = passages.promote(project_id, body.mode, body.audio, body.sheet)
    except (
        locate.NotFound,
        passages.PassageError,
        PasteError,
        FfmpegMissing,
        ConversionFailed,
    ) as exc:
        raise _refused(exc) from exc
    return PromotedOut(
        part=done.part,
        project_id=done.project_id,
        before_version=done.before_version,
        at_ms=done.at_ms,
        length_ms=done.length_ms,
        sheet=done.sheet,
    )
