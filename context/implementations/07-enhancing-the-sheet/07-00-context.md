# 07 — Enhancing the sheet: the context every task here starts from

**Read this file first, and read the files it tags with `@`.** It exists so that a brief in this
folder can be one paragraph about the problem, with no time spent hunting the codebase for what the
problem touches.

You are working on **the sheet** — the drawn score on the Playground's **Piano Sheet** tab. Almost
every task in this folder is a change to how that page looks, what a reader can do to it, or how the
notation is engraved.

---

## 1. Read these, in this order

### 1.1 How to work and how to write it up — always

@context/language/communication-implementation-plans.md
@context/09-coding-conventions.md
@context/04-local-development.md

The first one is **not optional**: it fixes the words you use, the shape of every report, and the
`# SUMMARY / # CRITICAL ISSUES / # DECISIONS / # HUMAN INTERVENTION / # HAND OFF` structure of the
walkthrough you finish with. Use the user's own terminology, never a synonym for something they have
already named.

### 1.2 The rules you may not quietly break

@context/implementations/03-time-based-concept/decisions.md
@context/implementations/03-time-based-concept/contract.md

**D-01 … D-34 are frozen.** A task may not reinterpret one. If implementation shows a decision is
wrong, say so in the walkthrough and stop rather than working around it. The contract is the
backend ↔ renderer seam: what is in the score payload and who owns which decision.

The five that come up most on this page: **D-14** a note's printed length is the gap to the next
onset **in the same hand** (so moving or hiding a note renames its neighbours), **D-17** a figure
override changes one glyph and nothing else, **D-22/D-23** one `time → x` map for the whole system
with silence compressed, **D-28** no bars and no metre, **D-34** the reader's beam break beats every
automatic rule.

### 1.3 What the sheet already does

@context/frontend/annotations.md
@context/frontend/rendering.md
@context/frontend/printing.md

`annotations.md` is the catalogue: every editorial decision the page offers, where its control is,
and what it changes. If a brief says "the X button", it is described there. `rendering.md` is why
the page is laid out as it is, and the traps.

### 1.4 The seam to the renderer, and the file-by-file detail

@documentation/services/frontend/grid-notation.md
@documentation/services/backend/rhythm-and-annotations.md
@documentation/services/frontend/components.md

`grid-notation.md` is the most important of the three for a drawing task: every option the app
passes the renderer, why some are driven through setters instead of the build, and the stale-`dist`
trap (§2.3 below). `rhythm-and-annotations.md` is `rhythm.json` field by field — the only things
about a score that are **not** derived.

### 1.5 The code

@aitu-frontend/src/pages/playground/RhythmPage.tsx
@aitu-frontend/src/components/time/TimeScoreView.tsx

These two are where most of the work lands. `RhythmPage` is the page — every control, every piece
of state, the save. `TimeScoreView` is the **one file in the app allowed to import
`@aimpromptu/grid-notation`**; keep it that way.

---

## 2. The six things that catch people out

### 2.1 The figure of a note is the backend's, never the page's

The backend names every printed note from a ladder the reader chose, and the page passes it
straight through `printedFigureFor`. **Nothing in the frontend may work out a note value from how
many columns it covers** — a column is a slice of wall clock and says nothing about note values.

### 2.2 A column is the only safe address

Every mark is keyed by column, because a column never moves while the piece's wall-clock length does
not change. **Never key anything by a line number or a system index**: the score re-wraps to the
window, so "the third line" is different music at another width. This has already been got wrong
once and fixed — see 06's per-line staff gap.

### 2.3 The renderer is a symlink and `dist/` is not built for you

`@aimpromptu/grid-notation` is the sibling checkout `../vexflow-v2`, installed from disk. npm does
**not** build it for you and nothing warns when `dist/` is stale — the browser runs whatever it was
last built from.

```bash
cd ../vexflow-v2 && npm run build
```

After **any** change there. If a documented feature seems missing, check the build before checking
the docs. Bump the package version when you change it, and rebuild.

### 2.4 The renderer is built once, and driven by methods after that

