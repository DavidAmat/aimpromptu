# Task 2.1.2 — Transition validator · progress report

Status: **done**. Date: 2026-07-26.

## Summary

`matrix/validator.py` enforces the per-row Markov rules, scanning left to right from an initial
state of `0`:

| From | Allowed next |
|------|--------------|
| `0` | `0`, `1` |
| `1` | `1`, `-1`, `0` |
| `-1` | `1`, `-1`, `0` |

Which means **exactly one transition is illegal: `0 -> -1`**, an orphan sustain — a key held that
was never struck. A test derives that fact from `ALLOWED_TRANSITIONS` rather than asserting it by
hand, so the table and the claim cannot drift apart.

| API | Behaviour |
|-----|-----------|
| `validate(matrix)` | `list[Violation]`, ordered by column then row |
| `is_valid(matrix)` | bool, no allocation |
| `validate_strict(matrix)` | returns the matrix or raises `TransitionError` |
| `normalize(matrix)` | corrected **copy**: every orphan sustain promoted to an onset |
| `normalized_violation_count(matrix)` | how many cells `normalize` would change |

`Violation` carries `row`, `key` (the Spanish name, e.g. `Do-4`), `column`, `previous`, `found`,
and a `.message` that reads like a sentence: *"Do-4 column 3: sustain (-1) after silence (0) at
column 2"*. Column 0 says "at the start of the piece" rather than "column -1".

`TransitionError` carries the full `violations` list and prints the first five with a `+N more`
suffix, so a badly-formed import does not produce a wall of text.

## Implementation note

Both `validate` and `normalize` run on a single vectorized mask:

```python
previous = concat([zeros(88, 1), grid[:, :-1]], axis=1)
orphans  = (grid == -1) & (previous == 0)
```

Prepending a silence column encodes "the chain starts at 0" for free, so a `-1` in column 0 is
caught by the same expression as one in the middle. No Python loop touches the grid — this runs
after **every** mutation, so it had to be cheap.

`normalize` needs only one pass: promoting a `-1` to `1` makes the following `-1` legal, and a
`-1` after a `-1` was never a violation. An idempotency test pins that.

## Scope boundary worth recording

The **onset rule** from the notation spec — *a sustain dies when any other key is struck* — is
**not** implemented here. It is a musical simplification (Appendix B), not a structural
constraint: a matrix that violates it is perfectly representable and perfectly renderable, just
harder to read. It belongs to the cleaning step, **Task 2.3.1**. This module only enforces what
cannot be represented at all. The module docstring says so, to stop a later worker from
"completing" the validator with it.

## Errors found and how they were solved

No blockers. Two things worth knowing:

1. **A sustain in column 0 is illegal**, which is easy to miss if you only compare adjacent pairs.
   The prepended-silence trick handles it; a dedicated test locks it in.
2. **`normalize` must not mutate its input.** `PianoMatrix.with_grid` builds a new instance from a
   copied grid and carries the metadata over. Tested explicitly, because a silent in-place mutation
   here would corrupt a stored artifact.

## Deviations from the task file

- The task's `normalize` description mentions "collisions resolved per the notation spec". Those
  collisions (a sustain colliding with a foreign onset in the same frame) **cannot exist in a
  matrix** — one cell holds one value; they are a *text notation* parsing concern, already handled
  in `matrix/text_notation.py`. Nothing to do here; recorded so it is not mistaken for an omission.
- Added `is_valid` and `normalized_violation_count` beyond the task's three functions.

## Verification

```
pytest tests/test_matrix_validator.py   # 28 passed
pytest                                  # 133 passed overall
mypy, flake8, black                     # clean
```

Coverage: all eight legal pairs parametrized, the single illegal pair, a leading sustain, a
sustain after a release, violation ordering, strict-mode raising and truncation, six normalization
cases (including idempotency and non-mutation), and four cases drawn from `02-notation-spec.md` —
notably that the text-notation parser already produces valid matrices, and that four `*Re-4`
strikes stay four separate notes while one onset plus three sustains stays one long note.

## Manual trial for the supervisor

```bash
cd aitu-backend && uv run python -c "
import numpy as np
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.validator import normalize, validate
g = np.zeros((88, 4), dtype=np.int8); g[39] = [0, -1, -1, 0]   # row 39 = Do-4
m = PianoMatrix.from_dense(g)
print(validate(m)[0].message)            # Do-4 column 1: sustain (-1) after silence (0) at column 0
print(normalize(m).grid[39].tolist())    # [0, 1, -1, 0]
"
```

## For the next worker

- Call `validate_strict` after any user edit (Task 7.4.1) and `normalize` on any tolerant
  ingestion path (JSON import, transcription output, a `slice_frames` result).
- `slice_frames` deliberately leaves orphan sustains; normalize the result if the slice is meant
  to stand alone.
- Appendix B cleaning is **Task 2.3.1**, not this module.
