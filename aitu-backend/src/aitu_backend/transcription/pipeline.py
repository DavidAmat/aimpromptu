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
import threading
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING

from aitu_backend.audio import store
from aitu_backend.audio.frames import FrameTable, frame_count, join_kept
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.pmn import events_file
from aitu_backend.pmn.events_file import PieceHeader
from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.transcription import saved_hands, split_cache
from aitu_backend.transcription.engine import (
    DEFAULT_ENGINE,
    NoteEvent,
    TranscriptionEngine,
    shared_engine,
)
from aitu_backend.transcription.events_to_matrix import shift_events
from aitu_backend.transcription.time_pipeline import TimeHands, impose_granularity_and_split

if TYPE_CHECKING:  # pragma: no cover - import for typing only
    from aitu_backend.schemas.rhythm import SavedRhythm

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

#: The reader's own decisions about this piece: the named ladder, the speed
#: changes, the notes renamed by hand and the beams they broke.
#:
#: Everything else in a score is derived from `events.json`, so it can be thrown
#: away and rebuilt. This cannot: nothing in the recording implies which pile is
#: the beat or where a phrase restarts, and a reader who loses it has to decide
#: it all again. See :mod:`aitu_backend.schemas.rhythm`.
RHYTHM_FILE = "rhythm.json"


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


def rhythm_path(audio_uuid: str) -> Path:
    return matrices_dir(audio_uuid) / RHYTHM_FILE


