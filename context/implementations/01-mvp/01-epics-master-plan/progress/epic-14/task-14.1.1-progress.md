# Task 14.1.1 — Final documentation · progress

Status: **done** on 2026-09-13. All four subtasks.

Markdown only. **No application code was changed**, per the prime directive in
`context/00-documentation-instructions.md`.

**Three defects were found by doing this work** and none of them is fixed *here*, because fixing
them is a code change. Each is recorded as an open question at the end with the exact fix.

> **All three were fixed later the same day**, at David's request, in
> [`task-14.1.2-progress.md`](task-14.1.2-progress.md). The open questions below are kept as
> written: they are the record of what a documentation pass found, and the fixes are worth reading
> against them.

1. `make test` does not run at all.
2. Octave brackets are saved and silently dropped — they do not survive a reload.
3. `npm run check:render`, the only guard against a silent rendering failure, has been broken for a
   month.

---

## What was wrong

The documentation described a different app. Not in details — in the model.

`00-project-complete-overview.md`, the file a new reader is told to start at, opened with "AImpromptu
turns a **custom text music notation** into rendered **sheet music**" and described a VexFlow
rendering pipeline through `matrixToNotation.ts` and `PianoSheet.tsx`. None of those files exist.
`endpoints.md` documented three routes — `/health`, `/scores`, `/sequence` — when the app answers
**sixty-three**. `time-matrix.md`, the schema-2.0 reference, was still marked **"Status: stub.
Nothing in the pipeline builds a time matrix yet"** from Phase 0, four months and one whole refactor
after that stopped being true.

A reader following the documentation as written would have concluded that the product is a text
editor with a music renderer attached, and would have gone looking for modules deleted in P4.2.

---

## 14.1.1.1 — The detail tree

`documentation/services/` rewritten against the code.

**Rewritten:**

| File | What it says now |
|---|---|
| `backend/time-matrix.md` | Un-stubbed. Every schema 2.0 model field by field, with the reason each field exists |
| `backend/endpoints.md` | All sixty-three routes in one table, then detail on the ones carrying the model |
| `backend/paths-and-data.md` | The whole storage tree, `v<N>_f<frameMs>`, staging, history, the scripts |
| `backend/transcription-pipeline.md` | The wall-clock order; isochrony, collapse and the tempo map removed |
| `frontend/components.md` | The real component tree; the `components/notation/` and `matrix/` folders are gone |
| `frontend/grid-notation.md` | The current seam. `GridScore`, `NotationPage`, `/notation/*` and merge-onsets were all still documented as live |

**New**, because these features had no detail file at all:

| File | Covers |
|---|---|
| `backend/events-to-sheet.md` | The derivation path: one stored file to a drawn staff, and **why each step is where it is** |
| `backend/rhythm-and-annotations.md` | `rhythm.json` — Epic 12's home, and the only non-derivable state in the product |
| `backend/editing-and-compose.md` | Epics 11 and 13: the splice rule, and the one place length may change |

**Scoped rather than rewritten:** `schemas.md` and `sequence-logic.md` describe the text-notation
MVP, which still runs correctly. Both now open by saying so and pointing at the wall-clock path, and
their module paths were corrected (`sequence.py` → `matrix/text_notation.py`, `schemas.py` →
`schemas/score.py`).

`hand-inference-second-pass.md` was already current and was left alone.

### The decision worth recording

`events-to-sheet.md` is a file the task did not ask for by name, and it is the one I would keep if
only one survived. The endpoint and schema references say *what* the shapes are; nothing said **why
the artifact filter runs before the leakage filter**, or why chord grouping is on raw times, or why
the hand split is before any measurement. Each of those orderings was arrived at by fixing a real
defect, and each is silently re-breakable. They were in module docstrings and commit messages and
nowhere a reader would look.

---

## 14.1.1.2 — The context overviews

**Rewritten:** `00-project-complete-overview.md`, `01-project.md`, `03-services-overview.md`,
`07-database.md`, `00-index.md`, `backend/README.md`, `backend/api.md`, `frontend/README.md`, the
root `README.md`, and both service READMEs.

**Updated:** `02-tech-stack.md` (renderer 0.15.x → 0.32.0, the onset threshold, the time-model row),
`04-local-development.md` (the root `make serve`, demo pieces, the renderer rebuild, a real
troubleshooting table), `09-coding-conventions.md`, `00-documentation-instructions.md`.

**New:** `backend/time-model.md`, `backend/editing.md`, `frontend/pages.md`, `frontend/rendering.md`,
`frontend/annotations.md`.

`backend/time-model.md` is the load-bearing one. The wall-clock model was explained in full only
inside the closed refactor folder, which a reader has no reason to open. It is now a first-class
context file and `00-index.md` tells a new reader to read it second.

### Banners: what I did with each

The task said not to leave a banner as the permanent answer. Four had one.

