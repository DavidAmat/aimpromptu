"""Copy and paste of a passage (implementation 02, plan section 12, Phase 8).

**Copy** puts a reference in the clipboard: the part and a stretch of it in milliseconds. The
clipboard carries no notes and no audio. **Paste** reads them from the source here, so a copied
passage can be as long as a song, and writes them into the target part in one write:

* **the notes** of the source whose onset is inside the stretch (taken off the page or not), cut
  where the stretch ends, with new ids and the hand they have;
* **the marks** of ``sheet.json`` inside the stretch (fingering, figures and beams set by hand,
  octave brackets, clef changes, lyrics pieces, cue size, spacing ...), at their new columns. The
  key signature in force where the copy starts becomes a key change at the insertion point, so the
  passage reads as it did in its song; the clef of each hand and the speed (what a gap is worth)
  the same way; and after the passage the target goes back to what it had there;
* **the audio**: the ranges of stored files the stretch plays, put into the target's timeline (no
  audio byte is copied, plan P-3), with silence where the passage plays longer than its audio;
* **everything after the insertion point** moves later by the passage's length, notes and marks
  and audio together: the Insert rule of Compose, made general (rule 2 as changed by Q-3).

With ``replace_to`` the stretch ``[at, replace_to)`` of the target is taken out first, in the same
write: its notes go, its marks go, its audio becomes cuts.

**A passage occupies a whole number of columns** of the target, as a composed one does
(:mod:`aitu_backend.editing.compose`): the stretch is in columns of the source's sheet, and the
insertion point in columns of the target's, so every mark after it moves by the same integer.

**Undo.** The target's notes, sheet, timeline and file names are kept as a snapshot of its history
before anything is written (:func:`aitu_backend.editing.history.snapshot_current`), and the answer
says which. Putting it back (:func:`aitu_backend.editing.history.restore`) keeps the pasted state as
the next snapshot, which is the redo.
"""

from __future__ import annotations

import math
import shutil
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from aitu_backend.audio import sources, timeline as audio_timeline
from aitu_backend.audio.timeline import Piece
from aitu_backend.editing import compose, history, marks
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS, frame_of_seconds, validate_frame_ms
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.schemas.rhythm import ClefChange, KeyChange, SavedRhythm, SpeedChange
from aitu_backend.storage import bundle, locate, paths
from aitu_backend.storage.bundle import SourceFile
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent

__all__ = [
    "CutResult",
    "Passage",
    "PasteError",
    "PasteResult",
    "apply_audio",
    "audio_with",
    "cut",
    "part_length_ms",
    "paste",
    "sheet_frame_ms_of",
    "whole_ms",
    "read_passage",
]

Hand = Literal["right", "left"]
Clef = Literal["treble", "bass"]
HANDS: tuple[Hand, Hand] = ("right", "left")
#: The clef each hand reads when nothing says otherwise.
DEFAULT_CLEF: dict[Hand, Clef] = {"right": "treble", "left": "bass"}
#: Two speeds closer than this read the same figures: no speed change is written for them.
SPEED_TOLERANCE = 0.02
#: The 10 ms frame of the audio timeline.
AUDIO_FRAME_MS = bundle.FRAME_MS


class PasteError(ValueError):
    """A paste that cannot be done, in words the page shows."""


@dataclass
class Passage:
    """A stretch of a part, read for a paste."""

    part_id: str
    title: str
    frame_ms: float
    #: The stretch, snapped to whole columns of the source's sheet.
    from_ms: float
    to_ms: float
    #: The notes, in seconds from the start of the stretch.
    events: list[NoteEvent]
    #: The ranges of stored files the stretch plays, in order; shorter than the stretch where the
    #: source's audio ends before it.
    pieces: list[Piece]
    #: The source's sheet, or ``None`` when it has none saved.
    rhythm: SavedRhythm | None
    #: Its marks inside the stretch, counted from its first column.
    marks: dict[str, list[Any]] = field(default_factory=dict)

    @property
    def length_ms(self) -> float:
        return self.to_ms - self.from_ms

    @property
    def columns(self) -> int:
        return int(round(self.length_ms / self.frame_ms))


