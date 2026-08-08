"""Structural operations the UI exposes on a matrix.

Every function here is **non-destructive** — it returns a new
:class:`~aitu_backend.matrix.model.PianoMatrix` and never mutates its input —
and every one leaves the result structurally valid (Task 2.1.2), because these
are the primitives the Matrix tab (Story 7.4), the notation tab (Epic 9) and the
range editor (Epic 11) call on user actions.

Four groups:

* **transposition** — shift every cell by K semitones, reporting what fell off
  the 88 keys instead of silently losing it
* **column insertion** — insert silence measured in *figures*, which is what
  "cut measure up to here" needs
* **slice / delete / replace** — range surgery, with replacements forced to the
  exact target width per ``context/music/notation-logic/03-editing-logic.md``
* **cell edits** — the validated single-cell primitives behind grid editing
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aitu_backend.matrix.keys import KEY_COUNT, build_grand_piano_rows
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.validator import normalize
from aitu_backend.schemas.matrix import ONSET, SILENCE, SUSTAIN

# ---------------------------------------------------------------- transposition


@dataclass(frozen=True)
class TranspositionReport:
    """What a transposition did, including what it could not keep."""

    matrix: PianoMatrix
    semitones: int
    #: Cells that fell outside the 88 keys and were dropped.
    dropped_cells: int = 0
    #: Note names that lost at least one cell, low to high.
    dropped_notes: list[str] = field(default_factory=list)

    @property
    def lossless(self) -> bool:
        return self.dropped_cells == 0

    def describe(self) -> str:
        if self.lossless:
            return f"Transposed by {self.semitones:+d} semitones, nothing lost."
        names = ", ".join(self.dropped_notes)
        return (
            f"Transposed by {self.semitones:+d} semitones; {self.dropped_cells} cell(s) "
            f"fell off the keyboard ({names})."
        )


def transpose(matrix: PianoMatrix, semitones: int) -> TranspositionReport:
    """Shift every cell by ``semitones`` rows (positive = higher).

    Cells pushed past ``La-0`` or ``Do-8`` are dropped and reported rather than
    wrapped — a note that leaves the keyboard cannot be played.
    """
    grid = matrix.grid
    shifted = np.zeros_like(grid)

    if semitones == 0:
        shifted = grid.copy()
        dropped_rows: list[int] = []
    elif semitones > 0:
        keep = KEY_COUNT - semitones
        shifted[semitones:, :] = grid[:keep, :]
        dropped_rows = list(range(keep, KEY_COUNT))
    else:
        shift = -semitones
        shifted[: KEY_COUNT - shift, :] = grid[shift:, :]
        dropped_rows = list(range(shift))

    lost = grid[dropped_rows, :] if dropped_rows else np.zeros((0, matrix.frame_count))
    dropped_cells = int(np.count_nonzero(lost))
    names = build_grand_piano_rows()
    dropped_notes = [
        names[row] for index, row in enumerate(dropped_rows) if np.any(lost[index] != SILENCE)
    ]

    return TranspositionReport(
        matrix=matrix.with_grid(shifted),
        semitones=semitones,
        dropped_cells=dropped_cells,
        dropped_notes=dropped_notes,
    )


def transpose_hands(
    right: PianoMatrix, left: PianoMatrix, semitones: int
) -> tuple[TranspositionReport, TranspositionReport]:
    """Transpose both hands by the same interval."""
    return transpose(right, semitones), transpose(left, semitones)


# ------------------------------------------------------------ column insertion


def insert_columns(matrix: PianoMatrix, at_frame: int, count: int) -> PianoMatrix:
    """Insert ``count`` silence columns before ``at_frame``.

    Any note sounding across the seam keeps its onset before the gap; the
    sustains that now follow the silence would be orphans, so the result is
    normalized — the note restarts after the inserted rest, which is what a
    lengthened measure should sound like.
    """
    if count < 0:
        raise ValueError("count cannot be negative")
    if not 0 <= at_frame <= matrix.frame_count:
        raise ValueError(f"Frame {at_frame} outside 0..{matrix.frame_count}")
    if count == 0:
        return matrix.copy()

    silence = np.zeros((KEY_COUNT, count), dtype=np.int8)
    grid = np.concatenate([matrix.grid[:, :at_frame], silence, matrix.grid[:, at_frame:]], axis=1)
    return normalize(matrix.with_grid(grid))


def append_silence(matrix: PianoMatrix, count: int) -> PianoMatrix:
    """Pad the end with ``count`` silent columns."""
    return insert_columns(matrix, matrix.frame_count, count)


# --------------------------------------------------------- slice / delete / replace


def slice_range(matrix: PianoMatrix, start: int, end: int) -> PianoMatrix:
    """Columns ``[start, end)`` as a standalone matrix.

    Unlike :meth:`PianoMatrix.slice_frames`, the result is normalized: a note
    held across ``start`` gets its opening sustain promoted to an onset, so the
    passage makes sense on its own.
    """
    return normalize(matrix.slice_frames(start, end))


def delete_range(matrix: PianoMatrix, start: int, end: int) -> PianoMatrix:
    """Remove columns ``[start, end)``, closing the gap.

    Normalized afterwards: whatever now sits at ``start`` may have been a
    sustain whose onset was just deleted.
    """
    _check_range(matrix, start, end)
    grid = np.concatenate([matrix.grid[:, :start], matrix.grid[:, end:]], axis=1)
    return normalize(matrix.with_grid(grid))


def fit_to_width(matrix: PianoMatrix, columns: int) -> PianoMatrix:
    """Force a matrix to exactly ``columns`` columns: trim excess, pad with silence.

    The editing-logic rule for replacements — a replacement passage must occupy
    exactly the range it replaces, so nothing after it shifts.
    """
    if columns < 0:
        raise ValueError("columns cannot be negative")
    if matrix.frame_count == columns:
        return matrix.copy()
    if matrix.frame_count > columns:
        return matrix.with_grid(matrix.grid[:, :columns].copy())
    padding = np.zeros((KEY_COUNT, columns - matrix.frame_count), dtype=np.int8)
    return matrix.with_grid(np.concatenate([matrix.grid, padding], axis=1))


def replace_range(
    matrix: PianoMatrix,
    start: int,
    end: int,
    replacement: PianoMatrix,
) -> PianoMatrix:
    """Swap columns ``[start, end)`` for ``replacement``, keeping the total width.

    ``replacement`` is forced to exactly ``end - start`` columns first, so the
    surrounding music never moves. The seam is normalized on both sides.
    """
    _check_range(matrix, start, end)
    fitted = fit_to_width(replacement, end - start)
    grid = np.concatenate([matrix.grid[:, :start], fitted.grid, matrix.grid[:, end:]], axis=1)
    return normalize(matrix.with_grid(grid))


def _check_range(matrix: PianoMatrix, start: int, end: int) -> None:
    if not 0 <= start <= end <= matrix.frame_count:
        raise ValueError(f"Frame range [{start}, {end}) outside 0..{matrix.frame_count}")


# ------------------------------------------------------------------ cell edits


class EditError(ValueError):
    """An edit the transition rules forbid."""


def add_onset(matrix: PianoMatrix, row: int, column: int) -> PianoMatrix:
    """Strike a key at ``(row, column)``.

    Always legal — an onset can follow any state. If a sustain was there, it is
    overwritten and the note it belonged to simply ends one column earlier.
    """
    _check_cell(matrix, row, column)
    grid = matrix.grid.copy()
    grid[row, column] = ONSET
    return matrix.with_grid(grid)


def extend_sustain(matrix: PianoMatrix, row: int, column: int) -> PianoMatrix:
    """Hold a key at ``(row, column)``.

    Legal only when the previous column in that row already sounds — you cannot
    hold a key that was never struck. Raises :class:`EditError` otherwise, which
    is the message the grid UI should surface.
    """
    _check_cell(matrix, row, column)
    previous = SILENCE if column == 0 else int(matrix.grid[row, column - 1])
    if previous == SILENCE:
        names = build_grand_piano_rows()
        where = "the start of the piece" if column == 0 else f"column {column - 1}"
        raise EditError(
            f"Cannot sustain {names[row]} at column {column}: nothing is sounding at {where}. "
            "Place an onset first."
        )
    grid = matrix.grid.copy()
    grid[row, column] = SUSTAIN
    return matrix.with_grid(grid)


def delete_note(matrix: PianoMatrix, row: int, column: int) -> PianoMatrix:
    """Remove the note occupying ``(row, column)``, tail included.

    Clicking anywhere in a note deletes the whole note: the run is traced back
    to its onset and forward through its chained sustains. Clicking silence is a
    no-op rather than an error — the grid should not punish a missed click.
    """
    _check_cell(matrix, row, column)
    if matrix.grid[row, column] == SILENCE:
        return matrix.copy()

    start = column
    while start > 0 and matrix.grid[row, start] == SUSTAIN:
        start -= 1

    end = start + 1
    while end < matrix.frame_count and matrix.grid[row, end] == SUSTAIN:
        end += 1

    grid = matrix.grid.copy()
    grid[row, start:end] = SILENCE
    return matrix.with_grid(grid)


def delete_cells(matrix: PianoMatrix, cells: list[tuple[int, int]]) -> PianoMatrix:
    """Delete several notes at once — the shift-multi-select case (Story 7.4)."""
    result = matrix
    for row, column in cells:
        result = delete_note(result, row, column)
    return result


def set_cell(matrix: PianoMatrix, row: int, column: int, value: int) -> PianoMatrix:
    """Write one raw cell value, validated. ``1`` / ``-1`` / ``0``."""
    if value == ONSET:
        return add_onset(matrix, row, column)
    if value == SUSTAIN:
        return extend_sustain(matrix, row, column)
    if value == SILENCE:
        return delete_note(matrix, row, column)
    raise EditError(f"Cell value must be 1, -1 or 0, got {value}")


def _check_cell(matrix: PianoMatrix, row: int, column: int) -> None:
    if not 0 <= row < KEY_COUNT:
        raise EditError(f"Row {row} outside the 88-key range")
    if not 0 <= column < matrix.frame_count:
        raise EditError(f"Column {column} outside 0..{matrix.frame_count - 1}")
