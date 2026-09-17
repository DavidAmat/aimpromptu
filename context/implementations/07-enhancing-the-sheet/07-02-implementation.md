# 07-02 — Zoom and Lyrics: implementation report

Brief: `07-01-new-enchancements-v1.md`, tasks **7** and **8**. Context: `07-00-context.md`.
Predecessor: `07-01-implementation.md` (tasks 1–6).

Both tasks delivered. One part of task 8 was built differently from the words of the brief and §5
says exactly why.

Package version: `@aimpromptu/grid-notation` **0.38.0 → 0.39.0**, rebuilt.

---

## 1. Task 7 — Zoom

**Frontend only. Nothing in the package changed.**

Command (or Control) plus the wheel over the sheet draws the page larger, from 1× to 4×. A chip
beside **Show frame numbers** reads `Zoom 180% — back to normal` and puts it back in one click.

### 1.1 It is a magnifier, not a change to the music

The score is scaled on screen with a CSS `transform` on the stage. Nothing is measured again: no
column changes width, the page wraps exactly where it did, `availableWidth` is untouched and no
mark moves relative to any note. That is the whole reason it was done this way rather than through
the package's `zoom(factor)`, which scales `pixelsPerFrame` and `frameWidths` — that would re-wrap
the page, and it is also wiped by the next `setNoteSpacing` / `setSpacings` / `setEvenSpacings`
call, because each of those re-measures from scratch.

`MIN_ZOOM = 1` is the floor the brief asked for: the natural size is already the page laid out for
this window, so there is nothing to see below it. `MAX_ZOOM = 4`.

### 1.2 Four things it had to get right

**The wheel listener is native and non-passive.** React's `onWheel` is registered passive, so
`preventDefault()` there does nothing and the browser's own page zoom takes the gesture instead.
It is `addEventListener("wheel", …, { passive: false })` on the scroll box, in an effect of its
own. `metaKey` **or** `ctrlKey`: Command is what the brief asked for, Control is what a trackpad
pinch sends and what the same gesture is on Windows.

**The step is exponential** — `zoom × exp(−deltaY × 0.0025)` — so one notch is the same proportion
of the page at every size. Linear steps race at the top of the range.

**The point under the pointer stays under it.** The anchor is recorded on the wheel event and a
`useLayoutEffect` keyed on `zoom` scrolls back by however far it drifted: the scroll box's own
`scrollLeft` horizontally, `document.scrollingElement.scrollTop` vertically. Measured after the
new size is laid out rather than computed in advance, so it is self-correcting. Without it the
page grows from its top-left corner and the passage the reader was working on slides away — which
kills the one thing zoom is for.

**Every pointer measurement is divided by it.** `secondsAt`, `frameAt` and `seekOnDoubleClick` all
went through `stage.getBoundingClientRect()`, and under a transform that box is the magnified one
while the drawing's units are not. They now share one helper, `drawingPoint(clientX, clientY)`.
Two hit paths needed nothing: the ruler cell's `frameAtPointer` already works from the ratio
`(clientX − box.left) / box.width`, and every other click is an SVG DOM listener the browser
resolves itself.

### 1.3 The layout

A transform is not layout, so a magnified drawing would be drawn over the rest of the page and
could not be scrolled to its far end. One sizing box was added between the scroll box and the
stage, `naturalSize × zoom`, where `naturalSize` is `host.offsetWidth/offsetHeight` watched by a
`ResizeObserver` — layout numbers, which a transform does not change, which is exactly why they are
the right ones to multiply. **At `zoom === 1` the box carries no `sx` at all**, so the layout is
byte-for-byte what it was before this task.

The playhead and the two range handles are inside the stage, so they scale with it and stay exactly
on the columns they mark. Nothing had to be placed twice.

### 1.4 Where the number lives

`RhythmPage.sheetZoom`, plain view state — **not** a `SheetEdits` field, not undoable and not
saved. It is how the page is being looked at, like `frameLabelsOn` beside it, and it says nothing
about the piece. `TimeScoreView` takes `zoom` and `onZoomChange`; with no `onZoomChange` the wheel
does nothing, which is what the print preview (`readOnly`) wants.

---

## 2. Task 8 — Lyrics

### 2.1 Above the right hand, at the top of the system box

The words used to be drawn under the **bass** staff, in room added to `extraBottomPadding`. They
are now above the **treble** staff, in a block of their own reserved in `extraTopPadding`.