@dataclass
class PasteResult:
    #: The snapshot that holds the target as it was: the undo.
    before_version: int
    at_ms: float
    length_ms: float
    notes_in: int
    notes_moved: int
    notes_removed: int
    duration_seconds: float
    #: The target's sheet after the paste, or ``None`` when it has none.
    sheet: SavedRhythm | None


# ------------------------------------------------------------------ what is in force


def key_at(rhythm: SavedRhythm | None, column: int) -> str:
    key = (rhythm.key_signature if rhythm else None) or "C"
    for change in sorted(rhythm.key_changes if rhythm else [], key=lambda c: c.from_column):
        if change.from_column <= column:
            key = change.key_signature
    return key


def clef_at(rhythm: SavedRhythm | None, hand: Hand, column: int) -> Clef:
    clef: Clef = DEFAULT_CLEF[hand]
    changes = [change for change in (rhythm.clef_changes if rhythm else []) if change.hand == hand]
    for change in sorted(changes, key=lambda c: c.from_column):
        if change.from_column <= column:
            clef = change.clef
    return clef


def anchor_at(rhythm: SavedRhythm | None, column: int) -> float | None:
    if rhythm is None:
        return None
    anchor = rhythm.anchor_ms
    for change in sorted(rhythm.speed_changes, key=lambda c: c.start_frame):
        if change.start_frame <= column:
            anchor = change.anchor_ms
    return anchor


@dataclass
class CutResult:
    #: The snapshot that holds the part as it was: the undo.
    before_version: int
    from_ms: float
    to_ms: float
    notes_removed: int
    duration_seconds: float
    #: The part's sheet after the cut, or ``None`` when it has none.
    sheet: SavedRhythm | None


# ------------------------------------------------------------------ the source


def part_length_ms(part_id: str) -> float:
    """How long the piece of a part is: its notes or its audio, whichever is longer."""
    stored = pipeline.load_note_events(part_id)
    notes_ms = stored.duration_seconds * 1000.0 if stored else 0.0
    audio_ms = audio_timeline.kept_frames(bundle.read_timeline(part_id)) * AUDIO_FRAME_MS
    return max(notes_ms, float(audio_ms))


def sheet_frame_ms_of(part_id: str) -> float:
    """The column length of a part's sheet: the saved one's, or the project's."""
    project = bundle.read_project(locate.part(part_id).project_id)
    return _sheet_frame_ms(pipeline.load_rhythm(part_id), project)


def whole_ms(part_id: str) -> float:
    """The length of a part rounded up to whole columns of its sheet: the stretch that holds all
    of it, and the moment after its last column."""
    frame_ms = sheet_frame_ms_of(part_id)
    return math.ceil(part_length_ms(part_id) / frame_ms - 1e-9) * frame_ms


def _sheet_frame_ms(rhythm: SavedRhythm | None, project: bundle.ProjectFile) -> float:
    if rhythm is not None:
        return validate_frame_ms(rhythm.frame_ms)
    return validate_frame_ms(project.frame_ms or DEFAULT_FRAME_MS)


