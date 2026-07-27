# Task 2.4.1 — Two-hands split

`matrix/hands.py`: Appendix D of `01-matrix-notation-logic.md`. Dummy threshold logic for the first iteration; smarter assignment is a future refinement.

## Subtask 2.4.1.1 — Split

- Input: clean matrix. Output: `r_matrix`, `l_matrix`, both exact duplicates of the clean matrix shape (same rows and columns — split never cuts).
- Right hand: zero out all rows below C4 (`Do-4`). Left hand: zero out C4 and above.
- Threshold key is a parameter (default `Do-4`) so future logic can move it per piece.

## Subtask 2.4.1.2 — Invariants

- `r.shape == l.shape == clean.shape`; frame counts always equal so hands stay aligned when rendered.
- Both outputs pass the transition validator (zeroing whole rows cannot create illegal transitions).
- Default clefs downstream: right = treble, left = bass.

## Acceptance

Tests: split of a mixed-register example; recombining r+l by element-wise max reproduces the clean matrix.
