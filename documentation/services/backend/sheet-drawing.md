> Context: [context/frontend/rendering.md](../../../context/frontend/rendering.md) (the backend half) ·
> [aitu-backend/src/aitu_backend/sheet/README.md](../../../aitu-backend/src/aitu_backend/sheet/README.md) (sections 10 and 15) ·
> [sheet-f1.md](sheet-f1.md) (the data the drawing reads)

# How the backend draws the sheet

The backend draws the new sheet as one SVG. The page shows that SVG and places its own overlay on it. This page
tells the drawing: the routes, the modules, the layout (columns, spacing, lines), the drawn lines, the glyphs, the
frame marks, the lyrics, the SVG and the pages for paper. The data the drawing reads is in
[sheet-f1.md](sheet-f1.md). The page that shows the drawing is [sheet-page.md](../../../context/frontend/sheet-page.md).

## 1. The routes and the call

| Route (`api/sheet.py`) | What it does |
|---|---|
| `GET /sheet/{audio_uuid}?width=` | `get_sheet` → `_answer`: the part's sheet, drawn for a page `width` staff spaces wide (default `DEFAULT_WIDTH` 130; the query accepts `build.MIN_WIDTH` 60 to `build.MAX_WIDTH` 320). Answers the SVG and the other fields of the page (section 9). |
| `GET /sheet/{audio_uuid}/pages?width=&height=&first=&gap=` | `pages`: the sheet on paper (Print to PDF), dealt onto pages (section 8). |

`_answer` takes the sheet's text (the run's text while the AI writes, else the stored one) and calls
`part_sheet/build.py` `draw(text, width)`. That function clamps the width, reads the text (`sheet/sheet/f1.py`
`read`), lists the drawn notes (`drawn_notes`), and calls `engrave/frames.py` `render_frames(sheet, Options(width=width))`.
The route then adds each note's end frame.

## 2. The modules

Paths are under `aitu-backend/src/aitu_backend/sheet/engrave/`. The line counts are from the code of implementation 05.