| Document | Decision | Why |
|---|---|---|
| `music/notation-logic/01-matrix-notation-logic.md` | **Archived** | Obsolete model. Appendix B (sustains) is still in force and now says so from `archive/superseded/README.md` |
| `music/notation-logic/03-editing-logic.md` | **Archived** | Describes a screen deleted in P4.2 |
| `music/notation-logic/02-notation-spec.md` | **Rewritten** | Not obsolete, *narrow*. The banner became a scope statement: it owns `POST /sequence`, plus the sparse-COO wire format and the 88-key order, which every matrix still uses |
| `music/transcription-quality.md` | **Rewritten** | Layers 1–3 hold. §4 is now "the layer that was removed", carrying the measurement that ended it and a table of what answers each of its two open problems |

Also archived, with no banner but no remaining truth: `frontend/app-shell.md`,
`loaded-scores.md`, `compose-panel.md`, `rendering-pipeline.md`.

`context/archive/superseded/README.md` is new and maps every archived file to where its current
answer lives, so archiving does not lose a reader.

### Dead links fixed

`context/shared/` did not exist; `00-index.md` and six other files linked into it. The notation
contract was linked as `02-notation-spec.md.md` in four places. Both corrected everywhere.

---

## 14.1.1.3 — The gap after the plan closed

Seven commits between 2026-08-10 and 2026-08-12 had no reports. Six now do, in
[`progress/plan-resume/`](../plan-resume/README.md); the seventh, the hand-inference second pass, was
already documented.

The reports are reconstructed from the commits, which in this repository carry the reasoning as well
as the change. Where a commit recorded a browser measurement, it is quoted rather than summarised.

**`user-reviews.md` and `CLOSURE.md` corrected.** Both were written on the morning of 2026-08-10 and
described the app as it stood that morning; the work restarted the same afternoon. Between them they
told a reader that there is no piano-roll view and no falling-notes view, that the Playground has two
tabs, and that a mid-piece key change cannot be stored. All three had been wrong for a month.

- `user-reviews.md` gains steps 16–20 covering the two visual views, note deletion, range editing,
  composing, annotations and the library, and its two closing tables are rewritten.
- `CLOSURE.md` §3 is corrected **with the wrong sentence struck through rather than deleted**,
  because removing it would hide that the document was wrong rather than that the app changed. A new
  §8 says what actually happened next.

---

## 14.1.1.4 — Closing the journal

[`progress/RETROSPECTIVE.md`](../RETROSPECTIVE.md). What the fourteen epics produced, what the
journal got right, what it got wrong, and what to carry forward. The checklists are untouched — they
stay as the historical record.

---

## Acceptance

> *The index is complete, every documented command runs, and no document mentions a BPM input, a
> granularity choice or the Matrix tab as if they existed.*

**The index is complete.** `00-index.md` lists every file in `context/` and `documentation/`, and
every link in it resolves.

**No document mentions a BPM input, a granularity choice or the Matrix tab as if they existed.**
Checked by grep across `context/` and `documentation/`. What remains are statements *that they are
gone*, the archive (which is labelled as history), and the passage header's printed BPM equivalent —
which is text beside the millisecond value, not an input.

**Every documented command was run.** Two do not work, and both are now documented as broken rather
than quietly left wrong:

| Command | Result |
|---|---|
| `make serve`, `make stop`, `make status`, `make logs` | Work |
| `uv sync`, `uv run python -m uvicorn …` | Work — the app imports and answers |
| `PYTHONPATH=. uv run pytest` | 764 passed, 1 pre-existing failure, ~13 s |
| **`make test`** | **Fails at collection.** See open question 1 |
| `uv run flake8`, `uv run black`, `uv run mypy` | Run. flake8 reports four findings on uncommitted work that was already in the tree at the start of this task; not touched, being code |
| `npm install`, `npm run dev`, `npm run build`, `npm run lint` | Work. Lint is clean |
| **`npm run check:render`** | **Fails.** See open question 3 |

---

## Open questions — three things needing a code change

Neither was fixed here. A documentation pass does not change application code; both are recorded
where a reader will meet them.

### 1. `make test` does not run

```
ERROR tests/test_migration.py
E   ModuleNotFoundError: No module named 'scripts'
```

`tests/test_migration.py` imports `scripts.migrate_to_time_matrix`, `aitu-backend/scripts/` has no
`__init__.py`, and `pyproject.toml` sets `pythonpath = ["src"]` only. Collection fails before any
test runs, so `make test` reports nothing at all.

**The fix is one line:** `pythonpath = ["src", "."]` in `[tool.pytest.ini_options]`.