def read_passage(
    part_id: str, from_ms: float, to_ms: float, *, sheet: SavedRhythm | None = None
) -> Passage:
    """The notes, marks and audio of ``[from_ms, to_ms)`` of a part, snapped to its columns.

    ``sheet`` is the part's sheet as a page holds it (a Proposal of Record in Sheet, Phase 9);
    without it the saved one is read."""
    project = bundle.read_project(locate.part(part_id).project_id)
    rhythm = sheet if sheet is not None else pipeline.load_rhythm(part_id)
    frame_ms = _sheet_frame_ms(rhythm, project)
    first = int(round(from_ms / frame_ms))
    last = int(round(to_ms / frame_ms))
    if last <= first:
        raise PasteError("The copied stretch is empty.")
    start, stop = first * frame_ms / 1000.0, last * frame_ms / 1000.0

    stored = pipeline.load_note_events(part_id)
    events: list[NoteEvent] = []
    for event in stored.events if stored else []:
        if not first <= frame_of_seconds(event.start, frame_ms) < last:
            continue
        begin = max(0.0, event.start - start)
        end = min(event.end, stop) - start
        if end <= begin:
            end = begin + 0.001
        events.append(event.model_copy(update={"id": None, "start": begin, "end": end}))

    timeline = bundle.read_timeline(part_id)
    pieces = audio_timeline.passage_pieces(
        timeline,
        int(round(first * frame_ms / AUDIO_FRAME_MS)),
        int(round(last * frame_ms / AUDIO_FRAME_MS)),
    )
    return Passage(
        part_id=part_id,
        title=project.title or "Untitled project",
        frame_ms=frame_ms,
        from_ms=first * frame_ms,
        to_ms=last * frame_ms,
        events=events,
        pieces=pieces,
        rhythm=rhythm,
        marks=marks.extract(rhythm, first, last) if rhythm else {},
    )


# ------------------------------------------------------------------ the notes


def _remove_events(
    events: list[NoteEvent], start: float, stop: float, frame_ms: float
) -> tuple[list[NoteEvent], int]:
    """The notes of ``[start, stop)`` seconds taken out, by onset column; the notes after move
    earlier by the stretch's length and a note sounding into it is cut where it starts."""
    first, last = frame_of_seconds(start, frame_ms), frame_of_seconds(stop, frame_ms)
    length = stop - start
    out: list[NoteEvent] = []
    removed = 0
    for event in events:
        column = frame_of_seconds(event.start, frame_ms)
        if first <= column < last:
            removed += 1
        elif column >= last:
            out.append(
                event.model_copy(update={"start": event.start - length, "end": event.end - length})
            )
        elif event.end > start:
            out.append(event.model_copy(update={"end": max(start, event.start + 0.001)}))
        else:
            out.append(event)
    return out, removed


# ------------------------------------------------------------------ the marks


def _rescaled(passage_marks: dict[str, list[Any]], factor: float, limit: int) -> dict[str, Any]:
    """The marks of a passage counted in columns of another length (``factor`` = source column /
    target column). Only for two sheets read at different ``frameMs``."""
    out: dict[str, list[Any]] = {}
    for name, attr in marks.POINTS:
        out[name] = [
            item.model_copy(update={attr: min(limit - 1, int(round(getattr(item, attr) * factor)))})
            for item in passage_marks.get(name, [])
        ]
    for name, first, end in marks.RANGES:
        if name not in passage_marks:
            continue
        scaled = []
        for item in passage_marks[name]:
            a = int(round(getattr(item, first) * factor))
            b = min(limit, int(round(getattr(item, end) * factor)))
            if b > a:
                scaled.append(item.model_copy(update={first: a, end: b}))
        out[name] = scaled
    return out


def _first_sheet(source: SavedRhythm, target: SavedRhythm | None, frame_ms: float) -> SavedRhythm:
    """The sheet of a target that had no music: the source's settings, none of its marks, and the
    target's own title lines."""
    empty: dict[str, list[Any] | None] = {name: [] for name, _ in marks.POINTS}
    empty.update({name: [] for name, _, _ in marks.RANGES})
    empty["ottavas"] = None if source.ottavas is None else []
    base = source.model_copy(
        update={
            **empty,
            "frame_ms": frame_ms,
            "title": target.title if target else None,
            "subtitle": target.subtitle if target else None,
            "artist": target.artist if target else None,
            "lyrics_pool": target.lyrics_pool if target else [],
            "hands_revision": None,
        }
    )
    return base


