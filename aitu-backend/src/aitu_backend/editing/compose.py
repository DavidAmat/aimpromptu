"""Building a piece out of nothing, one passage at a time (Epic 13).

Epic 11 replaces a passage and is forbidden to change the piece's length: everything after the
window keeps its column, so every mark after it keeps its address. This module is the one place
that restriction is lifted, and it is lifted for the reason the restriction existed — when you are
composing there is nothing after the insertion point to protect, or when there is, moving it is
precisely what you asked for.

Three placements:

* **append** — the passage goes after the last note, at a silence given in seconds.
* **insert** — the passage opens at a moment and everything from that moment on moves later by the
  passage's length. Marks move with the notes, in the same operation, and the caller is told how
  many.
* **replace** — not here. That is :mod:`aitu_backend.editing.splice`, unchanged.

**A passage occupies a whole number of columns.** Its length is rounded *up* to the next frame
before anything is written. That is what makes an insertion exact rather than nearly exact: every
column after the insertion point moves by the same integer, so `round(onset_ms / frameMs)` (D-02)
lands on the column a mark was shifted to, instead of one either side of it depending on where in
the piece it was. The cost is at most one frame of silence at the join, which is 40 ms.
"""

from __future__ import annotations

import math

from aitu_backend.audio import store
from aitu_backend.editing.splice import last_release_seconds, scale_take
from aitu_backend.matrix.time_grid import (
    DEFAULT_FRAME_MS,
    frame_of_seconds,
    validate_frame_ms,
)
from aitu_backend.schemas.editing import MovedMarks
from aitu_backend.schemas.metadata import AudioMetadata, AudioSource
from aitu_backend.schemas.rhythm import SavedRhythm
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent

# ------------------------------------------------------------------ the empty piece


def create_empty_piece(name: str, frame_ms: float = DEFAULT_FRAME_MS) -> AudioMetadata:
    """A new piece with nothing in it: an empty ``events.json`` and a ``frameMs``.

    There is no BPM to choose and no granularity to choose (wall-clock rewrite §5). The only
    question at creation is the name, and the column length, which is a view and can be changed
    later like any other view.

    No audio file is written. The first accepted passage creates one; until then the piece is
    silence of length zero, which is what an empty ``events.json`` says.
    """
    alias = name.strip()
    if not alias:
        raise ValueError("A piece needs a name.")
    frame_ms = validate_frame_ms(frame_ms)
    entry = store.create(alias, AudioSource.COMPOSED, "wav")
    metadata = store.update(entry.uuid, duration_seconds=0.0, frame_ms=frame_ms)
    pipeline.save_note_events(entry.uuid, [], 0.0, alias)
    return metadata


# ---------------------------------------------------------------- where it goes


def quantise_up(seconds: float, frame_ms: float) -> float:
    """Round a length up to a whole number of columns. See the module note."""
    step = validate_frame_ms(frame_ms) / 1000.0
    if seconds <= 0:
        return 0.0
    return math.ceil(seconds / step - 1e-9) * step


def frame_at_or_after(seconds: float, frame_ms: float) -> int:
    """The first column that starts at or after ``seconds``.

    Not :func:`frame_of_seconds`, which rounds to the nearest: an anchor that rounded *down* would
    put the new passage a little before the silence the user asked for.
    """
    step = validate_frame_ms(frame_ms) / 1000.0
    if seconds <= 0:
        return 0
    return math.ceil(seconds / step - 1e-9)


def append_anchor(events: list[NoteEvent], gap_seconds: float, frame_ms: float) -> float:
    """Where an appended passage starts: after the last note, plus the silence asked for.

    An empty piece starts at zero whatever the gap is. A gap is the distance between two passages,
    and there is no first passage to be distant from; a piece that opened with a second of silence
    nobody asked for would be a small lie about what was played.

    Notes the reader has taken off the page do not count as the last note: they are not heard and
    not drawn, so measuring from them would leave a silence whose reason is invisible.
    """
    sounding = [event for event in events if not event.removed]
    last = last_release_seconds(sounding)
    if last is None:
        return 0.0
    gap = max(0.0, float(gap_seconds))
    step = validate_frame_ms(frame_ms) / 1000.0
    return frame_at_or_after(last + gap, frame_ms) * step


