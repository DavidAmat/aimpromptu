"""Which steps of a piece are ready: the answer the flow page enables its tabs from.

Plan section 8. Each step records the revision of the step before it when it was made, and this
module compares them. It only reads: ``metadata.json``, ``events.json`` and ``rhythm.json``, and
the transcription queue.

A step is ``missing`` (never made), ``running`` (a transcription is working on it), ``stale`` (made
from an older revision of an earlier step; it must be done again) or ``ready``. A tab is
``enabled`` when every step before it is ready, so the user can always go back and can go forward
one step past the last ready one. The Sheet tab stays enabled when it is stale, because it opens
with a banner and asks the user to write the sheet again (plan section 8.3).

**A project with no audio and no notes yet** (an empty project, section 10.3) has its Source step
missing and every later step closed. **A part made from scratch with no audio yet** (From scratch,
or a piece whose first passage was not put in yet, Phases 8 and 9) is ``scratch``: it opens on the Sheet step, and its Audio step is closed
until a passage brings audio (Record or Paste); the page shows only the sheet. **A video project** (its part has a video, section 10.2) gets its notes
from reading the video instead of a transcription, so its Notes step says so, and is ``running``
while the video is read.

**The hands and the sheet** (implementation 03, Phase 5). The Hands step is gone: Sonnet decides the hands with the
sheet, and the Sheet step opens as soon as the notes are ready. It is ``running`` while Sonnet writes, ``ready`` once
a new sheet is stored (``sheet.f1``) or the sheet vexflow-v2 saved (``sheet.json``) still matches the notes,
``stale`` when only that old sheet is left and the notes or the hands changed, and ``missing`` otherwise. The new sheet
itself is never stale for the page: it is laid again on the current notes (``part_sheet.build``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from aitu_backend.audio import store
from aitu_backend.part_sheet import job as new_sheet_job
from aitu_backend.part_sheet import store as new_sheet_store
from aitu_backend.storage import bundle
from aitu_backend.transcription import jobs, pipeline
from aitu_backend.video import store as video_store

State = Literal["missing", "running", "stale", "ready"]

#: The steps of the flow page, in order (plan section 7.1). The Hands step was removed by implementation 03,
#: Phase 5: Sonnet decides the hands with the sheet.
STEPS = ("source", "audio", "notes", "sheet")


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
    #: Notes and no audio: a project made from scratch, still a blank or composed sheet.
    scratch: bool = False

    def step(self, name: str) -> StepStatus:
        return next(step for step in self.steps if step.step == name)


def piece_status(audio_uuid: str) -> PieceStatus:
    """The state of every step of a piece. Raises ``AudioNotFound`` for an unknown uuid."""
    metadata = store.read_metadata(audio_uuid)
    if not bundle.read_timeline(audio_uuid).audio and not pipeline.has_events(audio_uuid):
        return _no_audio(audio_uuid, metadata.audio_revision)
    stored = pipeline.load_note_events(audio_uuid)
    rhythm = pipeline.load_rhythm(audio_uuid)
    video = video_store.exists(audio_uuid)
    job = jobs.active(f"video-read:{audio_uuid}" if video else f"transcribe:{audio_uuid}")
    header = stored.header if stored is not None else None

    # Made from scratch (or composed) and with no audio yet: only its sheet is shown.
    scratch = metadata.source.value == "composed" and not bundle.read_timeline(audio_uuid).audio
    source = StepStatus("source", "missing" if scratch else "ready")
    audio = StepStatus(
        "audio",
        "missing" if scratch else "ready",
        enabled=not scratch,
        reason="Record or paste a passage first." if scratch else None,
        details={"audioRevision": metadata.audio_revision, "cuts": len(metadata.cuts)},
    )

    # ------------------------------------------------------------------ notes
    notes: StepStatus
    if job is not None:
        notes = StepStatus(
            "notes",
            "running",
            reason="The video is being read." if video else "The transcription is running.",
            details={"jobId": job.id, "jobStatus": job.status, "video": video},
        )
    elif stored is None:
        notes = StepStatus(
            "notes",
            "missing",
            reason=pipeline.needs_rederivation(audio_uuid)
            or (
                "Read the notes of the video to see them."
                if video
                else "Transcribe the audio to see its notes."
            ),
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

    # ------------------------------------------------------------------ sheet
    # The Hands step is gone (implementation 03, Phase 5, plan section 3.5): Sonnet decides the hands with the
    # sheet, so the Sheet step opens as soon as the notes are ready.
    sheet: StepStatus
    sheet_enabled = notes.state == "ready"
    running = new_sheet_job.job_of(audio_uuid) if sheet_enabled else None
    written = new_sheet_store.load(audio_uuid) is not None if sheet_enabled else False
    legacy = _legacy_sheet(rhythm, header) if sheet_enabled else "missing"
    details = {"newSheet": written, "legacy": legacy}
    if not sheet_enabled:
        sheet = StepStatus(
            "sheet",
            "stale" if rhythm is not None else "missing",
            enabled=False,
            reason=_first_notes(notes, video),
        )
    elif running is not None:
        sheet = StepStatus(
            "sheet",
            "running",
            details={**details, "jobId": running.id, "jobStatus": running.status},
        )
    elif written or legacy == "ready":
        sheet = StepStatus("sheet", "ready", details=details)
    elif legacy == "stale":
        sheet = StepStatus(
            "sheet",
            "stale",
            reason="The notes or the hands changed since this sheet was saved.",
            details=details,
        )
    else:
        sheet = StepStatus("sheet", "missing", reason="Not written yet.", details=details)

    steps = [source, audio, notes, sheet]
    return PieceStatus(
        audio_uuid=audio_uuid,
        steps=steps,
        resume="sheet" if scratch and sheet.enabled else _resume(steps),
        scratch=scratch,
        revisions={
            "audio": metadata.audio_revision,
            "notes": header.notes_revision if header else None,
            "notesAudio": header.audio_revision if header else None,
            "hands": header.hands_revision if header else None,
            "handsNotes": header.hands_notes_revision if header else None,
            "sheetHands": (rhythm.hands_revision or 0) if rhythm is not None else None,
        },
    )


def _first_notes(notes: StepStatus, video: bool = False) -> str:
    if notes.state == "running":
        return (
            "Wait for the video to be read." if video else "Wait for the transcription to finish."
        )
    if notes.state == "stale":
        return "Transcribe again first: the selected region changed."
    return "Read the notes of the video first." if video else "Transcribe first."


def _legacy_sheet(rhythm: Any, header: Any) -> str:
    """The sheet vexflow-v2 saved (``sheet.json``): ``ready`` while it matches the notes and the hands, ``stale``
    after they changed, ``missing``. The old editor (the switch of the Sheet step) opens a stale one with its
    banner."""
    if rhythm is None:
        return "missing"
    if header is not None and (rhythm.hands_revision or 0) != header.hands_revision:
        return "stale"
    return "ready"


def _no_audio(audio_uuid: str, audio_revision: int) -> PieceStatus:
    """A part with no audio yet: only its Source step can be opened."""
    closed = "Add an audio first."
    steps = [
        StepStatus("source", "missing", reason="No audio yet."),
        StepStatus("audio", "missing", enabled=False, reason=closed),
        StepStatus("notes", "missing", enabled=False, reason=closed),
        StepStatus("sheet", "missing", enabled=False, reason=closed),
    ]
    return PieceStatus(
        audio_uuid=audio_uuid,
        steps=steps,
        resume="source",
        revisions={
            "audio": audio_revision,
            "notes": None,
            "notesAudio": None,
            "hands": None,
            "handsNotes": None,
            "sheetHands": None,
        },
    )


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
