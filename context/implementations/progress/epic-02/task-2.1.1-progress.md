# Task 2.1.1 — Matrix model · progress report

Status: **done**. Date: 2026-07-26.

## Summary

`matrix/model.py` — the `PianoMatrix` dataclass every other matrix module manipulates.

**Fields**: `grid` (numpy `int8`, 88 x N), `granularity`, `tempo_bpm`, `processing_step`,
`key_signature`, `title`, `hand` (filled by Task 2.4.1).
**Derived**: `time_step_seconds`, `beats_per_column`, `duration_seconds`, `frame_count`, `shape`.

| Group | API |
|-------|-----|
| construct | `empty`, `from_dense`, `from_coo_payload`, `from_envelope`, `load_npz` |
| timing | `frame_to_time`, `time_to_frame`, `frames_for_seconds`, `frame_to_beats`, module-level `beats_per_column` / `seconds_per_column` |
| access | `cell`, `row_of`, `row_for_note`, `active_rows`, `onsets_in_column`, `key_names`, `is_empty` |
| convert | `to_dense`, `to_array`, `to_coo_payload`, `to_envelope`, `save_npz` |
| structure | `copy`, `with_grid`, `slice_frames`, `__eq__`, `__len__`, `__repr__` |

`HIERARCHY` is exported as the task file spells it (a list of plain strings), derived from
`GRANULARITY_HIERARCHY` in `schemas/matrix.py` so the two can never drift.

Constructor validation rejects a non-88-row grid, a non-positive tempo, and any cell value
outside `{1, -1, 0}`.

## The one design decision worth reading

**The in-memory backing is a dense numpy array, not `scipy.sparse`.** The task file says "backed by
`scipy.sparse` COO"; the sparse form is kept for the **wire and disk** (`to_coo_payload`,
`save_npz`, `matrix_store.py`) but not in memory.

Reasoning: every operation this epic needs — collapse, clean, split, transpose, slice — is
whole-array numpy work, and the plan requires it to be *vectorized* (Task 2.2.1) and *sub-second*
(the epic's exit criteria). An 88 x N `int8` grid is 88 bytes per frame: ~1 MB for two hours of
fusas at 120 BPM. Sparsity saves nothing at that size and blocks vectorization, while COO
in particular does not support element access at all. Storage stays sparse and compressed, which
is where the size actually mattered.

This is an implementation-level choice, not a requirements change: every externally visible
format (wire COO, `.npz`, the envelope) is exactly what Task 1.3.1 and 1.4.1 specified. **If the
supervisor prefers sparse in memory, say so — it is a contained change inside this one file.**

## Errors found and how they were solved

1. **`to_coo_payload` ordering.** Iterating `np.nonzero(self.grid)` gives row-major = *key*-major
   order, but the contract requires `(col, row)`. Transposing first (`np.nonzero(self.grid.T)`)
   yields frame-major directly and cost nothing. Pinned by a test with deliberately out-of-order
   input.
2. **`slice_frames` and orphan sustains.** Slicing mid-note leaves a leading `-1` with nothing to
   continue — structurally illegal. Rather than fix it here, `slice_frames` returns the raw slice
   and the docstring points at `validator.normalize`, so the promote-to-onset policy exists in one
   place (and Task 2.4.2's range replacement can choose when to apply it).
3. **Circular imports.** `model.py` needs `storage.matrix_store`, which needs `schemas.matrix`,
   which `model.py` also imports. The two storage calls are imported **inside** `save_npz` /
   `load_npz` — the only two methods that touch disk.

## Deviations from the task file

- Dense numpy in memory (see above).
- `from_dense` / `to_dense` take a `frames_as_rows` flag so both orientations are reachable
  explicitly. Task 1.3.1 left the JSON export transposed relative to the wire form; this is the one
  place inside `matrix/` allowed to flip it.
- Added `from_envelope` / `to_envelope`, `with_grid`, `slice_frames`, `active_rows`,
  `onsets_in_column` — all needed by the later tasks in this epic.
- Subtask 2.1.1.3 (key mapping) was already delivered as `matrix/keys.py` in Task 1.3.1, which
  needed it for the EN+ES column headers. Nothing to add; `PianoMatrix.key_names()` and `row_of()`
  delegate to it.

## Verification

```
pytest tests/test_matrix_model.py   # 28 passed
mypy, flake8, black                 # clean
```

The acceptance property tests: dense <-> sparse <-> npz round-trips in both orientations,
including the empty matrix; and the timing helpers checked against the worked examples in
`01-matrix-notation-logic.md` — the 60 BPM / 0.5 s = corchea default, the four-row BPM/resolution
table, and the "`*Re-4` held over 2 frames = 1 beat" example.

## Manual trial for the supervisor

```bash
cd aitu-backend && uv run python -c "
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.text_notation import sequence_to_sparse_payload
m = PianoMatrix.from_coo_payload(
    sequence_to_sparse_payload(['*Do-4','Do-4','*Re-4','*Mi-4','Mi-4','Mi-4','Mi-4','*Sol-4']),
    granularity='corchea', tempo_bpm=60)
print(m)                                  # 88x8, corchea, 60.0 BPM, raw, 8 active cells
print(m.time_step_seconds, m.duration_seconds)   # 0.5 4.0
print(m.frame_to_time(4), m.time_to_frame(1.6))  # 2.0 3
"
```

## For the next worker

- **Task 2.1.2** (validator) consumes `matrix.grid` directly and returns new matrices via
  `with_grid` — that helper exists so metadata is never dropped by accident.
- **Task 2.2.1** (collapse/upsample): work on `matrix.grid` with numpy, then
  `with_grid(new, granularity=...)`. `HIERARCHY` gives the ladder; moving one step is an index
  step through it.
- Do not mutate `matrix.grid` in place across a public boundary — use `copy()` or `with_grid`.
- `PianoMatrix.__eq__` compares grid **and** granularity/tempo/step, so tests can assert on whole
  matrices.
