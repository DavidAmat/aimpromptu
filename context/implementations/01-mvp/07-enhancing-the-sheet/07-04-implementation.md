# 07-04 — Task 9, more things: implementation report

Brief: `07-01-new-enchancements-v1.md`, task **9**. Context: `07-00-context.md`.
Predecessors: `07-01-implementation.md` (tasks 1–6), `07-02-implementation.md` (tasks 7–8),
`07-03-implementation.md` (task 6B).

All three items delivered. Nothing in the brief had to be built differently from the words of it.
Two things reported afterwards are in §7: clicking a bracket no longer marks the frames under it,
and the reason Save was failing.

Package version: `@aimpromptu/grid-notation` **0.40.0 → 0.42.0**, rebuilt.

---

## 1. What the brief asked for, and where each piece landed

| Asked | Where it is |
|---|---|
| **Remove decorative notes** as a pill next to **Show piano** | `RhythmPage.tsx`, the chip row above the sheet |
| A button on the note toolbox that shifts the selection to the frames it covers | `ToolboxDialog.headerAction`, `RhythmPage.selectRangeOfNotes` |
| The same in reverse, so the two selections toggle | `RhythmPage.selectNotesUnderRange`, `notesUnderRange` |
| A dragged octave tip that says where it is | `annotations/draw-ottavas.ts`: `.grid-ottava-drag-edge` and its label |
| Helper vertical lines at the frames around it | `.grid-ottava-drag-guide` |
| The multi-line band the purple frame selector draws, in another colour | `.grid-ottava-drag-band`, one per line, in amber |

---

## 2. The decorative-notes pill

Moved, and nothing else about it changed: the same chip, the same tooltip, the same
`score.decorativeDropped` caption travelling with it. It now sits between **Zoom** and **Show
piano**, which puts the three chips that change *what the page shows you* together at the end of the
row and leaves the key, the two spacing sliders and the `8va` proposal — which change the reading —
in front of them.

---

## 3. The two selections, and the button in each title bar

### 3.1 The gesture

`ToolboxDialog` gained `headerAction`: one control in the title bar, to the left of the close
button. It is in the bar rather than in the body because everything in the body of either panel
edits the piece, and this edits only what is picked.

- **Note toolbox → Select frames.** The stretch from the first picked column to the last, whichever
  staff the notes are on. `toColumn` is the last picked column **plus one**, because every range on
  this page is half-open — a stretch ending at the column its last note begins in would not contain
  that note.
- **Frames toolbox → Select notes.** Every note that *begins* inside the stretch, on the staves
  **Applies to** names. Disabled, with a tooltip saying which of the two it is, when the stretch
  holds no such note.

**Which hand travels with the selection.** Notes all on one hand arrive with that hand's pill
already pressed, because a reader who picked only left-hand notes is about to do something to the
left hand; notes on both leave the scope at **Both**. Going the other way the scope is dropped,
since the noteheads themselves now say which staff this is about and a scope left behind would
narrow the *next* stretch the reader marks.

### 3.2 A note is in a stretch when it *begins* in it

The one real decision here. A note struck before the stretch and still sounding through it is not
in it — the same way it is not in that stretch's beam and does not take its figure from it. A
column is a note's address everywhere else on this page (`hand:startFrame:row`), and two different
answers to "which notes are these columns" would be a second opinion about the same music.

### 3.3 The selection is made through the renderer, not written into state

`sheetRenderer.setSelection(keys)` and `clearSelection()`. The renderer owns which noteheads are
picked — `RhythmPage` only mirrors what it is told — and both calls report straight back through the
same `onSelectionChange` a click does. So the far panel opens, is placed beside the notes and takes
the recording to them exactly as if the reader had clicked, with no second code path to keep in step
with the first. Unknown keys are pruned by the renderer, so a hidden note can never be selected.

**Neither direction raises `clearedAt`.** That is the page's *drop everything picked*, and it clears
the stretch **and** the noteheads — precisely one half too much here, and it would wipe the selection
the button had just handed over. Each side is closed by hand instead.

### 3.4 One thing in `TimeScoreView` had to change for it to be true

The effect that keeps the marked stretch on the drawing only ever *set* it:

```ts
if (selectedRange) renderer.current?.setSelectedRange(selectedRange);
```