With `PYTHONPATH=.` the suite is **764 passed, 1 failed** in about 13 seconds. The failure,
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas`, is
pre-existing on a clean checkout and was already recorded in the Epic 13 report.

The working invocation is documented in `04-local-development.md`, `transcription-pipeline.md` and
`aitu-backend/README.md`.

### 2. Octave brackets are saved and silently dropped

Found by reading the frontend's save body against the backend's model.

`RhythmPage.save()` sends `ottavas` in the `PUT /time/{uuid}/rhythm` body, and `SavedRhythm` in
`api/timeScore.ts` declares the field. The backend's `SavedRhythm` has **no such field**, and
Pydantic's default is to ignore extras. So they are dropped without an error, and
`RhythmPage` reading `found.ottavas ?? []` back always gets an empty list.

**Octave brackets do not survive a reload.** Verified:

```python
from aitu_backend.schemas.rhythm import SavedRhythm
r = SavedRhythm.model_validate({"anchorMs": 480,
        "ottavas": [{"kind": "8va", "hand": "right", "fromColumn": 0, "toColumn": 10}]})
r.model_dump(by_alias=True).get("ottavas")   # -> None
```

No test covers it. The Epic 13 report knew half of this — it notes that ottavas are not in backend
`SavedRhythm` and so are not shifted by an insertion — but read that as a design choice rather than
a missing field.

**The fix:** an `Ottava` model and an `ottavas: list[Ottava]` field on `SavedRhythm`, then an entry
in `compose.shift_marks` so an insertion moves brackets with everything else. One fix closes both.

Recorded in `rhythm-and-annotations.md`, `editing-and-compose.md`, `grid-notation.md`,
`frontend/annotations.md` and `user-reviews.md`.

### 3. `npm run check:render` has been broken for a month

```
TypeError: This is a 1.x matrix file, written against a beat grid. It cannot be
converted here, because a wall-clock matrix is built from the recorded onset times
and this file does not carry them.
```

`aitu-frontend/scripts/check-render.mjs` still builds a 1.x envelope — `tempoBpm: 60`,
`granularity: 'semicorchea'` — and constructs a `GridNotationEditor`, the class the app stopped
using. The package's 1.x reader was deleted in P6.9, so the fixture has been rejected ever since.

**This one matters more than it looks.** `check:render` is the project's only guard against a
*silent* rendering failure: a score that draws no noteheads, loses a hand or stops beaming renders a
blank-looking page with no error, and neither typecheck nor lint can see it. That guard has not run
for a month, and nothing said so — the script exits without a non-zero status the eye catches in a
chained command.

**The fix:** replace the fixture with a 2.0 envelope (`frameMs`, `matrixProcessingStep`, no tempo and
no granularity), construct `GridNotationRenderer` rather than `GridNotationEditor`, and pass
`printedFigureFor` — the assertions themselves about noteheads, hands and beams still stand.

Documented as broken in `04-local-development.md`, `context/frontend/rendering.md`,
`components.md`, `grid-notation.md` and `aitu-frontend/README.md`.

---

## For the next worker

- **`00-index.md` is the contract.** A new file that is not in it is a file nobody will find. The
  rule is in `00-documentation-instructions.md` and it was not being followed.
- **`backend/time-model.md` is the file to send a newcomer to**, after the overview. Everything else
  assumes it.
- **`events-to-sheet.md` holds the orderings that are silently re-breakable.** If you move a step in
  the pipeline, that file says what breaks.
- **Archiving beats a banner.** A banner asks every future reader to do the same triage. Moving the
  file and writing one line about where the truth went does it once.
- **Fix `check:render` before trusting any rendering change.** It is the only thing standing between
  a layout regression and nobody noticing, and it is not currently standing there.
- The renderer's own documentation lives in the sibling `vexflow-v2` checkout under
  `documentation/`, not here, and was out of scope for this task.

## One side effect worth naming

Running `uv run pytest` and `uv run flake8` **rewrote `aitu-backend/uv.lock`**. Not a change this
task authored: `pyproject.toml` already carried an uncommitted yt-dlp floor bump
(`>=2026.7.4` → `>=2026.8.19`, because every earlier build picks a YouTube player client that now
answers `403`), and `uv run` re-resolved the lock to match it, which also shuffled some CUDA
platform markers. The dependency decision was already made; `uv run` only wrote it down.

`02-tech-stack.md` now records the new floor and its reason, since that file claims to state locked
versions.

## How this was checked, not asserted

- **Links:** a script walked every relative markdown link in `context/`, `documentation/` and the
  three READMEs — 291 files. It found 27 broken, including six dead links into a `context/shared/`
  folder that does not exist. **Now zero.**
- **Routes:** the endpoint table was generated from `app.routes` on the live FastAPI app, not read
  off the source.
- **Schemas:** every field table was read from the Pydantic model, and the ottava defect was found
  by running the round trip.
- **Vocabulary:** grep for `bpm`, `granularit`, `tempo` and `matrix tab` across every live document.
  Every survivor is either a statement that the thing is gone, the passage header's printed BPM
  equivalent, or a scoped text-notation MVP page that says so at the top.
- **Commands:** each one run, with the result in the table above.