def _transitions(
    sheet: SavedRhythm,
    before: SavedRhythm | None,
    passage: Passage,
    at: int,
    columns: int,
    music_after: bool,
    empty_target: bool,
) -> SavedRhythm:
    """The key, the clefs and the speed at the edges of the passage: what the passage had where
    the copy starts, from the insertion point; what the target had there, again after it.

    ``before`` is the target's sheet before the paste (after any stretch was taken out), where
    what is in force around the insertion point is read; ``None`` for a target with no music.
    ``sheet`` already has the target's marks moved and the passage's put in.
    """
    source = passage.rhythm
    end = at + columns
    first = int(round(passage.from_ms / passage.frame_ms))
    key_signature = sheet.key_signature
    key_changes = list(sheet.key_changes)
    clef_changes = list(sheet.clef_changes)
    speed_changes = list(sheet.speed_changes)

    # Where the passage starts: what the source had there.
    passage_key = key_at(source, first)
    if empty_target or before is None:
        key_signature = passage_key
    elif passage_key != key_at(before, at - 1):
        if at == 0:
            key_signature = passage_key
        else:
            key_changes.append(KeyChange(from_column=at, key_signature=passage_key))
    for hand in HANDS:
        clef = clef_at(source, hand, first)
        # No clef change can be stored at column 0: each hand starts on its own clef.
        if at > 0 and clef != clef_at(before, hand, at - 1):
            clef_changes.append(ClefChange(hand=hand, from_column=at, clef=clef))
    passage_anchor = anchor_at(source, first)
    target_anchor = anchor_at(before, at - 1)
    if (
        not empty_target
        and at > 0
        and passage_anchor
        and target_anchor
        and abs(passage_anchor / target_anchor - 1) > SPEED_TOLERANCE
    ):
        speed_changes.append(SpeedChange(start_frame=at, anchor_ms=passage_anchor))

    placed = sheet.model_copy(
        update={
            "key_signature": key_signature,
            "key_changes": key_changes,
            "clef_changes": clef_changes,
            "speed_changes": speed_changes,
            # A target with no music reads at the speed the passage had where the copy starts
            # (a stretch after a speed change of its song, Phase 10).
            **({"anchor_ms": passage_anchor} if empty_target and passage_anchor else {}),
        }
    )
    # After it: what the target had from the insertion point on, unless a mark of its own (moved
    # to the end of the passage) already says it.
    if music_after and before is not None and not empty_target:
        wanted = key_at(before, at)
        if key_at(placed, end - 1) != wanted and not any(c.from_column == end for c in key_changes):
            key_changes.append(KeyChange(from_column=end, key_signature=wanted))
        for hand in HANDS:
            wanted_clef = clef_at(before, hand, at)
            if clef_at(placed, hand, end - 1) != wanted_clef and not any(
                c.hand == hand and c.from_column == end for c in clef_changes
            ):
                clef_changes.append(ClefChange(hand=hand, from_column=end, clef=wanted_clef))
        wanted_anchor = anchor_at(before, at)
        now = anchor_at(placed, end - 1)
        if (
            wanted_anchor
            and now
            and abs(now / wanted_anchor - 1) > SPEED_TOLERANCE
            and not any(c.start_frame == end for c in speed_changes)
        ):
            speed_changes.append(SpeedChange(start_frame=end, anchor_ms=wanted_anchor))

    return placed.model_copy(
        update={
            "key_changes": sorted(key_changes, key=lambda c: c.from_column),
            "clef_changes": sorted(clef_changes, key=lambda c: (c.from_column, c.hand)),
            "speed_changes": sorted(speed_changes, key=lambda c: c.start_frame),
        }
    )


# ------------------------------------------------------------------ the audio


def _clock(ms: float) -> str:
    seconds = int(round(ms / 1000.0))
    return f"{seconds // 60}:{seconds % 60:02d}"


