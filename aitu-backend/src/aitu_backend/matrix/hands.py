"""Appendix D: split a clean matrix into a right hand and a left hand.

Deliberately dumb for the first iteration: **``Do-4`` (middle C, MIDI 60) and
above is the right hand, everything below is the left**. Knowing which hand
actually played a note is an optimization problem in its own right; this gets a
readable grand staff today and can be replaced without changing any caller.

Splitting **never cuts**. Both outputs are full 88 x N matrices, exact copies of
the clean matrix with the other hand's rows zeroed — so the two stay
frame-aligned when rendered one above the other, which is what the notation
contract requires (``r_matrix`` and ``l_matrix`` must have equal ``shape[1]``).

Downstream default clefs: right = treble, left = bass.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aitu_backend.matrix.keys import MIDDLE_C_ROW, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import Hand, MatrixProcessingStep

#: Row at and above which a note belongs to the right hand. ``Do-4`` = middle C.
DEFAULT_SPLIT_ROW = MIDDLE_C_ROW


@dataclass(frozen=True)
class TwoHands:
    """The result of a split: two aligned, full-size matrices."""

    right: PianoMatrix
    left: PianoMatrix
    #: Row index at and above which notes went to the right hand.
    split_row: int

    @property
    def frame_count(self) -> int:
        return self.right.frame_count

    def combined(self) -> PianoMatrix:
        """Merge the hands back into one matrix.

        Exact for any matrix produced by :func:`split_hands`, because the split
        partitions the rows: no row is non-zero in both hands.
        """
        grid = np.where(self.right.grid != 0, self.right.grid, self.left.grid)
        return self.right.with_grid(grid, hand=None, processing_step=MatrixProcessingStep.CLEAN)


def resolve_split_row(threshold: int | str = DEFAULT_SPLIT_ROW) -> int:
    """Accept a row index or a note name (``"Do-4"``) as the threshold."""
    return note_to_row(threshold) if isinstance(threshold, str) else threshold


def split_hands(
    matrix: PianoMatrix,
    threshold: int | str = DEFAULT_SPLIT_ROW,
) -> TwoHands:
    """Split ``matrix`` at ``threshold`` (inclusive for the right hand).

    ``threshold`` may be a row index or a Spanish note name. The default,
    ``Do-4``, is Appendix D's rule; it is a parameter so a future per-piece
    heuristic can move it without touching callers.
    """
    split_row = resolve_split_row(threshold)
    if not 0 <= split_row <= matrix.shape[0]:
        raise ValueError(f"Split row {split_row} outside 0..{matrix.shape[0]}")

    right_grid = matrix.grid.copy()
    right_grid[:split_row, :] = 0

    left_grid = matrix.grid.copy()
    left_grid[split_row:, :] = 0

    common = {"processing_step": MatrixProcessingStep.TWO_HANDS}
    return TwoHands(
        right=matrix.with_grid(right_grid, hand=Hand.RIGHT.value, **common),
        left=matrix.with_grid(left_grid, hand=Hand.LEFT.value, **common),
        split_row=split_row,
    )


def combine_hands(right: PianoMatrix, left: PianoMatrix) -> PianoMatrix:
    """Merge two hands back into one matrix.

    Where both hands hold a value for the same cell — which cannot happen for a
    :func:`split_hands` result, but can for hand-edited matrices — the right
    hand wins.
    """
    if right.shape != left.shape:
        raise ValueError(
            f"Hands must have the same shape to combine, got {right.shape} and {left.shape}"
        )
    grid = np.where(right.grid != 0, right.grid, left.grid)
    return right.with_grid(grid, hand=None, processing_step=MatrixProcessingStep.CLEAN)


def hand_of_row(row: int, threshold: int | str = DEFAULT_SPLIT_ROW) -> Hand:
    """Which hand a row belongs to under the threshold rule."""
    return Hand.RIGHT if row >= resolve_split_row(threshold) else Hand.LEFT
