# 04 · Phase 1: the sheet page

Technical report, for the agents of the next phases. Plan: [`04-plan.md`](04-plan.md) section 4.1 and Phase 1.
Branch `feat/04-phase-1` (from `master` at `57a15a2`). Frontend only: no backend file changed, no AI call, no
database change.

# 1. What was done

| Task | Result |
|---|---|
| 1.1 Study | Section 2 |
| 1.2 ⌘ and the wheel, a trackpad pinch | `FramesSheetPage`: a non-passive `wheel` listener on the sheet's box; a CSS scale at once, one `GET /sheet` per pause (220 ms); the line under the pointer kept under it |
| 1.3 The AI symbol | `AiMark` next to the title (`data-ai-mark`); the `Pill` and `data-enhanced-badge` are gone |
| 1.4 The header toolbox | `sheetButtons(place)`: one list, drawn in the header (`data-sheet-header`, `position: sticky`) and in the floating toolbox |
| 1.5 The hidden floating toolbox comes back | `FloatingBar`: the round button moved to where the hide button was, with a border and an eye; the page holds the hidden state (kept in the browser) and the header has a toggle |
| 1.6 The cursor dragged and dropped | `FramesSheetView`: `grab` / `grabbing`, across lines, the page scrolled near the window's edges, a seek on release |
| 1.7 Checks | New `npm run check:frames-page` (33 checks, all pass); the existing checks (section 6); screenshots in [`screenshots/phase-1/`](screenshots/phase-1/) |

# 2. Study (task 1.1)

- **The header.** `FramesSheetPage` drew the title (`data-sheet-title`) and, when `sheet.llm.enhanced`, a green
  `Pill` "Enhanced with AI" (`data-enhanced-badge`, title "The AI enhanced this sheet N times"). Not drawn in Play
  mode, for a passage role, or on an empty sheet. It scrolled away with the page.
- **What scrolls.** The window (`document.documentElement`, 3,591 px tall for 7 Years at 1440 × 900); no element
  scrolls. The project's top bar (back, steps, **Save to library**) is not sticky. So a `position: sticky; top: 0`
  header works as a direct child of the page's `Stack`.
- **The floating toolbox** (`ui/FloatingBar.tsx`, also used by the Audio step and the Notes editor). Hidden, it
  rendered a small `Fab` with a lightning icon at the bar's **left** edge (`position.x`), white on white, no
  border. Measured in the browser on a copy of 7 Years: the button was there (`[aria-label="Show sheet buttons"]`,
  at x 805 while the hide button was at x 1397) and a click brought the bar back. So it worked, but it was **not
  seen**: about 600 px from where the user clicked, small, on top of the notes, with an icon that says nothing
  about a toolbox. Fixed by placing it at the bar's right end (where the hide button was: 1 px away in the check),
  with a border and the eye icon that matches the eye-off of the hide button.
- **The cursor and the click to seek.** `FramesSheetView` draws `data-frames-cursor` from
  `placeAt(columns, systems, ms)`; a click goes `click` → `headAt` (a notehead within 6 px picks it and seeks to
  its frame) → else `seekTo` → `msAtPoint` (the reverse of `placeAt`). The overlay SVG has `pointer-events: none`.
  While it plays, `scrollIntoView` keeps the line of the cursor in view when its line changes. `ScorePlayer.seek`
  already keeps playing across a seek.
- **The zoom path.** `zoom` (0.7 to 2, `aitu.framesSheet.zoom`) → `width = round((boxWidth / (8.5 · zoom) - 8) / 4) · 4`
  staff spaces (60 to 320) → `useFramesSheet` refetches (`AbortController` cancels the one before). The slider's
  aria label already said "also Command and scroll over the sheet", but no wheel handler existed. A drawing of
  7 Years takes about 60 ms at any width (measured: 148, 120, 100, 84 spaces; 16 to 29 lines, about 400 kB of SVG).

# 3. The header and the one list of buttons (tasks 1.3, 1.4, 1.5)

- `sheetButtons(place: "bar" | "header")` returns the same JSX for both places: Play, (the Proposal's own
  actions), Record a passage, Paste, Print, Undo, Redo, the sheet toolbox, `⋯`, **Enhance with AI**. Only the
  tooltip side (`top` in the bar, `bottom` in the header) and the `data-testid` change: the header's start with
  `header-` (`header-sheet-undo`, `header-enhance-with-ai`, ...), so the old checks still find one `sheet-undo`.
  Play got a `data-testid` (`sheet-play`, `header-sheet-play`).
- The header (`data-sheet-header`) is drawn where the title was (not in Play mode, a passage role or an empty
  sheet); its buttons once the sheet is loaded. `position: sticky; top: 0; z-index: 3`, the page's background. The
  row wraps on a narrow window (`flexWrap`). After the buttons, one toggle: **Hide the floating toolbox** /
  **Show the floating toolbox** (`header-floating-toggle`, eye-off / eye).