| File | Lines | What it does for the new sheet |
|---|---|---|
| `frames.py` | 1,072 | The engine of the new sheet: the columns, the spacing, the line breaks, the drawing of each line, the frame marks, the lyrics, the render step (`render_frames`) and the pages (`render_pages`). Its docstring names the rules. |
| `layout.py` | 2,649 | The drawing rules of the notes, from the bars engine: chords, stems, beams, accidentals, clefs, armaduras, grace notes, ottavas, the brace. `frames.py` calls about thirty of its functions (`L._draw_chord`, `L._draw_beam_group`, `L._draw_key`, ...). Its `STYLES` set the look; `set_style` runs when the module loads, with `"verovio"` as the default. |
| `vrv.py` | 1,196 | Verovio's drawing rules: beam places and slopes, stem lengths, the ledger lines, the rests, the dots, the accidentals. Used through `layout.py` while the style is `"verovio"` (`_vrv()`). |
| `glyphs.py` | 277 | The music font as SVG paths: `box(name)` (the metrics of a glyph) and `path_d(name)` (its outline). The font is Leipzig (section 5). |
| `svg.py` | 172 | `to_svg`: the SVG text of an `Engraving`. |
| `spacing.py` | 72 | `SpacingModel` and `load()`: the measured spacing (section 3). |
| `lyric_text.py` | 69 | `text_width` and `wrap`: how wide the words of a lyrics block are and where they wrap (section 6). |
| `cursor.py` | 119 | `render_song`: the render step of the **bars** sheet (the research viewer's sheet, with compases). Not used by the app; `scripts/draw_sheet.py` calls it. |
| `__init__.py` | 31 | The package's exports: `engrave`, `engrave_frames`, `render`, `render_frames`, `set_style`, `to_svg`. |

Data files in the same folder: `leipzig.json` (the glyphs), `spacing_model.json` (the spacing), and
`lyric_fonts.json` (the widths of the lyrics fonts). They are frozen: section 10 says how each one is made.

The files the page reads in `frames.py` are `FRAME_MS` (40 ms per frame) and `LYRIC_SIZE` in `sheet/sheet/data.py`.

## 3. The layout: from the columns to the lines

`frames.plan(sheet, opts)` makes the `Layout` in these steps:

1. **Columns.** One column for each frame that holds a note. Both hands share the column: what sounds at one frame is
   on one vertical line. A grace note joins the next chord of its hand (one slot per column). A note covered by an
   ornament is not drawn. A unison is merged into one head when `Options.merge_unisons` is on (the default).
2. **Signs.** The printed accidentals come from `sheet/sheet/frames.py` `printed_signs` (the courtesy sign after a
   becuadro included). `_head` gives each head its sign, and `layout.py` places the signs beside the heads.
3. **Clef and armadura changes.** A clef change is drawn before the first column of its hand at or after the change.
   When grace notes sound before the change, the clef goes between them and their note. Changes where a hand plays
   nothing meet before its next chord: only the last one is drawn, and none when it gives back the clef in force. An
   armadura change draws the cancelling becuadros and the new armadura before its column.
4. **Gaps.** `_gap` gives the natural gap after each column from the time to the next column in either hand. The
   reference figure is `Options.quarter_ms`, else `sheet.space_ms`, else `sheet.quarter_ms`, else 500 ms. Figures
   are not read.
5. **Line breaks.** `_break_lines`, greedy, from the start of each line (section 4).

### The spacing

`SpacingModel.gap(ioi)` is `base` × `f(ioi)`, where `ioi` is the time to the next column in negras (the reference
figure). `f` reads the measured `table` (12 values, interpolated on a log scale between the points), a power law
beyond the longest point, and the `floor` below. The values in `spacing_model.json` are: `base` 2.0 (a 16th gap, in
staff spaces), `alpha` 0.377 and `alpha_low` 0.285 (the power above and below a 16th), `floor` 0.72,
`accidental` 0.296 (extra room before a column with a printed sign), `clearance` 0.3 (the least paper between two
glyphs of neighbouring columns).

Empty time is shortened. Up to a blanca (`LONG_GAP`, 2.0 negras) the gap is the measured one. Beyond it, only
`Options.silence` (0.3) of the width the extra time would add is kept.

The least gap of a column is what its glyphs need: the right side of its chords, the left side of the next column,
and `clearance`. The gap is never less than that least gap.

### The line breaks

`_break_lines` fills each line from its start. Among the columns that fill the line to at least `Options.fill`
(0.8 of the staff width), the break goes after the longest pause (the most time between two columns). It never cuts
a beam group when a free place exists. Among the candidates, the cost counts first the beam groups cut with a part of
one note, then all the groups cut; a free place at least half the width from the start is preferred when one exists.
The last line of the song is not stretched when it is under 0.8 of the width (unless `Options.justify_last`).

A line is justified by adding the same amount to every gap. `_break_lines` finds that amount by a binary search (50
steps between -10 and 60 staff spaces) so that the line is `Options.width` wide.

## 4. The drawing of one line

`draw(lay)` draws every line of the plan (or the ones named) in `_draw_system`. A line is drawn in this order:

1. The **header**: the G and F clefs of both staves (`L._draw_key` for the armadura at the start).
2. The **columns**: each chord (`L._draw_chord`), its grace notes (`L._draw_graces`), its stems (`L._draw_unbeamed_stem`
   or the beam groups `L._draw_beam_group` and `L._draw_cross_beam` across the hands), its ornaments, its fingers
   and the ottavas (`L._ottavas`). Ledger lines and the brace come from `L._vrv_ledgers` and `L._vrv_brace`.
3. The **armadura and clef changes** inside the line, and `Options.key_line` (a thin double line before an
   armadura change, off by default).
4. The **frame marks** (`_frame_marks`, section 7).
5. The **lyrics** (`_lyrics`, section 6). They come after the frame marks so that the words clear the numbers.

The systems are then stacked from the top. The gap between two lines is `Sheet.line_space` (when the sheet sets it)
or `Options.system_gap` (5.0). The margin of the whole drawing is 3.0 staff spaces.

`Options` (the defaults): `width` 130 (the staff width, in staff spaces), `min_staff_gap` 6.0, `system_gap` 5.0,
`silence` 0.3, `fill` 0.8, `merge_unisons` True, `quarter_ms` None (the sheet's own), `key_line` False,
`frame_numbers` True, `justify_last` False.

## 5. The glyphs and the style

- The default style is `"verovio"`: the font is **Leipzig** (`glyphs.py`, the file `leipzig.json`, SIL OFL 1.1). Its
  drawing constants are Verovio's (for example `STAFF_LINE_W` 13/180, `STEM_W` 18/180, `BEAM_T` 0.5, `DOT_GAP` 0.5).
- The glyph outlines are in font units of 250 per staff space (`UNITS`). `to_svg` writes each glyph once in `<defs>`
  and places it with one `<use>` per glyph.
- A second style, `"op62"`, exists in `layout.py` (the Leland head, the Leipzig flat, slanting beams). It is not the
  default and nothing in the app selects it. Its engraved heads are off unless its style is chosen (`set_engraved`).

## 6. The lyrics

A lyrics piece is drawn above the upper staff, in the line that holds its first column. Its x is the x of that column
(between two drawn columns, by time, as the cursor's rule). The pieces of one line share one baseline, above the
ink under them: `LYRIC_BASE` is the lowest, `LYRIC_CLEAR` (0.8 staff spaces) the room above the ink. `Lyric.lift`
raises a piece further. Two lines of one piece are `LYRIC_LEADING` (1.2) of its size apart.

- The default size is `LYRIC_SIZE` (1.4 staff spaces); the sizes allowed are 0.8 to 4.2 (`LYRIC_MIN`, `LYRIC_MAX`, in
  `sheet/sheet/data.py`).
- A block put by hand (`at`, `dx`, `dy`) sits where it was put. A block with a `width` is wrapped to it
  (`lyric_text.wrap`, with the advance widths of `lyric_fonts.json`, so that the page and the PDF break the lines in
  the same places). No block passes the end of its line.
- A piece whose frames cross a line break is drawn in one part per line (`lyric_parts`, `data-part`). Its words are
  shared between the parts by the width of its frames on each line.
- The fonts are Lora (serif), Geist and Montserrat (`svg.LYRIC_FAMILIES`). The text colour is `#3a3a3a`.

## 7. The frame marks

Every `FRAME_MARK_EVERY` (100) frames, from the first column on, there is a **frame mark**: a grey dashed line across
both staves and beyond them (`FRAME_LINE_BELOW`, 2.0 staff spaces under the lower staff). It sits at the x of that
frame, by the cursor's rule. It is drawn before the notes, so the notes cover it. On its top, the frame number, and
above it the time of the frame (`mm:ss`, from 40 ms per frame). The numbers of one line share one height, above the
ink of the upper staff under any of them (`FRAME_NUMBER_CLEAR`). A number that would sit too close to the one before
it is left out (`FRAME_NUMBER_ROOM`); its line stays.

The SVG classes are `frame-line` (with `data-frame`, the frame), `frame-number` and `frame-time`. The colours are
`#b4b4b4` for the line and `#8a8a8a` for the numbers. `Options(frame_numbers=False)` draws none.

## 8. The SVG and the pages

`svg.to_svg(eng, px_per_space=10.0, note_ids=True)` writes the SVG. The user unit is the staff space, and the
drawing is scaled by `px_per_space` in the page. The SVG marks:

- `<g class="system">` for each line;
- `data-note="<frame>:<midi>"` on each notehead, the grace notes too (a merged unison lists all its pitches);
- `<text class="lyric" data-lyric data-start data-end>` for each lyrics piece, with `data-base`, `data-width`,
  `data-part`, `font-weight` and `font-style` when they are set, and one `tspan` per line;
- the frame marks as in section 7.

`render_frames` also returns the rows that the page uses (the same keys as `GET /sheet/{audio_uuid}` in section 9):
`columns` (one row for each drawn column: `system`, `frame`, `x` in SVG units with the margin, `ms` = frame × 40),
`systems` (`index`, `first` and `last` frame, `top`, `bottom`, `staff_top`, `staff_bottom`, `left`, `right`), `width`,
`height`, `lines` (the systems of the whole song) and `timings` (`parse_ms`, `plan_ms`, `draw_ms`, `svg_ms`,
`cursor_ms`, `total_ms`).

`render_frames(segment=(a, b))` draws only the systems that hold a column of frames `[a, b)`, with the line breaks
of the whole song. The app's routes do not pass `segment`: they draw the whole song. Only the scripts use it.

**The pages** (`render_pages`, Print to PDF): the song is drawn once at the paper's width (`Options.width`), and then
whole lines are dealt onto pages `page_height` staff spaces high. The first page is `first_height` (under its title).
A line never splits across a page turn; a line taller than a page has a page of its own. `gap` is the space between
two lines on paper (the default is the sheet's `line_space`). The route `GET /sheet/{audio_uuid}/pages` checks its
query: `width` 40 to `MAX_WIDTH`, `height` 20 to 1000, `first` 10 to 1000, `gap` 0 to 40. Each page answers `svg`,
`width`, `height`, `first` and `last` (the frames of its first and last columns). The route also answers
`build.sheet_settings` (the titles, the lyrics and the line space of the sheet).

## 9. The answer of `GET /sheet/{audio_uuid}`

Besides the SVG, the columns and the systems (section 8), `build.draw` answers `notes` (`drawn_notes`: `ref`,
`hand`, `pitch`, `figure`, `beam`, `grace`, `fixed`, `graceRule`, `spelled`, `finger`, `ornaments`, `ottava`),
`reading` (the key, the armadura and clef changes, `reading_summary`) and the sheet's settings (`sheet_settings`:
titles, lyrics, `quarterMs`, `spaceMs`, `lineSpace`). `_answer` adds `segments`, `source`, `stale`, `llm`, `editable`,
`history`, `audioRevision` and the end frame of each note. The fields of the edits are in
[endpoints.md](endpoints.md) (and [sheet-f1.md](sheet-f1.md) for the data).

## 10. Frozen data and where it comes from

| File | Made by |
|---|---|
| `leipzig.json` | `aitu_research.engrave.glyphs.export_bundle` (the research repository, not this one) |
| `spacing_model.json` | `aitu_research.engrave.spacing.fit`: the refit on 31,133 clean gaps (its `source` field says so) |
| `lyric_fonts.json` | `aitu-frontend/scripts/measure-lyric-fonts.mjs`, measured in the browser with the app's own fonts |

The listing of the frozen files is in [`sheet/README.md`](../../../aitu-backend/src/aitu_backend/sheet/README.md) section 6.

## 11. Tests and scripts

- `aitu-backend/tests/test_sheet_engrave_frames.py`: each note drawn once, the two hands on one column x, the printed
  signs, the grace notes and their clefs, the clef and armadura changes, the empty time, the line breaks (beam groups
  kept whole, the width filled), one segment drawn with the whole song's breaks, the beams across the hands, the
  frame marks and their numbers.
- `aitu-backend/tests/test_sheet_toolbox.py`: the lyrics blocks (the format, the wrapping, the drawing, a piece over a
  line break) and the route of the sheet's settings.
- `aitu-backend/scripts/draw_frames.py`: draws the parts of the app (or a layer) with the new engine, checks each note
  is drawn once and counts the beam groups a break cuts, and times the cold and the warm draws.
- `aitu-backend/scripts/frames_gallery.py`: the gallery of the new sheet beside the bars sheet (`render_frames` with
  `segment`).
- `aitu-backend/scripts/draw_sheet.py`: the bars sheet, through `cursor.render_song`.
