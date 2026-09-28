"""The sparse form to the 88 x N piano matrix notation at any ``frameMs``, and back.

The dense matrix is the user's format: 88 rows (MIDI 21 to 108), one column per ``frameMs``, a cell
is ``1`` (onset), ``-1`` (sustain) or ``0`` (silence). It is an ``int8`` array here, whole or for one
hand, and it is what the hand split and the ``.npz`` exports work on.

**Sparse to dense.** A note's onset column is its onset time rounded to the nearest column, halves
up (D-02, :func:`aitu_backend.matrix.time_grid.frame_of_ms`), and its release column is its release
rounded the same way. A note always owns at least its onset column. Two rules keep one rectangle
equal to one run:

* **One key sounds one note at a time.** A note ends at its own release or at the next onset of the
  same key, whichever comes first. This is the rule of the prompt and of MuScriptor.
* **Two notes on one key in one column are one note.** The longer one is kept. At 40 ms two strikes
  of a key 20 ms apart land in one column, and the matrix cannot show both.

This is the plain conversion. The builder of the piano sheet, which groups near-simultaneous onsets
first (D-04) and drops notes shorter than one column (D-05), is still
:func:`aitu_backend.transcription.events_to_matrix.events_to_time_matrix`.

**Dense to sparse.** Every onset starts a rectangle that runs until the first cell of its row that is
not a sustain. A sustain with nothing before it (an orphan, for example at the first column of a
slice) is read as an onset, as :func:`aitu_backend.hands.events.decode_matrix` does.

The round trips are exact: dense to sparse to dense gives the same cells for any valid matrix, and
sparse to dense to sparse gives the same notes whenever the times are whole columns, which is every
MuScriptor note at ``frameMs = 10``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aitu_backend.matrix.time_grid import validate_frame_ms
from aitu_backend.pmn.notes import HAND_LEFT, HAND_NONE, HAND_RIGHT, KEY_COUNT, Notes
from aitu_backend.schemas.matrix import ONSET, SILENCE, SUSTAIN

__all__ = [
    "DenseReport",
    "column_count",
    "columns_of",
    "from_dense",
    "from_hand_grids",
    "to_dense",
    "to_dense_report",
    "to_hand_grids",
]


def column_count(duration_ms: float, frame_ms: float) -> int:
    """How many columns cover ``duration_ms``: rounded up, at least one."""
    step = validate_frame_ms(frame_ms)
    return max(1, int(np.ceil(round(float(duration_ms) / step, 9))))


def _round_half_up(values: np.ndarray, step: float) -> np.ndarray:
    # The same rule as `frame_of_ms`, on a whole array. The inner round removes the 1e-13 noise of
    # dividing a float by 40, so a time exactly on a boundary does not fall on the wrong side.
    return np.floor(np.round(values / step, 9) + 0.5).astype(np.int64)


def columns_of(notes: Notes, frame_ms: float) -> tuple[np.ndarray, np.ndarray]:
    """The onset column and the release column (exclusive) of every note, before any clipping."""
    step = validate_frame_ms(frame_ms)
    start = _round_half_up(notes.on_ms, step)
    end = np.maximum(start + 1, _round_half_up(notes.end_ms, step))
    return start, end


@dataclass
class DenseReport:
    """What happened to the notes on the way to one matrix."""

    grid: np.ndarray
    #: Notes whose onset is past the last column.
    past_end: int = 0
    #: Notes that shared a column with another note of the same key and were joined to it.
    merged: int = 0
    #: Notes shortened because the same key was struck again before their release.
    shortened: int = 0


def to_dense_report(
    notes: Notes,
    frame_ms: float,
    duration_ms: float | None = None,
    *,
    hand: int | None = None,
) -> DenseReport:
    """The 88 x N ``int8`` matrix of the live notes (or of one hand), and what was changed on the way.

    ``duration_ms`` fixes the number of columns; without it the matrix ends with the last release.
    ``hand`` is ``HAND_RIGHT``, ``HAND_LEFT`` or ``HAND_NONE`` (the notes with no hand yet), and
    ``None`` takes every note.
    """
    step = validate_frame_ms(frame_ms)
    chosen = notes.live()
    if hand is not None:
        chosen = chosen.of_hand(hand)
    start, end = columns_of(chosen, step)
    if duration_ms is None:
        frames = int(end.max()) if end.size else 1
    else:
        frames = column_count(duration_ms, step)

    out = DenseReport(grid=np.zeros((KEY_COUNT, frames), dtype=np.int8))
    inside = start < frames
    out.past_end = int((~inside).sum())
    key = chosen.key[inside].astype(np.int64)
    start, end = start[inside], np.minimum(end[inside], frames)

    if key.size:
        # By key, then onset column, then the longest first, so the note kept for a shared cell
        # is the first of its (key, column) pair.
        order = np.lexsort((-end, start, key))
        key, start, end = key[order], start[order], end[order]
        first = np.ones(key.size, dtype=bool)
        first[1:] = (key[1:] != key[:-1]) | (start[1:] != start[:-1])
        out.merged = int((~first).sum())
        key, start, end = key[first], start[first], end[first]

        # A note ends where the next onset of the same key begins.
        next_start = np.full(key.size, np.iinfo(np.int64).max)
        same_key = key[1:] == key[:-1]
        next_start[:-1][same_key] = start[1:][same_key]
        cut = np.minimum(end, next_start)
        out.shortened = int((cut < end).sum())
        end = cut

        lengths = end - start
        rows = np.repeat(key, lengths)
        offsets = np.arange(lengths.sum()) - np.repeat(np.cumsum(lengths) - lengths, lengths)
        out.grid[rows, np.repeat(start, lengths) + offsets] = SUSTAIN
        out.grid[key, start] = ONSET

    return out


def to_dense(
    notes: Notes,
    frame_ms: float,
    duration_ms: float | None = None,
    *,
    hand: int | None = None,
) -> np.ndarray:
    """The 88 x N ``int8`` matrix of the live notes, or of one hand's. See :func:`to_dense_report`."""
    return to_dense_report(notes, frame_ms, duration_ms, hand=hand).grid


