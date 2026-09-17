# 06 — Phase 2: the space between lines

Technical report. The plan is [`06-plan.md`](06-plan.md), the status lookup is
[`06-checklist.md`](06-checklist.md).

## What shipped

| File | Change |
|---|---|
| `vexflow-v2/src/renderer/draw-grand-staff.ts` | `SYSTEM_ROOM`, `MIN_SYSTEM_GAP`, `MAX_SYSTEM_GAP` and `resolveSystemGap` beside the existing `SYSTEM_GAP` |
| `vexflow-v2/src/renderer/grid-notation-renderer.ts` | `systemGap` on the options and on the state; `setSystemGap`; passed to `drawGrandStaff` and to `renderPages` |
| `vexflow-v2/src/annotations/draw-range-markers.ts` | The corner marks measured from the staves, and the lanes tightened — section 6.1 |
| `vexflow-v2/src/annotations/draw-ottavas.ts` | The bracket measured from the notes it covers — section 7 |
| `vexflow-v2/tests/ottava-span.test.ts` | **New.** Four assertions |
| `vexflow-v2/tests/staff-gap-per-line.test.ts` | **New.** Five assertions — section 8 |
| `vexflow-v2/src/annotations/suggest-ottavas.ts` | An open bracket is what a proposed one must beat — section 9 |
| `vexflow-v2/tests/ottava-suggestion-keeps-the-open-one.test.ts` | **New.** Three assertions |
| `vexflow-v2/src/print/paginate.ts` | `systemHeights`, so a page is never given more lines than fit |
| `vexflow-v2/src/print/render-pages.ts`, `paginate.ts` | The same gap resolver, and no clamping the gap at nought |
| `vexflow-v2/src/index.ts` | The new constants and the resolver exported |
| `vexflow-v2/tests/system-gap.test.ts` | **New.** Eight assertions |
| `vexflow-v2/package.json` | 0.32.0 → **0.37.0**, and `dist/` rebuilt |
| `aitu-frontend/src/components/time/TimeScoreView.tsx` | `lineSpacing` prop, the white-space mapping, and the effect that applies it |
| `aitu-frontend/src/pages/playground/RhythmPage.tsx` | The slider beside the Key signature, and `lineSpacing` in the save body |
| `aitu-frontend/src/api/timeScore.ts` | `lineSpacing` on `SavedRhythm` |
| `aitu-backend/src/aitu_backend/schemas/rhythm.py` | `line_spacing: float \| None`, `0 ≤ f ≤ 240` |
| `aitu-backend/tests/test_saved_rhythm.py` | Three tests: the round trip, absent, and out of range |
| `aitu-frontend/scripts/check-render.mjs` | Three assertions at the seam the app uses |

**Sections 1 to 5 are the first cut and 0.33.0. Sections 6 to 9 are what came back from trying it,
and 6 supersedes the numbers in 3 and 4** — read them before trusting anything above them.

## 1. The gap already existed; nothing could reach it

`SYSTEM_GAP = 28` has always been the number `drawGrandStaff` lays the systems out with, and
`renderScorePages` has always taken a `systemGap` option — the PDF panel's "Extra space between
lines" slider drives it. What was missing was the browser renderer: `GridNotationRendererOptions`
had no field, and `render()` never passed one, so the screen always drew at 28.

So this is four small additions mirroring `staffGap`, which already had all of it including a drag
handle on the page. The two are kept separate on purpose: `staffGap` is the gap *inside* a system,
between the two staves of one hand pair, and a reader who wants more room between lines does not
want the two hands pulled apart to get it.

`renderPages` passes `systemGap: this.state.systemGap` **before** its `...options` spread, so the
printed page starts from what the screen is set to and the print panel's own slider still wins.

## 2. The prop must not be a dependency of the build

`TimeScoreView` builds the renderer in one big effect whose dependency list is everything it draws
from. Putting `lineSpacing` there would tear down and rebuild every note on every pixel of a slider
drag. So:

- the constructor reads it from `gapNow` (a ref), for the first drawing only, so the page never
  draws once at 28 and then jumps;
- an effect of its own calls `renderer.setSystemGap(...)` for every change after that.

`setSystemGap` calls `render()`, which **replaces the last render**. The playhead and the two range
handles are placed imperatively against that render rather than from React state, so both have to
be put back:

- the range handles, by `placeRangeHandles()` inside the same effect;
- the playhead, by adding `lineSpacing` to the playhead effect's dependency list. The gap effect is
  written **above** it, and effects run in the order they are written, so the geometry is new by the
  time the playhead is placed.

Checked that this does not cause a spurious scroll: the playhead effect only calls `scrollIntoView`
when `placement.systemIndex` changes, and a vertical gap does not re-wrap, so the index is the same.

## 3. The clamp

`setSystemGap` throws a `RangeError` outside its range, which is right for a mistake in code and
wrong for a number arriving from a saved reading. `systemGapFor()` in `TimeScoreView` holds it
inside the range, so a `rhythm.json` written by hand or by an older version draws with a sensible
gap rather than taking the whole page down. The backend validates as well, and the slider is
bounded; this is the third line of defence, at the point where a throw would be fatal.

*(Section 6.2 gave this function its second job: taking `SYSTEM_ROOM` off the reader's number. It
was called `safeLineSpacing` in the first cut.)*

## 4. Saved with the piece

`lineSpacing` sits beside `annotationScale` and is optional. `None` / absent means **nobody was
asked** — a reading saved before the control existed — and the page draws with its own default; a
number means a reader answered. The distinction is the same one `ottavas` makes, and for the same
reason: the page's own default may change and a reader's answer must not change with it.

`DEFAULT_LINE_SPACING` lives in `TimeScoreView` and the page imports it from there, rather than
either of them importing the package's own constant. `09-coding-conventions.md` says exactly one
file may touch `@aimpromptu/grid-notation`, and that file is `TimeScoreView`; it is also the only
place that knows the reader's number is not the package's, which after section 6.2 is the whole
point. *(In the first cut the page held its own `28` and the two were kept in step by hand.)*

## 5. Checks

- `vexflow-v2`: `npx vitest run` — **404 passing** at this point, 408 after section 6. One pre-existing
  failure in `_to_delete/p63-deleted/bars.test.ts`, which imports a `../src` that is not there and
  is unrelated to anything here.
- **The first version of the sideways test passed vacuously** — it compared
  `getLastRender().frameXs`, which does not exist, so `undefined === undefined`. The typecheck
  caught it (`npm run build` failed on TS2339); vitest had not. Rewritten to read every column's x
  off `render.grid.xForFrame`.
- `aitu-frontend`: `npm run check:render` — **30 passing**, up from 26, with three new ones at the
  seam. The first attempt failed honestly: the fixture fits on one system at 1100 px and a gap
  between lines needs two lines to be between. Narrowed to 240 px, which wraps onto 2, and the
  height grows 468 → 536 — exactly one extra gap of 68.
- `aitu-backend`: `uv run pytest tests/test_saved_rhythm.py` — 16 passing.
- Round-tripped through the **running server** on `classical-mix`: `lineSpacing: 72` saved and read
  back as `72.0`. The test reading was deleted afterwards, so the demo piece is as it was.

## 6. The follow-up: the slider did almost nothing, and why

Shipped, tried, and reported back: at the slider's **minimum there was still a LOT of spacing**, and
the corner marks sat a long way off the staves. Both were true, and they were the same bug wearing
two hats. Measured in jsdom on a wrapped system:

| | |
|---|---|
| Staves of one line, top to bottom | **120 px** |
| White space between two lines at `systemGap: 0` | **178 px** |
| Reserved for the corner marks, above the staff | 43 px — **empty** |
| Where the start corner was actually drawn | **78 px above** the treble staff, up in the frame-number strip |

### 6.1 The corner marks were measured from the wrong thing