So dropping the stretch left its purple band painted until something raised `clearSelectionsAt` —
which is exactly what this feature must not do. It now passes `selectedRange ?? undefined`, so a
host that asks for no stretch gets none. The two range handles were already correct: they are placed
from `latestRange.current`, which was assigned unconditionally on the line above.

This also fixes the same defect for any other caller that drops the range without clearing
everything; nothing else in the app does today.

---

## 4. Holding a tip of an octave bracket

### 4.1 What was wrong

The drag itself was exact — 07-03 §3.3 — and invisible past the end of the line. The ink it moves
is the bracket's own fragment, which is clipped to its own system, so a tip pulled towards the line
below moved nothing a reader could see, and nothing on the page said which column it would drop
into. The reader reported both halves: no sense of where the dragged end is, and no sense of the
frames it is passing over.

### 4.2 What is drawn now

While a tip is held, and only then, a `.grid-ottava-drag` group is put **over the whole drawing**:

| Element | What it says |
|---|---|
| `.grid-ottava-drag-band` | The stretch the bracket would cover, one box per line it crosses |
| `.grid-ottava-drag-edge` | The column the held end would drop into, on the line it landed on |
| `.grid-ottava-drag-label` | That column's number, above the line |
| `.grid-ottava-drag-guide` | The columns either side of it, so a small movement is a visible step |

It is taken down on pointer-up, on pointer-cancel, and never drawn on hover. That last part is not
taste: a permanent or hover-triggered outline around a bracket has been reported and removed twice
already on this page (the corner marks' preview in 07-01, and the reason the band itself is
transparent until the pointer is on it in 07-03).

**Amber, not the selection purple.** A reader dragging a bracket very often has a stretch of columns
marked at the same time, and that band is `palette.selection`; two purple bands over one passage,
one of them moving, read as one selection. The brief asked for another colour and there is a reason
for it beyond variety.

**The band is the multi-line one the brief pointed at.** `drawFrameRuler` paints a marked stretch
per system, so it follows the music round the wrap; this does the same thing with the same shape, in
the same band the playhead and the range handles occupy.

### 4.3 How it knows where anything is

Two more lazy lookups on `DrawOttavasOptions`, filled in by `drawGrandStaff` exactly the way
`frameAtPoint` already was, and for the same reason — at the moment a bracket on line 1 is drawn, the
lines below it have not been laid out, and nobody can touch a tip until they all have:

```ts
spanOnPage: (from, to) => (laidOut ? spanOnPage(laidOut, from, to) : []),
frameOnPage: (frame) => (laidOut ? placeCursor(laidOut, frame) : undefined),
```

`spanOnPage(render, fromColumn, toColumn)` is **new**, and it lives in `player/playback-cursor.ts`
beside `placeCursor` and `frameAtPoint` deliberately. It has to agree with the cursor about where a
line begins and how tall it is down to the pixel — the playhead, the two range handles and this band
are read against each other on one screen — and a second reckoning of "how tall is a system" would
drift the first time either was touched. It is half-open like every other column range here, and it
returns nothing at all for an empty or inverted span.

A caller that hands over neither lookup — a printed page, a bare staff — gets exactly what it got
before: the fragment's own ink moves and nothing is painted over the page.

### 4.4 Three smaller decisions inside it

**The helper lines stop at the line the end landed on.** `GUIDE_REACH` is 5 columns either side, and
any column that resolves to another system is dropped rather than drawn on the far line: a helper
line on a line the reader is not pointing at is a line about music they are not aiming for. Near a
wrap that simply means fewer of them, which is truthful.

**Two helper lines are never closer than `GUIDE_MIN_GAP` (5 px).** Columns collapse to slivers
through silence, and a line per column there paints a solid block that says nothing. The end's own
line is exempt: it is the answer, so it is always drawn.

**A one-column band is widened to 2 px and not moved.** A stretch that narrow in a silence is a
sliver, and a sliver reads as nothing at all; widening it keeps it visible without moving it off the
column it is about.

---

## 5. Tests

### The package

**`tests/ottava-editing.test.ts`, 7 new tests** (20 → 27): nothing is drawn until a tip is pressed;
pressing paints the band and names the column the end is on; moving the tip moves the line and
renames it; the helper lines are around the end and only near it; a stretch pulled onto the line
below is painted on both lines; the band is not the colour a marked stretch is; all of it is taken
down when the tip is let go — that last one asserts the overlay **is** there mid-drag first, so it is
about the overlay going rather than about it never having been drawn.

