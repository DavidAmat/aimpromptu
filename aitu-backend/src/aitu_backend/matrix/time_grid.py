"""Frame ↔ millisecond conversion. The only module that knows how long a frame is.

A matrix column used to be a note figure, so its width in seconds had to come from a tempo that
somebody typed in. It is now a fixed slice of wall clock: 40 milliseconds by default, recorded per
piece in the matrix metadata. Column *n* starts at ``n * frameMs`` after the beginning of the audio,
in every piece, and no BPM takes part in the calculation (D-01).

That is what makes the columns stable. Re-running the pipeline on the same audio produces the same
column indices, because nothing in this file depends on a judgement.

Every other module asks this one. If a second module starts dividing by 40, changing the frame
length stops being a one-line change and the two answers drift.

See ``context/implementations/time-based-concept/decisions.md`` for D-01 and D-02, and
``documentation/services/backend/time-matrix.md`` for the field reference.
"""

from __future__ import annotations

import math

from aitu_backend.schemas.time_matrix import DEFAULT_FRAME_MS

__all__ = [
    "DEFAULT_FRAME_MS",
    "MS_PER_SECOND",
    "frame_count_for_duration",
    "frame_of_ms",
    "frame_of_seconds",
    "frame_start_ms",
    "frame_start_seconds",
    "frame_span_of_ms",
    "seconds_per_frame",
    "validate_frame_ms",
]

MS_PER_SECOND = 1000.0


def validate_frame_ms(frame_ms: float = DEFAULT_FRAME_MS) -> float:
    """Reject a frame length that cannot describe a grid.

    A non-positive or infinite frame makes every conversion below meaningless, and the failure would
    otherwise appear far from its cause, as an empty matrix or a division by zero deep in a loop.
    """
    value = float(frame_ms)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(
            f"frameMs must be a positive finite number of milliseconds, got {frame_ms}"
        )
    return value


def seconds_per_frame(frame_ms: float = DEFAULT_FRAME_MS) -> float:
    """Length of one column in seconds. This replaces ``timeStepSeconds``."""
    return validate_frame_ms(frame_ms) / MS_PER_SECOND


def frame_of_ms(milliseconds: float, frame_ms: float = DEFAULT_FRAME_MS) -> int:
    """The column an instant snaps to, rounded to the nearest column (D-02).

    Halves round **up**: an onset exactly 20 ms into a 40 ms frame goes to the later column. Python's
    built-in ``round`` would send it to the *even* column instead, which is deterministic but sends
    two onsets the same distance from a boundary to different sides depending on where they are in
    the piece. Rounding up is the reading of D-02 that a person predicts.

    The rule is arithmetic, not a judgement, which is what success criterion 3 needs: the same audio
    always gives the same columns.
    """
    step = validate_frame_ms(frame_ms)
    if milliseconds < 0:
        raise ValueError(f"An instant cannot be negative, got {milliseconds} ms")
    return int(math.floor(milliseconds / step + 0.5))


def frame_of_seconds(seconds: float, frame_ms: float = DEFAULT_FRAME_MS) -> int:
    """The column an onset in seconds snaps to (D-02). See :func:`frame_of_ms`."""
    if seconds < 0:
        raise ValueError(f"An instant cannot be negative, got {seconds} s")
    return frame_of_ms(seconds * MS_PER_SECOND, frame_ms)


def frame_start_ms(frame: int, frame_ms: float = DEFAULT_FRAME_MS) -> float:
    """When a column starts, in milliseconds from the beginning of the audio."""
    step = validate_frame_ms(frame_ms)
    if frame < 0:
        raise ValueError(f"A column index cannot be negative, got {frame}")
    return frame * step


def frame_start_seconds(frame: int, frame_ms: float = DEFAULT_FRAME_MS) -> float:
    """When a column starts, in seconds. Column 0 starts at 0.0."""
    return frame_start_ms(frame, frame_ms) / MS_PER_SECOND


def frame_count_for_duration(duration_seconds: float, frame_ms: float = DEFAULT_FRAME_MS) -> int:
    """How many columns an audio of this length needs, always at least one.

    The last column is rounded up rather than down, so the grid covers the whole recording. The
    audio can therefore end up to one frame short of the grid, which is why the envelope carries
    ``durationSeconds`` separately instead of letting the reader multiply.
    """
    step = validate_frame_ms(frame_ms)
    if duration_seconds <= 0:
        raise ValueError(f"Duration must be positive, got {duration_seconds}")
    return max(1, int(math.ceil(duration_seconds * MS_PER_SECOND / step)))


def frame_span_of_ms(milliseconds: float, frame_ms: float = DEFAULT_FRAME_MS) -> int:
    """How many columns a *length of time* occupies, always at least one.

    This is not :func:`frame_of_ms`. That one answers "which column is this instant in"; this one
    answers "how wide is this stretch". A note of 45 ms is one frame long here and would be column 1
    there.
    """
    step = validate_frame_ms(frame_ms)
    if milliseconds < 0:
        raise ValueError(f"A duration cannot be negative, got {milliseconds} ms")
    return max(1, int(math.floor(milliseconds / step + 0.5)))
