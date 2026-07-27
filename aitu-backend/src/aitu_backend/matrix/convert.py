"""Sparse <-> dense conversion for the piano matrix.

The orientation flip lives here and nowhere else:

* sparse COO is **88 x N** (row = key, col = time frame)
* dense is **N x 88** (row = time frame, col = key) — the Matrix tab's layout,
  and what ``columnHeaders`` / ``rowTimestamps`` describe

Both directions are lossless, which the round-trip test pins.
"""

from __future__ import annotations

import numpy as np

from aitu_backend.matrix.keys import KEY_COUNT
from aitu_backend.schemas.matrix import (
    ONSET,
    SILENCE,
    SUSTAIN,
    Granularity,
    KeyLabel,
    PianoMatrixEnvelope,
    SparseCooMatrix,
    key_labels,
)


def sparse_to_dense(matrix: SparseCooMatrix) -> list[list[int]]:
    """COO (88 x N) -> dense grid of ``1`` / ``-1`` / ``0``, **frames x keys**."""
    grid = np.zeros((matrix.shape[1], KEY_COUNT), dtype=np.int8)
    for row, col, onset in zip(matrix.rows, matrix.cols, matrix.onset):
        grid[col, row] = ONSET if onset != -1 else SUSTAIN
    return grid.tolist()


def dense_to_sparse(grid: list[list[int]]) -> SparseCooMatrix:
    """Dense grid (**frames x keys**) -> COO (88 x N), sorted by ``(col, row)``.

    Any non-zero that is neither ``1`` nor ``-1`` is rejected by the model.
    """
    array = np.asarray(grid, dtype=np.int8).reshape(len(grid), KEY_COUNT)
    frames, keys = np.nonzero(array)  # np.nonzero yields row-major = (col, row) order here.

    rows = keys.astype(int).tolist()
    cols = frames.astype(int).tolist()
    onset = [row if array[col, row] == ONSET else -1 for row, col in zip(rows, cols)]

    # np.nonzero already returns frame-major order, which is exactly (col, row).
    return SparseCooMatrix(
        shape=[KEY_COUNT, len(grid)],
        rows=rows,
        cols=cols,
        onset=onset,
    )


def dense_column_headers() -> list[KeyLabel]:
    """The 88 key labels describing the dense columns."""
    return key_labels()


def dense_row_timestamps(frame_count: int, time_step_seconds: float) -> list[float]:
    """Start time in seconds of each dense row."""
    return [round(index * time_step_seconds, 6) for index in range(frame_count)]


def to_dense_envelope(envelope: PianoMatrixEnvelope) -> PianoMatrixEnvelope:
    """Return an equivalent envelope carrying the dense payload.

    Adds ``columnHeaders`` and ``rowTimestamps``, since a dense export is the
    human-readable form and those are what make it readable.
    """
    if not envelope.sparse:
        return envelope.model_copy(deep=True)

    data = envelope.model_dump(by_alias=True)
    data["sparse"] = False
    data["matrix"] = None
    data["rMatrix"] = None
    data["lMatrix"] = None
    data["denseMatrix"] = sparse_to_dense(envelope.matrix) if envelope.matrix else None
    data["denseRMatrix"] = sparse_to_dense(envelope.r_matrix) if envelope.r_matrix else None
    data["denseLMatrix"] = sparse_to_dense(envelope.l_matrix) if envelope.l_matrix else None
    data["columnHeaders"] = [label.model_dump() for label in dense_column_headers()]
    data["rowTimestamps"] = dense_row_timestamps(envelope.frame_count, envelope.time_step_seconds)
    return PianoMatrixEnvelope.model_validate(data)


def to_sparse_envelope(envelope: PianoMatrixEnvelope) -> PianoMatrixEnvelope:
    """Return an equivalent envelope carrying the sparse COO payload."""
    if envelope.sparse:
        return envelope.model_copy(deep=True)

    data = envelope.model_dump(by_alias=True)
    data["sparse"] = True
    data["matrix"] = (
        dense_to_sparse(envelope.dense_matrix).model_dump(by_alias=True)
        if envelope.dense_matrix is not None
        else None
    )
    data["rMatrix"] = (
        dense_to_sparse(envelope.dense_r_matrix).model_dump(by_alias=True)
        if envelope.dense_r_matrix is not None
        else None
    )
    data["lMatrix"] = (
        dense_to_sparse(envelope.dense_l_matrix).model_dump(by_alias=True)
        if envelope.dense_l_matrix is not None
        else None
    )
    data["denseMatrix"] = None
    data["denseRMatrix"] = None
    data["denseLMatrix"] = None
    return PianoMatrixEnvelope.model_validate(data)


def empty_dense(frame_count: int) -> list[list[int]]:
    """A silent dense grid of ``frame_count`` frames."""
    return [[SILENCE] * KEY_COUNT for _ in range(frame_count)]


def time_step_for(granularity: Granularity, tempo_bpm: float) -> float:
    """Seconds per column implied by a granularity at a tempo."""
    return granularity.seconds(tempo_bpm)


__all__ = [
    "ONSET",
    "SILENCE",
    "SUSTAIN",
    "dense_column_headers",
    "dense_row_timestamps",
    "dense_to_sparse",
    "empty_dense",
    "sparse_to_dense",
    "time_step_for",
    "to_dense_envelope",
    "to_sparse_envelope",
]