def audio_with(
    part_id: str,
    pieces: list[Piece],
    *,
    label: str,
    kind: str,
    at_frame: int,
    length_frames: int,
    replace_to_frame: int | None = None,
) -> tuple[bundle.Timeline, list[SourceFile]] | None:
    """The part's timeline with ``pieces`` put in at ``at_frame`` of the piece (10 ms frames),
    ``length_frames`` long (silence after them when they play less), and the names of its files.

    ``replace_to_frame`` first cuts ``[at_frame, replace_to_frame)`` out. ``None`` when neither
    the part nor the pieces have any audio: there is nothing to keep in step with the notes.
    Writes nothing but a stored file of silence when one is needed (:func:`apply_audio` writes).
    """
    timeline = bundle.read_timeline(part_id)
    has_audio = bool(timeline.source_list())
    if not has_audio and not pieces:
        return None
    project = bundle.read_project(locate.part(part_id).project_id)
    names = bundle.source_files(project, part_id, timeline) if has_audio else []
    if replace_to_frame is not None and has_audio:
        timeline = audio_timeline.remove(timeline, at_frame, replace_to_frame)

    def described(piece: Piece, name: str, what: str) -> SourceFile:
        return SourceFile(
            audio=piece.audio,
            name=name,
            kind=what,
            format=piece.format,
            duration_seconds=piece.frames * AUDIO_FRAME_MS / 1000.0,
        )

    placed = list(pieces)
    arriving = [described(piece, label, kind) for piece in placed]
    played = sum(piece.frames for piece in placed)
    if played < length_frames:
        gap = audio_timeline.silence(length_frames - played)
        placed.append(gap)
        arriving.append(described(gap, "Silence", "silence"))
    have = audio_timeline.kept_frames(timeline)
    if at_frame > have:
        gap = audio_timeline.silence(at_frame - have)
        placed.insert(0, gap)
        arriving.insert(0, described(gap, "Silence", "silence"))
        at_frame = have
    result, origins = audio_timeline.insert_with_origins(timeline, at_frame, placed)
    files = [
        names[index].model_copy() if origin == "old" else arriving[index].model_copy()
        for origin, index in origins
    ]
    return result, files


def apply_audio(part_id: str, timeline: bundle.Timeline, files: list[SourceFile]) -> None:
    """Point the part at its new timeline, name its files, and forget the derived audio."""
    cache = paths.part_cache_dir(part_id)
    before = bundle.read_timeline(part_id)
    if before.source_list() and not before.joined:
        # Its normalized.wav is its one file's 16 kHz copy: keep it as that file's.
        only = before.source_list()[0]
        normalized, copy = cache / "normalized.wav", cache / f"{sources.SOURCE_PREFIX}{only}.wav"
        if normalized.is_file() and not copy.is_file():
            shutil.copyfile(normalized, copy)
    project_id = locate.part(part_id).project_id
    with bundle.project_lock(project_id):
        bundle.write_timeline(part_id, timeline)
        project = bundle.read_project(project_id)
        source = project.part(part_id).source
        if timeline.joined:
            source.files = files
        else:
            source.files = []
            if files:
                first = files[0]
                # A part of one file says where it came from in the words of an upload; a pasted
                # whole file or a stretch of silence is a segment of something else.
                known = {kind.value for kind in AudioSource}
                source.kind = first.kind if first.kind in known else AudioSource.SEGMENT.value
                source.format = first.format
                source.original_filename = first.original_filename
                source.duration_seconds = first.duration_seconds
        bundle.write_project(project)
    history.forget_derived(part_id)


def _share_sixteen_k(source_part: str, target_part: str, pieces: list[Piece]) -> None:
    """The source's 16 kHz copy of a file the passage plays, given to the target's cache, so the
    target's joined audio does not decode that file again."""
    timeline = bundle.read_timeline(source_part)
    hashes = {piece.audio for piece in pieces}
    target = paths.part_cache_dir(target_part)
    target.mkdir(parents=True, exist_ok=True)
    origin = paths.part_cache_dir(source_part)
    candidates: dict[str, Any] = {}
    if timeline.source_list() and not timeline.joined:
        candidates[timeline.source_list()[0]] = origin / "normalized.wav"
    for content_hash in hashes:
        candidates.setdefault(content_hash, origin / f"{sources.SOURCE_PREFIX}{content_hash}.wav")
    for content_hash in hashes:
        found = candidates.get(content_hash)
        copy = target / f"{sources.SOURCE_PREFIX}{content_hash}.wav"
        if found is not None and found.is_file() and not copy.is_file():
            shutil.copyfile(found, copy)


# ------------------------------------------------------------------ the paste


