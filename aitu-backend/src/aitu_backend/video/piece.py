"""The step that makes a video into the piece (Task 4.1.3).

Reading a video produces `events.json` and nothing else (V-02). The hand split,
the matrix, the peaks, the ladder and the sheet are untouched and do not know
where the notes came from, so this module is the whole of the boundary: the
stitched roll's notes on one side, `pipeline.save_note_events` on the other, and
no third thing anywhere.

Three rules it obeys and never bends:

* **No `hand` is written on any event** (V-17). Many of these videos colour the
  left hand and the right hand differently and the app already has a way to split
  hands; a hint from a colour is exactly what V-17 refuses.
* **The saved reading is cleared**, as a transcription clears it. A reading is a
  set of column numbers over the notes that were there before; these are
  different notes, so those numbers point at nothing in particular now.
* **It advances the music version.** This is the step that changes the piece, so
  what was there is snapshotted first and the version counter moves — the
  ordinary rule for a piece whose music changed, with nothing invented for a
  video.

**A video whose scroll speed is not stable is not turned into a piece quietly**
(V-06). The refusal is here as well as in the reading, because this is the last
door before the piece changes.
"""

from __future__ import annotations

from dataclasses import dataclass

from aitu_backend.editing import history
from aitu_backend.schemas.video import NoteCorrections, VideoNote, VideoNotes
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.video import store

#: What every event a video writes carries. The rendering draws a rectangle,
#: not a loudness: the picture cannot say how hard a key was struck, so every
#: note gets the same middling velocity the reader of `events.json` defaults to,
#: and nothing downstream is told a number that was never measured.
VIDEO_VELOCITY = 64


class NotRead(RuntimeError):
    """The video has not been read into notes yet."""


class NotStable(RuntimeError):
    """The scroll speed is not stable, so the times would be wrong (V-06)."""


@dataclass(frozen=True)
class Written:
    """What one write did, so the screen can say it plainly."""

    audio_uuid: str
    title: str
    duration_seconds: float
    notes: int
    removed: int
    added: int
    #: Corrections that named a note the reading no longer holds. They are
    #: reported rather than dropped in silence: a correction made against an
    #: older reading is a thing the person will want to know about.
    unmatched: int
    music_version: int


def _key(midi: int, start: float) -> tuple[int, float]:
    """How a correction names a note: its pitch and its onset, rounded as the
    piece stores it. The same key `POST /matrix/removals` uses."""
    return midi, round(start, 4)


def corrected(
    notes: VideoNotes, corrections: NoteCorrections
) -> tuple[list[VideoNote], int, int, int]:
    """The reading with what a person decided applied to it (Task 4.3.1).

    A removal names a note by pitch and onset; an addition carries the whole
    note, because there is nothing in the picture to name it by.
    """
    removed = {_key(one.midi, one.start) for one in corrections.removed}
    seen: set[tuple[int, float]] = set()
    kept: list[VideoNote] = []
    for note in notes.notes:
        key = _key(note.midi, note.start)
        if key in removed:
            seen.add(key)
            continue
        kept.append(note)

    added = 0
    for one in corrections.added:
        end = one.end if one.end is not None else one.start + 0.1
        kept.append(
            VideoNote(
                midi=one.midi,
                start=one.start,
                end=max(end, one.start + 1e-4),
                row_top=0,
                row_bottom=0,
                width_keys=0.0,
            )
        )
        added += 1

    kept.sort(key=lambda note: (note.start, note.midi))
    return kept, len(removed & seen), added, len(removed - seen)


def events_for(notes: list[VideoNote]) -> list[NoteEvent]:
    """The notes as the piece stores them. No `hand` on any of them (V-17)."""
    return [
        NoteEvent(
            midi_note=note.midi,
            start=max(0.0, note.start),
            end=max(note.end, max(0.0, note.start) + 1e-4),
            velocity=VIDEO_VELOCITY,
        )
        for note in notes
    ]


def write(audio_uuid: str) -> Written:
    """Turn what the stitched roll read into `events.json`, corrections and all."""
    notes = store.load_notes(audio_uuid)
    if notes is None:
        raise NotRead(
            f"Audio {audio_uuid} has not been read into notes yet. "
            "Read the video first, and look at what it found before writing it."
        )
    measurement = store.load_measurement(audio_uuid)
    if measurement is None or not measurement.scroll_speed.stable:
        reason = measurement.scroll_speed.reason if measurement else "it has not been measured"
        raise NotStable(
            f"The scroll speed of audio {audio_uuid} is not stable, so a row is not a time: "
            f"{reason}. A video whose scroll speed is not stable is reported, not transcribed "
            "(V-06)."
        )

    metadata = store.load_metadata(audio_uuid)
    kept, removed, added, unmatched = corrected(notes, store.load_corrections(audio_uuid))
    duration = max(
        metadata.duration_seconds,
        max((note.end for note in kept), default=0.0),
        0.001,
    )

    # Whatever the piece was, it is about to be different music. The ordinary
    # rule for that is a snapshot and a version, and nothing here is special.
    version = history.current_version(audio_uuid)
    if pipeline.has_events(audio_uuid):
        version = history.snapshot_current(audio_uuid)

    title = metadata.title or None
    pipeline.save_note_events(audio_uuid, events_for(kept), duration, title=title)
    pipeline.clear_rhythm(audio_uuid)
    pipeline.clear_needs_rederivation(audio_uuid)
    return Written(
        audio_uuid=audio_uuid,
        title=title or "",
        duration_seconds=duration,
        notes=len(kept),
        removed=removed,
        added=added,
        unmatched=unmatched,
        music_version=version,
    )