**Proven against the pre-change state** by taking the two lines that hand the page to the bracket
out of `draw-grand-staff.ts`, which is byte-for-byte what a bracket saw before this task — with both
lookups absent the overlay is never built:

| | |
|---|---|
| **6 failed** | everything the drag now shows |
| **1 passed** | the control: *shows nothing at all until a tip is pressed* |

The other 20 tests in the file, and the whole rest of the suite, passed in both states.

**`tests/player.test.ts`, 3 new tests** for `spanOnPage` itself: one box in the cursor's own band
when the stretch stays on one line, with the right-hand edge at the first column outside it; one box
per line when it crosses a wrap, cut at the boundary; nothing at all for an empty, an inverted or a
`NaN` span.

### The app

**`check-render.mjs`, 8 new checks** (51 → 59), driving the app's own path in jsdom:

- Four on the drag, taken *between* the pointer-move and the pointer-up of the check that was
  already there: the band is painted, the end's line and its label agree and name a column past
  where the bracket ended, the helper lines are drawn, and every piece of it is gone after the drop.
- Four on the selection hand-over: there are notes to hand over, `setSelection` reports them back
  through the callback the buttons rely on, they are marked on the page, and `clearSelection` leaves
  nothing reported and nothing marked.

The two buttons themselves are app-level React with no DOM harness on this page, so what is checked
is the renderer mechanism underneath them — which is the half that can fail silently.

### Results

| Check | Result |
|---|---|
| `vexflow-v2` `vitest` | **498 passed** (53 files) |
| `vexflow-v2` `npm run lint` | clean |
| `vexflow-v2` `tsc -b && tsup` | clean, `dist/` rebuilt at 0.42.0 |
| `aitu-frontend` `npx tsc -b` | clean |
| `aitu-frontend` `npm run lint` | clean |
| `aitu-frontend` `npm run build` | clean |
| `aitu-frontend` `npm run check:render` | **60 passed, 0 failed** |
| `aitu-frontend` `npm run check:history` | every check passed |
| `aitu-frontend` `npm run check:note-names` | **15 passed, 0 failed** |
| `aitu-backend` `pytest` | **906 passed, 1 failed** |

