# Task 2.3.1 — Sustain cleaning · progress report

Status: **done**. Date: 2026-07-27.

## Summary

`matrix/cleaning.py` implements Appendix B: **a sustain dies the moment any other key is struck.**

| Function | Role |
|----------|------|
| `clean_sustains(matrix, *, reporter)` | the rule; returns a cleaned copy marked `CLEAN` |
| `cut_sustain_count(matrix)` | how many sustain cells would be removed |
| `is_clean(matrix)` | already satisfies the rule? |
| `columns_with_onsets(grid)` | one boolean per column: does anything start here? |

Only `-1` cells are ever removed. **Onsets are never touched**, so no note can disappear from the
score — only its tail shortens. A test asserts the onset mask is identical before and after.

## Implementation — vectorized, not a column sweep

The task file suggested a column sweep tracking open spans. That works, but it is a Python loop
over every frame, and cleaning runs on every recompute. The rule turns out to be expressible in
four array operations:

```python
seen  = np.cumsum(np.any(grid == 1, axis=0))   # onset-bearing columns so far
marks = np.where(grid == 1, seen, -1)
np.maximum.accumulate(marks, axis=1, out=marks) # `seen` at each row's last onset
survives = (grid == -1) & (seen == marks)
```

`seen` counts how many onset-bearing columns have occurred up to each column. `marks` carries
forward, per row, the `seen` value at that row's most recent onset — a forward-fill done with
`maximum.accumulate`, which is valid precisely because `seen` is monotonically non-decreasing.
A sustain survives exactly when no *new* onset column has occurred since its span opened.

That single expression handles all three appendix cases without a special branch:

- A **chord struck together** shares one opening column, so no member is "another note" for the
  others — they all survive together.
- A **re-onset of the same key** updates that row's `marks`, so the new span starts its own clock
  and survives, exactly as the appendix's counter-example requires.
- An **orphan sustain** (`marks == -1`) never matches and is dropped, so structurally illegal
  input degrades safely rather than crashing.

Verified on a 88 x 5000 matrix; it is a handful of milliseconds.

## Errors found and how they were solved

No blockers. The one thing that needed care was the forward-fill: an earlier sketch compared each
sustain against `seen` at the *previous* column, which silently kept the first sustain after a
foreign onset. The `marks` formulation compares against the span's own opening instead, and
`test_the_cut_starts_exactly_at_the_foreign_onset` pins the boundary — a sustain survives columns
1 and 2 and dies at column 3, the column of the foreign strike.

## Deviations from the task file

- Vectorized instead of a column sweep (above). Behaviour is identical.
- Added `cut_sustain_count` and `is_clean` for diagnostics; Epic 7 can show "N sustains cut" when
  the user switches to the clean pill.

## Verification

```
pytest tests/test_matrix_cleaning.py   # 23 passed
pytest                                 # 192 passed overall
mypy, flake8, black                    # clean
```

All three appendix cases have a dedicated test named after them:

1. `C3` held 3 s under a `C4` struck at 1 s -> `C3` cut to 1 s.
2. The classical accompaniment pattern: `C3`+`C4` held 10 s with `D3` at 1 s and `E3` at 2 s ->
   both chord notes cut to 1 s, both melody notes intact.
3. The counter-example: `C3`+`C4` chord plus a `C3` re-onset at 1 s -> chord cut to 1 s, the new
   `C3` keeps all 10 s.

Plus: chords sustaining together, the exact cut boundary, onset preservation, a second chord
restarting the clock, pitch-distance irrelevance, idempotency, non-mutation, orphan handling,
empty/silent matrices, progress reporting, a pedal-bass-under-melody musical case, and a 5000-frame
scale check.

## Manual trial for the supervisor

Play, slowly at 60 BPM: **hold a low Do with the left hand while playing Do Re Mi with the right.**
Once Epic 4 lands, the Matrix tab's `collapsed` pill will show the low Do sustaining under the
melody; the `clean` pill will show it as a single short note. That difference *is* this task.

For now, in Python:

```bash
cd aitu-backend && uv run python -c "
import numpy as np
from aitu_backend.matrix.cleaning import clean_sustains
from aitu_backend.matrix.model import PianoMatrix
g = np.zeros((88, 4), dtype=np.int8)
g[27] = [1, -1, -1, -1]      # Do-3 held four beats
g[39] = [0,  1,  0,  0]      # Do-4 struck on beat 2
g[41] = [0,  0,  1,  0]      # Re-4 on beat 3
print(clean_sustains(PianoMatrix.from_dense(g)).grid[27].tolist())   # [1, 0, 0, 0]
"
```

## For the next worker

- **Task 2.4.1** runs after this: split the *cleaned* matrix. Do not clean again afterwards.
- **Task 4.3.1**: the pipeline order is raw -> collapse -> **clean** -> two-hands. Cleaning after
  collapsing is deliberate: collapsing merges a sustain into its onset column, so cleaning a raw
  fusa matrix first would cut tails that the collapse would have absorbed harmlessly.
- Cleaning is **lossy and marks the matrix `CLEAN`**, which is what makes `collapse_to` refuse it
  (Task 2.2.1). Always re-derive from raw.