The height they are drawn at is the interesting part, and it is the same lesson the passage header
learned in 07-01. An octave bracket is the one thing above a staff that is **not** at a fixed
offset from it: `bracketY` clears the highest note in its span, so over a passage reaching high the
bracket climbs and there is no distance from the staff at which words are safe. So the block is
measured **down from the top of the system box**, which is the one line everything above a staff
has to fit under:

```
topY ─┬─ markerPadding      (the corner marks)
      ├─ headerBlock        (negra = 480 ms · ≈125 BPM)
      ├─ lyricBlock         ← the words
      ├─ padding.top        (the frame-number strip)
      └─ trebleTopY
```

`drawAnnotations` takes a new `lyricTopY`, handed in by `drawGrandStaff` — **only the caller that
reserved the room knows how much it reserved**, which is why it is not worked out at the drawing
end. `lyricBlockHeight(annotations)` is now the tallest lyric's **full** height rather than its
extra lines, because the block no longer shares the padding under the staff with anything.
Reserved for the whole page rather than per system, so attaching one long lyric near the end does
not shuffle every staff before it down the page.

`print/render-pages.ts` moved the same term from `extraBottom` to `extraTop`. Its sum and the
drawing's have to agree or the last line of every page lands half off the bottom.

### 2.2 The frame numbers give way

`drawFrameRuler` takes `labelGaps`, and `drawGrandStaff` fills it with every lyric's columns. Both
are text in the strip above the staves; a column number is an address a reader can look up at any
time, and the words are the thing being read, so the number is the one that goes. The dashed
guides and the selectable cells are untouched — only the printed `f120`.

### 2.3 The block is the reader's

`LyricAnnotation` gained four optional fields, additive per D16: `offsetX`, `offsetY`, `width`,
`fontSize`. A host that drops all four draws exactly what it drew before.

- **Drag the block** (`.grid-lyric-box`) to move it anywhere.
- **Drag its right edge** (`.grid-lyric-grip`) to narrow it; the words re-wrap **while the edge is
  moving**, not after it is let go.
- **Text size** is a handle in the Lyrics tab, per lyric — one line is three words over eight
  seconds and the next a whole sentence over one, and no rule has that.
- **Put the block back over its stretch** clears the placement, keeping the size.

Both gestures move the drawing directly — a `transform` on the SVG group, or new attributes on the
three elements — and report **once**, on pointer-up, through `onLyricLayout`. So the host rebuilds
the sheet once per gesture and Command-Z sees one step, not one per pixel. A press that moved more
than 3 px is a placement and not a pick, so letting go does not also open the editor over the place
you just dropped it.

Screen pixels are turned into drawing units inside the package, from `svg.getAttribute('width')`
against `svg.getBoundingClientRect().width`. A dragged lyric therefore lands where the pointer is
at any zoom, and **the package has to be told nothing about the host's magnification**.

### 2.4 Three consequences that had to be handled

**A lyric is drawn once.** It used to be drawn on every system it reached across, with the whole
text centred in each — so a lyric spanning a wrap printed its words twice and read as two lyrics.
It is now drawn on the system its `fromColumn` falls on. A block the reader can move and resize
cannot sensibly be two blocks.

**A placed block stops widening its columns.** `measureFrameWidths` opens the frames under a lyric
wide enough to hold its words. Once the reader has dragged it away it is not over them, and paying
for room nobody can see is not honest. `lyricIsPlaced(lyric)` skips it.

**One set of measurements, used everywhere.** `wrapLyricLines`, `lyricBoxWidth` and `lyricBoxHeight`
in `lyric-blocks.ts` are what the spacing pass, the drawing, the reservation and the paginator all
ask. They estimate from a per-character fraction of the font size rather than measuring live text,
because the answer has to be identical under JSDOM and in a browser — the existing rule, extended
to cover wrapping and size.

### 2.5 Storing it

`SavedRhythm.lyrics[]` gained `offsetX`, `offsetY`, `width` (32…2000) and `fontSize` (7…36), all
optional. The bounds are the package's own constants, so a reading written by hand cannot ask for a
block that cannot be drawn. The save body already sent `[...lyrics]` and the read-back already took
`found.lyrics ?? []`, so neither needed changing.

---

## 3. What could not be built as written

**"This lyrics thing should be a `div` that should be draggable."**

