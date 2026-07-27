# Task 2.4.2 — Matrix operations · progress report

Status: **done**. Date: 2026-07-27. This closes Epic 2.

## Summary

`matrix/ops.py` — the structural primitives later epics expose in the UI. **Every function is
non-destructive** (returns a new matrix, never mutates its input) and **every result is
structurally valid**, because these run on user actions.

### Transposition

`transpose(matrix, semitones)` -> `TranspositionReport` carrying the new matrix, the interval,
`dropped_cells` and `dropped_notes`, plus `lossless` and a `describe()` line. Cells pushed past
`La-0` or `Do-8` are **dropped and reported, never wrapped** — a note that leaves the keyboard
cannot be played, and silently losing it in a transposition preview would be worse than saying so.
`transpose_hands` does both hands at one interval.

### Column insertion

- `insert_columns(matrix, at_frame, count)` — raw silence columns.
- `insert_figure(matrix, at_frame, figure, repeats=1)` — the unit "cut measure up to here"
  (Story 9.6) works in. The figure converts to columns at the matrix's own granularity, so an
  addition **can never be finer than the piece**: a negra-granularity piece accepts a negra or
  coarser, and asking for a corchea raises.
- `append_silence(matrix, count)`.

A note sounding across the seam keeps its onset before the gap and **restarts after the rest** —
its now-orphaned sustains are normalized into a fresh onset, which is what a lengthened measure
should sound like.

### Slice / delete / replace

- `slice_range(start, end)` — like `PianoMatrix.slice_frames` but normalized, so a passage cut mid-
  note stands on its own.
- `delete_range(start, end)` — closes the gap, normalizes the seam.
- `fit_to_width(matrix, columns)` — trim excess, pad with silence.
- `replace_range(matrix, start, end, replacement)` — **forces the replacement to exactly
  `end - start` columns first**, per `03-editing-logic.md`, so the surrounding music never moves.

### Cell edits

- `add_onset(row, column)` — always legal; over a sustain it simply ends the previous note early.
- `extend_sustain(row, column)` — legal only when the previous column already sounds. Otherwise
  raises `EditError` with a sentence the grid UI can show verbatim: *"Cannot sustain Do-4 at
  column 5: nothing is sounding at column 4. Place an onset first."*
- `delete_note(row, column)` — **clicking anywhere in a note deletes the whole note**: the run is
  traced back to its onset and forward through its chained sustains. Clicking silence is a **no-op,
  not an error** — the grid should not punish a missed click.
- `delete_cells(cells)` — the shift-multi-select case.
- `set_cell(row, column, value)` — dispatches on `1` / `-1` / `0`.

## Errors found and how they were solved

1. **`extend_sustain` needed to be the only strict edit.** The first sketch validated every edit
   with `validate_strict` afterwards, which turns "you clicked the wrong cell" into a stack trace
   listing unrelated violations. Now each primitive enforces its *own* precondition and produces a
   targeted message; `EditError` is a `ValueError` subclass so callers can still catch broadly.
2. **Seam handling.** Insertion, deletion and replacement all create seams where a sustain can lose
   its onset. Rather than special-casing each, all three route through `validator.normalize`, so
   the promote-to-onset policy stays in one place (the decision recorded in the Task 2.1.2 report).
3. **`np.zeros_like` for the transposition target** was necessary: building the shifted grid by
   slicing alone leaves the vacated rows holding stale data.

## Deviations from the task file

- Added `fit_to_width`, `append_silence`, `delete_cells`, `set_cell`, `hand`-aware
  `transpose_hands`, and the `TranspositionReport`/`EditError` types.
- The task listed `slice(matrix, f_start, f_end)`; named `slice_range` to avoid shadowing the
  builtin.
- `delete_note` on silence is a no-op rather than an error (UX call, documented in the docstring).

## Verification

```
pytest tests/test_matrix_ops.py        # 39 passed
pytest tests/test_matrix_pipeline.py   # 11 passed  (new, see below)
pytest                                 # 304 passed overall
mypy, flake8, black                    # clean
```

Per-operation tests including the rejection cases the task asks for: sustain-over-silence,
sustain-in-column-0, out-of-range rows and columns, a foreign cell value, bad frame ranges, a
too-fine figure insertion, `repeats < 1`. Plus non-mutation and post-edit validity for every
primitive.

## Epic 2 exit criteria — `tests/test_matrix_pipeline.py`

The epic's exit criteria asked for the full chain callable as pure functions with round-trip tests,
so this task also adds an end-to-end suite:

- **raw -> collapsed -> clean -> two-hands** runs end to end, each step carrying the right
  `processing_step`, every intermediate structurally valid, and the piece's wall-clock duration
  unchanged throughout.
- Hands stay aligned and recombine to the clean matrix.
- The notation-spec eight-frame example survives the chain with every struck note intact.
- Four repeated `*Re-4` strikes stay separate notes.
- A pedal bass under a melody is long after collapsing and short after cleaning — the clean step's
  whole purpose, shown on the real chain.
- Any granularity recomputes from the same raw matrix (semicorchea / corchea / negra).
- **Performance**: a random 88 x 9600 semifusa matrix — five minutes at 120 BPM — through the whole
  pipeline to negra in well under the 1 s the test allows (single-digit milliseconds in practice).
- The whole chain round-trips through `.npz` storage, and the envelope survives it.

### One finding worth recording

`test_a_held_bass_under_a_melody_ends_up_short` was originally authored with the **text notation**
and failed: the text parser applies its own onset rule at parse time, so it *cannot express* a
pedal note that genuinely keeps sounding under a melody. That state only comes from a transcribed
recording — which is precisely the case Appendix B exists for. The test now authors the grid
directly, and says so in its docstring. Anyone writing Epic 4 tests should know the text notation
is not a faithful stand-in for transcription output.

## Manual trial for the supervisor

```bash
cd aitu-backend && uv run python -c "
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.ops import add_onset, delete_note, insert_figure, transpose
from aitu_backend.matrix.text_notation import sequence_to_sparse_payload
m = PianoMatrix.from_coo_payload(sequence_to_sparse_payload(['*Do-4','Do-4','*Re-4','*Mi-4']),
                                 granularity='semicorchea', tempo_bpm=60)
print(transpose(m, 2).describe())                      # +2 semitones, nothing lost
print(transpose(m, 60).describe())                     # cells fell off the keyboard (...)
print(insert_figure(m, 2, 'negra').frame_count)        # 8  (4 columns of rest inserted)
print(delete_note(m, 39, 1).grid[39].tolist())         # [0, 0, 0, 0]  — whole note removed
print(add_onset(m, 41, 0).grid[41].tolist())           # [1, 0, 1, 0]
"
```

The transposition preview (Story 9.4.2) is the first UI that surfaces `TranspositionReport` —
please check the wording of `describe()` reads well when you get there.

## For the next worker

- **Story 7.4 (cell editing)**: `add_onset` / `extend_sustain` / `delete_note` / `delete_cells` are
  your primitives. Catch `EditError` and show `str(exc)` — the messages are written to be shown.
- **Epic 11 (range editing)**: `replace_range` already enforces the exact-width rule; build the
  staged session around it rather than re-implementing the fit.
- **Story 9.6 (cut measure)**: `insert_figure`, and let the `ValueError` for a too-fine figure
  drive the dropdown's disabled options.
- Epic 2 is complete. The engine is pure functions over `PianoMatrix` — Epic 4 wires it to audio.
