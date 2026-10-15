"""Putting a passage into a part: everything from a column on moves later (implementation 08,
Epic 13; implementation 02, plan section 4, rule 2 as changed by Q-3).

The one operation that changes a part's length. A paste (:mod:`aitu_backend.editing.paste`, Phase 8)
and a promotion of a re-recorded passage (:mod:`aitu_backend.editing.passages`, Phase 9) put their
notes in with :func:`insert_events`; their marks move with :mod:`aitu_backend.editing.marks` in the
same write. The staged session of Epics 11 and 13 (Record, Re-record) that used it first was
replaced in Phase 9 by the page of a passage.

**A passage occupies a whole number of columns.** Its length is rounded *up* to the next frame
before anything is written. That is what makes an insertion exact rather than nearly exact: every
column after the insertion point moves by the same integer, so `round(onset_ms / frameMs)` (D-02)
lands on the column a mark was shifted to, instead of one either side of it depending on where in
the piece it was. The cost is at most one frame of silence at the join, which is 40 ms.
"""

from __future__ import annotations

import math

from aitu_backend.matrix.time_grid import (
    DEFAULT_FRAME_MS,
    frame_of_seconds,
    validate_frame_ms,
)
from aitu_backend.transcription.engine import NoteEvent

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