`TimeScoreView` builds a `GridNotationRenderer` in one effect whose dependency list is everything it
draws from. **Anything a reader drags or slides must go through a renderer method in an effect of
its own**, never into that dependency list, or every note on the page is torn down and rebuilt on
every pixel of the drag. The playhead and the two range handles are placed imperatively against the
last render, so anything that re-lays-out has to place them again.

### 2.5 A new edit has three homes, not one

If a task adds something a reader can decide about the sheet, it is not done when it draws. It has
to go into all three or it is a control that silently forgets itself:

1. **`SheetEdits` in `RhythmPage.tsx`**, with a label in `EDIT_LABELS` — that is what makes it
   undoable with Command-Z and what makes **Remove all** clear it.
2. **The save body** in `save()`, and the read-back in the `rhythm()` effect.
3. **`SavedRhythm`** in `aitu-backend/.../schemas/rhythm.py`, with a round-trip test.

Anything held only by the renderer is lost on the reader's next edit, because the renderer is
rebuilt whenever the music or an annotation changes. That is a real bug that has been fixed twice.

### 2.6 The React Compiler is on

Lint **errors**, not warnings, on: reading or writing a ref during render, and manual memoization
whose dependencies it cannot verify. Design state as plain values and reducers. `npm run lint` must
come out clean.

---

## 3. Where things are

### The page and its parts

| File | What it is |
|---|---|
| `aitu-frontend/src/pages/playground/RhythmPage.tsx` | The whole page: the plot, the controls, every edit, the save |
| `aitu-frontend/src/components/time/TimeScoreView.tsx` | The only seam to the renderer |
| `aitu-frontend/src/hooks/useEditHistory.ts` | Undo and redo — one object of edits, a pure reducer |
| `aitu-frontend/src/components/common/ToolboxDialog.tsx` | The draggable panels the two selections open |
| `aitu-frontend/src/components/common/FloatingBar.tsx` | The bar that follows the reader down the page |
| `aitu-frontend/src/components/time/ScorePdfDialog.tsx` | Laying the sheet out on paper |
| `aitu-frontend/src/components/time/ScorePlayer.tsx` | The transport under the sheet |
| `aitu-frontend/src/components/time/PeakPlot.tsx` | The gap histogram the ladder is named from |
| `aitu-frontend/src/components/editing/RangeRerecordPanel.tsx` | Re-record a stretch — writes to the recording |
| `aitu-frontend/src/components/editing/ComposePassagePanel.tsx` | Put a passage in — writes to the recording |
| `aitu-frontend/src/music/renderOverrides.ts` | Note keys (`hand:startFrame:row`) and the page edits folded into the matrix |
| `aitu-frontend/src/api/timeScore.ts` | Every `/time` call and the payload types |
| `aitu-frontend/src/ui/palette.ts` | **The only place a colour may come from.** No hex literal in a component |

### The renderer, in `../vexflow-v2/src/`

| File | What it decides |
|---|---|
| `renderer/grid-notation-renderer.ts` | The public class: options, state, every setter |
| `renderer/draw-grand-staff.ts` | System layout, the gaps, what is drawn per line |
| `notation/grand-staff.ts` | One system: the brace, the two staves, the padding, the staff-gap handle |
| `notation/draw-music.ts` | Noteheads, stems, beams, ledger lines |
| `notation/pitch.ts`, `staff.ts`, `spacing.ts` | Staff steps, glyph metrics, the spacing constants |
| `grid/frame-grid.ts` | **The `time → x` map.** The one horizontal source of truth |
| `layout/system-layout.ts` | Where the music wraps |
| `annotations/` | Ottavas, lyrics, fingering, grace notes, cue size, the corner marks, and `suggest-ottavas.ts` |
| `ruler/frame-ruler.ts` | The column numbers and the dashed time lines |
| `print/render-pages.ts`, `print/paginate.ts` | The same music, on paper |
| `theme/palette.ts` | The package's own colours |

Its own client documentation is `../vexflow-v2/documentation/`, seven numbered files —
`03-rendering.md` and `05-annotations.md` are the two worth opening for a drawing task.