- The AI symbol is `AiMark` (the Projects page's component): green filled sparkle, tooltip "Enhanced with AI";
  hollow, "Not enhanced with AI yet", on a sheet the AI has not enhanced. The run count of the old pill is dropped.
- `FloatingBar` takes an optional `hidden` / `onHiddenChange`; the sheet page holds it in
  `aitu.framesSheet.floatingHidden` (localStorage), so a floating toolbox hidden stays hidden on the next page
  (its buttons are in the header). The passage Proposal keeps the bar's own state (it has no header). The label is
  now "the floating toolbox" (tooltips "Show the floating toolbox", aria "Hide the floating toolbox"); new hooks
  `data-floating-hide` and `data-floating-show`.
- **Bug found and fixed in the screenshots**: a bar hidden from the start (after a reload) was never measured, so
  shown again it sat at the top left (8, 8) over the app's top bar. The placing layout effect now waits for
  `!hidden`, and the round button of a bar never shown sits in the bottom right corner. The check covers both.
- The cursor line gets `scroll-margin-top` (the header's height + 8 px), so "keep the cursor in view" does not hide
  it under the sticky header.

# 4. ⌘ and the wheel (task 1.2)

- A native `wheel` listener, `{ passive: false }`, on the sheet's box (the element `useElementSize` measures);
  only with `metaKey` or `ctrlKey` (a trackpad pinch sends `ctrlKey`). Anything else scrolls as before. Outside
  the sheet the browser keeps its own behaviour.
- One event zooms by `exp(-deltaY · 0.002)`, capped at × 1.25 or ÷ 1.25 (a line or page `deltaMode` is turned into
  pixels), clamped to 0.7 … 2.
- At once: the inner box gets `transform: scale(to / drawnZoom)` from the pointer (`transform-origin` in pixels);
  the outer box has `overflow-x: clip`, so a scale up never gives the page a sideways scroll. `drawnZoom` is the zoom
  the drawing on the page was laid out for (set while drawing when a new sheet arrives, as `audioLoads` is: the
  lint rules forbid setting state in an effect and writing a ref during render).
- At a pause of 220 ms: `setZoom(rounded to 0.01)` (kept in the browser as before) → one new width → one
  `GET /sheet`. When the new width is the same step of 4 spaces, nothing is asked and the scale goes.
- The line under the pointer: at the first event of a gesture the page reads the time under the pointer
  (`msAtPoint`) and how far down its line it is (0 to 1); when the new drawing is in, a layout effect finds that
  time's line (`placeAt`) and `scrollBy`s so that the same point is under the same screen height. Measured in the
  check: 1 px off zooming in; zooming out near the top the page cannot scroll above 0 (the check accepts that).
- The Zoom slider of the sheet toolbox is unchanged (it asks for each value as it moves; the abort keeps one).

# 5. The cursor dragged and dropped (task 1.6)

- No new SVG element: the root's pointer handlers test the geometry. `onCursor(x, y)`: within 6 px of the cursor's
  x (in screen pixels, through `getScreenCTM`) and between `staff_top - 1.5` and `staff_bottom + 1.5` of its line
  (the line drawn). Over it the root's CSS cursor is `grab`; while dragging, `grabbing`.
- A press on the cursor starts `cursorDrag` (unless a lyrics block is under the pointer). It becomes a drag only
  after 5 px of movement (the box-drag threshold); then the pointer is captured, the cursor and the lit notes follow
  `msAtPoint` of the pointer on any line, and `data-dragging` is set. **A press that does not move is a click**: the
  click handler then picks the notehead under it, or seeks, as anywhere on the sheet. Why: after a click on a note
  the cursor stands on that note's column, so a cursor that always won would make the notes of that column
  impossible to pick. The plan's "a drag that starts on the cursor never picks notes or starts a box selection"
  holds for a drag.
- Near the window's bottom edge (56 px) or top edge (56 px below the header) a `requestAnimationFrame` loop scrolls
  the window (up to 18 px a frame) and moves the cursor to the time under the pointer.
- "Keep the cursor in view" stops while dragging (`follow && !draggingCursor`); on release `onSeek(ms)`; the
  player plays on if it played (`ScorePlayer.seek`). Works wherever `onSeek` is given: read-only sheets, Play mode,
  the passage page.

# 6. Checks

| Check | Result |
|---|---|
| `npx tsc -b`, `npm run lint`, `vite build` | clean (the chunk-size warning was there before) |
| `npm run check:frames-page` (new, on a copy of 7 Years) | 33 of 33 |
| `check:frames-sheet`, `check:frames-edit`, `check:frames-tools` | all passed |
| `check:frames-toolbox`, `check:play`, `check:paste`, `check:compose`, `check:passage -- --played` | all passed (passage: 39 ok) |
| `scripts/baseline-sheets.mjs` | 22 screenshots, no console error, no failed request, nothing left behind |
| `scripts/docs/check-links.py` | passes |
| `pytest` | not run: no backend file changed |

Checks changed on purpose: `check-frames-sheet` and `check-frames-edit` look for `[data-ai-mark] [data-enhanced]`
instead of the badge; `baseline-sheets` opens the sheet toolbox by `data-testid` and `check-frames-toolbox` takes
the first `⋯` (the header and the floating toolbox now both have one).

# 7. Notes for later phases

- The header now holds the sheet's buttons; a new button of the sheet goes into `sheetButtons` once and appears in
  both places. Its `data-testid` in the header is `header-<name>`.
- A browser check that looks for a sheet button by its accessible name finds two of them now (the header and the
  floating toolbox): use the `data-testid`, or `.first()`.
- The screenshots of this phase: [`screenshots/phase-1/`](screenshots/phase-1/) (`page/` from `check:frames-page`,
  the rest from `scripts/baseline-sheets.mjs`).
