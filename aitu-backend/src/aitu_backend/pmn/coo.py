"""The dense matrix and the sparse form to the COO payload of the piano sheet, with NumPy.

The COO payload (:class:`aitu_backend.schemas.matrix.SparseCooMatrix`) is what the piano sheet has
always received for each hand, and it does not change: ``rows``, ``cols`` and ``onset`` hold every
active cell sorted by ``(col, row)``, and ``onset[i]`` is the row for an onset and ``-1`` for a
sustain.

Building it used to loop over every cell in Python, and the payload model then checked every cell
again in another loop, twice per request. Both are array operations here. The builder is trusted,
so the payload it returns skips the per-cell check; a payload read from outside still gets it.
"""

from __future__ import annotations

import numpy as np

from aitu_backend.pmn.dense import to_dense
from aitu_backend.pmn.notes import KEY_COUNT, Notes
from aitu_backend.schemas.matrix import ONSET, SUSTAIN, SparseCooMatrix

__all__ = ["coo_from_grid", "coo_from_notes", "grid_from_coo"]


def coo_from_grid(grid: np.ndarray) -> SparseCooMatrix:
    """The COO payload of one 88 x N matrix, sorted by ``(col, row)``."""
    grid = np.asarray(grid, dtype=np.int8)
    if grid.ndim != 2 or grid.shape[0] != KEY_COUNT:
        raise ValueError(f"A piano matrix is {KEY_COUNT} x N, got shape {grid.shape}")
    # Walking the transpose visits the cells column by column, which is the (col, row) order.
    cols, rows = np.nonzero(grid.T)
    onset = np.where(grid[rows, cols] == ONSET, rows, SUSTAIN)
    return SparseCooMatrix.model_construct(
        shape=[KEY_COUNT, int(grid.shape[1])],
        rows=rows.tolist(),
        cols=cols.tolist(),
        onset=onset.tolist(),
    )


def coo_from_notes(
    notes: Notes, frame_ms: float, duration_ms: float | None = None, *, hand: int | None = None
) -> SparseCooMatrix:
    """The COO payload of the live notes (or of one hand) at ``frameMs``."""
    return coo_from_grid(to_dense(notes, frame_ms, duration_ms, hand=hand))


def grid_from_coo(payload: SparseCooMatrix | dict) -> np.ndarray:
    """The 88 x N ``int8`` matrix of a COO payload. The inverse of :func:`coo_from_grid`."""
    coo = (
        payload if isinstance(payload, SparseCooMatrix) else SparseCooMatrix.model_validate(payload)
    )
    grid = np.zeros((coo.shape[0], coo.shape[1]), dtype=np.int8)
    rows = np.asarray(coo.rows, dtype=np.int64)
    cols = np.asarray(coo.cols, dtype=np.int64)
    onset = np.asarray(coo.onset, dtype=np.int64)
    grid[rows, cols] = np.where(onset == SUSTAIN, SUSTAIN, ONSET)
    return grid
