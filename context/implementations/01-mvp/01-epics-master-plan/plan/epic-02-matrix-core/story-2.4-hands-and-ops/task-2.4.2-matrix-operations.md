# Task 2.4.2 — Matrix operations

`matrix/ops.py`: structural operations later epics expose in the UI. All return new matrices (non-destructive) and run the validator.

## Subtask 2.4.2.1 — Transposition

Shift all `1`/`-1` cells up or down by K semitones (row index shift). Cells shifted off the 88-key range are dropped with a warning report. Applies to one hand or both.

## Subtask 2.4.2.2 — Tempo insertion (new columns)

Insert M silence columns at frame f. The addition unit is a figure (fusa … redonda) converted to columns at the piece granularity; additions cannot be more granular than the piece granularity (a negra-granularity piece accepts negra or coarser additions only). This powers "Cut measure up to here" in Epic 9.

## Subtask 2.4.2.3 — Slice, cut, replace

- `slice(matrix, f_start, f_end)` -> submatrix
- `delete_range(matrix, f_start, f_end)` -> columns removed
- `replace_range(matrix, f_start, f_end, replacement)` -> replacement forced to exactly the target column count (trim excess, pad with silence), per the editing-logic doc

## Subtask 2.4.2.4 — Cell edits

`add_onset(row, col)`, `extend_sustain(row, col)`, `delete_note(row, col)` (deleting a `1` also deletes its chained `-1`s). These are the primitives for Matrix-tab editing (Story 7.4); every edit is validated — e.g. a `-1` can only be placed after a `1` or an existing `-1` in that row.

## Acceptance

Unit tests per operation, including validator rejection cases.
