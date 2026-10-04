# 08 Phase 8: The Hands tab and the Sheet tab

The plan is [`08-plan.md`](08-plan.md) sections 8.3, 9.6 and 9.7, and section 12, Phase 8. The status
lookup is [`08-checklist.md`](08-checklist.md). This report is for the agents of later phases: what was
built, the choices made inside the phase, the measurements, and what Phase 9 must know.

Story 8.1 (the Hands tab) was built early, at the end of Phase 7, and is reported there:
[`08-implementation-phase-7.md`](08-implementation-phase-7.md) sections 6 to 8. This report covers
Story 8.2, the Sheet tab, done on 2026-10-01.

# 1. What was done

| Task | Result |
|---|---|
| 8.2.1 `RhythmPage` in the flow page | `pages/piece/SheetTab.tsx` renders `RhythmPage` with a `step` prop (`SheetStep`: `audioUuid`, `label`, the Sheet step's `state` and `reason`, `onChanged`). Without the prop the page is the Playground's, unchanged. With it: the piece comes from the flow page, not from the working artifact; no page title (the tab names it), the subtitle stays; `onChanged` (the flow page's `refresh()`) after a saved reading and after **Remove all**, so the tab's tick follows. `LaterStepTab.tsx` is deleted (this was its last use) |
| 8.2.2 stale banner, **Write the sheet** required | When the status says `sheet: stale`, the reading is loaded but the page does not draw it by itself (the "restore the saved sheet" effect is skipped), and a warning banner says the notes or the hands changed, the reading is kept, press **Write the sheet**, check, then **Save**. After **Write the sheet** the banner says "Press Save to make it the sheet of this piece". **Save** only exists once a sheet is drawn, so a stale reading can never be saved without a press of **Write the sheet**; the save stamps the current `handsRevision` and the step is `ready`. A piece with no reading shows the backend's reason as an info banner |
| 8.2.3 a hand move on the piano sheet, part by part | `npm run bench:sheet` (`scripts/bench-sheet.mjs`). Before: 438 ms median on Elefants (3:53), 385 to 507 ms on the Superestrella tutorial. After three fixes (section 2.3): **252 ms** and **272 ms**, under the 300 ms target. The largest piece of the library (4:33, 4,295 notes) is 599 ms; there the drawing is the largest part (section 3) |

Checks: frontend `tsc -b`, `npm run lint`, `npm run build`, `check:render` (60), `check:history`,
`check:note-names` (15), `check:geometry`, `check:cuts`, `check:notes`, and `check:flow` with 9 new
checks for the Sheet tab (78 in all) pass, no console error, no failed request. Backend: `make
test-backend` 1,039 passed, 1 failed (the known
`test_the_worked_example_at_00_46_prints_three_equal_corcheas`, Phase 0 report 2.1); `black` and
`flake8` clean on `api/time_score.py`.

# 2. Choices made inside the phase

## 2.1 The Sheet tab is `RhythmPage` with one optional prop

The plan asks for `RhythmPage` inside the flow page "otherwise unchanged". The page reads its piece
from the Playground's working artifact; the flow page sets that artifact when it loads a piece, but
in the same update as its own state, and a page that reads two sources can show one piece's sheet
over another's. The prop makes the flow page the only source on the Sheet tab, and `SheetTab` keys
the page by the uuid. `frameMs` still comes from the working artifact (40 ms by default), as on the
Playground.

The Sheet tab does not register unsaved changes with `useUnsavedChanges`. `RhythmPage` has no record
of what is unsaved (its undo history does not say whether the reading on disk matches), and the
Playground loses an unsaved reading on leaving in the same way. A stale or missing step already
shows on the tab. If the user wants the leave dialog here too, it needs a "reading differs from the
saved one" signal in `RhythmPage`.

## 2.2 The stale rule

- **Not drawn by itself.** A stale reading is the reader's work (named gap, overrides, beam breaks,
  fingers) laid over notes that changed. Drawing it at once would look like the old sheet is
  current. The page loads it, so **Write the sheet** draws with it, and `live` drops the marks that
  name notes that are gone, as it always did.
- **Save only after a drawn sheet.** The floating bar and the "Save this rhythm" button live inside
  the drawn sheet's card, so they appear only after **Write the sheet**. No extra guard was needed.
- **Hand moves and note edits on a stale sheet** keep it stale: `PUT /time/{uuid}/hands` moves
  `rhythm.json` forward only when it was current (Phase 5). Only **Save** makes it ready.
- `check:flow` walks it: a new piece (info banner, **Write the sheet**, **Save**, tick), a notes
  edit through `PATCH /pieces/{uuid}/notes` (stale), reload (banner, nothing drawn after 2.5 s, no
  **Save** button), **Write the sheet** (banner asks for Save, still stale), **Save** (ready, tick).

## 2.3 The three fixes found by the measurement

The first measurement (section 3) gave 438 ms on Elefants. The backend parts were small (the hand
request 20 ms, the sheet built in 50 ms, sent in under 1 ms); the browser took the rest. A CPU
profile and a count of the sheet's full redraws (the redraw effect of `TimeScoreView` starts by
emptying its container) showed **five full redraws for one hand move**, where one is needed:

