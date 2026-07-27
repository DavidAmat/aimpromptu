"""Per-row transition rules for the piano matrix.

Scanning one row left to right, the cell values form a small Markov chain whose
initial state is ``0`` (silence before the piece starts):

======  ==========================  ================================
From    Allowed next                Meaning
======  ==========================  ================================
``0``   ``0``, ``1``                a key that is not sounding can stay
                                    silent or be struck — it can never
                                    "continue" a note that never began
``1``   ``1``, ``-1``, ``0``        struck: re-struck, held, or released
``-1``  ``1``, ``-1``, ``0``        held: re-struck, held on, or released
======  ==========================  ================================

So exactly one transition is illegal: **``0 -> -1``**, an orphan sustain.

Two entry points:

* :func:`validate` reports every violation without changing anything.
* :func:`normalize` returns a corrected matrix, promoting each orphan sustain to
  an onset — the same rule the text-notation parser already applies ("you cannot
  hold a key that was never struck"), now available to every ingestion path.

:func:`validate_strict` raises. Use it after user edits and in tests.

The **onset rule** from the notation spec — a sustain dies when any *other* key
is struck — is a different, musical rule; it lives in the Appendix B cleaning
step (Task 2.3.1), not here. This module only enforces what is structurally
representable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aitu_backend.matrix.keys import build_grand_piano_rows
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import ONSET, SILENCE, SUSTAIN

#: Legal successors for each state. The only omission is ``0 -> -1``.
ALLOWED_TRANSITIONS: dict[int, frozenset[int]] = {
    SILENCE: frozenset({SILENCE, ONSET}),
    ONSET: frozenset({SILENCE, ONSET, SUSTAIN}),
    SUSTAIN: frozenset({SILENCE, ONSET, SUSTAIN}),
}

_CELL_LABEL = {ONSET: "onset (1)", SUSTAIN: "sustain (-1)", SILENCE: "silence (0)"}


@dataclass(frozen=True)
class Violation:
    """One illegal transition, located and explained."""

    row: int
    #: Spanish key name of ``row``, e.g. ``"Do-4"``.
    key: str
    #: Column where the illegal value sits (the *destination* of the transition).
    column: int
    previous: int
    found: int

    @property
    def message(self) -> str:
        origin = "the start of the piece" if self.column == 0 else f"column {self.column - 1}"
        return (
            f"{self.key} column {self.column}: {_CELL_LABEL[self.found]} after "
            f"{_CELL_LABEL[self.previous]} at {origin}"
        )

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.message


class TransitionError(ValueError):
    """Raised by :func:`validate_strict`. Carries the full violation list."""

    def __init__(self, violations: list[Violation]) -> None:
        self.violations = violations
        shown = "; ".join(violation.message for violation in violations[:5])
        suffix = f" (+{len(violations) - 5} more)" if len(violations) > 5 else ""
        super().__init__(f"{len(violations)} illegal transition(s): {shown}{suffix}")


def _orphan_sustain_mask(grid: np.ndarray) -> np.ndarray:
    """Boolean mask of every ``-1`` whose predecessor is ``0`` (or the start).

    Vectorized: prepend a column of silence, then a cell is an orphan when it
    holds ``-1`` and the shifted grid holds ``0`` at the same position.
    """
    if grid.shape[1] == 0:
        return np.zeros_like(grid, dtype=bool)
    previous = np.concatenate(
        [np.zeros((grid.shape[0], 1), dtype=grid.dtype), grid[:, :-1]], axis=1
    )
    return (grid == SUSTAIN) & (previous == SILENCE)


def validate(matrix: PianoMatrix) -> list[Violation]:
    """Every illegal transition, ordered by column then row."""
    grid = matrix.grid
    mask = _orphan_sustain_mask(grid)
    rows, columns = np.nonzero(mask)
    key_names = build_grand_piano_rows()

    violations = [
        Violation(
            row=int(row),
            key=key_names[int(row)],
            column=int(column),
            previous=SILENCE,
            found=SUSTAIN,
        )
        for row, column in zip(rows, columns)
    ]
    violations.sort(key=lambda violation: (violation.column, violation.row))
    return violations


def is_valid(matrix: PianoMatrix) -> bool:
    """True when the matrix has no illegal transition."""
    return not np.any(_orphan_sustain_mask(matrix.grid))


def validate_strict(matrix: PianoMatrix) -> PianoMatrix:
    """Return ``matrix`` unchanged, or raise :class:`TransitionError`."""
    violations = validate(matrix)
    if violations:
        raise TransitionError(violations)
    return matrix


def normalize(matrix: PianoMatrix) -> PianoMatrix:
    """A corrected copy: every orphan sustain promoted to an onset.

    Tolerant ingestion path. Mirrors the text-notation parser's rule — a key
    that was never struck cannot be held, so the first cell of the run becomes
    the strike and the rest of the run keeps sustaining.

    The returned matrix is always valid; the input is never mutated.
    """
    grid = matrix.grid.copy()
    # One pass suffices: promoting a `-1` to `1` makes the *next* `-1` legal,
    # and a `-1` following a `-1` was never a violation to begin with.
    grid[_orphan_sustain_mask(grid)] = ONSET
    return matrix.with_grid(grid)


def normalized_violation_count(matrix: PianoMatrix) -> int:
    """How many cells :func:`normalize` would change. Useful for logging."""
    return int(np.count_nonzero(_orphan_sustain_mask(matrix.grid)))