def passage_bounds(
    prepared: list[NoteEvent],
    *,
    at_seconds: float,
    factor: float,
    frame_ms: float,
) -> tuple[float, list[NoteEvent]]:
    """How long the passage is once scaled, and its notes already placed at ``at_seconds``.

    The length is measured from the take's last release rather than from the notes that survive
    scaling, so dropping a sub-frame note (D-05) never shortens the passage under the reader's
    feet. Rounded up to a whole number of columns, so nothing the take played is cut.
    """
    if factor <= 0:
        raise ValueError(f"factor must be a positive number, got {factor}")
    raw = (last_release_seconds(prepared) or 0.0) * factor
    length = quantise_up(raw, frame_ms)
    if length <= 0:
        return 0.0, []
    arriving = scale_take(
        prepared,
        factor=factor,
        start_seconds=at_seconds,
        end_seconds=at_seconds + length,
        frame_ms=frame_ms,
    )
    return length, arriving


# --------------------------------------------------------------------- the splice


def insert_events(
    original: list[NoteEvent],
    arriving: list[NoteEvent],
    *,
    at_seconds: float,
    passage_seconds: float,
    duration_seconds: float,
    placement: str,
    frame_ms: float = DEFAULT_FRAME_MS,
) -> tuple[list[NoteEvent], int, float]:
    """Open the piece at ``at_seconds`` and put the passage in it.

    Returns ``(result, notes_moved, new_duration)``.

    **Append** moves nothing: the passage lands after the last note and the piece is as long as it
    was, or as long as the passage now makes it, whichever is more. Trailing silence is never
    thrown away by appending into it.

    **Insert** moves every note **in the insertion column or after it**, and a note that started
    earlier and still sounds across the moment is cut there: it was not played against the passage
    now arriving, and letting it ring over the new material would be inventing a sustain nobody
    played. Sustain is measurement (D-06); what is printed comes from D-14 and does not change.

    Membership is by column and not, as in the replacement splice, by onset in seconds. The two
    differ by up to half a frame, and that half frame matters here in a way it never does there.
    Marks are addressed by column, so a mark in the insertion column moves; a note whose onset is
    a few milliseconds before the moment but which *rounds into* that column would not, under an
    onset test, and would be left stranded inside the passage the reader had just opened — visibly
    in the middle of their new music, with its fingering gone on ahead without it. Deciding both by
    the column is what makes "everything from here on moves by the same number of columns" true
    rather than nearly true.
    """
    if placement not in ("append", "insert"):
        raise ValueError(f"placement must be 'append' or 'insert', got {placement!r}")
    if passage_seconds <= 0:
        raise ValueError("A passage with no sounding notes cannot be placed.")

    moved = 0
    kept: list[NoteEvent] = []
    if placement == "append":
        kept = list(original)
        new_duration = max(float(duration_seconds), at_seconds + passage_seconds)
    else:
        at_frame = frame_at_or_after(at_seconds, frame_ms)
        for event in original:
            if frame_of_seconds(event.start, frame_ms) >= at_frame:
                kept.append(
                    event.model_copy(
                        update={
                            "start": event.start + passage_seconds,
                            "end": event.end + passage_seconds,
                        }
                    )
                )
                moved += 1
            elif event.end > at_seconds:
                kept.append(event.model_copy(update={"end": at_seconds}))
            else:
                kept.append(event)
        new_duration = float(duration_seconds) + passage_seconds

    result = sorted(kept + arriving, key=lambda item: (item.start, item.midi_note))
    return result, moved, new_duration