| When | Why | Fix |
|---|---|---|
| At the press | `closeNotes()` raises `clearSelectionsAt`; the effect calls `setSelectedRange(undefined)`, and every setter of the drawing package calls `render()`, even with nothing to clear | Clear the stretch only when the renderer has one (`getSelectedRange()`); the same check for a `selectedRange` prop that is a new object for the same stretch |
| After the hand answer | `moveSelected` hands the fingerings back as a new object (`setFingers` always copies); `live` gives six new objects; the draw effect sees five new props and rebuilds the sheet **with the old notes** | `drawnMarks` in `RhythmPage`: `live` kept as the same objects while its content (JSON) is the same |
| After each rebuild | `live.evenSpacings` is a new array after any change, and the `setEvenSpacings` effect redraws again | `sameContent` in `TimeScoreView`: the spacing setters (`spacings`, `evenSpacings`, `staffGaps`) skip a value equal to the one the sheet was drawn with |

Two more parts were then the largest:

- **The press render blocked the answer.** Closing the panel re-renders the whole `RhythmPage`
  (about 85 ms with React in development mode, which the frontend container runs, Q-5). The hand
  answer arrives after 20 ms but its code runs only after that render, so the sheet request left
  about 85 ms after the answer. The panel close, the spinner and the cleared message are now set in
  `startTransition`, which React renders in slices: the sheet request now leaves about 22 ms after
  the press.
- **The sheet build with decorative notes removed** (`dropDecorative`, on for the Superestrella
  tutorial) was 90 to 150 ms. It names the figures up to 4 times, and each pass deep-copied the
  whole `TimeHands` (`copy.deepcopy`, about two thirds of the time: 875,000 calls for 5 requests).
  `_editable_copy` in `api/time_score.py` copies only the two hand grids, the only thing the page
  edits and the trills write (`PianoMatrix` keeps no data derived from its grid). The set of hidden
  notes is also built once per pass instead of once per note. Checked: the answers are identical
  on both pieces with a reading, in 5 combinations each (plain, hidden notes, decorative, trills,
  all; the trills made up from the notes, because neither piece has one); the request went from 88
  to 50 ms (decorative) and from 125 to 51 ms (all), measured in the backend container.

## 2.4 A library piece was changed by a debug script, and put back

While tracing the redraws, a temporary debug script opened the real `b99bc3ae` (Superestrella
tutorial) instead of a copy and pressed **L** on one note of its piano sheet. The backend did what
the sheet's first hand move does on an old piece (Phase 5 report 2.5): it saved the hand of every
live note as the sheet drew it, then moved the note. `events.json` was rewritten in schema 1.1
(`handsRevision` 1, `handsNotesRevision` 1), and `rhythm.json` was moved forward (`handsRevision`
1). The history folders (`v1`, `v2`, 16 September) are older versions and could not restore it.

