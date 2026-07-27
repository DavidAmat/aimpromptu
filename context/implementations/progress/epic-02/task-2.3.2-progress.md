# Task 2.3.2 — Duration approximation · progress report

Status: **done**. Date: 2026-07-27. **One question for the supervisor at the end — please read it.**

## Summary

`matrix/approximation.py` fits human-played timings onto the matrix grid (Appendix C).

| Function | Role |
|----------|------|
| `approximate_duration(seconds, granularity, bpm, *, max_figures, strict_adjacent)` | -> `DurationFit` |
| `snap_onset(seconds, granularity, bpm, *, tolerance)` | which column an onset belongs to |
| `snap_note(row, start, duration, …)` | -> `SnappedNote` (row, start column, fit) |
| `figure_columns`, `available_figures`, `expressible_columns` | the figure/column tables |

`DurationFit` carries `columns`, `sustain_columns` (what the matrix writer needs),
`figures` (one or two, coarsest first — what Epic 9 needs to draw the ligature),
`seconds`, `error_seconds` and `exact`, plus a `describe()` for logs:
*"negra + semicorchea (5 columns, +0.020 s)"*.

## Reading the appendix — it states its rule two ways

The appendix gives its acceptance test twice, and the two phrasings disagree:

1. *"if the difference in seconds is smaller than the temporal resolution … then we accept it
   (a 1.1 second at semicorchea resolution will be counted as a 1 second)"*
2. *"keep attempting to add a new figure until … if we were to add the minimum figure for that
   temporal resolution, we will distort more the melody than our current approximation"*

Phrasing 1, taken literally, accepts a plain **negra** for 1.23 s (error 0.23 < 0.25) — which the
appendix's **own worked example explicitly rejects** in favour of negra + semicorchea.

Phrasing 2 is the operative rule, and phrasing 1 is a loose paraphrase of it. "Stop when one more
minimum figure would increase the error" *is* **round to the nearest column**. That reproduces both
worked numbers:

| Duration | / 0.25 s | Rounds to | Figures | Appendix says |
|----------|----------|-----------|---------|---------------|
| 1.1 s | 4.4 | 4 columns | negra | "counted as a 1 second" |
| 1.23 s | 4.92 | 5 columns | negra + semicorchea | "1.25 s, 0.02 s closer" |

So the implementation rounds to the nearest column, then expresses that count in at most two
figures. Both readings are documented in the module docstring so no one re-litigates this.

## ⚠️ Contradiction needing your decision: which ligatures are legal?

The sources disagree, and I followed the **acceptance criterion**:

| Source | Says |
|--------|------|
| Appendix C worked example | 1.23 s -> **negra + semicorchea** (skips corchea) |
| Appendix C next paragraph | *"What is not a valid ligature is to have a negra ligated with a semicorchea for example, never do this"* |
| Task file, subtask 2.3.2.2 | *"never ligate non-adjacent figures like negra+semicorchea when corchea exists"* |
| Task file, **Acceptance** | *"1.23 s … -> negra + semicorchea (`1 -1 -1 -1 -1`)"* |

**Implemented**: any two distinct figures, first strictly coarser — so negra + semicorchea is legal
and the acceptance test passes. This is also the musically standard set: it yields every dotted
note (negra + corchea, corchea + semicorchea, blanca + negra) *and* the double-dotted ones.

**If you prefer adjacency-only**, pass `strict_adjacent=True` — the flag exists, is tested, and
restricts the table to dotted notes. Changing the default is a one-word edit plus updating one
test. I did **not** change the plan text, per the rule about not altering requirements
autonomously. Tell me which you want and I will make it the default and fix the task file.

Note the practical cost of adjacency-only: at semicorchea granularity the representable column
counts drop from {1,2,3,4,5,6,8,9,10,12,16,17,18,20,24} to {1,2,3,4,6,8,12,16,24}. A 5-column note
would have to become 4 or 6 — a 25% duration error where 0% was available.

