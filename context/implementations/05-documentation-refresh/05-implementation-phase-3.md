# 05, Phase 3: How the sheet is drawn (the backend): report

Plan: [`05-plan.md`](05-plan.md), section 6, Phase 3 (wave B). Checklist: [`05-checklist.md`](05-checklist.md).
Written for: the join of wave B and the agent of Phase 4 (the frontend half of the same drawing).

## Docs changed

- `documentation/services/backend/sheet-drawing.md` (new, 205 lines): the two routes and the call to `build.draw`; the
  modules of `sheet/engrave/`; the layout (columns, spacing, empty time, line breaks, justification); the drawing of
  one line; the glyphs (Leipzig, the `"verovio"` style, `"op62"` off); the lyrics; the frame marks; the SVG marks and
  the pages; the answer of `GET /sheet/{uuid}`; the frozen data and who makes it; the tests and scripts.
- `context/frontend/rendering.md`: the backend half. A pointer in the intro and a line in "Where to look deeper". The
  rest of the backend half was true when checked (see "What was stale").
- `aitu-backend/src/aitu_backend/sheet/README.md`: section 1, the sentence "how it is drawn is in ... (Phase 3)" is a
  link now; sections 10 and 15 get a pointer each to `sheet-drawing.md`. No claim of those sections was changed.
- `05-inventory.md`: the row of `rendering.md` (`updated`), the core README's state, the row of the new page (`new`).
- `05-checklist.md`: Phase 3 ticked.

Not changed: `endpoints.md` (both routes, `GET /sheet/{uuid}?width=N` and `GET /sheet/{uuid}/pages`, are already
listed with the right query: no pending edit). The frontend half of `rendering.md` is Phase 4's.

## What was stale

- `rendering.md`, backend half: nothing false found. It names `engrave.frames`, the Leipzig glyphs and the route
  `GET /sheet/{part}?width=N`; all three are right. It lacked a pointer to the drawing's own page: added.
- Core README section 1: "(Phase 3)" after a page name that did not exist yet: now a link to the page.
- Core README section 10 (the drawing part): every name, constant and output key I checked is right (`Options`
  defaults, `LONG_GAP`, `FRAME_MARK_EVERY`, the `columns` and `systems` keys, the tests and the scripts).
- Core README section 15 (paper pages, lyrics): checked, right. Its routes match `api/sheet.py`.
- `sheet-f1.md` line 7 says the drawing page is "written by Phase 3 of implementation 05": now it exists. Pending
  edit E3 below.

## Code and docs that disagree (for the user)

1. `sheet/engrave/frames.py`, the module docstring, "Line breaks": "a changed segment moves the rest of the sheet
   little (Phase 5 redraws one segment)". The app's routes never pass `segment=` (only `scripts/draw_frames.py` and
   `scripts/frames_gallery.py` do). `part_sheet/build.py` `draw` draws the whole song on each request. The docstring
   describes a path the app does not take. The docs say what the code does (section 8 of `sheet-drawing.md`).
2. `sheet/engrave/spacing.py`: the class defaults (`alpha` 0.38, `floor` 0.78) differ from `spacing_model.json`
   (`alpha` 0.377, `floor` 0.72). `load()` reads the JSON, so the app uses the JSON. Looks intended; the defaults are
   only for a model without its file.
3. `sheet/engrave/cursor.py` (`render_song`, the bars sheet) has no caller in the app; only `scripts/draw_sheet.py`
   uses it. The docs say so. If the bars sheet is meant to be kept only for the research, the module docstring could
   say so too.

## New terms for the glossary (Phase 20)

- **frame mark**: a grey dashed line on every 100 frames (4 seconds), with its frame number and its time above it.
- **empty time**: time between two columns beyond a blanca; drawn at 0.3 (`Options.silence`) of the width it would take.
- **column**: one drawn frame, with the chords of both hands on one vertical line (the page's term is already "column").

## Not checked

- The "about 20 ms per song" time in the core README's section 10 diagram: not measured; left as it is.
- The `"op62"` style's details: only the switch and its purpose were read; its drawing constants were not compared.
- The keys of `sheet_settings` beyond `titles` and `lyrics` (`quarterMs`, `spaceMs`, `lineSpace`) come from the core
  README's section 15; I read the first lines of the function only.
- No code was run and no test was run (the rules of the plan). The tests named in the page were read by their names
  and docstrings only.
- `scripts/grace_gallery.py` (it also calls `render_frames`) is not described in the page.
- `check-names.py` (below): the four names it lists are the expected ones, see below.

## Checks

- `check-links.py`: 526 files checked, 0 broken links.
- `check-names.py` on the three files I changed: 3 docs, 328 names, 4 missing:
  - `sheet-drawing.md:10` `context/frontend/sheet-page.md`: the page is Phase 4's (a plain-text name until it exists).
  - `rendering.md:90`, `92` `components/time/TimeScoreView.tsx`, `VexflowSheetPage`, `TimeScoreView`: the removed old
    sheet, named in its history section on purpose.

## Pending edits for shared files

- **E1** `documentation/services/README.md`, the table of the backend files (after the row of `sheet-f1.md`): add
  ```text
  | [sheet-drawing.md](backend/sheet-drawing.md) | How the backend draws the sheet: the routes, the layout and the lines, the glyphs, the frame marks, the lyrics, the SVG and the pages |
  ```
- **E2** `context/00-index.md`, the table of the documentation files (after the row of `sheet-f1.md`, line ~293): add
  ```text
  | [../documentation/services/backend/sheet-drawing.md](../documentation/services/backend/sheet-drawing.md) | How the backend draws the new sheet: the routes, the layout and the lines, the glyphs, the frame marks, the lyrics, the SVG and the pages |
  ```
- **E3** `documentation/services/backend/sheet-f1.md`, line 7 (Phase 2's file): replace
  "The drawing is told in `sheet-drawing.md`, written by Phase 3 of implementation 05." with
  "The drawing is told in [sheet-drawing.md](sheet-drawing.md)."

## Left for later phases

- Phase 4: in `sheet-drawing.md` line 10, turn `context/frontend/sheet-page.md` into a link once the page exists (it
  is plain text now). Also the frontend half of `rendering.md`.
- Phase 20: the core README's map at its top should list section 10's pointer to `sheet-drawing.md`.
- Phase 20: the glossary terms in the section above.