`drawMarker` placed them at `geometry.topY + INSET + lane`. `topY` is the top of the **system box**,
which begins above the 60 px frame-number strip — while `extraTopPadding = rangeMarkerPadding()`
reserved a 43 px band for them *immediately above the staff*. So the band was reserved, left empty,
and the corners were drawn outside it. The room was paid for twice and the mark read as page
furniture rather than as a mark on a passage.

Now measured from the staves — `trebleTopY - INSET - ARM - lane` and
`bassTopY + STAFF_HEIGHT + INSET + ARM + lane` — and the lanes tightened (`LANE_STEP` 7 → 5,
`HAND_STEP` 3 → 2, `INSET` 4 → 3), so the band is 31 px and is the band that gets drawn in.
`rangeMarkerPadding()` is now exactly what the furthest corner reaches.

This needed `DrawRangeMarkersOptions.geometry` widened from `{ topY, bottomY }` to the full
`GrandSystemGeometry`. On one staff `trebleTopY === bassTopY`, so `bassTopY + STAFF_HEIGHT` is the
bottom of the only staff there is and the arithmetic needs no branch.

### 6.2 `systemGap` was never the number the reader wanted

A system is not its staves. `SYSTEM_ROOM` — new, exported — names the sum:

```
GRAND_STAFF_TOP_PADDING(60) + GRAND_STAFF_BOTTOM_PADDING(40) + 2 * rangeMarkerPadding(31) = 162
```

So `systemGap: 0` leaves **162 px** of white, and the package's default of 28 leaves **190** — more
than the staves are tall. A reader dragging the slider to its minimum was moving 28 px of a 190 px
gap, which is exactly what "still a LOT of spacing" means.

`TimeScoreView` now subtracts `SYSTEM_ROOM`, so **the slider's number is the white space**, verified
pixel for pixel:

| Slider | White space drawn |
|---|---|
| 0 px | **0 px** — the staves touch |
| 40 px | 40 px |
| **72 px (default)** | 72 px |
| 240 px | 240 px |

`MIN_SYSTEM_GAP` is `-SYSTEM_ROOM`, so the option cannot ask for more room than there is.

### 6.3 The floor has to be per render, not a constant

`SYSTEM_ROOM` assumes corner marks and frame numbers. A **printed** page has neither
(`rangeMarkers: false`, `frameLabels: false` → top padding 24), so its room is 64, and a screen
setting of −162 would have pushed one line clean through the next on paper.

So `resolveSystemGap({ systemGap, padding, extraTopPadding, extraBottomPadding })` floors at
`-(the room this render actually has)`. One function, used by `drawGrandStaff` and by
`renderScorePages`, for the same reason `resolveSystemPadding` is one function: a paginator and a
drawing working from two different sums is how a last line ends up half off the bottom of a page.
Room a lyric needs is in `extraBottomPadding`, so it is never given back — the words live in it.
`planPages` and `systemsPerPage` stopped clamping the gap at nought, or a reader who pulled the
lines together to save pages would have been given the pages straight back.

### 6.4 Checks added

Four more, eight in `system-gap.test.ts` in total, **all eight proven to fail against the pre-change
source** (`git stash`, run, `git stash pop`):

- the white space is `SYSTEM_ROOM + systemGap`, and at the floor the staves touch exactly;
- `resolveSystemGap` keeps its own floor on a bare render, never gives back a lyric's room, and
  still honours the ceiling;
- the corners are drawn nearer the staff than the edge of the box, and within 30 px of it;
- nothing a marker draws reaches past the band reserved for it.

Version **0.34.0**, `dist/` rebuilt, 408 package tests passing.

## 7. The second follow-up: the octave bracket did not say what it covered

Reported next, on the same page: the dashed line **"ends just before the next note that is not
affected"**, so a reader cannot tell whether that note is in or out.

True, and worse than it looks. `drawOttava` ran the span from `xForFrame(fromColumn)` to
`xForFrame(toColumn)`, and `toColumn` is **exclusive** — so the end x was the column of the first
note the bracket does *not* cover. A notehead is centred on its column (`draw-music.ts` names the
variable `centerX`), so the hook came down **dead on that notehead**. The one question a bracket
exists to answer was the one thing it was ambiguous about.

