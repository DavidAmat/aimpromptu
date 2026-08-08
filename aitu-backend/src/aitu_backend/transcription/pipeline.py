"""Audio to two hands on a wall clock, and the one file that is kept forever.

The pipeline used to have five steps, and the middle three existed to move a
recording onto a grid whose spacing came from a tempo somebody typed. There is
no tempo any more (D-01), so those steps have nothing to do and the whole thing
is short::

    audio -> the engine's note events, in seconds  (events.json, kept forever)
          -> impose the frame length and split the hands   (time_pipeline.py)

Only the first arrow is expensive, and only its result is stored. Everything
after it is a function of ``events.json`` and a frame length, so it is computed
again on every request rather than saved. That is what makes ``frameMs`` a query
parameter instead of a migration: asking for the same piece at 20 ms is another
request, not another stored artifact, and there is no state on disk that could
disagree with what the screen shows.

``events.json`` is therefore the only thing here that cannot be recreated. It
holds the real onsets and releases in seconds, before any grid was involved, and
every measurement in Phase 2 reads it (D-03, D-07).

What used to live in this module and no longer does:

``derive`` / ``recompute`` / ``PipelineResult``
    The collapse, clean and re-quantise steps. A column is 40 ms of wall clock
    now, so there is nothing to collapse to and no tempo to re-quantise for.

``load_raw`` / ``raw.npz`` / ``raw-granularity.txt`` / ``raw-edited.flag``
    The stored grid and the sidecars that described which tempo and granularity
    it had been written at. A grid that is a pure function of a file next to it
    is not worth storing, and a sidecar recording the tempo it was built at is
    not worth keeping when no tempo takes part.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from aitu_backend.audio import store
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.transcription.engine import (
    DEFAULT_ENGINE,
    NoteEvent,
    TranscriptionEngine,
    create_engine,
)
from aitu_backend.transcription.events_to_matrix import shift_events
from aitu_backend.transcription.time_pipeline import TimeHands, impose_granularity_and_split

#: Subfolder of an audio's uuid folder. It is called ``matrices`` for historical
#: reasons and now holds one file; renaming it is P4.4's decision, not this one's.
MATRICES_DIR = "matrices"

#: The transcription in **seconds**, before any grid was involved.
#:
#: This is the real output of the model and the only artifact worth keeping. The
#: matrix is a quantised view of it (D-03), so it can always be rebuilt, while
#: nothing can rebuild these times once they are gone.
EVENTS_FILE = "events.json"

#: Written by the migration for a piece that has no recorded notes to rebuild from.
#:
#: Success criterion 5 is that nothing is silently reinterpreted. A grid built
#: before the note events were kept describes a piece at some tempo nobody wrote
#: down, and reading it as wall clock would move every note without saying so. So
#: the piece is marked instead, the screens say what is wrong and what to do, and
#: the old files are left exactly where they are.
NEEDS_REDERIVATION_FILE = "needs-rederivation.json"


# ------------------------------------------------------------------- storage


def matrices_dir(audio_uuid: str) -> Path:
    return store.get(audio_uuid).directory / MATRICES_DIR


def events_path(audio_uuid: str) -> Path:
    return matrices_dir(audio_uuid) / EVENTS_FILE


def has_events(audio_uuid: str) -> bool:
    """Is there a transcription to work from, without re-running the model?"""
    return events_path(audio_uuid).is_file()


def needs_rederivation_path(audio_uuid: str) -> Path:
    return matrices_dir(audio_uuid) / NEEDS_REDERIVATION_FILE


def needs_rederivation(audio_uuid: str) -> str | None:
    """Why this piece cannot be drawn, in plain words, or ``None`` when it can.

    The text is written to be shown to a reader as it stands, because a flag that
    only a developer can interpret is not much better than silence.
    """
    path = needs_rederivation_path(audio_uuid)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return str(payload.get("reason") or "This piece has to be transcribed again.")
    except (ValueError, OSError):
        return "This piece has to be transcribed again."


def mark_needs_rederivation(audio_uuid: str, reason: str) -> Path:
    """Flag a piece the migration could not carry over. Never called at runtime."""
    path = needs_rederivation_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schemaVersion": "1.0", "reason": reason}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def clear_needs_rederivation(audio_uuid: str) -> None:
    """Transcribing again is what fixes it, so that is where the flag is cleared."""
    needs_rederivation_path(audio_uuid).unlink(missing_ok=True)


@dataclass(frozen=True)
class TranscribedEvents:
    """The model's output in seconds, plus the length of what it listened to.

    ``duration_seconds`` is kept because the events alone do not carry it: a
    piece that ends in silence would otherwise shrink every time it was rebuilt.
    """

    events: list[NoteEvent]
    duration_seconds: float
    title: str | None = None


def save_note_events(
    audio_uuid: str,
    events: list[NoteEvent],
    duration_seconds: float,
    title: str | None = None,
) -> Path:
    """Persist the transcription in seconds. The only write this module makes."""
    path = events_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": "1.0",
        "durationSeconds": round(float(duration_seconds), 6),
        "title": title,
        # Milliseconds are far finer than any frame length this project uses, and
        # the rounding keeps a 5000-note piece around a hundred kilobytes.
        "events": [
            {
                "midiNote": event.midi_note,
                "start": round(event.start, 4),
                "end": round(event.end, 4),
                "velocity": event.velocity,
            }
            for event in events
        ],
    }
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return path


def load_note_events(audio_uuid: str) -> TranscribedEvents | None:
    """The stored transcription, or ``None`` when there is none."""
    path = events_path(audio_uuid)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return TranscribedEvents(
            events=[
                NoteEvent(
                    midi_note=int(item["midiNote"]),
                    start=float(item["start"]),
                    end=float(item["end"]),
                    velocity=int(item.get("velocity", 64)),
                )
                for item in payload.get("events", [])
            ],
            duration_seconds=float(payload["durationSeconds"]),
            title=payload.get("title"),
        )
    except (ValueError, KeyError, TypeError):
        # A file written by an older schema is not worth failing a render over.
        return None


# ------------------------------------------------------------------ the steps


def transcribe_audio(
    audio_uuid: str,
    *,
    engine: TranscriptionEngine | str = DEFAULT_ENGINE,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    reporter: BaseProgress | None = None,
) -> TranscribedEvents:
    """Run the model and store what it heard. No tempo, no grid, no figures.

    A time range transcribes only that slice: the WAV is cut first, so the engine
    never sees the rest of the piece and the events come back already relative to
    the range start.
    """
    entry = store.get(audio_uuid)
    if not entry.has_normalized():
        from aitu_backend.audio import ingest  # noqa: PLC0415 - avoids a cycle at import time

        ingest.finalize(audio_uuid)
        entry = store.get(audio_uuid)

    progress = default_reporter(reporter)
    if isinstance(engine, str):
        options = {"reporter": progress} if engine == "bytedance" else {}
        model = create_engine(engine, **options)
    else:
        model = engine

    source_wav = entry.normalized_path
    duration = entry.metadata.duration_seconds or 0.0
    offset = 0.0

    if start_seconds is not None and end_seconds is not None:
        from aitu_backend.audio import formats  # noqa: PLC0415

        clip = entry.directory / "transcribe_range.wav"
        formats.slice_wav(source_wav, clip, start_seconds, end_seconds)
        source_wav = clip
        duration = end_seconds - start_seconds
        offset = start_seconds

    progressive = getattr(model, "transcribe_with_progress", None)
    if callable(progressive):
        events = progressive(source_wav, progress)
    else:
        with progress.stage("transcribe", total=1, message=model.name) as stage:
            events = model.transcribe(source_wav)
            stage.advance()

    if offset and events and min(event.start for event in events) >= offset:
        # Defensive: an engine that reports absolute times despite the clip.
        events = shift_events(events, offset)

    span = max(duration, 0.001)
    save_note_events(audio_uuid, events, span, title=entry.metadata.alias)
    # Whatever was wrong with this piece before, it now has its recorded notes.
    clear_needs_rederivation(audio_uuid)
    return TranscribedEvents(events=events, duration_seconds=span, title=entry.metadata.alias)


def run_pipeline(
    audio_uuid: str,
    *,
    frame_ms: float = DEFAULT_FRAME_MS,
    engine: TranscriptionEngine | str = DEFAULT_ENGINE,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    reuse_events: bool = True,
    reporter: BaseProgress | None = None,
) -> TimeHands:
    """Audio in, two hand matrices out, storing only the note events.

    ``reuse_events`` (default) skips the model when this audio has already been
    transcribed, which is the common case: a different frame length is a rebuild,
    not a re-transcription. Pass ``False`` to force the model to run again, for
    example after switching engines.

    A time range always re-transcribes, because a stored transcription of the
    whole piece is not a transcription of the range.
    """
    ranged = start_seconds is not None and end_seconds is not None

    stored = None if ranged or not reuse_events else load_note_events(audio_uuid)
    if stored is None:
        stored = transcribe_audio(
            audio_uuid,
            engine=engine,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            reporter=reporter,
        )

    return impose_granularity_and_split(
        stored.events,
        stored.duration_seconds,
        frame_ms=frame_ms,
        title=stored.title,
        reporter=reporter,
    )


def hands_of(
    audio_uuid: str,
    *,
    frame_ms: float = DEFAULT_FRAME_MS,
) -> TimeHands | None:
    """The two hands of a piece already transcribed, or ``None`` if it is not.

    The read path every screen uses. It never runs the model and never writes,
    so calling it twice with two frame lengths is two answers about one piece
    rather than two competing artifacts.
    """
    stored = load_note_events(audio_uuid)
    if stored is None:
        return None
    return impose_granularity_and_split(
        stored.events,
        stored.duration_seconds,
        frame_ms=frame_ms,
        title=stored.title,
    )