def to_hand_grids(
    notes: Notes, frame_ms: float, duration_ms: float | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """The right hand matrix and the left hand matrix, with the same number of columns.

    Notes with no hand are in neither. The two grids are two masks of the same notes, which is what
    lets a hand change move a whole rectangle, onset and sustain, from one matrix to the other.
    """
    if duration_ms is None:
        _, end = columns_of(notes.live(), frame_ms)
        duration_ms = (int(end.max()) if end.size else 1) * validate_frame_ms(frame_ms)
    right = to_dense(notes, frame_ms, duration_ms, hand=HAND_RIGHT)
    left = to_dense(notes, frame_ms, duration_ms, hand=HAND_LEFT)
    return right, left


def _runs(grid: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``(row, start column, length in columns)`` of every run, ordered by row then column."""
    grid = np.asarray(grid, dtype=np.int8)
    if grid.ndim != 2 or grid.shape[0] != KEY_COUNT:
        raise ValueError(f"A piano matrix is {KEY_COUNT} x N, got shape {grid.shape}")
    illegal = ~np.isin(grid, (ONSET, SUSTAIN, SILENCE))
    if illegal.any():
        raise ValueError("A piano matrix holds only 1 (onset), -1 (sustain) and 0 (silence)")
    width = grid.shape[1] + 1
    # One silent column after each row, so a run never continues into the next row.
    flat = np.concatenate([grid, np.zeros((KEY_COUNT, 1), dtype=np.int8)], axis=1).ravel()
    before = np.concatenate([[SILENCE], flat[:-1]])
    before[::width] = SILENCE
    starts = np.nonzero((flat == ONSET) | ((flat == SUSTAIN) & (before == SILENCE)))[0]
    stops = np.nonzero(flat != SUSTAIN)[0]
    ends = stops[np.searchsorted(stops, starts, side="right")]
    return starts // width, starts % width, ends - starts


def from_dense(
    grid: np.ndarray, frame_ms: float, *, hand: int = HAND_NONE, first_id: int = 0
) -> Notes:
    """One note per run of the matrix, in canonical order, with ids from ``first_id``."""
    step = validate_frame_ms(frame_ms)
    rows, cols, lengths = _runs(grid)
    order = np.lexsort((rows, cols))
    rows, cols, lengths = rows[order], cols[order], lengths[order]
    return Notes.build(
        key=rows,
        on_ms=cols * step,
        len_ms=lengths * step,
        hand=np.full(rows.size, hand, dtype=np.int8),
        first_id=first_id,
    )


def from_hand_grids(
    right: np.ndarray, left: np.ndarray, frame_ms: float, *, first_id: int = 0
) -> Notes:
    """The notes of a right hand matrix and a left hand matrix, each with its hand."""
    if np.shape(right) != np.shape(left):
        raise ValueError(
            f"The two hand matrices differ in shape: {np.shape(right)}, {np.shape(left)}"
        )
    both = [
        from_dense(right, frame_ms, hand=HAND_RIGHT),
        from_dense(left, frame_ms, hand=HAND_LEFT),
    ]
    merged = Notes.build(
        key=np.concatenate([part.key for part in both]),
        on_ms=np.concatenate([part.on_ms for part in both]),
        len_ms=np.concatenate([part.len_ms for part in both]),
        hand=np.concatenate([part.hand for part in both]),
    ).sorted()
    return Notes.build(
        key=merged.key,
        on_ms=merged.on_ms,
        len_ms=merged.len_ms,
        hand=merged.hand,
        first_id=first_id,
    )