The one failure is the
documented pre-existing one,
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas` — both
that test file and `matrix/hands.py` were already modified in the working tree before this task
started, which `git status` confirms.

---

## 6. Files touched

### `../vexflow-v2` (0.41.0)

| File | Why |
|---|---|
| `player/playback-cursor.ts` | `spanOnPage`, `PageSpan` |
| `annotations/draw-ottavas.ts` (§7.1) | clicking the band picks the bracket instead of reporting a stretch |
| `annotations/draw-ottavas.ts` | `spanOnPage` / `frameOnPage` options, the drag overlay, its colours |
| `renderer/draw-grand-staff.ts` | fills both lookups from the page it is about to return |
| `index.ts` | exports `spanOnPage`, `PageSpan` |
| `tests/ottava-editing.test.ts`, `tests/player.test.ts` | 10 new tests |
| `documentation/03-rendering.md`, `05-annotations.md` | the overlay's DOM and why it is drawn |

### `aitu-frontend`

| File | Why |
|---|---|
| `components/common/ToolboxDialog.tsx` | `headerAction`, kept out of the title bar's drag |
| `pages/playground/RhythmPage.tsx` | the chip moved; `notesUnderRange`, `selectNotesUnderRange`, `selectRangeOfNotes`, both header buttons |
| `components/time/TimeScoreView.tsx` | the marked stretch is cleared as well as set |
| `scripts/check-render.mjs` | nine checks |
| `api/client.ts` | a 422's field and reason in words, in place of raw JSON |

### `aitu-backend`

| File | Why |
|---|---|
| `schemas/rhythm.py` | `StaffGap.gap` floor down to the package's own 24 px |
| `tests/test_saved_rhythm.py` | one new test, proven against the old bound |

### Documentation

`context/frontend/annotations.md` (the hand-over, what the drag shows, what clicking a bracket does),
`documentation/services/backend/rhythm-and-annotations.md` (the corrected bound),
`documentation/services/frontend/components.md`,
`documentation/services/frontend/grid-notation.md`.

---

## 7. Two things reported after the first pass

### 7.1 Clicking the dashed line of an octave also marked the frames

Reported: *whenever I click on a dash line of an octave, it gets the frame selection. It shouldn't.*

07-03 §3.6 passed the band's click straight on to `onRangeMarkerSelect`, which the page answers by
marking the stretch of columns and opening the frames toolbox on it. So one press made **two**
selections: the bracket the reader was reaching for, and a purple band painted over the very thing
they were about to drag.

- `draw-grand-staff.ts` no longer binds `onOttavaSelect` to the marker list. The option stays on
  `DrawOttavasOptions` for a host that wants it; nothing in this app passes one.
- A click on the band now **picks the bracket**: the group takes `is-picked`, and the band and its
  two tips stay lit until the reader picks another bracket or presses anywhere else on the drawing.
  Picked-ness lives in the class rather than in a closure, because a bracket across a line break is
  several fragments and they all have to agree; the release listener is bound once per drawing,
  guarded by an attribute on the SVG, which is rebuilt on every render and so cannot pile up.
- **The corner marks are untouched** and are still the way to the stretch and to the **Octave**
  pill. Nothing lost the way back.

Two tests replaced the one that pinned the old rule: a band click reports no stretch and leaves the
group picked and lit; a picked bracket survives the pointer leaving it and lets go on a press
elsewhere. `check-render.mjs` gained the same check on the app's own path — the page listens for
corner marks there, so *no stretch was asked for* is a real assertion rather than a vacuous one.

Package version: **0.41.0 → 0.42.0**, rebuilt.

### 7.2 Save did nothing, and said nothing

Reported: *I am changing the figures from negras to corcheas, I click Save, and I cannot save it.*

**The cause is a bound in the backend that is tighter than the one the page enforces.**
`SavedRhythm.StaffGap.gap` read `ge=30`, while the handle between two staves clamps at the drawing
package's `MIN_STAFF_GAP` — `MIN_STAFF_GAP_SPACES` (3) × `STAFF_LINE_SPACING` (8) = **24**. So a
reader who tightened one line past 30 px made the **whole reading** unsaveable: every later save of
that piece answered `422` about a field they were not editing, including a figure they had just
renamed. Proved against a copy of the real piece:

```
gap=  24.0 -> 422 Input should be greater than or equal to 30
gap=  28.0 -> 422 Input should be greater than or equal to 30
gap=  30.0 -> 200
```

Fixed to `ge=24`. The ceiling stays at 200, looser than the package's `MAX_STAFF_GAP` of 160,
because this model reads stored files as well as requests and a bound that refuses something already
written takes a reading away from whoever saved it. New test
`test_the_tightest_line_the_page_can_draw_is_saveable`, **proven to fail against the old bound**.

Every other bound was checked for the same trap and they all agree with the page: `annotationScale`
0.5–2 against `gt=0.3, le=2`, `lineSpacing` 0–240, `noteSpacing` 0–48, `spacings.scale` 0.25–4
against `gt=0.2`, `evenSpacings.scale` 0.25–4, the lyric's width and font size exactly.

**Three things about the failure were as bad as the failure.**

1. **It was invisible.** The only Save is on the floating bar since 07-03, and the outcome was
   printed next to the old Save at the foot of the page — past every stave of a long piece. A refused
   save now turns the bar's button red, labels it **Save failed**, and opens an error bar at the
   bottom of the window that stays until it is closed.
2. **A 422 was unreadable.** `readError` printed FastAPI's whole validation list as raw JSON. It now
   says the field and the reason: `staffGaps → 0 → gap: Input should be greater than or equal to 24`.
   That is the whole app's error path, not just this page's.
3. **A failure after the reading was stored lied.** `save()` writes the reading and then takes the
   hidden notes off the recording; a failure in the second call said *could not save this rhythm*
   when the rhythm was already on disk. The two are now separate messages.

And a greyed Save now says why: until a pile of gaps is named there is no reading to save, which a
reader looking at a drawn sheet has no way of guessing.

---

## 8. Still true after this task

**The known issue from 07-01 §11 is unchanged.** `useEditHistory` opens one step per run of the
event loop, so a slider drag still records many steps. Nothing here adds a slider, and neither new
button writes to `SheetEdits` at all — a selection is not an edit, which is also why Command-Z does
not take one back.
