"""Recording in Sheet: a passage of a part, re-recorded and promoted (implementation 02, plan
section 13, Phase 9).

**A passage** is a stretch ``[fromMs, toMs)`` of a part, marked on its sheet, or a moment of it
(``fromMs == toMs``: a new passage put in there, the Record of the floating bar and of a blank
sheet). It is kept as a project of its own in the owner's Personal Vault, hidden from every list
(``kind = 'passage'``):

* its one part is the **Current**: a copy of the marked frames, made by a paste into an empty part
  (:func:`aitu_backend.editing.paste.paste`), so it has the notes, the marks, the key and the clefs
  of the stretch, and its audio as ranges of the stored files (no audio byte is copied). A moment
  has an empty Current;
* ``origin`` holds the state of the page: the part and the stretch, what a figure lasts there, the
  takes, the take on show, the speed and where the window lies.

**A take** is a recording made for the passage, kept as one more hidden project of one part
(``origin.takeOf`` names the passage). It is an ordinary part, so everything a project does works on
it: its audio is a stored file and the range of it the user keeps is its cuts (the Audio step's own
rule), :func:`read_take` runs the transcription (with its live progress), the hand split and a
first sheet written **with the passage's key and figure**, and the page draws it as the Proposal
with the whole sheet page and its toolboxes.

**The promotion** is one write into the part, through the paste: the take's notes, marks and audio,
read the way a copy is (:func:`aitu_backend.editing.paste.read_passage`), played ``speed`` times as
fast, put in place of the stretch. It keeps the part as a snapshot of its history first, so the
sheet's undo puts it back (:func:`aitu_backend.editing.history.restore`), as for a paste.

* ``window``: the stretch of the take under the window, ``length × speed`` long, fitted into the
  passage: the song keeps its length. With ``audio = 'original'`` only the notes and marks change
  and the audio stays; with ``'recording'`` the take's audio, played at the speed with its pitch
  kept, replaces the passage's.
* ``whole``: the whole kept take, at the speed, replaces the passage, and everything after it moves
  by the difference (decision Q-3). It always uses the recording.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, BinaryIO, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from scipy.io import wavfile

from aitu_backend.audio import formats, ingest, sources, store, timeline as audio_timeline
from aitu_backend.db.users import current_user_id
from aitu_backend.editing import audio_splice, marks, paste
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS
from aitu_backend.progress import BaseProgress
from aitu_backend.schemas.rhythm import SavedRhythm
from aitu_backend.schemas.time_matrix import FIGURE_NEGRAS, FigureName
from aitu_backend.storage import audio_files, bundle, locate, paths
from aitu_backend.storage.bundle import PartSource
from aitu_backend.transcription import jobs, pipeline, saved_hands
from aitu_backend.transcription.engine import NoteEvent

__all__ = [
    "Facts",
    "PassageError",
    "PassageState",
    "Promotion",
    "add_take",
    "delete_take",
    "discard",
    "facts",
    "open_passage",
    "promote",
    "read_take",
    "state",
    "take_job_key",
    "update",
]

Mode = Literal["window", "whole"]
AudioChoice = Literal["original", "recording"]
#: How much faster or slower a take may be played into the song (plan section 13).
SPEED_RANGE = (0.25, 4.0)
#: The 10 ms frame of the audio timeline.
AUDIO_FRAME_MS = bundle.FRAME_MS


class PassageError(ValueError):
    """Something about a passage that cannot be done, in words the page shows."""


class PassageState(BaseModel):
    """``origin`` of a passage's project."""

    model_config = ConfigDict(populate_by_name=True)

    passage_of: str = Field(..., alias="passageOf")
    from_ms: float = Field(..., alias="fromMs")
    to_ms: float = Field(..., alias="toMs")
    #: What the song's figure (``anchorFigure``) lasts where the passage starts, in ms; ``None``
    #: when the song has no sheet yet (a blank one): the take's own figures are then read from it.
    anchor_ms: float | None = Field(None, alias="anchorMs")
    anchor_figure: FigureName = Field(FigureName.NEGRA, alias="anchorFigure")
    takes: list[str] = Field(default_factory=list)
    take: str | None = None
    speed: float = 1.0
    #: Where the window starts over the take, in ms of the take as played.
    window_ms: float = Field(0.0, alias="windowMs")
    #: The part as it was when the passage opened (its notes, hands, audio and sheet): the same
    #: stretch of an unchanged part opens this passage again, with its takes.
    source_revision: str | None = Field(None, alias="sourceRevision")

    @property
    def length_ms(self) -> float:
        return self.to_ms - self.from_ms


