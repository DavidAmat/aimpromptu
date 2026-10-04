# Task 14.1.2 — The three defects the documentation pass found · progress

Status: **done** on 2026-09-13.

Task 14.1.1 was markdown only and recorded three defects rather than fixing them, per the prime
directive in `context/00-documentation-instructions.md`. David then asked for them fixed. This is
that work.

All three were found the same way: **reading what a document claimed against what the code does.**
None had a failing test, and two of them had been silently broken for a month.

---

## 1. `make test` did not run at all

```
ERROR tests/test_migration.py
E   ModuleNotFoundError: No module named 'scripts'
```

`tests/test_migration.py` imports `scripts.migrate_to_time_matrix`, `aitu-backend/scripts/` has no
`__init__.py`, and `pyproject.toml` set `pythonpath = ["src"]` only. Collection failed before a
single test ran, so **the command reported nothing at all** — not a failure count, not a pass count.

**Fix.** `pythonpath = ["src", "."]`, with a comment saying why the second entry is load-bearing so
nobody tidies it away.

**Result.** `make test` → **769 passed, 1 failed** in about 15 seconds. The failure,
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas`, is
pre-existing on a clean checkout and was already recorded in the Epic 13 report. It is not touched
here.

---

## 2. Octave brackets were saved and silently dropped

`RhythmPage.save()` sends `ottavas` in the `PUT /time/{uuid}/rhythm` body and `SavedRhythm` in
`api/timeScore.ts` declares the field. The backend's `SavedRhythm` had **no such field**, and
Pydantic's default is to ignore extras — so every bracket was dropped without an error, and
`RhythmPage` reading `found.ottavas ?? []` back always got an empty list.

**Octave brackets did not survive a reload.** No test covered it.

### The fix

An `Ottava` model in `schemas/rhythm.py` — `kind`, `hand`, `fromColumn`, `toColumn`, half-open like
every other range in that file, with the same inverted-range refusal — and an
`ottavas: list[Ottava] | None` field on `SavedRhythm`.

**`kind` is a four-way literal**, not a string: `8va`, `8vb`, `15ma`, `15mb`. Those are the four the
renderer draws, so anything else is a mistake that should be a `422` rather than a bracket that
silently does not appear. The TypeScript side was tightened to the same four, so a typo is now a
compile error rather than a round trip.

### The one decision worth recording

**`null` and `[]` mean different things, and the field is optional so they can.**

`null` is a reading that was never asked the question — saved before brackets were stored — and the
page may still offer its own suggestion. `[]` is a reader who was asked and answered *none*, and the
page must leave it alone. Collapsing them would put brackets back on a page somebody had
deliberately cleared, which is the same class of failure as the one being fixed: a decision quietly
discarded.

`compose.shift_marks` preserves the distinction — a `null` stays `null` through an insertion,
because moving columns does not answer a question nobody was put.

### Which also closes Epic 13's gap

Epic 13 recorded that an insertion leaves brackets where they were, and read that as a design
consequence of ottavas living in renderer state. It was the same missing field. `shift_marks` now
moves them with everything else, and a bracket straddling the insertion point widens rather than
tears, like any other range.

### Tests

Five new, all passing:

- `test_saved_rhythm.py::test_octave_brackets_survive_a_round_trip`
- `test_saved_rhythm.py::test_never_asked_and_asked_none_are_different_answers`
- `test_saved_rhythm.py::test_a_bracket_that_ends_before_it_starts_is_refused`
- `test_compose_live.py::test_an_octave_bracket_moves_with_the_notes_it_is_over`
- `test_compose_live.py::test_never_asked_about_brackets_stays_never_asked`

`marked_rhythm()` in the compose tests gained a bracket, so the existing "marks after an insertion
move" test now counts 7 marks instead of 6 and covers it too.

---

## 3. `npm run check:render` had been broken since P6.9

```
TypeError: This is a 1.x matrix file, written against a beat grid.
```

`scripts/check-render.mjs` still built a `tempoBpm: 60` / `granularity: 'semicorchea'` envelope and
constructed a `GridNotationEditor` — the class the app stopped using. The package's 1.x reader was
deleted in P6.9, so the fixture had been refused ever since.

**This one mattered most.** `check:render` is the project's only guard against a *silent* rendering
failure: a score that draws no noteheads, loses a hand or stops beaming renders a blank-looking page
with no error, and neither typecheck nor lint can see it. That guard had not run for a month, and
nothing said so.

### The fix

Rewritten against the model the app actually uses: a schema 2.0 envelope (`schemaVersion`,
`frameMs`, `matrixProcessingStep`, no tempo and no granularity) drawn by a `GridNotationRenderer`
with `printedFigureFor`, `frameGroup` / `frameMeasure` / `silenceGroupPx`, `beamGroups: true` and
`rests: false` — the same options `TimeScoreView` passes.

**It crosses the figure-name seam rather than skipping it.** The backend names figures in Spanish
and the package in English, and the app maps between them (`VEXFLOW_FIGURE`). The check now names
its figures in Spanish and maps them the same way, so a change on either side of that map is caught.

New assertions beyond the ones restored:

| Assertion | Guards |
|---|---|
| a column is `frameMs` of wall clock | The 2.0 header, in one line |
| the wall-clock length follows from the columns | `durationSeconds` is derived, not supplied |
| **the backend's figures are what get drawn** | The central promise: the renderer draws what it is told and never derives a note value from a column count |
| no rest is drawn | D-16 |
| the lyric is drawn under the staff | The annotation layer reaches the DOM |

### Two things the check itself got wrong first, and what they taught

Worth recording, because both were the check being wrong rather than the code.

**`summary.handSplit` and `summary.timeStepSeconds` do not exist in 2.0.** The summary now reports
`frameMs`, `durationSeconds` and per-hand onset counts. The assertions were rewritten against what
the summary actually carries — which is itself a statement of the model: it reports a column length
and no tempo.

**`GridNotationRenderer.destroy()` does not empty its host.** That was the *editor*, which removes
its own root. The renderer releases its resize observer and leaves the drawing for whoever created
it — which for the app is React unmounting the container. The assertion now pins the real contract.

**Result:** 26 checks, all passing.

---

## Verification

| Command | Result |
|---|---|
| `make test` (backend) | **769 passed**, 1 pre-existing failure |
| `uv run mypy` | No new errors — none in any file changed here |
| `uv run flake8` | Back to its pre-existing four findings |
| `npm run lint` | Clean |
| `npm run build` | Clean |
| `npm run check:render` | **26 passed, 0 failed** |

## One thing to know about the diff

`make format` ran black across the whole package and reformatted **14 files**, most of them
unrelated to this work. The formatting-only churn in files that were clean beforehand has been
reverted, so the change set is the four files these fixes actually needed plus their tests.

The files that were **already** uncommitted when this started — Epic 13's work — kept black's
formatting, because reverting them would have discarded that work and pre-commit applies black to
them at commit time anyway.

## For the next worker

- **The `null` / `[]` distinction on `ottavas` is deliberate.** Making it a plain
  `list[Ottava] = []` would put brackets back on a page somebody cleared.
- **`check:render` mirrors `TimeScoreView` on purpose.** If the view starts passing a new option
  that changes layout, the check should pass it too, or it stops guarding the real path.
- The pre-existing failure in `test_time_score_payload.py` is still open and predates all of this.