It is an SVG block, not a `div`, and it does everything the brief asked a `div` for: it is dragged,
its right edge is pulled in, the words wrap, and the text size is a control.

The reason is printing. `ScorePdfDialog` lays the same music out on paper through
`print/render-pages.ts`, which is the same drawing code. An HTML overlay would have to be placed
against every render — like the playhead and the two range handles are — and would be **absent from
every printed page**, so a reader who wrote words on the sheet would print a sheet without them.
Wrapping is the only thing an HTML box gives for free, and `wrapLyricLines` is fourteen lines and
is also what lets the spacing pass and the paginator agree with the drawing.

---

## 4. Tests

### 4.1 New package tests — `vexflow-v2/tests/lyric-placement.test.ts`, 16 tests

| What it pins |
|---|
| The block draws clear above the treble staff |
| It stays above an octave bracket over notes high enough that the bracket climbs |
| Attaching a lyric makes the system taller |
| The frame numbers over its columns are left off, and the rest are printed |
| A lyric spanning a line break draws **once** |
| A width folds the words into more lines, and the block is that wide |
| A `fontSize` reaches the text and makes the block taller |
| An offset moves the block by exactly that much |
| An untouched lyric widens its frames; a placed one does not |
| A drag reports its offsets once; a press that did not move reports nothing |
| Dragging the right edge reports a new width, and the words wrap during the drag |
| `wrapLyricLines` always breaks at a typed break, and never inside a word |

**Proven against the pre-change geometry.** The placement was put back by a scripted reversal —
the lyric block returned to `extraBottomPadding`, `lyricTopY` withheld so the fallback is the old
position under the bass staff, the per-system draw back to `overlapsSystem`, and the placed-lyric
skip in `measureFrameWidths` disabled. Result: **5 failed, 11 passed**.

The five that fail are exactly the five geometry changes of this task. The eleven that pass do so
because the reversal deliberately left the block model, the drag and the wrapping helpers in place
— reverting those as well would have failed the file at import and proved nothing about geometry.
The reversal script is at `/tmp/claude-501/revert.py` and is not part of the repository.

### 4.2 New backend tests — `test_saved_rhythm.py`, 3 tests

A placement round-trips; a lyric nobody moved reads back with all four fields `None`; a width of 4
and a font size of 96 are both 422.

### 4.3 `check-render.mjs`, 4 new checks (40 → 44)

On the app's own path: the words sit above the right hand (`0.0 + 23.0` vs a `trebleTopY` of
`89.0`); the frame numbers over the lyric's columns are gone and the rest are printed
(`16, 32`); a block narrowed to 70 px wraps into four lines; and it is drawn at exactly the width
and size it was given.

### 4.4 Results

| Check | Result |
|---|---|
| `vexflow-v2` `vitest` | **463 passed** (52 files) |
| `vexflow-v2` `tsc -b && tsup` | clean, `dist/` rebuilt at 0.39.0 |
| `aitu-frontend` `npx tsc -b` | clean |
| `aitu-frontend` `npm run lint` | clean |
| `aitu-frontend` `npm run build` | clean |
| `aitu-frontend` `npm run check:render` | **44 passed, 0 failed** |
| `aitu-frontend` `npm run check:history` | every check passed |
| `aitu-backend` `pytest` | **903 passed, 1 failed** |