@dataclass
class Take:
    id: str
    name: str
    #: ``recorded`` (audio only), ``reading`` (the job runs), ``ready`` (notes, hands, sheet).
    state: str
    seconds: float
    from_seconds: float
    to_seconds: float
    job_id: str | None
    #: Played on a MIDI piano: its notes are the keys played, not a transcription.
    midi: bool
    #: Changes with the stretch kept: the page plays the take at a new address then.
    audio_revision: int


@dataclass
class Facts:
    """What a promotion would do, worked out before anything is written."""

    mode: Mode
    audio: AudioChoice
    notes_out: int
    notes_in: int
    marks_dropped: dict[str, int]
    length_change_ms: float
    duration_seconds: float


@dataclass
class Promotion:
    part: str
    project_id: str
    before_version: int
    at_ms: float
    length_ms: float
    sheet: SavedRhythm | None


# ------------------------------------------------------------------ reading and writing state


def _project(passage_id: str) -> bundle.ProjectFile:
    project = bundle.read_project(passage_id)
    if project.kind != bundle.PASSAGE_KIND or not (project.origin or {}).get("passageOf"):
        raise locate.NotFound("passage", passage_id)
    return project


def load(passage_id: str) -> PassageState:
    return PassageState.model_validate(_project(passage_id).origin)


def _save(passage_id: str, passage: PassageState) -> None:
    with bundle.project_lock(passage_id):
        project = bundle.read_project(passage_id)
        project.origin = passage.model_dump(by_alias=True)
        bundle.write_project(project)


def take_job_key(take_id: str) -> str:
    return f"take:{take_id}"


def _clock(ms: float) -> str:
    seconds = int(round(ms / 1000.0))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _frame_ms(rhythm: SavedRhythm | None, project: bundle.ProjectFile) -> float:
    if rhythm is not None:
        return rhythm.frame_ms
    return project.frame_ms or DEFAULT_FRAME_MS


# ------------------------------------------------------------------ the passage


def _source_revision(part_id: str) -> str:
    """What the part is now, in one string: its revisions and its saved sheet."""
    stored = pipeline.load_note_events(part_id)
    header = stored.header if stored else None
    sheet = pipeline.rhythm_path(part_id)
    stamp = hashlib.sha256(sheet.read_bytes()).hexdigest()[:16] if sheet.is_file() else "-"
    revisions = f"{header.notes_revision}.{header.hands_revision}" if header is not None else "-"
    return f"{revisions}.{bundle.read_timeline(part_id).audio_revision}.{stamp}"


def _reopened(part_id: str, start: float, stop: float, revision: str) -> str | None:
    """A passage already open on this stretch of the part as it is now, if there is one."""
    for other in bundle.dependents(locate.part(part_id).project_id):
        try:
            found = load(other)
        except (locate.NotFound, ValueError):
            continue
        if (
            found.passage_of == part_id
            and abs(found.from_ms - start) < 1e-6
            and abs(found.to_ms - stop) < 1e-6
            and found.source_revision == revision
        ):
            return other
    return None


def open_passage(part_id: str, from_ms: float, to_ms: float) -> str:
    """A passage of ``part_id``: its Current made, its state written. Returns its id.

    The stretch is snapped to whole columns of the part's sheet. ``to_ms == from_ms`` is a moment
    (a new passage put in there); a moment past the end of the part is its end. A passage already
    open on the same stretch of the part as it is now is opened again instead, with its takes.
    """
    source = bundle.read_project(locate.part(part_id).project_id)
    rhythm = pipeline.load_rhythm(part_id)
    frame_ms = _frame_ms(rhythm, source)
    stored = pipeline.load_note_events(part_id)
    if stored is None and bundle.read_timeline(part_id).source_list():
        raise PassageError("Transcribe this project first: its notes are not there yet.")
    first = int(round(from_ms / frame_ms))
    last = int(round(to_ms / frame_ms))
    if last < first:
        raise PassageError("The end of the passage is before its start.")
    duration_ms = (stored.duration_seconds if stored else 0.0) * 1000.0
    end = int(math.ceil(duration_ms / frame_ms - 1e-9))
    if first > end:
        first = last = end
    last = min(last, max(end, first))
    start, stop = first * frame_ms, last * frame_ms
    revision = _source_revision(part_id)
    again = _reopened(part_id, start, stop, revision)
    if again is not None:
        return again

    passage = bundle.create_project(
        owner_id=current_user_id(),
        title=f"{source.title or 'Untitled project'} {_clock(start)}–{_clock(stop)}",
        source=PartSource(kind="composed", format="wav"),
        kind=bundle.PASSAGE_KIND,
        frame_ms=frame_ms,
    )
    current = passage.parts[0].id
    try:
        if last > first:
            paste.paste(current, paste.read_passage(part_id, start, stop), at_ms=0.0)
        else:
            pipeline.save_note_events(current, [], 0.0, passage.title)
        state = PassageState(
            passage_of=part_id,
            from_ms=start,
            to_ms=stop,
            anchor_ms=paste.anchor_at(rhythm, first),
            anchor_figure=rhythm.anchor_figure if rhythm else FigureName.NEGRA,
            source_revision=revision,
        )
        _save(passage.id, state)
    except Exception:
        bundle.delete_project(passage.id)
        raise
    return passage.id


