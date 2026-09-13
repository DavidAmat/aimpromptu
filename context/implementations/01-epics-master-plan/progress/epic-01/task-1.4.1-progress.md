# Task 1.4.1 — Storage layout · progress report

Status: **done**. Date: 2026-07-26.

## Summary

### Folder tree

`storage/paths.py` now builds the full tree exactly as the task file draws it, and
`ensure_data_tree()` (called from the FastAPI `lifespan`) creates the four roots on startup:
`data/audio/`, `data/playground/`, `data/library/tracks/`, `data/library/playlists/`.

Path helpers, grouped by area — **no path literal exists outside this module**:

| Area | Helpers |
|------|---------|
| roots | `backend_root`, `data_dir`, `audio_root`, `playground_root`, `library_root`, `library_tracks_root`, `library_playlists_root`, `ensure_data_tree` |
| audio | `audio_dir`, `audio_metadata_path`, `audio_original_path`, `find_audio_original`, `list_audio_uuids` |
| playground | `playground_artist_dir`, `playground_track_dir`, `playground_track_metadata_path`, `playground_version_dir`, `playground_version_metadata_path`, `playground_matrix_path`, `list_playground_artists`, `list_playground_tracks`, `list_playground_versions` |
| library | `library_track_dir`, `library_track_metadata_path`, `library_matrix_path`, `playlist_dir`, `playlist_metadata_path`, `list_library_artists`, `list_library_tracks`, `list_playlists` |
| seed | `scores_json_path` |

Folder names are never spelled out here either — they come from `schemas/naming.py`
(`version_folder`, `matrix_filename`), so `v2_gn` is defined once for the whole project.

### Matrix file format

`storage/matrix_store.py` implements the decision: `scipy.sparse` COO of `int8`, written with
`scipy.sparse.save_npz(..., compressed=True)`, shape **88 x N** (the wire orientation — no
transposition on the storage path).

The encoding is worth stating plainly: **the stored value is the cell value** — `1` for an onset,
`-1` for a sustain, absent for silence. That maps exactly onto the COO wire format's
`onset[i] = rows[i] | -1`, so nothing is invented or lost in either direction. `load_matrix`
rejects any other value rather than guessing.

API: `to_coo`, `from_coo`, `save_matrix`, `load_matrix`, `matrix_exists`.
`save_matrix` creates parent folders and refuses a filename that is not `.npz` (a real trap:
`scipy.sparse.save_npz` silently appends the suffix, which would produce a file at a path no
helper can find again).

Dense grids are never persisted; dense exists only transiently for JSON export/import.

### Gitignore policy

Added to the root `.gitignore`, with the reasoning inline:

```gitignore
aitu-backend/data/audio/**          # always heavy, always reproducible
aitu-backend/data/**/*.npz          # binary matrices anywhere under data/
!aitu-backend/data/examples/**/*.npz  # except the small committed samples
```

`metadata*.json` is deliberately **not** ignored: those files are small, human-readable and the
actual record of what was done. `data/example-scores.json` stays committed as before.

### `data/README.md`

New file documenting the tree, the commit policy and the npz format, so someone opening `data/`
on disk can tell what they are looking at without reading Python.

## Errors found and how they were solved

1. **`scipy.sparse.save_npz` silently appends `.npz`.** Saving to `matrix.bin` writes
   `matrix.bin.npz`, which no path helper would ever find. `save_matrix` now rejects a non-`.npz`
   filename up front, with a test.
2. **COO ordering is not guaranteed after a round trip.** `scipy` does not promise sort order in
   COO. `from_coo` converts through CSC (column-major = frame-major) with `sort_indices()` before
   returning, so a loaded matrix always satisfies the contract's `(col, row)` sort. Pinned by
   `test_loaded_cells_come_back_sorted_by_column_then_row`, which saves deliberately unsorted
   cells and asserts sorted cells come back.
3. **Testing path helpers without touching the real `data/`.** All the helpers derive from
   `backend_root()`, so the tests monkeypatch that single function to a `tmp_path`. One extra test
   (`test_backend_root_holds_pyproject`) checks the **real** root still resolves — otherwise the
   monkeypatched suite would happily pass with a broken `parents[3]` depth.

## Deviations from the task file

- Added `storage/matrix_store.py`. The task described the format decision but left the code
  unplaced; every later epic needs save/load, and a decision without an implementation gets
  reinterpreted.
- Added the `list_*` helpers (not requested). Epics 5 and 10 must enumerate what is on disk, and
  that means `iterdir()` — which is exactly the kind of path knowledge this module exists to hold.
- Added `data/README.md`.
- `data/examples/` is referenced by the gitignore exception but not created by `ensure_data_tree()`:
  it only exists once something is actually committed there.

## Verification

```
pytest        # 77 passed (17 new in tests/test_storage_layout.py)
mypy          # Success: no issues found in 31 source files
flake8, black # clean
```

The task's acceptance — "unit test exercises every path helper" — is met: each helper is asserted
against an expected absolute path under a temporary root, plus the listing helpers on both an empty
and a populated tree, plus five npz round-trip tests (normal, empty, unsorted, missing file, bad
suffix).

## Manual trial for the supervisor

```bash
cd aitu-backend && uv sync && make serve
```

Then, in another shell:

```bash
find data -type d | sort
# data
# data/audio
# data/library
# data/library/playlists
# data/library/tracks
# data/playground
git status --short data/          # nothing — the empty tree adds no noise
```

Round-trip a matrix through the real format:

```bash
uv run python -c "
from pathlib import Path
from aitu_backend.matrix.text_notation import sequence_to_sparse_payload
from aitu_backend.schemas.matrix import Granularity, SparseCooMatrix
from aitu_backend.storage.matrix_store import load_matrix, save_matrix
from aitu_backend.storage.paths import playground_matrix_path
m = SparseCooMatrix.model_validate(sequence_to_sparse_payload(['*Do-4','Do-4','*Re-4','*Mi-4']))
p = playground_matrix_path('demo', 'scale', 1, Granularity.SEMICORCHEA)
save_matrix(p, m); print(p, p.stat().st_size, 'bytes')
print(load_matrix(p).model_dump() == m.model_dump())   # True
"
```

Then delete `data/playground/demo/` — it is throwaway.

## For the next worker

- **Epic 3**: `audio_dir(uuid)`, `audio_original_path(uuid, ext)` and `audio_metadata_path(uuid)`
  are ready. `find_audio_original(uuid)` finds the file when you do not know the extension.
- **Epic 4**: persist the raw matrix first — `parentMatrix` in `VersionMetadata` points back to it,
  and that pointer is what makes a sub-second recompute possible.
- **Epic 5**: `list_playground_versions()` + `next_version()` (from `schemas/naming.py`) gives you
  the next folder name. Two-hands matrices save as two files via the `hand` argument.
- Never build a path with string concatenation. If a path is missing, add a helper here.