def paste(
    part_id: str,
    passage: Passage,
    *,
    at_ms: float,
    replace_to_ms: float | None = None,
    sheet: SavedRhythm | None = None,
    keep_audio: bool = False,
    columns: int | None = None,
    audio_name: str | None = None,
    audio_kind: str = "passage",
) -> PasteResult:
    """Put ``passage`` into the part at ``at_ms`` (or in place of ``[at_ms, replace_to_ms)``).

    ``sheet`` is the sheet as the page holds it, unsaved edits included: it is what the marks are
    moved in, and it is saved by the paste. Without it the saved sheet is used.

    Two options of a promotion of Record in Sheet (Phase 9): ``keep_audio`` leaves the part's
    audio as it is (only the notes and marks change, so the length must not), and ``columns`` is
    the passage's length in columns of the part, instead of its own length rounded up (a take
    fitted into the window it replaces is exactly as long as the window). ``audio_name`` and
    ``audio_kind`` are what the Source step calls the file put in (a take: ``"Take 2"``,
    ``recording``); by default the copied passage's title and stretch, ``passage``.
    """
    project = bundle.read_project(locate.part(part_id).project_id)
    with pipeline.piece_lock(part_id):
        stored = pipeline.load_note_events(part_id)
        timeline = bundle.read_timeline(part_id)
        if stored is None:
            if timeline.source_list():
                raise PasteError("Transcribe this project first: its notes are not there yet.")
            pipeline.save_note_events(part_id, [], 0.0, project.title)
            stored = pipeline.load_note_events(part_id)
            assert stored is not None
        saved = pipeline.load_rhythm(part_id)
        current = sheet if sheet is not None else saved
        frame_ms = _sheet_frame_ms(current, project)
        at = int(round(at_ms / frame_ms))
        cut_to = None if replace_to_ms is None else int(round(replace_to_ms / frame_ms))
        if cut_to is not None and cut_to <= at:
            raise PasteError("Mark a stretch to paste over, or none to paste at the cursor.")
        if columns is None:
            columns = max(1, math.ceil(passage.length_ms / frame_ms - 1e-9))
        if keep_audio and (cut_to is None or cut_to - at != columns):
            raise PasteError("Only a passage as long as the one it replaces keeps the audio.")
        at_seconds = at * frame_ms / 1000.0
        length_seconds = columns * frame_ms / 1000.0
        live_before = [event for event in stored.events if not event.removed]
        empty_target = not live_before and not timeline.source_list()

        # The stretch pasted over goes first.
        events = list(stored.events)
        duration = stored.duration_seconds
        removed = 0
        before = current
        if cut_to is not None:
            stop = cut_to * frame_ms / 1000.0
            events, removed = _remove_events(events, at_seconds, stop, frame_ms)
            duration -= max(0.0, min(stop, duration) - at_seconds)
            if before is not None:
                before = _cut_transitions(before, at, cut_to)
        # Then the passage.
        arriving = [
            event.model_copy(
                update={"start": event.start + at_seconds, "end": event.end + at_seconds}
            )
            for event in passage.events
        ]
        result_events, moved, _ = compose.insert_events(
            events,
            arriving,
            at_seconds=at_seconds,
            passage_seconds=length_seconds,
            duration_seconds=duration,
            placement="insert",
            frame_ms=frame_ms,
        )
        new_duration = max(duration, at_seconds) + length_seconds
        music_after = at_seconds < duration - 1e-9

        new_sheet = _sheet_after(
            before,
            passage,
            at=at,
            columns=columns,
            frame_ms=frame_ms,
            music_after=music_after,
            empty_target=empty_target,
        )

        audio = (
            None
            if keep_audio
            else audio_with(
                part_id,
                passage.pieces,
                label=audio_name
                or f"{passage.title} {_clock(passage.from_ms)}–{_clock(passage.to_ms)}",
                kind=audio_kind,
                at_frame=int(round(at_seconds * 1000 / AUDIO_FRAME_MS)),
                replace_to_frame=(
                    None if cut_to is None else int(round(cut_to * frame_ms / AUDIO_FRAME_MS))
                ),
                length_frames=int(round(length_seconds * 1000 / AUDIO_FRAME_MS)),
            )
        )

        # Everything is worked out: keep the part as it is, then write.
        before_version = history.current_version(part_id)
        history.snapshot_current(part_id)
        try:
            header = stored.header
            if audio is not None:
                _share_sixteen_k(passage.part_id, part_id, passage.pieces)
                apply_audio(part_id, *audio)
                header = replace(header, audio_revision=audio[0].audio_revision)
            written = pipeline.save_edit(
                part_id,
                result_events,
                new_duration,
                stored.title or project.title,
                before=header,
                notes_changed=True,
                hands_changed=True,
            )
            if new_sheet is not None:
                # The page that pasted draws the result, so a sheet that was current stays current.
                was_current = (
                    sheet is not None
                    or saved is None
                    or ((saved.hands_revision or 0) == stored.header.hands_revision)
                )
                new_sheet = new_sheet.model_copy(
                    update={
                        "hands_revision": (
                            written.header.hands_revision
                            if was_current
                            else (saved.hands_revision if saved else None)
                        )
                    }
                )
                pipeline.save_rhythm(part_id, new_sheet)
        except Exception:
            history.restore(part_id, before_version)
            raise
    return PasteResult(
        before_version=before_version,
        at_ms=at * frame_ms,
        length_ms=columns * frame_ms,
        notes_in=len(arriving),
        notes_moved=moved,
        notes_removed=removed,
        duration_seconds=new_duration,
        sheet=new_sheet,
    )