def _take(take_id: str) -> Take:
    project = bundle.read_project(take_id)
    timeline = bundle.read_timeline(take_id)
    files = timeline.source_list()
    whole = timeline.audio[files[0]].frames if files else None
    seconds = (whole or 0) * AUDIO_FRAME_MS / 1000.0
    kept = [(segment.from_ms, segment.to_ms) for segment in timeline.segments]
    lo = kept[0][0] / 1000.0 if kept else 0.0
    hi = (
        (kept[-1][1] / 1000.0 if kept and kept[-1][1] is not None else seconds) if kept else seconds
    )
    job = jobs.active(take_job_key(take_id))
    stored = pipeline.load_note_events(take_id)
    # Read: notes of the kept stretch, and a hand for each. Its sheet may still be the page's to
    # write (a song with no sheet gives the take none).
    current = (
        stored is not None
        and stored.header.notes_revision > 0
        and stored.header.hands_notes_revision == stored.header.notes_revision
        and not pipeline.notes_are_stale(take_id, stored)
    )
    return Take(
        id=take_id,
        name=project.title,
        state="reading" if job is not None else ("ready" if current else "recorded"),
        seconds=seconds,
        from_seconds=lo,
        to_seconds=hi,
        job_id=job.id if job is not None else None,
        midi=_midi_path(take_id).is_file(),
        audio_revision=timeline.audio_revision,
    )


def state(passage_id: str) -> tuple[PassageState, bundle.ProjectFile, list[Take]]:
    """The passage, the project of the part it is about, and its takes."""
    passage = load(passage_id)
    source = bundle.read_project(locate.part(passage.passage_of).project_id)
    takes = []
    for take_id in passage.takes:
        try:
            takes.append(_take(take_id))
        except (locate.NotFound, OSError, ValueError):
            continue
    return passage, source, takes


def update(
    passage_id: str,
    *,
    take: str | None = None,
    speed: float | None = None,
    window_ms: float | None = None,
) -> PassageState:
    passage = load(passage_id)
    if take is not None:
        if take not in passage.takes:
            raise locate.NotFound("take", take)
        passage.take = take
    if speed is not None:
        low, high = SPEED_RANGE
        if not low - 1e-9 <= speed <= high + 1e-9:
            raise PassageError(f"The speed goes from ×{low:g} to ×{high:g}.")
        passage.speed = float(speed)
    if window_ms is not None:
        passage.window_ms = max(0.0, float(window_ms))
    _save(passage_id, passage)
    return passage


def discard(passage_id: str) -> None:
    """The passage and its takes, deleted. The part it was about is not touched."""
    _project(passage_id)
    bundle.delete_project(passage_id)


# ------------------------------------------------------------------ the takes


#: The notes of a take played on a MIDI piano, beside its part's other files.
MIDI_FILE = "midi.json"
#: The name a take's notes are written under when they come from a MIDI piano, not a transcription.
MIDI_ENGINE = "midi"


class MidiNote(BaseModel):
    """A key played on a MIDI piano during a take, in seconds from the start of its recording."""

    model_config = ConfigDict(populate_by_name=True)

    midi_note: int = Field(..., alias="midiNote", ge=21, le=108)
    start: float = Field(..., ge=0)
    end: float = Field(..., gt=0)
    velocity: int = Field(64, ge=1, le=127)


