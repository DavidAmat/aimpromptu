"""`/pieces` — a piece as the flow page sees it: its steps, its notes, its edits, its hands.

Implementation 08, Phase 5 (plan sections 6.4, 8 and 9.6).

* `GET /pieces/{uuid}/status` — which steps are ready, running, stale or missing, and which tabs
  the flow page may open.
* `GET /pieces/{uuid}/notes` — the notes as columns, one list per field.
* `PATCH /pieces/{uuid}/notes` — a list of operations, refused with 409 when the page's
  `baseRevision` is old.

**Predict hands** (`POST /pieces/{uuid}/hands/predict` and its job) went with the Hands step in
implementation 03, Phase 10: the AI writes the hands with the sheet, starting from the hand split
(`pipeline.starting_hands`).
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.audio import store
from aitu_backend.audio.store import AudioNotFound
from aitu_backend.pieces import edits
from aitu_backend.pieces.status import piece_status
from aitu_backend.pmn import events_file
from aitu_backend.pmn.columns import to_columns
from aitu_backend.transcription import pipeline

router = APIRouter(prefix="/pieces", tags=["pieces"])


# --------------------------------------------------------------------------- models


class StepOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    step: str
    #: `missing`, `running`, `stale` or `ready`.
    state: str
    enabled: bool
    reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class StatusOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    audio_uuid: str = Field(..., alias="audioUuid")
    steps: list[StepOut]
    #: The step the piece opens on.
    resume: str
    #: `audio`, `notes`, `notesAudio`, `hands`, `handsNotes` (plan section 8.2).
    revisions: dict[str, int | None]
    #: Notes and no audio yet: a project made from scratch (Phase 8). The page shows only its sheet.
    scratch: bool = False


class NotesPatch(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    #: The `revision` (notes revision) of the notes the page edited.
    base_revision: int = Field(..., alias="baseRevision", ge=0)
    #: The `handsRevision` the page had. Optional: when given, a change of the hands made
    #: elsewhere is also refused.
    base_hands_revision: int | None = Field(None, alias="baseHandsRevision", ge=0)
    ops: list[edits.Operation] = Field(..., min_length=1, max_length=50_000)


class AddedOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    temp_id: int = Field(..., alias="tempId")
    id: int


class NotesPatchResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    revision: int
    hands_revision: int = Field(..., alias="handsRevision")
    #: False when the operations changed nothing, and nothing was written.
    saved: bool
    added: list[AddedOut] = Field(default_factory=list)
    #: The notes the backend changed or created, as columns (`id`, `key`, `onMs`, `lenMs`,
    #: `hand`, `guessed`): the added notes with their ids, the notes the same-key rule shortened,
    #: and the notes the quick rule gave a hand. The page replaces its copy of each.
    changed: dict[str, Any]


# --------------------------------------------------------------------------- helpers


def _audio_or_404(audio_uuid: str) -> None:
    if not store.exists(audio_uuid):
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'")


def _notes_or_409(audio_uuid: str) -> pipeline.TranscribedEvents:
    stored = pipeline.load_note_events(audio_uuid)
    if stored is None:
        raise HTTPException(
            status_code=409,
            detail=pipeline.needs_rederivation(audio_uuid)
            or "This piece has not been transcribed yet. Transcribe it first.",
        )
    return stored


def _check_revision(stored: pipeline.TranscribedEvents, base: int, hands: int | None) -> None:
    header = stored.header
    if base != header.notes_revision:
        raise HTTPException(
            status_code=409,
            detail=(
                f"The notes changed since this page loaded them (revision {header.notes_revision}, "
                f"the page has {base}). Reload the notes before saving."
            ),
        )
    if hands is not None and hands != header.hands_revision:
        raise HTTPException(
            status_code=409,
            detail=(
                f"The hands changed since this page loaded them (hands revision "
                f"{header.hands_revision}, the page has {hands}). Reload the notes before saving."
            ),
        )


def _json(payload: dict[str, Any]) -> Response:
    return Response(
        content=json.dumps(payload, separators=(",", ":")), media_type="application/json"
    )


# --------------------------------------------------------------------------- routes


@router.get("/{audio_uuid}/status", response_model=StatusOut, response_model_by_alias=True)
def get_status(audio_uuid: str) -> StatusOut:
    """Every step of the piece: `missing`, `running`, `stale` or `ready`, whether its tab may be
    opened and why not, and the step the piece opens on (plan sections 7.1 and 8.2)."""
    try:
        status = piece_status(audio_uuid)
    except AudioNotFound:
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{audio_uuid}'") from None
    return StatusOut(
        audio_uuid=status.audio_uuid,
        steps=[
            StepOut(
                step=step.step,
                state=step.state,
                enabled=step.enabled,
                reason=step.reason,
                details=step.details,
            )
            for step in status.steps
        ],
        resume=status.resume,
        revisions=status.revisions,
        scratch=status.scratch,
    )


@router.get("/{audio_uuid}/notes")
def get_notes(audio_uuid: str) -> Response:
    """The live notes as columns (plan section 6.4), with the revisions an edit must name.

    ``{"revision", "handsRevision", "durationMs", "stale", "id", "key", "onMs", "lenMs", "hand",
    "guessed"}``. ``stale`` is true when the selected region changed after the transcription.
    """
    _audio_or_404(audio_uuid)
    piece = events_file.read_piece(pipeline.events_path(audio_uuid))
    if piece is None:
        _notes_or_409(audio_uuid)
        raise HTTPException(status_code=409, detail="The notes of this piece cannot be read.")
    payload = to_columns(
        piece.notes,
        revision=piece.header.notes_revision,
        hands_revision=piece.header.hands_revision,
        duration_ms=piece.duration_ms,
    )
    payload["stale"] = piece.header.audio_revision != store.read_metadata(audio_uuid).audio_revision
    return _json(payload)


@router.patch("/{audio_uuid}/notes", response_model=NotesPatchResult, response_model_by_alias=True)
def patch_notes(audio_uuid: str, body: NotesPatch = Body(...)) -> NotesPatchResult:
    """Apply the page's operations and save them (plan section 6.4).

    Refused with 409 when `baseRevision` (or `baseHandsRevision`, when given) is not the stored
    one, so a page never writes over a newer version, and when the selected region changed after
    the transcription (the notes are stale; transcribe again). Refused with 422 when an operation
    cannot be applied; then nothing is written.

    A notes operation makes the revision go up; any operation makes the hands revision go up. A
    stored sheet is laid again on the new notes when it is next drawn (``part_sheet.build``).
    """
    _audio_or_404(audio_uuid)
    with pipeline.piece_lock(audio_uuid):
        stored = _notes_or_409(audio_uuid)
        _check_revision(stored, body.base_revision, body.base_hands_revision)
        if pipeline.notes_are_stale(audio_uuid, stored):
            raise HTTPException(
                status_code=409,
                detail="The selected region changed after the transcription. Transcribe again.",
            )
        try:
            applied = edits.apply_ops(stored.events, stored.duration_seconds * 1000.0, body.ops)
        except edits.EditRefused as refused:
            raise HTTPException(status_code=422, detail=str(refused)) from None

        if not applied.changed:
            return NotesPatchResult(
                revision=stored.header.notes_revision,
                hands_revision=stored.header.hands_revision,
                saved=False,
                changed=to_columns(events_file.notes_from_events([])),
            )

        saved = pipeline.save_edit(
            audio_uuid,
            stored.events,
            stored.duration_seconds,
            stored.title,
            before=stored.header,
            notes_changed=applied.notes_changed,
            hands_changed=applied.hands_changed,
        )

    changed: dict[int, Any] = {}
    for event in [*applied.added.values(), *applied.adjusted, *saved.guessed]:
        if event.id is not None and not event.removed:
            changed[event.id] = event
    return NotesPatchResult(
        revision=saved.header.notes_revision,
        hands_revision=saved.header.hands_revision,
        saved=True,
        added=[
            AddedOut(temp_id=temp_id, id=int(event.id))  # type: ignore[arg-type]
            for temp_id, event in applied.added.items()
        ],
        changed=to_columns(events_file.notes_from_events(list(changed.values()))),
    )