def cut(
    part_id: str, from_ms: float, to_ms: float, *, sheet: SavedRhythm | None = None
) -> CutResult:
    """Take ``[from_ms, to_ms)`` out of the part, the opposite of a paste (Phase 10, a part split
    in two): its notes go, its marks go (a key, clef or speed change inside moves to its start),
    its audio becomes cuts (the Audio step can restore them), and everything after moves earlier.

    ``sheet`` is the sheet as the page holds it; without it the saved one. The part is kept as a
    snapshot first, so the cut is undone like a paste."""
    project = bundle.read_project(locate.part(part_id).project_id)
    with pipeline.piece_lock(part_id):
        stored = pipeline.load_note_events(part_id)
        if stored is None:
            raise PasteError("Transcribe this project first: its notes are not there yet.")
        saved = pipeline.load_rhythm(part_id)
        current = sheet if sheet is not None else saved
        frame_ms = _sheet_frame_ms(current, project)
        start, stop = int(round(from_ms / frame_ms)), int(round(to_ms / frame_ms))
        if stop <= start:
            raise PasteError("The stretch to take out is empty.")
        start_seconds, stop_seconds = start * frame_ms / 1000.0, stop * frame_ms / 1000.0
        events, removed = _remove_events(stored.events, start_seconds, stop_seconds, frame_ms)
        duration = stored.duration_seconds - max(
            0.0, min(stop_seconds, stored.duration_seconds) - start_seconds
        )
        # A stretch that runs to the end leaves nothing after it to keep reading as before.
        tail = stop_seconds >= stored.duration_seconds - 1e-9
        new_sheet = (
            None
            if current is None
            else (
                marks.cut_out(current, start, stop)
                if tail
                else _cut_transitions(current, start, stop)
            )
        )
        timeline = bundle.read_timeline(part_id)
        audio = None
        if timeline.source_list():
            audio = (
                audio_timeline.remove(
                    timeline,
                    int(round(start_seconds * 1000 / AUDIO_FRAME_MS)),
                    int(round(stop_seconds * 1000 / AUDIO_FRAME_MS)),
                ),
                bundle.source_files(project, part_id, timeline),
            )

        before_version = history.current_version(part_id)
        history.snapshot_current(part_id)
        try:
            header = stored.header
            if audio is not None:
                apply_audio(part_id, *audio)
                header = replace(header, audio_revision=audio[0].audio_revision)
            written = pipeline.save_edit(
                part_id,
                events,
                max(0.0, duration),
                stored.title or project.title,
                before=header,
                notes_changed=True,
                hands_changed=True,
            )
            if new_sheet is not None:
                was_current = (
                    sheet is not None
                    or saved is None
                    or ((saved.hands_revision or 0) == stored.header.hands_revision)
                )
                new_sheet = new_sheet.model_copy(
                    update={
                        "hands_revision": (
                            written.header.hands_revision
                            if was_current
                            else (saved.hands_revision if saved else None)
                        )
                    }
                )
                pipeline.save_rhythm(part_id, new_sheet)
        except Exception:
            history.restore(part_id, before_version)
            raise
    return CutResult(
        before_version=before_version,
        from_ms=start * frame_ms,
        to_ms=stop * frame_ms,
        notes_removed=removed,
        duration_seconds=max(0.0, duration),
        sheet=new_sheet,
    )