The start had the same shape of problem in the other direction: the `8va` glyph was drawn at the x
of the first covered note, so it sat on top of it rather than before it.

### 7.1 Measured from the notes

`bracketSpan` gathers every onset of this hand **on this system**, splits them into the ones inside
`[fromColumn, toColumn)` and the ones either side, and returns:

```
startX = firstCoveredX - noteheadWidth/2 - lead
endX   = lastCoveredX  + noteheadWidth/2 + trail
```

`lead` and `trail` are `OVERHANG` (0.9 of a staff space), cut to `REACH` (0.4) of the way to the
neighbouring note when that note is closer than the overhang. So the hook is always in the gap
between the last note inside and the first note outside, and always nearer the one it covers.

Measured on a fixture with onsets every four frames and a bracket over frames 8–23:

| | Before | After |
|---|---|---|
| Last covered note | x = 199 | x = 199 |
| **Hook** | **x = 236 — on the excluded note** | **x = 211 — 12 px past the last covered note, 25 px short of the excluded one** |
| First covered note | x = 136 | x = 136 |
| **`8va` glyph** | **x = 136 — on the first covered note** | **x = 124 — 12 px before it** |

It falls back to the columns when there is no music to measure, which is what it always did, and it
is computed per system so a bracket broken across a wrap hugs the notes on each line.

### 7.2 Checks

`tests/ottava-span.test.ts`, four assertions, **three of the four proven to fail against the
pre-change source** (`git stash push src/annotations/draw-ottavas.ts`, run, pop). The fourth guards
the no-note-on-the-far-side case, which was never broken.

The third is worth a note: a reader drags a stretch over the **column numbers**, so a range rarely
ends on an onset. Empty columns collapse to slivers, so the old end x for a range let go on column
23 sat about a pixel from the note at column 24 — visually identical to the bug. That test asserts
the hook is nearer the note it covers than the note it does not, which is what makes it catch this.

Version **0.35.0**, `dist/` rebuilt, 412 package tests passing.

## 8. The third follow-up: one line spread, all of them spread

Reported next: the handle between the two staves of a line — *"if I do this on one line, it changes
all the lines"*. True. `bindStaffGapHandles` called `setStaffGap`, which is `GridRendererState`'s
one number for the whole page, so a reader opening out a chord that needed the room got the whole
score opened out and a page half again as long for it.

### 8.1 Keyed by a column, not by a line number

The obvious key is the system index, and it is wrong: the score re-wraps on every change of width,
so "line 3" is different music afterwards and the room would drift onto notes that never needed it.
So an answer is `StaffGapOverride { fromColumn, gap }`, keyed by a column inside the line — the same
rule `annotations.md` states for every other mark on this page.

`resolveStaffGap(fallback, overrides, system)` returns the widest answer whose column falls inside
that line, or the page's own. **Widest** where a re-wrap has brought two onto one line: both were a
reader asking for room, and giving less than was asked for is the only outcome that loses something.

### 8.2 Lines can now be different heights

`drawGrandStaff` used to compute one `systemHeight` and lay the tops out as
`topOffset + index * (systemHeight + systemGap)`. That cannot survive per-line gaps, so the tops
accumulate instead, and the drawing's own height is the sum rather than a multiplication.

