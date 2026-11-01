# Rendering: how the sheet is drawn

The sheet is drawn by the backend, not in the browser. Since implementation 03 (plan:
[`implementations/03-apply-poc-research/03-plan.md`](../implementations/03-apply-poc-research/03-plan.md)) every
screen that shows a sheet (the Sheet step, a version of My library, Play mode, the two sheets of a passage, From
other projects, the requests review) asks `GET /sheet/{uuid}` for an SVG and draws it with
`pages/piece/sheet/frames/FramesSheetPage`. `SheetPage.tsx` keeps only the step types and `SheetPage`, which draws
`FramesSheetPage`.

## The sheet (implementation 03, Phases 5 to 8)

It is the sheet without compases, tempo, puntillos or silencios, which the backend draws
(`aitu_backend.sheet.engrave.frames`, the Leipzig glyphs and Verovio's drawing rules). The page asks `GET /sheet/{part}?width=N` for the width it has (about 8.5 px a staff
space) and gets one SVG and a cursor map: one row per drawn column (its line, its x, its time) and one box per
line. The backend side (the layout, the lines, the frame marks, the lyrics, the SVG, the pages) is told in
[sheet-drawing.md](../../documentation/services/backend/sheet-drawing.md).

The frontend side is told in [sheet-page.md](sheet-page.md): the header and the buttons, the floating toolbox, the
zoom, the cursor and the recording, what the view draws over the drawing, and the keys. In short, the code is in
`pages/piece/sheet/frames/`:

- `FramesSheetPage.tsx`: the page (the header, the buttons, the floating toolbox, the zoom, the recording, the keys,
  the toolboxes and the dialogs);
- `FramesSheetView.tsx`: the SVG as the backend wrote it, scaled to the page, and an overlay in the same units (the
  cursor, the lit noteheads, the picked notes, the marked stretch, the lyrics pieces, the veil and the reveal of a
  segment the AI writes, the batches of a run);
- `useFramesSheet.ts`: the sheet as the page holds it (read for the width, read again at each message of the AI's
  job on its stream, `event: sheet`; an edit is one request whose answer is the sheet drawn again);
- `geometry.ts`: the page's arithmetic (where the cursor is, the time under a point, the noteheads of a column);
- `FramesNoteToolbox.tsx`, `FramesRangeToolbox.tsx`, `FramesSheetToolbox.tsx`, `FramesLyricsToolbox.tsx`,
  `EnhanceDialog.tsx`, `AiRunPanel.tsx`, `AiRunDetail.tsx`, `AiHistoryPanel.tsx`, `PatternCatalog.tsx`, and the
  dialogs `FramesPdfDialog.tsx`, `FramesPreviewDialog.tsx`: the tools and the runs, told in
  [annotations.md](annotations.md) and [`context/ai/`](../ai/README.md).

Hooks for the browser checks: `[data-frames-sheet]` (`data-source`, `data-llm`, `data-working`),
`data-note="<frame>:<midi>"` on each notehead, `[data-lit]`, `[data-frames-cursor]` (`data-ms`, `data-dragging`),
`[data-segment-state=working]`, `[data-revealing]`, `[data-selected]` on the picked noteheads, `[data-pick-box]`,
`[data-frames-note-toolbox]`, `sheet-undo`, `sheet-redo` (`data-testid`), `[data-range-strip]`,
`[data-range-band]` (`data-start`, `data-end`), `[data-frames-range-toolbox]`, the `data-testid` of each tool
(`figure-4`, `beam-join`, `grace`, `ornament-trill`, `notes-remove`, `range-enhance`, `stretch-words`, ...),
`[data-lyric]` (`data-lyric-lit`, `data-lyric-picked`), `[data-lyric-landing]`, `[data-frames-sheet-toolbox]`,
`[data-pdf-page]`, `sheet-toolbox`, `sheet-print`, `line-space`, `piece-key`, `pdf-download` (`data-testid`),
`[data-sheet-header]`, `[data-sheet-header-buttons]`, `header-floating-toggle` (`data-testid`), `[data-floating-hide]`,
`[data-floating-show]`, `[data-enhance-dialog]`, `[data-enhance-status]`, `song-run-*`, `song-confirm`,
`stretch-confirm`. The checks are `npm run check:frames-sheet` (`--live` spends a few cents of the AI on a 40 s
clip), `npm run check:frames-edit` (picking, the hand, undo and redo, and the time of one edit),
`npm run check:frames-tools` (every tool of the two toolboxes and the range selection; `--live` makes one stretch
request, about $0.01), `npm run check:frames-toolbox` (the sheet toolbox, lyrics, the keyboard panel, Print to PDF,
the lyrics in Play mode), `npm run check:frames-page` (the header, the floating bar hidden and shown, the wheel
zoom, the cursor dragged across lines, the frame marks on the sheet and on the printed pages, the frames typed in
the range toolbox, a decoration note lit at its own onset) and `npm run check:enhance-dialog` (the dialog; a stand-in
answers the requests that would start the AI).

The engine stays in the backend (implementation 03, Phase 6, task 4): one edit takes about a quarter of a second
from the click to the new drawing on the page, most of it in the backend's rules (the stored sheet laid again on
the new hands), which a browser port of the drawing alone would not remove.

## Rules that stay from the old sheet

The sheet keeps the time model of [`../backend/time-model.md`](../backend/time-model.md): no Beats Per Minute (BPM),
no bar lines, no time signature, no metre, and the new sheet goes further (no compases, no tempo, no puntillos, no
silencios). The **reference figure** (the length the sheet calls a negra, `quarterMs` of `sheet.f1`) is named by
the AI (a reference request) or by the algorithm (`proposal.beat`), not by the reader; **Transpose figures** of the
sheet toolbox is the override. The music is laid out again for a narrower window or for the paper, never shrunk
([printing.md](printing.md)).

## The old sheet (vexflow-v2), removed in implementation 03, Phase 10

Until Phase 8B a second sheet lived beside this one: the staff was drawn in the browser by
`@aimpromptu/grid-notation`, a TypeScript package developed in the sibling `vexflow-v2` checkout, through one file,
`components/time/TimeScoreView.tsx`, on the page `VexflowSheetPage`. Phase 8B made every screen draw the new sheet,
and Phase 10 (2026-10-27) removed the old one: the package dependency, its build step in the frontend image, the
page, `TimeScoreView`, its toolboxes and `npm run check:render`. Its renderer (one `time → x` map shared by both
staves, the space between lines, the magnifier, the octave brackets, the beam rules, the stale-`dist` trap) is
described in [`documentation/deprecated/grid-notation.md`](../../documentation/deprecated/grid-notation.md), kept
as the record.

## Where to look deeper

- [`documentation/services/backend/sheet-drawing.md`](../../documentation/services/backend/sheet-drawing.md): how the
  backend draws the sheet (the routes, the layout, the lines, the glyphs, the SVG, the pages)
- [sheet-page.md](sheet-page.md): the Sheet page, the frontend shell of the sheet
- `aitu-backend/src/aitu_backend/sheet/README.md` sections 9 to 17: the engine, the AI step, the edits, the tools,
  the marks of the old sheets
- [`documentation/services/frontend/components.md`](../../documentation/services/frontend/components.md) section 3:
  the modules of the page
- [`../backend/time-model.md`](../backend/time-model.md): why the layout is what it is
- [annotations.md](annotations.md): the tools of the sheet
- [printing.md](printing.md): the same drawing, on paper
