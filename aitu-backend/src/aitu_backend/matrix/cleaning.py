"""Appendix B cleaning: a sustain dies when any other key is struck **on that hand**.

.. important::

   "Any other key" means any other key *of the same hand*. The rule is about one
   hand's fingers running out, so it only makes sense once the hands are known —
   which is why the pipeline splits first and cleans each hand afterwards. Applied
   to the whole keyboard it lets the right hand's melody amputate the left hand's
   accompaniment: in ``When I Was Your Man`` a left-hand Do-2/Do-3 octave held for
   twelve frames was cut to two by a right-hand Sol an eighth later.

   This module does not know about hands, and does not need to: it applies the
   rule to whatever grid it is handed. Hand it one hand.


The goal is a readable sheet. A note held for ten seconds under a moving melody
is *musically* true but produces a page full of tied whole notes crossing every
bar — so the matrix records the strike and drops the tail as soon as anything
else happens.

The rule, from ``context/music/notation-logic/01-matrix-notation-logic.md``
Appendix B:

    A note keeps sustaining only while **no other note produces an onset**. At
    the first column where any other key is struck, every carried sustain is
    cut from that column onward (for that sounding span).

Two consequences the appendix spells out:

* **A chord struck together survives together.** All its notes were struck in
  the same column, so none of them is "another note" for the others; the chord
  sustains until something outside it is struck.
* **A re-onset of the same key is untouched.** A new ``1`` opens its own span
  regardless of what else happens in that column.

Worked example from the appendix::

    C3, C4 struck at 0s and held 10s
    D3 struck at 1s, E3 at 2s
    -> the C3/C4 chord is cut to 1 second; D3 and E3 keep their own durations

Only sustain (``-1``) cells are ever removed. Onsets are never touched, so no
note disappears from the score — only its tail shortens.
"""

from __future__ import annotations

import numpy as np

from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.progress import BaseProgress, default_reporter
from aitu_backend.schemas.matrix import ONSET, SILENCE, SUSTAIN, MatrixProcessingStep


def columns_with_onsets(grid: np.ndarray) -> np.ndarray:
    """Boolean mask, one per column: does any key start there?"""
    return np.any(grid == ONSET, axis=0)


def clean_sustains(
    matrix: PianoMatrix,
    *,
    reporter: BaseProgress | None = None,
    processing_step: MatrixProcessingStep = MatrixProcessingStep.CLEAN,
) -> PianoMatrix:
    """Apply the Appendix B rule and return a cleaned copy.

    ``processing_step`` labels the result. It defaults to ``clean`` because that
    is what cleaning a one-hand matrix produces; pass ``two-hands`` when cleaning
    one half of a split, so the label keeps describing what the grid actually is.

    Vectorized, no column loop. The insight: a sustain cell at ``(row, col)``
    survives only if **no column strictly after the sustain's own span start,
    up to and including ``col``, contains an onset from another key**. Since
    the span's own onset sits in a column that also "contains an onset", the
    test reduces to: *has any column since this span began — excluding the
    span's opening column — contained an onset?*

    Implementation: for every column, count the onset-bearing columns seen so
    far (a cumulative sum). A sustain cell survives iff that count equals the
    count at the column where its span was opened. Comparing the running count
    against the count carried forward from each span's onset column does the
    whole grid in a few array operations.
    """
    grid = matrix.grid
    rows, columns = grid.shape
    if columns == 0:
        return matrix.with_grid(grid.copy(), processing_step=processing_step)

    progress = default_reporter(reporter)
    with progress.stage("clean", total=1) as stage:
        # How many onset-bearing columns have occurred up to and including each column.
        onset_columns = columns_with_onsets(grid)
        seen = np.cumsum(onset_columns)

        # For each cell, the `seen` value at the most recent onset of that row.
        # forward-fill: where the row has an onset, take `seen`; elsewhere carry.
        row_onsets = grid == ONSET
        marks = np.where(row_onsets, seen[None, :], -1).astype(np.int64)
        np.maximum.accumulate(marks, axis=1, out=marks)

        # A sustain survives while no *new* onset column has occurred since its
        # span opened. The span's own onset column is already counted in `marks`.
        survives = (grid == SUSTAIN) & (seen[None, :] == marks)

        cleaned = grid.copy()
        cleaned[(grid == SUSTAIN) & ~survives] = SILENCE

        stage.advance(message=f"{int(np.count_nonzero(grid != cleaned))} sustains cut")

    return matrix.with_grid(cleaned, processing_step=processing_step)


def cut_sustain_count(matrix: PianoMatrix) -> int:
    """How many sustain cells :func:`clean_sustains` would remove."""
    cleaned = clean_sustains(matrix)
    return int(np.count_nonzero(matrix.grid != cleaned.grid))


def is_clean(matrix: PianoMatrix) -> bool:
    """True when the matrix already satisfies the Appendix B rule."""
    return cut_sustain_count(matrix) == 0