def _cut_transitions(sheet: SavedRhythm, start: int, stop: int) -> SavedRhythm:
    """``[start, stop)`` taken out of a sheet, keeping what was in force after it: a key or clef
    change inside the stretch moves to its start, so the music after it reads as it did."""
    key_after = key_at(sheet, stop)
    clefs_after = {hand: clef_at(sheet, hand, stop) for hand in HANDS}
    anchor_after = anchor_at(sheet, stop)
    cut = marks.cut_out(sheet, start, stop)
    key_changes = [c for c in cut.key_changes if c.from_column != start]
    if key_at(cut.model_copy(update={"key_changes": key_changes}), start) != key_after:
        key_changes.append(KeyChange(from_column=start, key_signature=key_after))
    clef_changes = [c for c in cut.clef_changes if c.from_column != start]
    for hand, clef in clefs_after.items():
        here = cut.model_copy(update={"clef_changes": clef_changes})
        if clef_at(here, hand, start) != clef and start > 0:
            clef_changes.append(ClefChange(hand=hand, from_column=start, clef=clef))
    speed_changes = [c for c in cut.speed_changes if c.start_frame != start]
    here = cut.model_copy(update={"speed_changes": speed_changes})
    if anchor_after and anchor_at(here, start) != anchor_after and start > 0:
        speed_changes.append(SpeedChange(start_frame=start, anchor_ms=anchor_after))
    return cut.model_copy(
        update={
            "key_changes": sorted(key_changes, key=lambda c: c.from_column),
            "clef_changes": sorted(clef_changes, key=lambda c: (c.from_column, c.hand)),
            "speed_changes": sorted(speed_changes, key=lambda c: c.start_frame),
        }
    )


def _sheet_after(
    before: SavedRhythm | None,
    passage: Passage,
    *,
    at: int,
    columns: int,
    frame_ms: float,
    music_after: bool,
    empty_target: bool,
) -> SavedRhythm | None:
    """The target's sheet with its marks moved out of the way and the passage's put in."""
    source = passage.rhythm
    if before is None and source is None:
        return None
    if before is None or empty_target:
        assert source is not None
        base = _first_sheet(source, before, frame_ms)
    else:
        base = before
    shifted, _ = marks.shift(base, at, columns, straddle="tear")
    arriving = passage.marks
    if source is not None and abs(passage.frame_ms - frame_ms) > 1e-9:
        arriving = _rescaled(arriving, passage.frame_ms / frame_ms, columns)
    # The edges are written by ``_transitions`` from what is in force there.
    arriving = {
        name: [
            item
            for item in items
            if not (
                name in ("key_changes", "clef_changes", "speed_changes")
                and getattr(item, "from_column", getattr(item, "start_frame", 1)) == 0
            )
        ]
        for name, items in arriving.items()
    }
    if base.ottavas is None and arriving.get("ottavas"):
        shifted = shifted.model_copy(update={"ottavas": []})
    if base.ottavas is None and not arriving.get("ottavas"):
        arriving = {name: items for name, items in arriving.items() if name != "ottavas"}
    placed = marks.put_in(shifted, arriving, at)
    if source is None:
        return placed
    return _transitions(
        placed,
        None if empty_target else before,
        passage,
        at,
        columns,
        music_after,
        empty_target,
    )