def load_rhythm(audio_uuid: str) -> "SavedRhythm | None":
    """The reading saved for this piece, or ``None`` when nobody has saved one.

    A file written by an older shape comes back as ``None`` rather than raising.
    Losing a saved reading is a nuisance; refusing to open the piece at all
    because of it would be worse, and the reader can simply name the gap again.
    """
    from aitu_backend.schemas.rhythm import SavedRhythm  # noqa: PLC0415 - avoids a cycle

    path = rhythm_path(audio_uuid)
    if not path.is_file():
        return None
    try:
        return SavedRhythm.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def save_rhythm(audio_uuid: str, rhythm: "SavedRhythm") -> Path:
    """Write the reading, replacing whatever was there.

    One per piece. A rhythm is a decision rather than a version: what a reader
    wants back is the last reading they were happy with, not a list of the ones
    they abandoned.
    """
    path = rhythm_path(audio_uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rhythm.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8")
    return path


def clear_rhythm(audio_uuid: str) -> None:
    """Forget the saved reading. Transcribing again also does this, in `transcribe_audio`."""
    rhythm_path(audio_uuid).unlink(missing_ok=True)


@dataclass(frozen=True)
class TranscribedEvents:
    """The model's output in seconds, plus the length of what it listened to.

    ``duration_seconds`` is kept because the events alone do not carry it: a
    piece that ends in silence would otherwise shrink every time it was rebuilt.
    ``header`` holds the revisions and the next free note id (implementation 08,
    plan section 6.3); a file written before it existed reads with the defaults.
    """

    events: list[NoteEvent]
    duration_seconds: float
    title: str | None = None
    header: PieceHeader = field(default_factory=PieceHeader)


def save_note_events(
    audio_uuid: str,
    events: list[NoteEvent],
    duration_seconds: float,
    title: str | None = None,
    *,
    header: PieceHeader | None = None,
) -> Path:
    """Persist the transcription in seconds. The only write this module makes.

    Every note keeps its ``id``; a note without one gets the next free id, and
    the id is set on the event itself. Without ``header`` the one already on
    disk is kept, so a writer that only changes notes cannot lose the revisions.
    The format is :mod:`aitu_backend.pmn.events_file`.
    """
    path = events_path(audio_uuid)
    base = events_file.read_header(path) if header is None else header
    payload = events_file.payload_from_events(events, base, duration_seconds, title)
    return events_file.write_payload(path, payload)


_locks_guard = threading.Lock()
_locks: dict[str, threading.Lock] = {}


def piece_lock(audio_uuid: str) -> threading.Lock:
    """One lock per piece. A writer holds it from reading ``events.json`` to writing it, so a
    revision check and its write cannot interleave with another request's (plan section 6.4)."""
    with _locks_guard:
        return _locks.setdefault(audio_uuid, threading.Lock())


@dataclass(frozen=True)
class SavedEdit:
    """What :func:`save_edit` wrote."""

    header: PieceHeader
    #: Live notes the quick rule gave a hand to, because the piece's hands were saved and these
    #: notes had none (an added note, or a note put back).
    guessed: list[NoteEvent]
    #: True when ``rhythm.json`` was current and moved forward with the edit.
    sheet_moved: bool


def save_edit(
    audio_uuid: str,
    events: list[NoteEvent],
    duration_seconds: float,
    title: str | None,
    *,
    before: PieceHeader | None = None,
    notes_changed: bool,
    hands_changed: bool,
    sheet_follows: bool = False,
    new_notes: bool = False,
) -> SavedEdit:
    """Write an edit of the piece and move the revisions of plan section 8.2. Every writer of
    ``events.json`` except a transcription goes through here.

    * ``notesRevision`` goes up when a note changed (``notes_changed``): moved, resized, added,
      deleted, put back.
    * ``handsRevision`` goes up on every edit: anything above the hands, or a hand.
    * ``handsNotesRevision`` becomes the new ``notesRevision`` when a hand changed and every live
      note the piano sheet places now has one: the hands were saved as a whole for these notes.
    * **The quick rule** (plan section 8.3): when the hands were saved as a whole before, a live
      note with no hand (an added note, a note put back) gets the hand of its neighbours, marked
      as guessed. ``new_notes`` is a whole new set of notes (a video read into notes): no quick
      rule, and the hands are missing.
    * **The piano sheet** (``rhythm.json``) records the ``handsRevision`` it was saved for. An edit
      made on the Sheet tab passes ``sheet_follows``: the page that made it already draws the
      result, so a reading that was current moves forward with it and stays current. Any other
      edit leaves it behind, which makes the Sheet tab stale.

    ``before`` is the header the caller read with the notes; without it the one on disk is used.
    The caller holds :func:`piece_lock` from its read to this write.
    """
    base = before if before is not None else events_file.read_header(events_path(audio_uuid))
    guessed: list[NoteEvent] = []
    # The notes the piano sheet places: only those need a hand (a note it cannot place stays red).
    placed: set[int] | None = None
    if not new_notes and (base.hands_notes_revision > 0 or hands_changed):
        placed = saved_hands.placed_ids(
            events, duration_seconds, **filters_for(base.engine)  # type: ignore[arg-type]
        )
    if not new_notes and base.hands_notes_revision > 0:
        guessed = saved_hands.fill_quick_hands(events, placed)
    notes_revision = base.notes_revision + (1 if notes_changed else 0)
    if new_notes:
        hands_notes_revision = 0
    elif hands_changed and saved_hands.hands_complete(events, placed):
        hands_notes_revision = notes_revision
    else:
        hands_notes_revision = base.hands_notes_revision
    header = replace(
        base,
        notes_revision=notes_revision,
        hands_revision=base.hands_revision + 1,
        hands_notes_revision=hands_notes_revision,
    )
    save_note_events(audio_uuid, events, duration_seconds, title, header=header)
    ids = [event.id for event in events if event.id is not None]
    header = replace(header, next_id=max([header.next_id, *(value + 1 for value in ids)]))

    moved = False
    if sheet_follows:
        rhythm = load_rhythm(audio_uuid)
        if rhythm is not None and (rhythm.hands_revision or 0) == base.hands_revision:
            save_rhythm(
                audio_uuid, rhythm.model_copy(update={"hands_revision": header.hands_revision})
            )
            moved = True
    # The cache keys change with the file's mtime already; a clock tick can hold two saves.
    split_cache.forget(audio_uuid)
    return SavedEdit(header=header, guessed=guessed, sheet_moved=moved)


def load_note_events(audio_uuid: str) -> TranscribedEvents | None:
    """The stored transcription, or ``None`` when there is none.

    Reading never writes. A file saved before note ids existed gets ``0, 1, 2 ...``
    in file order, the same on every read, and keeps them at its next save.
    """
    path = events_path(audio_uuid)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload.get("events", [])
        header = events_file.header_from_payload(payload)
        ids, _ = events_file.assign_ids(
            (item.get("id") for item in items), int(payload.get("nextId") or 0)
        )
        return TranscribedEvents(
            events=[
                NoteEvent(
                    id=note_id,
                    midi_note=int(item["midiNote"]),
                    start=float(item["start"]),
                    end=float(item["end"]),
                    velocity=int(item.get("velocity", 64)),
                    hand=item.get("hand"),
                    hand_guessed=bool(item.get("handGuessed", False)),
                    removed=bool(item.get("removed", False)),
                )
                for note_id, item in zip(ids, items)
            ],
            duration_seconds=float(payload["durationSeconds"]),
            title=payload.get("title"),
            header=header,
        )
    except (ValueError, KeyError, TypeError):
        # A file written by an older schema is not worth failing a render over.
        return None


def notes_are_stale(audio_uuid: str, stored: TranscribedEvents | None = None) -> bool:
    """Were the stored notes transcribed from other cuts than the ones saved now? (plan section 8)

    A cut saved after a transcription makes the notes stale, and the next transcription request
    transcribes again instead of reusing them (Q-2). A piece with no notes is not stale, it is
    missing.
    """
    stored = stored if stored is not None else load_note_events(audio_uuid)
    if stored is None:
        return False
    return stored.header.audio_revision != store.read_metadata(audio_uuid).audio_revision


def current_events(audio_uuid: str) -> TranscribedEvents | None:
    """The stored notes when they exist and are not stale, else ``None``."""
    stored = load_note_events(audio_uuid)
    if stored is None or notes_are_stale(audio_uuid, stored):
        return None
    return stored


def filters_for(engine: str | None) -> dict[str, None]:
    """The filters the hand split applies to the notes of a piece made by ``engine``.

    ``artifacts.py`` and ``leakage.py`` were tuned for ByteDance. Phase 1 measured them on six
    pieces of MuScriptor notes: the first drops 0 to 4 notes per song, and the second would merge
    real repeated notes, because MuScriptor has no velocity and closes a note at the next onset of
    its key (a gap of 0 ms). Both are off for a piece whose header says ``muscriptor-*``, and on,
    as before, for every other piece (plan section 9.1). The answer is keyword arguments for
    :func:`impose_granularity_and_split`: empty means its defaults.
    """
    if engine and engine.startswith("muscriptor"):
        return {"leakage": None, "artifacts": None}
    return {}


def split_of(
    audio_uuid: str,
    frame_ms: float = DEFAULT_FRAME_MS,
    *,
    reporter: BaseProgress | None = None,
) -> TimeHands:
    """The hand split of a transcribed piece, shared by every reader (:mod:`.split_cache`).

    **D-31, changed in implementation 08, Phase 5.** When every live note has a saved hand, the
    two hand matrices are painted from those hands (:func:`saved_hands.split_with_saved_hands`,
    a few milliseconds) and no inference runs. Otherwise the old behaviour runs: the inference on
    the snapped time matrix, then the reader's pinned hands on top. Both build the whole keyboard
    the same way.

    Raises ``FileNotFoundError`` when the piece has no notes. The object is shared: treat it as
    read-only. ``reporter`` receives the progress of the split only when it is computed here.
    """
    path = events_path(audio_uuid)
    try:
        stamp = path.stat().st_mtime_ns
    except FileNotFoundError:
        raise FileNotFoundError(f"Audio {audio_uuid} has no stored note events") from None

    def compute() -> TimeHands:
        stored = load_note_events(audio_uuid)
        if stored is None:
            raise FileNotFoundError(f"Audio {audio_uuid} has no readable note events")
        # A piece being composed is empty until its first passage lands, and an empty piece is a
        # `durationSeconds` of zero (Epic 13). It still has to draw: one empty column is enough for
        # a pair of staves, and the column is a property of the view, not of the music.
        duration = max(stored.duration_seconds, frame_ms / 1000.0)
        complete = saved_hands.hands_complete(stored.events, placed_note_ids(audio_uuid, frame_ms))
        split = saved_hands.split_with_saved_hands if complete else impose_granularity_and_split
        return split(
            stored.events,
            duration,
            frame_ms=frame_ms,
            title=stored.title,
            reporter=reporter,
            **filters_for(stored.header.engine),
        )

    return split_cache.get((audio_uuid, float(frame_ms), stamp), compute)


def placed_note_ids(audio_uuid: str, frame_ms: float = DEFAULT_FRAME_MS) -> set[int]:
    """The ids of the live notes the piano sheet places (:func:`saved_hands.placed_ids`), cached
    until ``events.json`` changes. Raises ``FileNotFoundError`` when the piece has no notes."""
    path = events_path(audio_uuid)
    try:
        stamp = path.stat().st_mtime_ns
    except FileNotFoundError:
        raise FileNotFoundError(f"Audio {audio_uuid} has no stored note events") from None

    def compute() -> set[int]:
        stored = load_note_events(audio_uuid)
        if stored is None:
            raise FileNotFoundError(f"Audio {audio_uuid} has no readable note events")
        return saved_hands.placed_ids(
            stored.events,
            stored.duration_seconds,
            frame_ms=frame_ms,
            **filters_for(stored.header.engine),  # type: ignore[arg-type]
        )

    return split_cache.get((audio_uuid, float(frame_ms), stamp, "placed"), compute)


def inferred_split(
    audio_uuid: str,
    frame_ms: float = DEFAULT_FRAME_MS,
    *,
    keep_saved: bool = True,
    reporter: BaseProgress | None = None,
) -> TimeHands:
    """The split the hand inference makes, whatever hands are saved: **Predict hands**.

    ``keep_saved`` lays the saved hands that were not guessed over the inference, as the old
    behaviour lays the reader's pins (so a hand the user set survives a new prediction); a
    guessed hand is inferred again. Without it every note is inferred. Cached beside the ordinary
    split under its own key, so pressing the button twice pays the inference once. ``reporter``
    receives the progress (stages ``events`` and ``two-hands``) only when it is computed here.
    """
    path = events_path(audio_uuid)
    try:
        stamp = path.stat().st_mtime_ns
    except FileNotFoundError:
        raise FileNotFoundError(f"Audio {audio_uuid} has no stored note events") from None

    def compute() -> TimeHands:
        stored = load_note_events(audio_uuid)
        if stored is None:
            raise FileNotFoundError(f"Audio {audio_uuid} has no readable note events")
        events = [
            (
                event
                if keep_saved and event.hand and not event.hand_guessed
                else event.model_copy(update={"hand": None, "hand_guessed": False})
            )
            for event in stored.events
        ]
        return impose_granularity_and_split(
            events,
            max(stored.duration_seconds, frame_ms / 1000.0),
            frame_ms=frame_ms,
            title=stored.title,
            reporter=reporter,
            **filters_for(stored.header.engine),
        )

    key = (audio_uuid, float(frame_ms), stamp, "keep" if keep_saved else "all")
    return split_cache.get(key, compute)


def warm_split(audio_uuid: str, frame_ms: float = DEFAULT_FRAME_MS) -> threading.Thread:
    """Compute the hand split on a background thread, so the first sheet request finds it ready.

    Used by the transcription job after it saves: the ``done`` frame is not delayed by the split
    (0.3 to 4.3 s), and a page that asks for the sheet right after waits for this computation
    instead of starting a second one (:func:`split_cache.get`).
    """

    def run() -> None:
        try:
            split_of(audio_uuid, frame_ms)
        except Exception:  # pragma: no cover - the reader that needs it will raise it
            pass

    thread = threading.Thread(target=run, name="aitu-split-warm", daemon=True)
    thread.start()
    return thread


# ------------------------------------------------------------------ the steps


def _engine(engine: TranscriptionEngine | str, progress: BaseProgress) -> TranscriptionEngine:
    """A name becomes the process's shared engine (:mod:`.models`): no model is loaded twice."""
    if isinstance(engine, str):
        return shared_engine(engine, reporter=progress)
    return engine


def _run_on_file(
    model: TranscriptionEngine, wav_path: Path, progress: BaseProgress
) -> list[NoteEvent]:
    progressive = getattr(model, "transcribe_with_progress", None)
    if callable(progressive):
        return list(progressive(wav_path, progress))
    with progress.stage("transcribe", total=1, message=model.name) as stage:
        events = model.transcribe(wav_path)
        stage.advance()
    return list(events)


def transcribe_file(
    wav_path: Path,
    *,
    engine: TranscriptionEngine | str = DEFAULT_ENGINE,
    reporter: BaseProgress | None = None,
) -> list[NoteEvent]:
    """Run the model on a WAV and return events. Does not write ``events.json``.

    Range editing transcribes the take into the session folder. Writing onto the
    piece here would replace the music being edited.
    """
    progress = default_reporter(reporter)
    return _run_on_file(_engine(engine, progress), wav_path, progress)


def transcribe_audio(
    audio_uuid: str,
    *,
    engine: TranscriptionEngine | str = DEFAULT_ENGINE,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    reporter: BaseProgress | None = None,
) -> TranscribedEvents:
    """Run the model and store what it heard. No tempo, no grid, no figures.

    **The selected region** (implementation 08, plan section 9.2). The engine hears the piece: the
    frames of ``normalized.wav`` that no cut of ``metadata.json`` deletes, joined in memory with a
    5 ms fade at each join. No audio file is written for an engine that takes samples
    (MuScriptor's ``run_signal``); the others get a temporary WAV when there is a cut. The notes
    are stored in the time of the piece, which is shorter than the original by the cuts.

    **What the header records.** The engine's name, the ``audioRevision`` the notes were made from
    (a later cut makes them stale), the lag correction, and ``notesRevision``: 1 for a first
    transcription, one more than before for a new one. The ids of the new notes continue after
    every id the piece has used.

    **Nothing is lost.** A piece that already has notes gets its ``events.json`` and
    ``rhythm.json`` copied into ``history/vN/`` before they are replaced (plan section 8.3).

    A time range (``start_seconds``, ``end_seconds``) is the older way to transcribe part of the
    file: the WAV is cut first, the cuts are not applied, and the events come back relative to the
    range start.
    """
    entry = store.get(audio_uuid)
    if not entry.has_normalized():
        from aitu_backend.audio import ingest  # noqa: PLC0415 - avoids a cycle at import time

        ingest.finalize(audio_uuid)
        entry = store.get(audio_uuid)

    progress = default_reporter(reporter)
    model = _engine(engine, progress)
    before = events_file.read_header(events_path(audio_uuid))
    had_notes = has_events(audio_uuid)
    metadata = entry.metadata
    lag_correction_ms = 0.0
    #: True when the engine numbered the notes from the piece's ``nextId`` itself.
    numbered = False

    if start_seconds is not None and end_seconds is not None:
        from aitu_backend.audio import formats  # noqa: PLC0415

        clip = entry.directory / "transcribe_range.wav"
        formats.slice_wav(entry.normalized_path, clip, start_seconds, end_seconds)
        events = _run_on_file(model, clip, progress)
        duration = end_seconds - start_seconds
        if events and min(event.start for event in events) >= start_seconds:
            # Defensive: an engine that reports absolute times despite the clip.
            events = shift_events(events, start_seconds)
    else:
        events, duration, lag_correction_ms, numbered = _transcribe_piece(
            model, entry, before.next_id, progress
        )

    if not numbered:
        # The ids of a new transcription continue after every id the piece has used.
        for event in events:
            event.id = None

    if had_notes:
        from aitu_backend.editing import history  # noqa: PLC0415 - history imports this module

        history.snapshot_notes(audio_uuid)

    span = max(duration, 0.001)
    header = replace(
        before,
        engine=model.name,
        notes_revision=before.notes_revision + 1 if had_notes else 1,
        # New notes have no hand: the hands are missing, and the piano sheet must be written again.
        hands_revision=before.hands_revision + 1,
        hands_notes_revision=0,
        audio_revision=metadata.audio_revision,
        lag_correction_ms=float(lag_correction_ms),
    )
    save_note_events(audio_uuid, events, span, title=metadata.alias, header=header)
    # A saved reading is a set of column numbers over the notes that were there
    # before. A new transcription is a different set of notes, so those numbers
    # point at nothing in particular now and keeping them would be worse than
    # asking the reader to name the gap again. The copy is in history.
    clear_rhythm(audio_uuid)
    # Whatever was wrong with this piece before, it now has its recorded notes.
    clear_needs_rederivation(audio_uuid)
    return TranscribedEvents(
        events=events,
        duration_seconds=span,
        title=metadata.alias,
        header=events_file.read_header(events_path(audio_uuid)),
    )


def _transcribe_piece(
    model: TranscriptionEngine,
    entry: store.StoredAudio,
    first_id: int,
    progress: BaseProgress,
) -> tuple[list[NoteEvent], float, float, bool]:
    """The engine on the kept frames. Returns the events, the length of the piece in seconds, the
    lag correction and whether the engine numbered the notes."""
    from aitu_backend.audio import formats  # noqa: PLC0415

    run_signal = getattr(model, "run_signal", None)
    if not entry.metadata.cuts and not callable(run_signal):
        # The whole file, as before implementation 08: the engine reads it itself.
        duration = entry.metadata.duration_seconds or 0.0
        return _run_on_file(model, entry.normalized_path, progress), duration, 0.0, False

    rate, samples = formats.read_wav(entry.normalized_path)
    table = FrameTable.from_cuts(entry.metadata.cuts, frame_count(len(samples)))
    if not table.is_whole and rate != formats.TRANSCRIPTION_SAMPLE_RATE:
        raise ValueError(
            f"normalized.wav of {entry.uuid} is at {rate} Hz; the cuts need "
            f"{formats.TRANSCRIPTION_SAMPLE_RATE} Hz. Upload the audio again."
        )
    piece = join_kept(samples, table)
    if table.is_whole:
        duration = entry.metadata.duration_seconds or len(samples) / rate
    else:
        duration = len(piece) / rate

    if callable(run_signal):
        run = run_signal(piece, rate, progress, first_id=first_id)
        return run.events, duration, run.lag_correction_ms, True
    if table.is_whole:
        return _run_on_file(model, entry.normalized_path, progress), duration, 0.0, False

    import tempfile  # noqa: PLC0415

    from scipy.io import wavfile  # noqa: PLC0415

    with tempfile.TemporaryDirectory(prefix="aitu-piece-") as folder:
        joined = Path(folder) / "piece.wav"
        wavfile.write(joined, rate, piece)
        return _run_on_file(model, joined, progress), duration, 0.0, False


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
    example after switching engines. Notes made before the cuts last changed are
    stale and are never reused (Q-2).

    The split comes from the shared cache, so the first sheet request after this
    finds it ready (plan section 10.5).

    A time range always re-transcribes, because a stored transcription of the
    whole piece is not a transcription of the range.
    """
    ranged = start_seconds is not None and end_seconds is not None

    stored = None if ranged or not reuse_events else current_events(audio_uuid)
    if stored is None:
        transcribe_audio(
            audio_uuid,
            engine=engine,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            reporter=reporter,
        )

    return split_of(audio_uuid, frame_ms, reporter=reporter)


def hands_of(
    audio_uuid: str,
    *,
    frame_ms: float = DEFAULT_FRAME_MS,
) -> TimeHands | None:
    """The two hands of a piece already transcribed, or ``None`` if it is not.

    The read path every screen uses. It never runs the model and never writes,
    so calling it twice with two frame lengths is two answers about one piece
    rather than two competing artifacts. The answer comes from the shared split
    cache and must be treated as read-only.
    """
    try:
        return split_of(audio_uuid, frame_ms)
    except FileNotFoundError:
        return None