class _PlayedNotes:
    """The transcription of a take played on a MIDI piano: the keys it heard, already exact.

    Given to :func:`pipeline.transcribe_audio` in place of the model, so the notes are written with
    the header, the revisions and the history of a transcription; the audio is not read."""

    name = MIDI_ENGINE

    def __init__(self, events: list[NoteEvent]) -> None:
        self.events = events

    def transcribe(self, wav_path: Path) -> list[NoteEvent]:
        return [event.model_copy() for event in self.events]


def _midi_path(take_id: str) -> Path:
    return paths.part_dir(take_id) / MIDI_FILE


def midi_notes(take_id: str) -> list[MidiNote] | None:
    """The notes a take was played with on a MIDI piano, or ``None`` for a take recorded only."""
    path = _midi_path(take_id)
    if not path.is_file():
        return None
    return [MidiNote.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def _silence(seconds: float, folder: Path) -> Path:
    """A silent WAV, the audio of a take played on a MIDI piano with no microphone."""
    rate = 16_000
    path = folder / "silence.wav"
    wavfile.write(path, rate, np.zeros(max(rate, int(rate * seconds)), dtype=np.int16))
    return path


def add_take(
    passage_id: str,
    stream: BinaryIO | None,
    filename: str | None,
    notes: list[MidiNote] | None = None,
) -> str:
    """A take of the passage: a new take, the one on show. Returns its id.

    A recording (``stream``), the notes played on a MIDI piano (``notes``, in seconds from the
    start of the recording), or both: the recording is the take's audio and the notes are what
    **Write the proposal** keeps instead of transcribing it. Notes with no recording get silence as
    long as them."""
    if stream is None and not notes:
        raise PassageError("Record a take, or play one on a MIDI piano.")
    passage = load(passage_id)
    names = []
    for take_id in passage.takes:
        try:
            names.append(bundle.read_project(take_id).title)
        except locate.NotFound:
            continue
    number = 1 + max(
        [
            int(name.split()[-1])
            for name in names
            if name.split()[-1:] and name.split()[-1].isdigit()
        ]
        or [0]
    )
    extension = formats.detect_extension(filename) if stream is not None and filename else "wav"
    project = bundle.create_project(
        owner_id=current_user_id(),
        title=f"Take {number}",
        source=PartSource(kind="recording", format=extension, original_filename=filename),
        kind=bundle.PASSAGE_KIND,
        frame_ms=_frame_ms(pipeline.load_rhythm(passage.passage_of), _project(passage_id)),
    )
    take_id = project.parts[0].id
    try:
        with bundle.project_lock(take_id):
            project = bundle.read_project(take_id)
            project.origin = {"takeOf": passage_id}
            bundle.write_project(project)
        with tempfile.TemporaryDirectory(prefix="aitu-take-") as folder:
            if stream is not None:
                received = Path(folder) / f"received.{extension}"
                with received.open("wb") as handle:
                    shutil.copyfileobj(stream, handle)
            else:
                received = _silence(max(note.end for note in notes or []) + 1.0, Path(folder))
            # Raised to a level that reads: the browser's automatic gain is off (it pumps a piano).
            raised = Path(folder) / "take.flac"
            formats.louder(received, raised)
            with raised.open("rb") as handle:
                store.save_original(take_id, handle, "flac")
        ingest.finalize(take_id)
        if notes:
            _midi_path(take_id).write_text(
                json.dumps([note.model_dump(by_alias=True) for note in notes]) + "\n",
                encoding="utf-8",
            )
    except Exception:
        bundle.delete_project(take_id)
        raise
    passage.takes.append(take_id)
    passage.take = take_id
    _save(passage_id, passage)
    return take_id


def delete_take(passage_id: str, take_id: str) -> PassageState:
    passage = load(passage_id)
    if take_id not in passage.takes:
        raise locate.NotFound("take", take_id)
    bundle.delete_project(take_id)
    passage.takes.remove(take_id)
    if passage.take == take_id:
        passage.take = passage.takes[-1] if passage.takes else None
    _save(passage_id, passage)
    return passage


def _first_sheet(passage: PassageState, frame_ms: float) -> SavedRhythm | None:
    """The sheet a take is first drawn with: the settings of the song where the passage starts
    (its key there, its figure, its spacing), none of its marks. ``None`` for a song with no
    sheet: the take's own figures and key are then the page's defaults of a first write."""
    rhythm = pipeline.load_rhythm(passage.passage_of)
    if rhythm is None:
        return None
    column = int(round(passage.from_ms / rhythm.frame_ms))
    base = paste._first_sheet(rhythm, None, frame_ms)
    return base.model_copy(
        update={
            "key_signature": paste.key_at(rhythm, column),
            "anchor_ms": (passage.anchor_ms or rhythm.anchor_ms) * passage.speed,
            # Nobody decided about brackets on this take: the page proposes them.
            "ottavas": None,
        }
    )


def read_take(
    passage_id: str,
    take_id: str,
    from_seconds: float,
    to_seconds: float,
    *,
    reporter: BaseProgress | None = None,
) -> None:
    """The condensed steps of a take: keep ``[from, to)`` of it, transcribe it, split the hands,
    and write its first sheet. The job of **Write the proposal**."""
    passage = load(passage_id)
    if take_id not in passage.takes:
        raise locate.NotFound("take", take_id)
    timeline = bundle.read_timeline(take_id)
    files = timeline.source_list()
    if not files:
        raise PassageError("This take has no audio.")
    frames = timeline.audio[files[0]].frames or 0
    lo = max(0, min(frames, int(round(from_seconds * 1000 / AUDIO_FRAME_MS))))
    hi = max(0, min(frames, int(round(to_seconds * 1000 / AUDIO_FRAME_MS))))
    if hi - lo < 5:
        raise PassageError("Keep a longer stretch of the take.")
    cuts = [cut for cut in ((0, lo), (hi, frames)) if cut[1] > cut[0]]
    store.set_cuts(take_id, cuts)

    played = midi_notes(take_id)
    if played is not None:
        # Played on a MIDI piano: the keys of the kept stretch, in its time, are the notes.
        first, last = lo * AUDIO_FRAME_MS / 1000.0, hi * AUDIO_FRAME_MS / 1000.0
        kept = [
            NoteEvent(
                midi_note=note.midi_note,
                start=note.start - first,
                end=max(min(note.end, last) - first, note.start - first + 0.001),
                velocity=note.velocity,
            )
            for note in played
            if first <= note.start < last
        ]
        pipeline.transcribe_audio(take_id, engine=_PlayedNotes(kept), reporter=reporter)
    else:
        pipeline.transcribe_audio(take_id, reporter=reporter)
    stored = pipeline.load_note_events(take_id)
    if stored is None:
        raise PassageError("The take could not be transcribed.")
    frame_ms = bundle.read_project(take_id).frame_ms or DEFAULT_FRAME_MS
    with pipeline.piece_lock(take_id):
        split = pipeline.inferred_split(take_id, frame_ms, keep_saved=False, reporter=reporter)
        hands = saved_hands.hands_of_split(split, stored.events, guess_unplaced=True)
        events = [
            (
                event.model_copy(
                    update={"hand": hands.get(event.id, event.hand), "hand_guessed": False}
                )
                if event.id in hands
                else event
            )
            for event in stored.events
        ]
        written = pipeline.save_edit(
            take_id,
            events,
            stored.duration_seconds,
            stored.title,
            before=stored.header,
            notes_changed=False,
            hands_changed=True,
        )
        sheet = _first_sheet(passage, frame_ms)
        if sheet is not None:
            pipeline.save_rhythm(
                take_id, sheet.model_copy(update={"hands_revision": written.header.hands_revision})
            )
        else:
            pipeline.clear_rhythm(take_id)


# ------------------------------------------------------------------ the promotion


def _kept_ms(take_id: str) -> float:
    return audio_timeline.kept_frames(bundle.read_timeline(take_id)) * AUDIO_FRAME_MS


def _in_song_time(
    rhythm: SavedRhythm | None, speed: float, figure: FigureName | None, anchor_ms: float | None
) -> SavedRhythm | None:
    """The take's sheet as the song reads it: what a figure lasts, played ``speed`` times as fast,
    named with the song's figure. The columns are left in the take's (the paste rescales them)."""
    if rhythm is None:
        return None
    named = figure or rhythm.anchor_figure
    ratio = FIGURE_NEGRAS[named] / FIGURE_NEGRAS[rhythm.anchor_figure]
    anchor = (anchor_ms if anchor_ms is not None else rhythm.anchor_ms / speed) * ratio
    return rhythm.model_copy(
        update={
            "anchor_figure": named,
            "anchor_ms": anchor,
            "speed_changes": [
                change.model_copy(update={"anchor_ms": change.anchor_ms / speed * ratio})
                for change in rhythm.speed_changes
            ],
        }
    )


@dataclass
class _Plan:
    passage: PassageState
    take_id: str
    raw: paste.Passage
    at_ms: float
    replace_to_ms: float | None
    columns: int | None
    keep_audio: bool
    #: The take's audio at the speed: the stored ranges, or a file to render first.
    render: tuple[float, float] | None
    #: A window's length in ms of the song: a note of the take that starts after it is not in.
    limit_ms: float | None


def _plan(passage_id: str, mode: Mode, audio: AudioChoice, sheet: SavedRhythm | None) -> _Plan:
    passage = load(passage_id)
    take_id = passage.take
    if take_id is None:
        raise PassageError("Record a take first.")
    if _take(take_id).state != "ready":
        raise PassageError("Write the proposal of this take first.")
    take_sheet = sheet if sheet is not None else pipeline.load_rhythm(take_id)
    speed = passage.speed
    length = passage.length_ms
    if mode == "window":
        if length <= 0:
            raise PassageError("A new passage has no window: put the whole take in.")
        start = passage.window_ms
        stop = start + length * speed
    elif mode == "whole":
        start, stop = 0.0, _kept_ms(take_id)
    else:
        raise PassageError(f"Unknown promotion {mode!r}.")
    if audio not in ("original", "recording"):
        raise PassageError(f"Unknown audio choice {audio!r}.")
    keep_audio = audio == "original"
    if keep_audio and mode != "window":
        raise PassageError("A passage of another length cannot keep the original audio.")
    raw = paste.read_passage(take_id, start, max(stop, start + 1.0), sheet=take_sheet)
    target_rhythm = pipeline.load_rhythm(passage.passage_of)
    target_frame = _frame_ms(
        target_rhythm, bundle.read_project(locate.part(passage.passage_of).project_id)
    )
    columns = int(round(length / target_frame)) if mode == "window" else None
    rendered: tuple[float, float] | None = None
    if not keep_audio and abs(speed - 1.0) > 1e-9:
        rendered = (raw.from_ms, raw.to_ms if mode == "whole" else raw.from_ms + length * speed)
    return _Plan(
        passage=passage,
        take_id=take_id,
        raw=raw,
        at_ms=passage.from_ms,
        replace_to_ms=passage.to_ms if length > 0 else None,
        columns=columns,
        keep_audio=keep_audio,
        render=rendered,
        limit_ms=length if mode == "window" else None,
    )


def _song_passage(plan: _Plan, pieces: list[audio_timeline.Piece] | None) -> paste.Passage:
    """The take's passage read in the song's time: ``speed`` times as fast."""
    speed = plan.passage.speed
    raw = plan.raw
    target = pipeline.load_rhythm(plan.passage.passage_of)
    rhythm = _in_song_time(
        raw.rhythm,
        speed,
        target.anchor_figure if target is not None else None,
        plan.passage.anchor_ms,
    )
    limit = None if plan.limit_ms is None else plan.limit_ms / 1000.0
    events = []
    for event in raw.events:
        start, end = event.start / speed, event.end / speed
        if limit is not None:
            # The window is the passage's length exactly: a note snapped in after it is not in it.
            if start >= limit - 1e-9:
                continue
            end = min(end, limit)
        events.append(event.model_copy(update={"start": start, "end": max(end, start + 0.001)}))
    return replace(
        raw,
        frame_ms=raw.frame_ms / speed,
        from_ms=raw.from_ms / speed,
        to_ms=raw.to_ms / speed,
        events=events,
        pieces=raw.pieces if pieces is None else pieces,
        rhythm=rhythm,
    )


def _rendered(plan: _Plan, folder: Path) -> list[audio_timeline.Piece]:
    """The take's kept audio under the passage, played ``speed`` times as fast with its pitch
    kept, stored as a new file. The paste puts this file in."""
    assert plan.render is not None
    start, stop = plan.render
    timeline = bundle.read_timeline(plan.take_id)
    first = int(round(start / AUDIO_FRAME_MS))
    last = int(round(stop / AUDIO_FRAME_MS))
    pieces = audio_timeline.passage_pieces(timeline, first, last)
    if not pieces:
        return []
    played = folder / "played.wav"
    sources.write_ranges(
        [(piece.audio, piece.format, piece.start, piece.end) for piece in pieces], played
    )
    faster = folder / "faster.wav"
    audio_splice.stretch_by_rate(played, faster, plan.passage.speed, keep_format=True)
    rate, samples = formats.sample_count(faster)
    frames = math.ceil(samples * 1000 / (rate * AUDIO_FRAME_MS))
    content_hash = audio_files.add_file(faster, "wav", duration_ms=frames * AUDIO_FRAME_MS)
    want = int(round((last - first) / plan.passage.speed))
    return [
        audio_timeline.Piece(
            audio=content_hash, format="wav", file_frames=frames, start=0, end=min(frames, want)
        )
    ]


def facts(
    passage_id: str, mode: Mode, audio: AudioChoice, sheet: SavedRhythm | None = None
) -> Facts:
    """What :func:`promote` would do, without writing anything."""
    plan = _plan(passage_id, mode, audio, sheet)
    passage = plan.passage
    target = passage.passage_of
    rhythm = pipeline.load_rhythm(target)
    stored = pipeline.load_note_events(target)
    frame_ms = _frame_ms(rhythm, bundle.read_project(locate.part(target).project_id))
    first = int(round(passage.from_ms / frame_ms))
    last = int(round(passage.to_ms / frame_ms))
    notes_out = sum(
        1
        for event in (stored.events if stored else [])
        if not event.removed and first <= int(round(event.start * 1000 / frame_ms)) < last
    )
    if plan.columns is not None:
        columns = plan.columns
    else:
        columns = max(1, math.ceil(plan.raw.length_ms / passage.speed / frame_ms - 1e-9))
    duration = stored.duration_seconds if stored else 0.0
    change = (columns - (last - first)) * frame_ms
    return Facts(
        mode=mode,
        audio=audio,
        notes_out=notes_out,
        notes_in=sum(1 for event in _song_passage(plan, []).events if not event.removed),
        marks_dropped=marks.dropped(rhythm, first, last),
        length_change_ms=change,
        duration_seconds=max(duration, passage.from_ms / 1000.0) + change / 1000.0,
    )


def promote(
    passage_id: str, mode: Mode, audio: AudioChoice, sheet: SavedRhythm | None = None
) -> Promotion:
    """Put the take into the part in place of the passage, in one write, and close the passage.

    ``sheet`` is the Proposal's sheet as the page holds it, unsaved edits included."""
    plan = _plan(passage_id, mode, audio, sheet)
    target = plan.passage.passage_of
    with tempfile.TemporaryDirectory(prefix="aitu-promote-") as folder:
        pieces = _rendered(plan, Path(folder)) if plan.render is not None else None
        done = paste.paste(
            target,
            _song_passage(plan, pieces),
            at_ms=plan.at_ms,
            replace_to_ms=plan.replace_to_ms,
            keep_audio=plan.keep_audio,
            columns=plan.columns,
            audio_name=bundle.read_project(plan.take_id).title,
            audio_kind="recording",
        )
    project_id = locate.part(target).project_id
    bundle.delete_project(passage_id)
    return Promotion(
        part=target,
        project_id=project_id,
        before_version=done.before_version,
        at_ms=done.at_ms,
        length_ms=done.length_ms,
        sheet=done.sheet,
    )


def describe(passage_id: str) -> dict[str, Any]:
    """The passage as the page reads it (the answer of ``GET /passages/{id}``)."""
    passage, source, takes = state(passage_id)
    shown = next((take for take in takes if take.id == passage.take), None)
    return {
        "id": passage_id,
        "part": passage.passage_of,
        "projectId": source.id,
        "title": source.title or "Untitled project",
        "current": passage_id,
        "fromMs": passage.from_ms,
        "toMs": passage.to_ms,
        "anchorMs": passage.anchor_ms,
        "anchorFigure": passage.anchor_figure.value,
        "take": passage.take,
        "speed": passage.speed,
        "windowMs": passage.window_ms,
        "takeMs": _kept_ms(shown.id) if shown is not None else None,
        "takes": [
            {
                "id": take.id,
                "name": take.name,
                "state": take.state,
                "seconds": take.seconds,
                "fromSeconds": take.from_seconds,
                "toSeconds": take.to_seconds,
                "jobId": take.job_id,
                "midi": take.midi,
                "audioRevision": take.audio_revision,
            }
            for take in takes
        ],
    }
