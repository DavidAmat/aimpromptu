# Task 2.4.1 — Two-hands split · progress report

Status: **done**. Date: 2026-07-27.

## Summary

`matrix/hands.py` implements Appendix D: **`Do-4` (middle C, MIDI 60) and above is the right
hand, everything below is the left.**

| API | Role |
|-----|------|
| `split_hands(matrix, threshold="Do-4")` | -> `TwoHands(right, left, split_row)` |
| `TwoHands.combined()` | merge the pair back into one matrix |
| `combine_hands(right, left)` | same, for hands that did not come from one split |
| `hand_of_row(row, threshold)` | -> `Hand.RIGHT` / `Hand.LEFT` |
| `resolve_split_row`, `DEFAULT_SPLIT_ROW` | threshold plumbing |

**Splitting never cuts.** Both outputs are full 88 x N copies with the other hand's rows zeroed,
so `r.shape == l.shape == clean.shape` and the two staves stay frame-aligned — which the notation
contract requires (`r_matrix` and `l_matrix` must have equal `shape[1]`). Each output is tagged
`hand="right"` / `"left"` and `processing_step=TWO_HANDS`.

`threshold` accepts a **row index or a Spanish note name** and defaults to `Do-4`, so the future
per-piece heuristic Appendix D anticipates can move it without touching any caller.

## Errors found

None. The one thing worth stating: the split partitions the rows, so no row is non-zero in both
hands, which makes recombination exact rather than approximate. `combine_hands` still documents a
tie-break (right hand wins) for hand-edited matrices that did not come from a split.

## Deviations from the task file

- Added `TwoHands` as a small frozen dataclass rather than returning a bare tuple; `split_row` is
  part of the answer and Epic 9 will want it.
- Added `combine_hands` and `hand_of_row` beyond the task's scope. Recombination is the acceptance
  criterion, and `hand_of_row` is what the Matrix tab needs to colour a cell.

## Verification

```
pytest tests/test_matrix_hands.py   # 20 passed
mypy, flake8, black                 # clean
```

Acceptance: a mixed-register example splits correctly, and **recombining reproduces the clean
matrix exactly** — asserted both via `TwoHands.combined()` and `combine_hands`, including a case
with sustains and silences.

Also covered: middle C itself going right and `Si-3` going left (the off-by-one that matters);
shape and frame-count invariants; both hands passing the transition validator; metadata carry-over;
non-mutation; note-name and row-index thresholds; the two extreme thresholds putting everything in
one hand; the out-of-range rejection; an empty matrix; and a musical case (a held `Do-3`+`Sol-3`
under a rising right-hand scale).

## Manual trial for the supervisor

Play **a low Do with the left hand and Do Re Mi with the right, at 60 BPM**. Once Epic 9 renders,
the grand staff should show the low Do alone on the bass clef and the melody alone on the treble.
Anything you play *below* middle C lands in the bass clef even if you played it with your right
hand — that is the known limitation of the dummy rule, not a bug.

```bash
cd aitu-backend && uv run python -c "
from aitu_backend.matrix.hands import split_hands
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.text_notation import sequence_to_sparse_payload
m = PianoMatrix.from_coo_payload(sequence_to_sparse_payload(['*Do-3 || *Do-5','*Do-3 || *Re-5']))
h = split_hands(m)
print(h.left.active_rows(), h.right.active_rows())   # [27] [51, 53]
print(h.right.shape == h.left.shape == m.shape)      # True
"
```

## For the next worker

- **Epic 4 pipeline**: split the **clean** matrix, and save both hands as separate `.npz` files —
  `matrix_filename(version, granularity, "left"/"right")` from `schemas/naming.py` already produces
  the names.
- **Epic 9**: right = treble, left = bass by default. `TwoHands.split_row` tells you where the
  boundary was, which matters for the left-hand treble-clef switch (Story 9.5).
- Improving the split (voice-leading, hand span) means replacing `split_hands` only; the shape
  contract and every caller stay the same.
