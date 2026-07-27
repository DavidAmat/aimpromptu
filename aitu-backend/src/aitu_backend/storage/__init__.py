"""Local filesystem persistence: paths, matrix files and metadata.

Everything lives under ``aitu-backend/data/`` (see ``data/README.md``).
:mod:`aitu_backend.storage.paths` builds every path; nothing else does.
:mod:`aitu_backend.storage.matrix_store` owns the ``.npz`` format. Epic 5 adds
the versioned artifact repository and library promotion on top.
"""

from aitu_backend.storage.matrix_store import load_matrix, matrix_exists, save_matrix
from aitu_backend.storage.paths import data_dir, ensure_data_tree

__all__ = [
    "data_dir",
    "ensure_data_tree",
    "load_matrix",
    "matrix_exists",
    "save_matrix",
]