## Design details

- **Non-representable counts fall back to the nearest representable, tie-breaking toward the
  shorter note.** 7 columns needs three figures (4+2+1), so 1.75 s becomes 6 columns, not 8. A note
  that ends early leaves a gap; a note that ends late collides with the next onset.
- **A note can never vanish**: the floor is one column, however short the sample.
- **The longest two-figure note is 24 columns** (redonda + blanca); anything longer clamps there.
  Epic 9 will need ties across barlines for genuinely longer notes.
- `snap_onset` takes a `tolerance` in *fractions of a column* (default `0.5` = nearest boundary).
  Lower values bias onsets later, which is the forgiving setting for a player who rushes. The
  docstring repeats the notation doc's General Note: **this is only as good as the BPM the user
  supplied** — a passage played faster than the stated tempo will drift, and no tolerance fixes it.

## Verification

```
pytest tests/test_matrix_approximation.py   # 42 passed
pytest                                      # 235 passed overall
mypy, flake8, black                         # clean
```

The acceptance case is `test_appendix_c_worked_case`: 1.23 s at 60 BPM / semicorchea ->
5 columns, `(negra, semicorchea)`, 1.25 s, +0.02 s error — i.e. `1 -1 -1 -1 -1`.
A companion test confirms the three candidates the appendix walks past (blanca, negra,
negra + corchea) all have larger error than the chosen fit.

Also covered: the figure/column table at every granularity, the expressible-count set including
which counts are *not* expressible, dotted notes falling out of the pair rule, `strict_adjacent`,
single-figure mode, twelve rounding cases, the sub-column floor, the non-representable fallback,
clamping, tempo scaling, all the onset-snapping cases, tolerance bounds, and an end-to-end
"Do Re Mi Fa Sol as slightly uneven negras" that lands on columns 0/4/8/12/16 with no overlaps.

## Manual trial for the supervisor

This is the task most exposed to how you actually play, so it is worth checking early.

**Record: Do Re Mi Fa Sol as slow negras at 60 BPM, one note per second, no pedal.**
Then, once Epic 4 is wired, transcribe at 60 BPM / semicorchea and check the Matrix tab: each note
should be exactly **4 columns** (one onset + three sustains), starting at columns 0, 4, 8, 12, 16.
If notes come out 3 or 5 columns, the BPM you played at is not the BPM you entered — that is the
sensitivity the General Note warns about, not a bug in this code.

Right now, without the UI:

```bash
cd aitu-backend && uv run python -c "
from aitu_backend.matrix.approximation import approximate_duration, snap_note
print(approximate_duration(1.23, 'semicorchea', 60).describe())  # negra + semicorchea (5 columns, +0.020 s)
print(approximate_duration(1.10, 'semicorchea', 60).describe())  # negra (4 columns, -0.100 s)
print(approximate_duration(1.50, 'semicorchea', 60).describe())  # negra + corchea (6 columns, +0.000 s)
n = snap_note(39, 1.02, 1.23, 'semicorchea', 60)
print(n.start_column, n.fit.columns, n.end_column)               # 4 5 9
"
```

## For the next worker

- **Task 4.2.1 (events to raw matrix)** is the main consumer. Use `snap_note` per transcription
  event, then write `1` at `start_column` and `-1` for `fit.sustain_columns` after it. Run the
  Task 2.1.2 validator on the result.
- The raw matrix is built at **fusa** granularity, so `approximate_duration` there has fusa as its
  finest figure. The user's chosen granularity is reached by *collapsing*, not by approximating
  twice.
- **Epic 9** should read `fit.figures` to draw the ligature rather than re-deriving it from the
  column count — the decomposition is already decided here.
- Overlap is **not** handled here: `snap_note` fits one note in isolation, so two snapped notes in
  the same row can collide. Whoever writes cells must resolve that (Appendix B cleaning then
  handles the musical side).
