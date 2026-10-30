# 04-3 · Phase 2b: frame numbers on the sheet and in the range toolbox

Status: **built and checked on 2026-10-30; waits for the user's check in the browser** (task 2b.4). Branch
`feat/04-3-phase-2b` from `master` (`9da2248`). No AI call, no database change.

Audience: the agents of this plan (Phase 3 next). Technical.

# 1. Study (task 2b.1)

- **The engine** (`sheet/engrave/frames.py`): `plan` makes the columns (one per `Note.frame` drawn) and the lines;
  `_draw_system` draws one line into a `Pen` of primitives (`layout.Prim`, kinds `g l p e z b t`), staff 1 y from
  the top line (negative is above). The upper staff's ink above the line: notes, ledger lines, ornaments, 8va lines,
  the clef (gClef top at y = -1.33). `_lyrics` runs last and lifts the words above the staff-1 ink under them
  (`_ink_x` + `_prim_yrange`). The bars engine already drew bar numbers with the tuplet digit glyphs
  (`layout._draw_number`, scale 0.7 at x 0.2, y -2.3); the frames engine drew none.
- **Every drawing goes through `_draw_system`**: the page (`part_sheet/build.draw` -> `render_frames`), one segment
  redrawn after an edit (`render_frames(segment=)`, same line breaks), Print to PDF (`render_pages`, `GET
  /sheet/{uuid}/pages`) and the zoom (the page asks a new drawing for its new width). So numbers drawn in the engine
  are in all of them with no frontend work.
- **The page** (`FramesSheetView.tsx`) shows the SVG as it is and draws its overlay in staff spaces. The strip where a
  stretch is marked is 3.5 spaces above the top line (`STRIP_SPACES`), hover only; numbers under it do not disturb it.
  No DOM query of the page reads `<text>` or `g` elements other than `[data-note]` and `[data-lyric]`.
- **The range toolbox** (`FramesRangeToolbox.tsx`) had the title *Frames* and the times under it. A stretch is marked
  as `{start, end}` with `start` a column frame and `end` the next column's frame (excluded). The read-only sheet has
  its own small *Frames* toolbox in `FramesSheetPage.tsx`.
- **How long a line is** (the user's sheets, read only, `Options(width=130)` and 200): 7 to 20 lines a song, a line
  of 10 to 16 s (median; 14 to 25 s at width 200), 40 to 75 columns; the last frame of a song is 4,700 to 5,900. A
  number only at the start of each line would leave 300 frames between two numbers.

# 2. What was built

## 2.1 The frame numbers on the sheet (task 2b.2)

`frames._frame_numbers(lay, cols, end_x, pen)`, called in `_draw_system` after the 8va lines and before the lyrics:

- **Where**: the line's first column's frame at `FRAME_NUMBER_X` (0.2, over the clef, as the bars engine's bar
  numbers); then over the first column whose notehead centre is at least `FRAME_NUMBER_EVERY` (36 staff spaces) after
  the previous number's column, centred on it; none whose right edge is within `FRAME_NUMBER_END` (8) of the line end
  (the next line starts with one). Result: about 3 numbers a line at the default width (99 Red Balloons: 64 on 20
  lines), about 5 at width 200. Spacing by width, not by time, keeps the look even where the music is dense or slow.
- **How high**: baseline `min(FRAME_NUMBER_BASE, top_of_ink_under_it - FRAME_NUMBER_CLEAR)` (-1.5 and 0.6), so a
  number sits just above the staff, or above the notes and 8va lines under it.
- **Look**: the tuplet digits at scale 0.7 (the bar-number look of the old sheet), grey `#8a8a8a`
  (`svg.FRAME_NUMBER_COLOR`), plain number (`112`, as the user writes "frame 112").
- **Primitive** `"n"` `(x, baseline y, digits, scale, frame)`: `layout._prim_yrange` and `_prim_xrange` know it
  (so do the lyrics through `_ink_x`: words over a number are lifted); `layout.number_width` (shared with
  `_draw_number`); `svg.to_svg` writes `<g class="frame-number" data-frame="112" fill="#8a8a8a">` with one `<use>` per
  digit (paths, so the PDF prints them without a font).
- `Options.frame_numbers = True`; `False` draws none. The Phase 2 gallery drawings, if made again, will show them.

## 2.2 The range toolbox (task 2b.3)

`readingTools.framesLabel(range, columns)`: "From frame 283 to frame 495" (the first and the last drawn column
inside the stretch), "Frame 283" for one column. First tried as the toolbox's title ("Frames 283 – 495"): the title
bar holds five buttons and cut it to "Frames 283 – 4…" (the time line under it was already cut before). It is now the
first line of the toolbox body (`data-range-frames`), on the editable toolbox and on the read-only one; the title
stays *Frames* with the times under it.

# 3. Checks

| Check | Result |
|---|---|
| `pytest tests/test_sheet_engrave_frames.py` (2 new tests: numbers at each line start and every 36 spaces, all column frames, above the staff; clear of the notes under them, in the SVG, off with the option) | 13 passed |
| Whole backend `pytest` on the CPU (another project holds 11 GB of the GPU) | all passed except the two `test_transcription_transkun.py` tests that load a CUDA model with the GPU hidden (unrelated) |
| `tsc`, `lint`, `vite build` | clean |
| `check:frames-page` (new section: every line starts with its first column's number, 66 numbers on 14 lines after the zoom, all column frames, grey, on the printed pages; a stretch marked shows "From frame 283 to frame 495") | all passed; the first run timed out before the sheet loaded (no sheet request reached the backend; the page opened fine at once by hand), the rerun alone passed |
| `check:frames-tools` (the range toolbox) | all passed |
| `scripts/docs/check-links.py` | 0 broken links |

Zoomed look (deviceScaleFactor 2) at the 99 Red Balloons sheet (width 130 and the printed page), 7 Years (the check's
copy) and a song with lyrics blocks: every number above the ink under it, under the 8va line where there is one, the
line-start number over the clef; the lyrics blocks (moved by hand) untouched. Screenshots in
`screenshots/04-3-phase-2b/`.

# 4. Documentation

The core's `sheet/README.md` (frames engine: frame numbers), `context/frontend/annotations.md` (marking a stretch),
`context/frontend/rendering.md` (`FramesRangeToolbox.tsx`, `check:frames-page`), `context/04-local-development.md`
(`check:frames-page`).

# 5. Needed later

- **Phase 3 and 4**: the frame numbers the user writes ("at frame 112") are `Note.frame` values, the `f112` of the F1
  text; a number on the sheet always names a drawn column. The catalog's parser of the words (plan 5.10 point 4) can
  take "frame 112" and "f112".
- How often the numbers appear is one constant (`FRAME_NUMBER_EVERY`); if the user wants more or fewer, change it and
  the test follows.
