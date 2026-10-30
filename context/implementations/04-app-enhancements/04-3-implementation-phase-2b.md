# 04-3 · Phase 2b: frame numbers on the sheet and in the range toolbox

Status: **approved by the user and merged into `master` on 2026-10-30** (second version, after the user's first
look). Branch `feat/04-3-phase-2b` from `master` (`9da2248`). No AI call, no database change.

Audience: the agents of this plan (Phase 3 next). Technical.

# 1. Study (task 2b.1)

- **The engine** (`sheet/engrave/frames.py`): `plan` makes the columns (one per `Note.frame` drawn) and the lines;
  `_draw_system` draws one line into a `Pen` of primitives (`layout.Prim`, kinds `g l p e z b t`), staff 1 y from
  the top line (negative is above), staff 0 in system units (the same origin as staff 1). `_lyrics` runs after the
  notes and lifts the words above the staff-1 ink under them (`_ink_x` + `_prim_yrange`). The bars engine already
  drew bar numbers with the tuplet digit glyphs (`layout._draw_number`, scale 0.7); the font (Leipzig) has the
  digits but no colon. `_x_of` gives the x of any frame of a line (between two columns by time, the cursor's rule).
- **Every drawing goes through `_draw_system`**: the page (`part_sheet/build.draw` -> `render_frames`), one segment
  redrawn after an edit (`render_frames(segment=)`, same line breaks), Print to PDF (`render_pages`), the zoom (a
  new drawing for the new width). Marks drawn by the engine are in all of them.
- **The page** (`FramesSheetView.tsx`) shows the SVG as it is; the strip where a stretch is marked is 3.5 spaces above
  the top line, hover only. **Lighting**: `geometry.headsByColumn` put in each column every head whose frame is from
  the column's frame to the next column's, so a decoration note (drawn before the next column's note, with its own
  frame in between) lit for the whole time of the note before it ("A grace note lights with the column before its
  note", implementation 03).
- **The range toolbox** (`FramesRangeToolbox.tsx`, and a small read-only one in `FramesSheetPage.tsx`): title
  *Frames*, the times under it, five buttons in the title bar. A stretch is `{start, end}`, `start` a column frame and
  `end` the next column's frame (excluded).
- **How long a line is** (the user's sheets, read only): 10 to 16 s at width 130, 40 to 75 columns; songs end near
  frame 4,700 to 5,900.

# 2. What was built

## 2.1 First version, replaced after the user's look

Numbers alone, each over a column (the first column of a line over the clef, then about every 36 staff spaces),
placed just above the notes. The user: a number so close to a note reads as a fingering. They asked for vertical
dashed lines every 100 frames, across both staves and beyond them, as bar lines, with the number on top, so that the
number is away from the notes; the line may cross a note. Then also the time above the number (`01:09`).

## 2.2 The frame marks on the sheet (task 2b.2)

`frames._frame_marks(lay, si, cols, end_x, pen)`, called in `_draw_system` after the 8va lines and before the lyrics:

- **Which frames**: every multiple of `FRAME_MARK_EVERY` (100, which is 4 s) that the line holds: from its first
  column to the next line's first column (the last line: to its last column). Nothing before the first note of the
  song. 99 Red Balloons: 48 marks, 2 to 4 a line at the default width.
- **The line**: `"l"` on staff 0, class `frame-line`, `ref` = the frame, dashed (`FRAME_LINE_DASH` 0.45/0.35, width
  0.09, grey `#b4b4b4`), at `_x_of(frame) + HEAD_W/2`, from just under its number down to `FRAME_LINE_BELOW` (2
  spaces) under the lower staff. Added once the space between the staves is known, and **inserted first** in the
  line's primitives, so the notes are drawn over it.
- **The labels**: two `"n"` primitives (tuplet digits, scale 0.7, grey `#8a8a8a`), centred on the line: the frame
  number (`frame-number`) and above it the time `MM:SS` of the frame (`frame-time`, `frame * 40 ms`, seconds cut
  down). The colon is two dots (`layout.COLON_W`), the upper one moved right with the italic digits. **All labels of
  a line share one height**: `FRAME_NUMBER_CLEAR` (0.8) above the highest staff-1 ink under any of them, at most
  `FRAME_NUMBER_BASE` (-2.4). A label too close to the one before (`FRAME_NUMBER_ROOM`) is left out; its line stays.
  The lyrics count the labels as ink.
- SVG: `<line class="frame-line" data-frame="300" stroke="#b4b4b4" stroke-dasharray=...>`,
  `<g class="frame-number" data-frame="300">` and `<g class="frame-time" data-frame="300">` (`svg.py`; the `<g>`
  takes the primitive's class). `Options.frame_numbers = False` draws no mark.

## 2.3 The range toolbox (task 2b.3)

`FrameRangeFields.tsx`, the first line of both toolboxes: "From frame [283] to frame [495]", the frames of the first
and last columns of the stretch (`readingTools.framesOfRange`). First shown as the title ("Frames 283 – 4…": the title
bar cut it), then as a text line, now two fields at the user's request: new numbers, then Enter or leaving both
fields (moving from one field to the other applies nothing; the first try applied a half-typed range), mark the
stretch `readingTools.rangeOfFrames(from, to, columns)` names: the columns from the first frame to the last, both
included (numbers typed the other way round are swapped; a frame between two columns starts at the next column, or
at the column that sounds there when no column is inside). The page marks it (`markFrames`) and scrolls the band into
view. Escape puts the numbers back; keys in the fields never reach the page's keys (Delete, ⌘Z).

## 2.4 A decoration note lights at its own onset (the user, during this phase)

The user saw a decoration note lit while the blanca before it still sounded. Their rule: a decoration note has an
onset of its own, before its note; it is never part of the chord before it. `geometry.headsByColumn` now returns per
column `now` (heads of its own frame and the next one: a chord played unevenly) and `later` (heads after that, with
their onset in ms). The page lights `later` heads only once the cursor reaches their onset (`laterOnsets`, from the
sheet's notes, so that the render does not read the DOM). The rule of the data (which short note is a decoration note,
implementation 04) did not change.

# 3. Checks

| Check | Result |
|---|---|
| `pytest tests/test_sheet_engrave_frames.py` (marks every 100 frames inside their line, drawn first, number and time on each with one height per line, beyond the lower staff; labels clear of the notes; SVG classes; option off) | passed, with `test_part_sheet`, `test_sheet_toolbox`, `test_sheet_frames` |
| Whole backend `pytest` on the CPU (first version; another project holds 11 GB of the GPU) | all passed except the two `test_transcription_transkun.py` tests that load a CUDA model with the GPU hidden (unrelated) |
| `tsc`, `lint`, `vite build` | clean |
| `check:frames-page` on a copy of 7 Years (57 marks, numbers and times; printed pages; 283 to 495 in the fields; 2598 to 2847 typed and marked, brought into view) | all passed. 7 Years has no decoration note, so the lighting was not tested there |
| `check:frames-page --version c0e39afe-…` on a copy of 99 Red Balloons (48 marks; the decoration note at frame 197, after the column at 173: not lit at the middle between 173 and 197, lit after 197) | all passed; copies deleted (17 projects in the vault, as before) |
| `check:frames-tools` | all passed |
| `scripts/docs/check-links.py` | 0 broken links |

Failures met on the way: the first `check:frames-page` run of the first version timed out before the sheet loaded
(rerun passed); the check first expected a mark at 100 on 7 Years, whose first note is at 177 (the check was wrong);
the fields applied a half-typed range on leaving the first field (fixed, 2.3).

Zoomed look: 99 Red Balloons (page width 130, 200 and the printed page), a song with lyrics blocks, one label at 8x
(the colon). Screenshots in `screenshots/04-3-phase-2b/`.

# 4. Documentation

The core's `sheet/README.md` (frame marks), `context/frontend/annotations.md` (marking a stretch, the fields),
`context/frontend/rendering.md` (`FrameRangeFields.tsx`, the lighting of decoration notes, `check:frames-page`),
`context/04-local-development.md` (`check:frames-page`).

# 5. Needed later

- **Phase 3 and 4**: a place the user writes ("at frame 300") is a `Note.frame` value, the `f300` of the F1 text; a
  mark on the sheet may fall between two columns. The parser of the words (plan 5.10 point 4) can take "frame 300",
  "f300", and a time ("at 01:09" is frame 1725).
- How often the marks appear is one constant (`FRAME_MARK_EVERY`).