# ----------------------------------------------------------------------- the marks


def shift_marks(
    rhythm: SavedRhythm | None,
    *,
    at_seconds: float,
    passage_seconds: float,
    placement: str,
) -> tuple[SavedRhythm | None, MovedMarks]:
    """Move every mark at or after the insertion point by the passage's length.

    Every editorial mark is anchored to a frame, so an insertion has to move those frames or the
    marks stop pointing at the notes they were put on. Doing it here, in the same operation as the
    splice, is the point of Subtask 13.1.1.3: a reader must never find their fingering on the wrong
    note and have to work out why.

    Columns are counted at the rhythm's **own** ``frameMs``, which is the length the numbers in it
    were written at and is not necessarily the length of the view the passage was recorded in.

    A range that straddles the moment — a lyric line, a cue-size stretch, a trill — widens rather
    than tears: its end moves and its start does not, so it still covers exactly the notes it
    covered before. Appending moves nothing, because there is nothing after the last note to move.
    """
    if rhythm is None or placement == "append" or passage_seconds <= 0:
        return rhythm, MovedMarks()

    frame_ms = validate_frame_ms(rhythm.frame_ms)
    at_frame = frame_at_or_after(at_seconds, frame_ms)
    shift = int(round(passage_seconds * 1000.0 / frame_ms))
    if shift <= 0:
        return rhythm, MovedMarks()

    moved = 0

    def start_of(frame: int) -> int:
        """A mark's own column: it moves when the moment is at or before it."""
        return frame + shift if frame >= at_frame else frame

    def end_of(frame: int) -> int:
        """The exclusive end of a range: it moves as soon as the moment is inside the range."""
        return frame + shift if frame > at_frame else frame

    def one(item, **fields):
        """Apply the new columns, and count the mark once however many of them changed."""
        nonlocal moved
        changed = {name: value for name, value in fields.items() if getattr(item, name) != value}
        if not changed:
            return item
        moved += 1
        return item.model_copy(update=changed)

    updated = rhythm.model_copy(
        update={
            "key_changes": [
                one(item, from_column=start_of(item.from_column)) for item in rhythm.key_changes
            ],
            "speed_changes": [
                one(item, start_frame=start_of(item.start_frame)) for item in rhythm.speed_changes
            ],
            "overrides": [
                one(item, start_frame=start_of(item.start_frame)) for item in rhythm.overrides
            ],
            "beam_breaks": [
                one(item, start_frame=start_of(item.start_frame)) for item in rhythm.beam_breaks
            ],
            "hidden_notes": [
                one(item, start_frame=start_of(item.start_frame)) for item in rhythm.hidden_notes
            ],
            "fingers": [
                one(item, start_frame=start_of(item.start_frame)) for item in rhythm.fingers
            ],
            "grace_notes": [
                one(item, start_frame=start_of(item.start_frame)) for item in rhythm.grace_notes
            ],
            "trills": [
                one(
                    item,
                    start_frame=start_of(item.start_frame),
                    end_frame=end_of(item.end_frame),
                )
                for item in rhythm.trills
            ],
            "lyrics": [
                one(
                    item,
                    from_column=start_of(item.from_column),
                    to_column=end_of(item.to_column),
                )
                for item in rhythm.lyrics
            ],
            "cue_ranges": [
                one(
                    item,
                    from_column=start_of(item.from_column),
                    to_column=end_of(item.to_column),
                )
                for item in rhythm.cue_ranges
            ],
            # ``None`` is "never asked", and an insertion does not answer the question, so it has
            # to survive as ``None`` rather than become an empty list.
            "ottavas": (
                None
                if rhythm.ottavas is None
                else [
                    one(
                        item,
                        from_column=start_of(item.from_column),
                        to_column=end_of(item.to_column),
                    )
                    for item in rhythm.ottavas
                ]
            ),
        }
    )
    return updated, MovedMarks(total=moved, frames=shift)
