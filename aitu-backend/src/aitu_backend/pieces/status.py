"""Which steps of a piece are ready: the answer the flow page enables its tabs from.

Plan section 8. Each step records the revision of the step before it when it was made, and this
module compares them. It only reads: ``metadata.json``, ``events.json`` and ``rhythm.json``, and
the transcription queue.

A step is ``missing`` (never made), ``running`` (a transcription is working on it), ``stale`` (made
from an older revision of an earlier step; it must be done again) or ``ready``. A tab is
``enabled`` when every step before it is ready, so the user can always go back and can go forward
one step past the last ready one. The Sheet tab stays enabled when it is stale, because it opens
with a banner and asks the user to write the sheet again (plan section 8.3).

**The hands of an old piece.** A piece transcribed before Phase 5 has no saved hands: the piano
sheet runs the hand split on each read, as it always did. When such a piece already has a saved
sheet, its Hands step reads ``ready`` with ``saved: false``, so its Sheet tab keeps opening as
today; **Predict hands** and **Save** then turn the computed hands into saved ones. Without a saved
sheet it reads ``missing``, like a new transcription.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from aitu_backend.audio import store
from aitu_backend.transcription import jobs, pipeline

State = Literal["missing", "running", "stale", "ready"]

#: The five steps of the flow page, in order (plan section 7.1).
STEPS = ("source", "audio", "notes", "hands", "sheet")


@dataclass
class StepStatus:
    step: str
    state: State
    enabled: bool = True
    #: Why the step is not ready, or why its tab is disabled, in words the page shows as they are.
    reason: str | None = None
    #: What else the page may show about the step (counts, the running job).
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PieceStatus:
    audio_uuid: str
    steps: list[StepStatus]
    #: The step a piece opens on: the furthest one that is ready (plan section 7.1).
    resume: str
    revisions: dict[str, int | None]

    def step(self, name: str) -> StepStatus:
        return next(step for step in self.steps if step.step == name)


def piece_status(audio_uuid: str) -> PieceStatus:
    """The state of every step of a piece. Raises ``AudioNotFound`` for an unknown uuid."""
    metadata = store.read_metadata(audio_uuid)
    stored = pipeline.load_note_events(audio_uuid)
    rhythm = pipeline.load_rhythm(audio_uuid)
    job = jobs.active(f"transcribe:{audio_uuid}")
    header = stored.header if stored is not None else None

    source = StepStatus("source", "ready")
    audio = StepStatus(
        "audio",
        "ready",
        details={"audioRevision": metadata.audio_revision, "cuts": len(metadata.cuts)},
    )

    # ------------------------------------------------------------------ notes
    notes: StepStatus
    if job is not None:
        notes = StepStatus(
            "notes",
            "running",
            reason="The transcription is running.",
            details={"jobId": job.id, "jobStatus": job.status},
        )
    elif stored is None:
        notes = StepStatus(
            "notes",
            "missing",
            reason=pipeline.needs_rederivation(audio_uuid)
            or "Transcribe the audio to see its notes.",
        )
    elif header is not None and header.audio_revision != metadata.audio_revision:
        notes = StepStatus(
            "notes",
            "stale",
            reason="The selected region changed after the transcription. Transcribe again.",
        )
    else:
        notes = StepStatus("notes", "ready")
    if stored is not None:
        live = [event for event in stored.events if not event.removed]
        notes.details.update({"noteCount": len(live), "engine": header.engine if header else None})

    # ------------------------------------------------------------------ hands
    hands: StepStatus
    if notes.state != "ready":
        hands = StepStatus(
            "hands",
            "stale" if notes.state == "stale" else "missing",
            enabled=False,
            reason=_first_notes(notes),
        )
    else:
        assert stored is not None and header is not None
        live = [event for event in stored.events if not event.removed]
        without = sum(1 for event in live if not event.hand)
        guessed = sum(1 for event in live if event.hand and event.hand_guessed)
        # A note the piano sheet cannot place gets no hand from the split and is left out of the
        # sheet: it stays red on the Hands tab, but it does not keep the step from being ready.
        placed = pipeline.placed_note_ids(audio_uuid) if without else set()
        unplaced = sum(1 for event in live if not event.hand and event.id not in placed)
        missing = without - unplaced
        details = {
            "withoutHand": without,
            "unplaced": unplaced,
            "guessed": guessed,
            "saved": missing == 0 and without < len(live),
        }
        if missing == 0 and (without < len(live) or not live):
            hands = StepStatus("hands", "ready", details=details)
        elif header.hands_notes_revision == 0 and rhythm is not None:
            hands = StepStatus(
                "hands",
                "ready",
                reason=(
                    "The piano sheet computes the hands of this piece each time it opens. Press "
                    "Predict hands and Save to keep them."
                ),
                details=details,
            )
        else:
            hands = StepStatus(
                "hands",
                "missing",
                reason=(
                    "Predict hands first."
                    if without == len(live)
                    else (
                        f"{missing} {'note has' if missing == 1 else 'notes have'} no hand. Give "
                        "each a hand on the Hands tab, or press Predict hands."
                    )
                ),
                details=details,
            )

    # ------------------------------------------------------------------ sheet
    sheet: StepStatus
    sheet_enabled = hands.state == "ready"
    disabled_reason = None if sheet_enabled else _first_hands(hands, notes)
    if rhythm is None:
        sheet = StepStatus(
            "sheet",
            "missing",
            enabled=sheet_enabled,
            reason=disabled_reason or "Write the sheet: name a gap and save the reading.",
        )
    elif not sheet_enabled:
        sheet = StepStatus("sheet", "stale", enabled=False, reason=disabled_reason)
    elif header is not None and (rhythm.hands_revision or 0) != header.hands_revision:
        sheet = StepStatus(
            "sheet",
            "stale",
            reason="The notes or the hands changed since this sheet was saved. Write the sheet again.",
        )
    else:
        sheet = StepStatus("sheet", "ready")

    steps = [source, audio, notes, hands, sheet]
    return PieceStatus(
        audio_uuid=audio_uuid,
        steps=steps,
        resume=_resume(steps),
        revisions={
            "audio": metadata.audio_revision,
            "notes": header.notes_revision if header else None,
            "notesAudio": header.audio_revision if header else None,
            "hands": header.hands_revision if header else None,
            "handsNotes": header.hands_notes_revision if header else None,
            "sheetHands": (rhythm.hands_revision or 0) if rhythm is not None else None,
        },
    )


def _first_notes(notes: StepStatus) -> str:
    if notes.state == "running":
        return "Wait for the transcription to finish."
    if notes.state == "stale":
        return "Transcribe again first: the selected region changed."
    return "Transcribe first."


def _first_hands(hands: StepStatus, notes: StepStatus) -> str:
    if notes.state != "ready":
        return _first_notes(notes)
    return "Predict hands first."


def _resume(steps: list[StepStatus]) -> str:
    """The furthest enabled step that is ready or running; a stale Sheet tab also counts, because
    it opens with its banner. A piece with a piano sheet opens on the Sheet tab, a piece that was
    only transcribed on the Notes tab (plan section 7.1)."""
    resume = "audio"
    for step in steps[1:]:
        if not step.enabled:
            break
        if step.state in ("ready", "running") or (step.step == "sheet" and step.state == "stale"):
            resume = step.step
    return resume