The moved note was found without guessing: on a copy, the saved hands were compared with
`POST /hands/predict` (`replace: true`): 11 notes differ, the 10 hands the user set earlier and
one more. Only one of the 11, note id 119 (key row 74, 13.60 s, frame 340 at 40 ms), sits at index
60 of the right-hand note targets, which is the note the script clicked. It was moved back with
`PUT /time/{uuid}/hands` (the route the sheet's undo uses), which keeps the sheet current.

The piece now draws as before (the saved hands paint the same cells as the inference with the
pins, Phase 5 section 2.3, checked on this piece) and its status is all `ready`, but the files are
not byte-identical: every live note now has a saved hand, `handsRevision` is 2, and the Hands step
reads `saved: true`. The reading was last saved on 2026-09-17 (`savedAt`), before the move to
Ubuntu, so the Mac's copy from Phase 0 holds the original `matrices/` files. The walkthrough offers
to copy them back. Every script of this phase now works on temporary copies only, and the lesson is
kept for later agents.

## 2.5 A bug of the drawing package (fixed after the user's check, section 6)

`bench:sheet` saw `Cannot access 'drag' before initialization` on the Superestrella tutorial. In
`vexflow-v2/src/annotations/draw-ottavas.ts`, `bindOttavaDrag` adds a `pointerleave` listener that
reads `drag`, but `let drag` is declared after `if (!report || (!startTip && !endTip)) return;`. A
middle segment of an octave bracket that spans several systems has no tips, so the function returns
before `drag` exists, and moving the pointer out of that segment throws. It is a one-line fix
(declare `drag` before the listeners). It was first left alone, because the plan does not change the drawing package here; the user then chose to fix this one bug (section 6.2).

## 2.6 Smaller points

- A click on a note of the sheet also moves the playhead line onto it, and the line then takes the
  next click on that same note. `bench:sheet` therefore moves a different note each time. This is
  the Playground's behaviour too and was not changed.
- A 404 on `GET /time/{uuid}/rhythm` is how the page asks whether a reading exists. `check:flow` and
  `bench:sheet` ignore that one 404; any other failed request is still reported.
- `bench:sheet` on a piece whose hands were never saved and which has no sheet (its Sheet tab is
  disabled) predicts and saves the hands through the API first, on the copy.

# 3. Measurements

`npm run bench:sheet` makes a temporary copy of each piece in the data folder, opens it on the Sheet
tab in a headless Chromium (1440 x 900), makes it current the way a reader does (a stale reading:
**Write the sheet**, **Save**; no reading: **Write the sheet**, **Save**), then moves 7 notes, each
with a click on the notehead and **L** or **R** in the panel. The first move is reported apart; the
table is the median of the other 6. Raw answer:
[`measurements/phase-8-sheet-hand.json`](measurements/phase-8-sheet-hand.json).

The parts, all on the page's clock: `hands` is the press to the answer of `PUT /time/{uuid}/hands`;
`wait` is that answer to the sheet request leaving; `build` is the sheet request sent to its first
byte (the backend); `transfer` is its first byte to its last; `draw` is the last byte to the moved
note in the page (JSON, React, the drawing package); `paint` is that to the next frame.

## 3.1 After this phase

| | Elefants | Superestrella tutorial | The Other Side |
|---|---:|---:|---:|
| Length, notes | 3:53, 1,292 | 3:10, 1,497 | 4:33, 4,295 |
| Notes from | MuScriptor, saved hands | ByteDance, decorative notes removed, lyrics | ByteDance, hands predicted by the script |
| `hands` | 19 ms | 22 ms | 49 ms |
| `wait` | 22 ms | 22 ms | 38 ms |
| `build` | 49 ms | 91 ms | 122 ms |
| `transfer` (sent / raw) | 0.6 ms (39 / 510 KB) | 0.7 ms (42 / 403 KB) | 0.8 ms (71 / 1,101 KB) |
| `draw` | 113 ms | 77 ms | 190 ms |
| `paint` | 47 ms | 55 ms | 170 ms |
| **Press to redrawn sheet** | **252 ms** | **272 ms** | **599 ms** |
| Full redraws of the sheet | 1 | 1 | 1 |

On Elefants the `draw` part is larger than before the transition fix because the press render now
finishes while the sheet is built, and part of it lands after the answer; the total is still lower.

## 3.2 Before and between the fixes

| Step | Elefants | Superestrella tutorial |
|---|---:|---:|
| Before (5 full redraws, deep copy, press render blocking) | 438 ms (`wait` 147, `draw` 170) | 507 ms first move (`wait` 163, `build` 152) |
| The three redraw fixes (section 2.3) | 267 ms | 385 ms (`build` 151) |
| `_editable_copy` in the backend | 270 ms | 328 ms (`build` 92) |
| `startTransition` at the press | 252 ms | 272 ms |

The tunnel from the Mac adds the network: 39 to 71 KB of gzip per move, a few milliseconds on the
home network. Headless Chromium on this machine paints without a GPU.

## 3.3 What is left, and the next step

On a piece of 3 to 4 minutes the move is under 300 ms. On the largest piece the drawing package is
the largest part: `draw` plus `paint` is 360 ms, because every move rebuilds the SVG of every system
of the piece (4,295 notes) and the browser lays all of it out again. The next step, which needs a
change in `vexflow-v2`, is one of:

1. **Redraw only the systems that changed.** A hand move changes the notes of one or two systems;
   the renderer could keep the other systems' SVG groups when their notes and widths are the same.
2. **Draw only the systems near the screen**, and the others when the page scrolls to them.

On the backend, the decorative passes could name the figures only, and build the payload once at
the end (about 30 ms on the Superestrella tutorial). React in production mode would also make the
`draw` part smaller; the container runs development mode (Q-5), which is what the user sees.

# 4. Notes for Phase 9

- Nothing of Phases 3 to 8 is committed yet.
- `check:flow` now ends on the Sheet tab (79 checks, about 2 minutes with the transcription).
  `bench:sheet` repeats section 3 (about 4 minutes for the three pieces).
- `vexflow-v2` has an uncommitted change (section 6.2): commit it in that repository with the rest.
- `b99bc3ae` (section 2.4): if the user copied the Mac's `matrices/` files back, check that
  `GET /pieces/b99bc3ae-.../status` answers `hands: ready, saved: false` and `sheet: ready` again.
- Q-4: the old Piano Roll goes; the Playground's piano sheet (`/playground/rhythm`) stays and is the
  same page as the Sheet tab.
- If the user wants the leave dialog on the Sheet tab (section 2.1), `RhythmPage` needs a signal
  that the reading on screen differs from the saved one.

# 5. Files

New, frontend: `src/pages/piece/SheetTab.tsx`, `scripts/bench-sheet.mjs`. Deleted:
`src/pages/piece/LaterStepTab.tsx`.

Changed, frontend: `src/App.tsx` (the Sheet route), `src/pages/playground/RhythmPage.tsx` (`SheetStep`,
`Frame`, the banner, the stale rule, `onChanged`, `drawnMarks`, `startTransition` in
`moveSelected`), `src/components/time/TimeScoreView.tsx` (`sameContent`, `sameRange`, the guarded
setters), `scripts/check-flow.mjs` (the Sheet tab, the expected 404), `package.json` (`bench:sheet`),
`README.md`.

Changed, backend: `src/aitu_backend/api/time_score.py` (`_editable_copy`, the hidden set per pass).

Documents: this report, `measurements/phase-8-sheet-hand.json`, the checklist, the plan (sections
7.1, 9.7 and 14).

# 6. After the user's check

## 6.1 A hand move on a zoomed sheet took the whole page down

The user moved a La of Elefants from the left hand to the right hand, then back, and the page showed
React Router's "Unexpected Application Error": `RangeError: SVG dimensions must be positive finite
numbers`, from `new GridNotationRenderer` in the draw effect of `TimeScoreView`.

- **Cause.** The note and its figure had nothing to do with it. `RhythmPage` gives no
  `availableWidth`, so the draw effect read `container.clientWidth` right after emptying the
  container. When the sheet is zoomed (Command and the wheel, or a trackpad pinch), the stage box
  is `inline-block` with `minWidth: 0`, so its width comes from its content, and an emptied
  container is 0 wide. The renderer refuses a 0-wide SVG. Any rebuild of a zoomed sheet crashed;
  this existed before Phase 8. The user most likely zoomed between the two moves.
- **Reproduced** on a copy of Elefants with a Control-wheel zoom before the move: the first move
  crashed with the same stack.
- **Fix** (`TimeScoreView`): the width is read before the container is emptied and again after;
  the first positive value of (after, before, the scroller's width, 900) is used. At zoom 1 this is
  the same value as before (the width after emptying). Checked on the copy: 6 La notes moved there
  and back, zoomed and not zoomed, no error, the SVG width the same before and after each move
  (1,358 px), so the zoomed sheet wraps in the same places.
- `check:flow` has one more check: a hand move on a zoomed sheet redraws without an error (79 in
  all, all pass).

## 6.2 The octave bracket bug of section 2.5, fixed in `vexflow-v2`

The user chose option 3: fix only this bug, and leave how the package draws as it is (no redraw of
only the changed lines). In `vexflow-v2/src/annotations/draw-ottavas.ts`, `bindOttavaDrag` now
declares `drag` before the hover listeners that read it. A new test in
`tests/ottava-editing.test.ts` draws a bracket over several lines (a fixed column width at 260 px),
takes the middle part (a band with no tips), and sends `pointerenter` and `pointerleave`: it failed
with one caught error before the fix and passes after. `vexflow-v2`: 499 tests pass, lint clean,
`npm run build`. The frontend image was built again (`docker compose build frontend`, then `up
-d`), because the container holds its own build of the package; the served file has the
declaration before the listener. `bench:sheet` on the Superestrella tutorial: no console error. The
change in `vexflow-v2` is not committed (that repository also has an unrelated
`package-lock.json` change from before).

## 6.3 Phase 8 closed

The user checked the Sheet tab in the browser on 2026-10-01, the hand move on a zoomed sheet
included, and closed the phase. Still open from section 2.4: the user may copy the Mac's original
`matrices/` files of `b99bc3ae` into `.run/b99bc3ae-from-mac/` for a comparison and an exact
restore; nothing was received yet.