### The backend, when a change needs storing

| File | What it is |
|---|---|
| `aitu-backend/src/aitu_backend/schemas/rhythm.py` | `SavedRhythm` — everything a reader decided |
| `aitu-backend/src/aitu_backend/schemas/time_matrix.py` | The score payload, `FigureOverride`, `BeamBreak` |
| `aitu-backend/src/aitu_backend/api/time_score.py` | `/time/*` — peaks, ladder, score, hands, removed, trills, rhythm |
| `aitu-backend/src/aitu_backend/matrix/ladder.py`, `peaks.py`, `passages.py` | Naming figures from a ladder |
| `aitu-backend/tests/test_saved_rhythm.py` | Where a new stored field is pinned |

**A wire field is camelCase in JSON and snake_case in Python**, via `Field(alias=...)`. Build models
with snake_case kwargs.

---

## 4. Before you say you are done

```bash
# The app
cd aitu-frontend
npx tsc -b            # typecheck
npm run lint          # must be clean — errors AND warnings
npm run build
npm run check:render  # draws a real score headlessly in jsdom
npm run check:history # the undo reducer
npm run check:note-names  # what the note toolbox calls a note, against how the sheet spells it

# The renderer, after any change there
cd ../../vexflow-v2
npx vitest run --exclude "_to_delete/**"
npm run build         # or dist/ is stale and your change does nothing

# The backend, if you touched it
cd ../aimpromptu/aitu-backend
uv run pytest -p no:warnings
```

**Two failures are pre-existing** and are not yours: `make lint` on the backend reports
`events_to_matrix.py:68 E402`, and `pytest` fails
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas` — the
latter is documented as pre-existing in `04-local-development.md`. Confirm rather than assume: check
`git status` shows the file unmodified.

**A notation renderer fails silently at layout time.** A wrong option name throws and you see it; a
score that draws no noteheads, loses a hand or stops beaming renders a blank-looking page with no
error at all, and neither typecheck nor lint can see it. That is what `check:render` is for, and why
a geometry change should get a test that you have **proven fails against the pre-change source**
(`git stash push <file>`, run, `git stash pop`).

To see it in a browser:

```bash
make serve            # from the repo root; frontend 5173, backend 8765
rm -rf aitu-frontend/node_modules/.vite   # after rebuilding the package
make stop
```

Then **Playground → Piano Sheet**, pick a transcribed piece, name a gap, **Write the sheet**.
`classical-mix` and `even-and-swung` are short hand-written demo pieces where the right answer is
known; `scripts/make_demo_pieces.py` rebuilds them.

---

## 5. What this folder is, and what came before it

Implementation **06** is the immediate predecessor and covers the same page. Read its report before
changing anything it touched — undo and redo, the space between lines, the per-line spread, the
octave bracket, the corner marks:

@context/implementations/06-varied-implementations/06-plan.md
@context/implementations/06-varied-implementations/06-phase-1-implementation.md
@context/implementations/06-varied-implementations/06-phase-2-implementation.md

Section 6 onward of the second phase report is a list of things that looked right and were not, each
with the measurement that showed it. It is the best short guide to how this page goes wrong. The
first phase report is how undo works, which §2.5 above says every new edit has to join.

The wider map, if a task reaches past the sheet:

- @context/implementations/README.md — every piece of planned work, numbered
- @context/00-index.md — every context file
- @context/frontend/README.md — the app's sections and what each is for
- @context/backend/time-model.md — why a column is a slice of wall clock

### House style for this folder

One brief per task, and the files it produces go beside this one:

| File | What it is |
|---|---|
| `07-<n>-prompt.md` | The brief, in the user's own words |
| `07-<n>-plan.md` | The plan, when the task is big enough to need one |
| `07-<n>-implementation.md` | The technical report: what changed, what was measured, what was proven |

Small tasks do not need a plan. Every task needs the walkthrough, in the structure
`communication-implementation-plans.md` sets, and every task that changes geometry needs a test that
has been proven to fail without the change.
