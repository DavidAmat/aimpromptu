"""Persist piano matrices as compressed ``.npz``.

Format decision (Task 1.4.1.2): a matrix is stored as a ``scipy.sparse`` COO
matrix of ``int8``, written with :func:`scipy.sparse.save_npz`. Tiny on disk,
one-line load, trivially densified with ``.toarray()``, native to the
numpy/scipy stack already in the lockfile. **Dense grids are never persisted**;
dense exists only transiently for JSON export/import.

Encoding inside the sparse array: the stored value *is* the cell value —
``1`` for an onset, ``-1`` for a sustain, absent for silence. That maps exactly
onto the COO wire format's ``onset[i] = rows[i] | -1``, so no information is
invented or lost on either conversion.

Orientation on disk is the wire orientation: **88 x N** (row = key, col = frame).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import sparse

from aitu_backend.matrix.keys import KEY_COUNT
from aitu_backend.schemas.matrix import ONSET, SUSTAIN, SparseCooMatrix

#: Suffix `save_npz` expects; it appends one if missing, which would break paths.
NPZ_SUFFIX = ".npz"


def to_coo(matrix: SparseCooMatrix) -> sparse.coo_matrix:
    """Model -> ``scipy.sparse`` COO of int8 (values 1 / -1), shape 88 x N."""
    values = np.fromiter(
        (ONSET if onset != -1 else SUSTAIN for onset in matrix.onset),
        dtype=np.int8,
        count=len(matrix.onset),
    )
    return sparse.coo_matrix(
        (values, (np.array(matrix.rows, dtype=np.int32), np.array(matrix.cols, dtype=np.int32))),
        shape=(matrix.shape[0], matrix.shape[1]),
        dtype=np.int8,
    )


def from_coo(coo: sparse.coo_matrix) -> SparseCooMatrix:
    """``scipy.sparse`` COO -> model, sorted by ``(col, row)``."""
    csc = coo.tocsc()  # Column-major: iterating it yields (col, row) order.
    csc.sort_indices()
    coo_sorted = csc.tocoo()

    rows = coo_sorted.row.astype(int).tolist()
    cols = coo_sorted.col.astype(int).tolist()
    values = coo_sorted.data.astype(int).tolist()

    unknown = {value for value in values} - {ONSET, SUSTAIN}
    if unknown:
        raise ValueError(f"Stored matrix contains illegal cell values {sorted(unknown)}")

    onset = [row if value == ONSET else -1 for row, value in zip(rows, values)]
    return SparseCooMatrix(
        shape=[coo_sorted.shape[0], coo_sorted.shape[1]],
        rows=rows,
        cols=cols,
        onset=onset,
    )


def save_matrix(path: Path, matrix: SparseCooMatrix) -> Path:
    """Write a matrix to ``path`` (compressed ``.npz``), creating parents."""
    if path.suffix != NPZ_SUFFIX:
        raise ValueError(f"Matrix files must end in {NPZ_SUFFIX}, got '{path.name}'")
    path.parent.mkdir(parents=True, exist_ok=True)
    sparse.save_npz(path, to_coo(matrix).tocoo(), compressed=True)
    return path


def load_matrix(path: Path) -> SparseCooMatrix:
    """Read a matrix written by :func:`save_matrix`."""
    if not path.is_file():
        raise FileNotFoundError(f"No matrix at {path}")
    loaded = sparse.load_npz(path)
    if loaded.shape[0] != KEY_COUNT:
        raise ValueError(f"{path} has {loaded.shape[0]} rows; a piano matrix has {KEY_COUNT}")
    return from_coo(loaded.tocoo())


def matrix_exists(path: Path) -> bool:
    return path.is_file()