`planPages` had the same assumption. It takes an optional `systemHeights` list now and walks it,
falling back to the single `systemHeight` when none is given — so the existing pagination tests
stand unchanged. `renderScorePages` measures the heights off its probe render
(`bottomY - topY`, which is exactly `systemHeight` for that line's own gap) and hands them over.
Without that a page would be given more lines than fit, which is the one thing pagination must never
do.

### 8.3 The answer belongs to the page, not to the renderer

The renderer is rebuilt whenever the music or an annotation changes, so anything it alone remembered
was lost on the reader's next edit — which is what has always happened to the old global staff gap.
So `onStaffGapsChange` reports a drag up, `RhythmPage` keeps the list in `SheetEdits`, and it is
therefore **undoable** ("Line spread") and **saved** with the piece as `staffGaps`.

`TimeScoreView` drives it through `setStaffGaps` in an effect of its own rather than through the
build, for the same reason the space between lines is: a drag must not tear down and rebuild every
note on the page.

### 8.4 Checks

- `tests/staff-gap-per-line.test.ts`, five assertions: the spread line moves and no other does; the
  lines below it move down and the ones above stay; setting it back to the page's own forgets the
  answer rather than storing one that says nothing; one answer per line rather than a pile; and the
  widest wins where a re-wrap brings two together.
- `tests/pagination.test.ts`, three more: each line budgeted at its own height, one line always
  taken however tall, and the same answer as before when no list is given.
- `tests/interaction.test.ts` — the existing "drags the staff gap with the keyboard" test asserted
  the *old* global behaviour, so it was rewritten to the new contract rather than deleted: the
  page's own number is untouched, the line's own answer is set, and it survives a re-wrap.
- Round-tripped through the **running server**: `staffGaps: [{fromColumn: 0, gap: 110}]` saved and
  read back, and the test reading deleted afterwards.

Version **0.36.0**, `dist/` rebuilt, 420 package tests passing, 887 backend tests.

## 9. The fourth follow-up: a 15ma over one note

Reported next, with a screenshot: *"Totally unnecessary to add a 15va section for only 1 note...
this note can already be rendered in the 8va and it will have been a normal high note."* And the
rule to apply: **whenever we are inside one octave section, prioritise keeping it** unless a
following *set* of notes deserves a change.

### 9.1 The cause

`kindFor` judges each chord **on its own account** and knows nothing about what is open. A lone very
high note therefore asks for `15ma` — the smallest transposition that brings it inside the threshold
*from where it is written on the bare staff*. The loop then did:

```ts
if (kind) {
  // Asking for the other bracket: this one is over.
  close();
}
```

— unconditionally. And `close()` keeps a span when `asked >= minRunLength` **or** `extreme`, where
`extreme` is `soloLedgerLines` (5) counted on the written steps. A note that far out is always
extreme, so one note kept a bracket to itself.

Two failures in one: the open `8va` was closed, and a `15ma` was opened over a single note.

### 9.2 The rule

A chord asking for a different bracket while one is open is now measured **under the open bracket**,
never against the bare staff — because that is what the reader is actually holding. The open bracket
keeps the chord when either is true:

- it reads under it anyway (`ledgerCount(steps, open.kind) < minLedgerLines`); or
- it is **alone** — fewer than `minRunLength` onsets in the next `minRunLength + bridgeOnsets` want
  the other bracket — and the open one at least keeps it within counting distance
  (`< soloLedgerLines`).

Only a real change of register, or one chord left hopeless even under the open bracket, is worth
making a reader let go of one transposition and take up another.

`ledgerCount(steps, kind?)` counts the **worse side** rather than the total, because that is what a
reader counts: three above and none below is a chord three lines out.

### 9.3 Checks

`tests/ottava-suggestion-keeps-the-open-one.test.ts`, three assertions: a lone high note is carried
by the open bracket and the span runs across it; four such onsets in a row still get their own
`15ma`; and music that never leaves the open bracket proposes nothing else.

Proven against the pre-change source: the first fails, and the old output is instructive — it was
`['8va', '8va']`, the open bracket broken in two around the one note. The same complaint wearing a
different hat.

Version **0.37.0**, `dist/` rebuilt, 423 package tests passing.

## 10. Numbers

| | |
|---|---|
| Slider | 0 – 240 px of white space, step 4, with a mark at the default |
| Default | **72 px** — was 190 px of white before this work |
| `systemGap` accepted | `-SYSTEM_ROOM` (−162) to 200, floored per render |
| Backend bound | `0 ≤ lineSpacing ≤ 240`, optional |
