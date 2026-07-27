# Task 2.2.1 — Collapse and upsample · progress report

Status: **done**. Date: 2026-07-27.

## Summary

`matrix/granularity.py` moves a matrix between temporal granularities.

| Function | Role |
|----------|------|
| `merge_pairs(grid)` | the merge table, vectorized; halves the column count |
| `collapse_one_step(matrix)` | one hierarchy step coarser |
| `collapse_to(matrix, target, *, allow_chaining, reporter)` | chained collapse |
| `expand_columns(grid)` | the expansion rules; doubles the column count |
| `upsample_one_step` / `upsample_to` | the finer direction |
| `retarget(matrix, target)` | picks the direction automatically |
| `hierarchy_index`, `steps_between`, `is_coarser`, `collapsed_frame_count` | ladder arithmetic |

Every rule from `project-features.md` is implemented and individually tested:

```text
[1, 1] -> 1    [0, 1]  -> 1    [-1, 0]  -> -1        0 -> [0, 0]
[1, 0] -> 1    [0, 0]  -> 0    [-1, 1]  ->  1        1 -> [1, -1]
[1,-1] -> 1    [0,-1]  -> n/a  [-1,-1]  -> -1       -1 -> [-1, -1]
```

The merge table collapses to one sentence, which is how it is implemented:
**an onset anywhere in the pair wins; otherwise a sustain in the pair wins; otherwise silence.**
`[0, -1]` needs no branch — the validator (Task 2.1.2) rejects it upstream, and were it to slip
through, "sustain wins over silence" is the sane answer anyway.

Collapsing halves the columns and doubles `time_step_seconds` with **BPM unchanged**, so the
piece's wall-clock duration is invariant. Tests assert that explicitly, both directions.

Odd column counts are **padded with a silence column before pairing**, never truncated — losing
the final frame of a piece would be a silent data loss.

## Implementation

Both directions are pure numpy, no Python loop over columns:

```python
# collapse: reshape to (88, N//2, 2) and take the priority of each pair
pairs = grid.reshape(rows, columns // 2, 2)
merged[(left == 1) | (right == 1)] = 1
merged[((left == -1) | (right == -1)) & (merged != 1)] = -1

# upsample: stack the column with its sustained twin, then reshape
second = np.where(grid == 1, -1, grid)
np.stack([grid, second], axis=2).reshape(rows, columns * 2)
```

`collapse_to` takes an optional `ProgressReporter` and advances one step per hierarchy step, so
the Matrix tab can show the chain running if a piece is ever long enough to need it.

## The `allow_chaining` guard, and a correction to my own first draft

I initially guarded `collapse_to` against *already-collapsed* matrices on the grounds that
"collapsing twice compounds the loss". Writing the test proved that wrong: `collapse_to` always
walks one step at a time, so two chained calls produce **identical cells** to one multi-step call.
Collapsing is associative.

What is genuinely unrecoverable is what the *later* pipeline steps remove — Appendix B cleaning
(Task 2.3.1) deletes sustains, the two-hands split zeroes half the rows. Collapsing one of those
compounds a real loss, silently.

So the guard now rejects **any matrix whose `processing_step` is not `raw`**, and the docstring
says why. `allow_chaining=True` overrides it. The test is parametrized over `collapsed`, `clean`
and `two-hands`, and a separate test documents the associativity finding so the next reader does
not re-derive it.

This is the reason the raw fusa matrix is stored forever: **always re-collapse from raw.**

## Errors found and how they were solved

1. The `allow_chaining` reasoning above — caught by a test that was supposed to demonstrate a
   difference and could not.
2. `flake8 F401`: `SILENCE` imported but unused, because "otherwise silence" is implemented as
   "the array is already zeroed". Removed the import; the comment explains the absence.
3. A copy-paste artifact in a test (`[...] and [...]`, which Python evaluates to the second list)
   — harmless but nonsense. Rewritten, and a companion test added asserting collapsed matrices are
   structurally valid too.

## Deviations from the task file

- The guard is on `processing_step != raw` rather than `== collapsed` (see above).
- Added `retarget`, `collapsed_frame_count`, `hierarchy_index`, `steps_between`, `is_coarser`.
  Epic 7's in-situ granularity switch needs to change direction without knowing which way it is
  going, and Epic 4 needs the frame count before doing the work.
- Subtask 2.2.1.4 says "then back to sparse". The matrix stays dense in memory (see the Task 2.1.1
  report); conversion to sparse happens at the storage and wire boundaries, unchanged.

## Verification

```
pytest tests/test_matrix_granularity.py   # 36 passed
pytest                                    # 169 passed overall
mypy, flake8, black                       # clean
```

Acceptance coverage: all 8 merge rules and all 3 expansion rules parametrized individually; the
documented X -> X//2 -> X//4 -> X//8 chain; odd-count padding; time-step doubling with constant
BPM and duration; both ladder-end errors; the direction errors; the processing-step guard over
three steps; `collapsed_frame_count` cross-checked against reality for seven frame counts;
structural validity after both operations; and a musical example (Do Re Mi Fa Sol as semifusas
collapsing to five clean onsets at fusa).

**Irreversibility is pinned by a test**: `[1, 0, 1, 0]` collapsed then upsampled comes back as
`[1, -1, 1, -1]` — the silences became sustains, and the original is gone.

**Performance** (the exit criterion): a random 88 x 9600 semifusa matrix — five minutes at 120 BPM —
collapsed four steps to negra in well under the 0.5 s the test allows. In the sandbox it ran in
single-digit milliseconds.

## Manual trial for the supervisor

```bash
cd aitu-backend && uv run python -c "
from aitu_backend.matrix.granularity import collapse_to
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.text_notation import sequence_to_sparse_payload
raw = PianoMatrix.from_coo_payload(
    sequence_to_sparse_payload(['*Do-4','Do-4','*Re-4','Re-4','*Mi-4','Mi-4','*Fa-4','Fa-4']),
    granularity='fusa', tempo_bpm=60)
c = collapse_to(raw, 'semicorchea')
print(raw.frame_count, '->', c.frame_count)                 # 8 -> 4
print(raw.duration_seconds, c.duration_seconds)             # 1.0 1.0  (unchanged)
print([c.cell(r, i) for i, r in enumerate([39, 41, 43, 44])]) # [1, 1, 1, 1]
"
```

Four notes played as pairs of fusas become four clean semicorchea onsets, and the piece still
lasts one second.

## For the next worker

- **Task 2.3.1 (cleaning)** runs *after* collapsing, on the collapsed matrix. Set
  `processing_step = CLEAN` on your output so the collapse guard protects it.
- **Task 4.3.1 (pipeline)**: raw (fusa or semifusa) -> `collapse_to(user_granularity)` -> clean ->
  split. Store the raw matrix; every later granularity change re-runs `collapse_to` **from raw**,
  which is what makes the recompute sub-second.
- **Epic 7**: `retarget` handles a granularity dropdown in either direction, but the correct
  behaviour for the in-situ switch is still "recompute from raw", not "retarget the displayed one".
- `merge_pairs` and `expand_columns` operate on raw numpy arrays, so the future hand-split code can
  reuse them per hand without building a `PianoMatrix` each time.