The one backend failure is the documented pre-existing one,
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas`. Both
that test file and `matrix/hands.py` were already modified in the working tree before this task
started, so the failure is not from this work.

---

## 4b. Reported after the first pass: two things the zoom broke

### The frames toolbox opened on top of the stretch

The panel is `position: fixed` and every placement number is a viewport coordinate, so the
magnification was **not** the thing going wrong. What went wrong is what the placement was measured
**from**: `clearOfRange(pressedAt.current)` — the click, which is sixteen pixels, while the stretch
it starts is whatever the reader drags it out to. At the natural size a stretch is small enough that
a panel beside the click is also beside the stretch. At 3× it is not, and the panel landed inside it.

Two fixes, both of which also help at the natural size:

- **The panel is placed against the highlight the page actually paints**, one animation frame later
  — the only moment that box is a real answer, because the band is drawn by the sheet's own effect.
  `firstLineBoxOf('.grid-frame-range-fill')` takes the fragment on the line the stretch **starts**
  on: a wrapped stretch paints rectangles on several lines, and unioning them gives a box the height
  of the page with nowhere clear left to open. The click is still used for the opening guess, so
  nothing flashes in from a default corner.
- **`clearOfRange` tries left, then right, then below, and clamps the result into the window.** It
  used to try left and then fall straight to below with no clamp at all, so a selection wider or
  taller than the window — ordinary once the page can be magnified — sent the panel off the edge of
  the screen, where the browser drew it and the reader read it as lost. `onScreen()` is the clamp
  and `besideOnScreen` takes it too.

A passive effect could not call `setState` directly (`react-hooks/set-state-in-effect`, the rule
`09-coding-conventions.md` names), which is why the measurement happens in a `requestAnimationFrame`
callback. That is the honest place for it in any case: the box exists once the page has painted.

### The staff-gap handle moved three times as fast as the pointer

`bindStaffGapHandles` set the new gap from `moveEvent.clientY - startY` — screen pixels used as
drawing units. True only while the sheet is drawn at its natural size, which stopped being
guaranteed the moment zoom existed.

`rendering/screen-units.ts` is new: `drawingUnitsPerPixel(svg)`, the SVG's `width` attribute against
the box it occupies, falling back to 1 wherever there is no layout to measure. The staff-gap drag
and the lyric block drag both use it, so **the package still has to be told nothing about the host's
magnification**. Two tests pin it.

---

## 5. A note for whoever comes next

`GridNotationRendererOptions.rangeMarkerPreview`, which 07-01's report §3 describes as added and
defaulting to on, **is not in the package**. The hover preview was removed outright instead —
`drawRangeMarkers` has no `band` option and its doc comment says so — and `TimeScoreView` no longer
passes the flag. The behaviour the reader sees is the one 07-01 wanted (no orange box on the way to
the ruler); only the report is describing a route that was not taken. Nothing to fix; worth knowing
before someone goes looking for the option.

---

## 6. Files touched

### `../vexflow-v2` (0.39.0)

| File | Why |
|---|---|
| `annotations/lyric-blocks.ts` | Wrapping, text size, block width and height, `lyricIsPlaced` |
| `annotations/types.ts` | `LyricAnnotation.offsetX/offsetY/width/fontSize` |
| `annotations/draw-annotations.ts` | `lyricTopY`, `LyricLayoutChange`, the drag and the resize, drawn once |
| `ruler/frame-ruler.ts` | `labelGaps` |
| `renderer/draw-grand-staff.ts` | The lyric block moved to the top, `lyricTopY`, `labelGaps`, `onLyricLayout` |
| `renderer/grid-notation-renderer.ts` | `onLyricLayout` |
| `notation/spacing.ts` | A placed lyric stops widening its columns |
| `rendering/screen-units.ts` | **new** — `drawingUnitsPerPixel`, so a drag is right at any scale |
| `renderer/grid-notation-renderer.ts` (staff-gap drag) | Screen pixels turned into drawing units |
| `print/render-pages.ts` | The lyric block moved from `extraBottom` to `extraTop` |
| `index.ts` | The new helpers and `LyricLayoutChange` |
| `tests/lyric-placement.test.ts` | **new**, 16 tests |
| `documentation/03-rendering.md`, `05-annotations.md` | The new fields, classes and options |

### `aitu-frontend`

| File | Why |
|---|---|
| `components/time/TimeScoreView.tsx` | The zoom, `drawingPoint`, the lyric fields and `onLyricLayoutChange` |
| `pages/playground/RhythmPage.tsx` | `sheetZoom` and its chip, `placeLyric`, the Lyrics tab controls |
| `api/timeScore.ts` | `LyricLine.offsetX/offsetY/width/fontSize` |
| `scripts/check-render.mjs` | Four checks |

### `aitu-backend`

| File | Why |
|---|---|
| `schemas/rhythm.py` | `Lyric.offset_x/offset_y/width/font_size` |
| `tests/test_saved_rhythm.py` | 3 new tests |

### Documentation

`context/frontend/rendering.md` (a new **Magnifying the page** section),
`context/frontend/annotations.md`, `documentation/services/frontend/grid-notation.md`,
`documentation/services/backend/rhythm-and-annotations.md`.

---

## 7. Still open, carried from 07-01

`useEditHistory` opens one step per run of the event loop, so a slider drag records many steps.
There are now four sliders — the Lyrics tab's **Text size** is the newest. The fix is a coalescing
rule in the reducer, and it still belongs in its own change with its own `check:history` cases.
