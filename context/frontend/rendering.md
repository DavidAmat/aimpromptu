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
line. The code is `pages/piece/sheet/frames/`:

- `FramesSheetPage.tsx`: the page (title lines, the player, the floating bar with Undo, Redo and **Enhance with
  AI**), and since Phase 6 the notes picked and the keys (⌘Z, ⇧⌘Z, Escape); since implementation 04, Phase 1, the
  header at the top of the window (the title, `AiMark`, and the floating bar's buttons: one list, `sheetButtons`,
  drawn in both places), the floating bar's hidden state (`aitu.framesSheet.floatingHidden` in this browser), and
  ⌘ and the wheel over the sheet (a CSS scale at once, one `GET /sheet` at a pause of 220 ms, the line under the
  pointer kept under it);
- `FramesNoteToolbox.tsx` (Phase 6): the note toolbox of the new sheet, beside the notes picked: **Hand** since
  Phase 6, every other note tool since Phase 7, and since Phase 8A the keyboard of the picked column (drawn by
  `ui/MiniPiano.tsx`'s `MiniKeys`; see [annotations.md](annotations.md), "The new sheet");
- `FramesRangeToolbox.tsx` (Phase 7): the range toolbox (*Frames*: Both / Right / Left, Key, Clef, Octave);
  `EnhanceDialog.tsx` (implementation 04, Phase 4): **Enhance with AI**, one dialog with two tabs, **A stretch**
  (both hands or one, the other then fixed; the user's words) and **The whole song** (**Simplify** the left hand, the
  right hand or both; **Write it all again**), each with its cost; `readingTools.ts`: what the two toolboxes share;
- `FramesSheetView.tsx`: the SVG as the backend wrote it, scaled to the page, and an overlay in the same units:
  the cursor (a line between two columns by their times), the lit noteheads of its column, the pale veil on the
  part Sonnet works on, and the blank staves that a part coming back from Sonnet is written into, column by
  column (about two seconds; when the AI writes one hand only, the segment's `staff`, both cover only that staff,
  cut halfway between the staves by `geometry.onStaff`); since Phase 6 also the picking of notes (a click on a notehead, ⌘ or Shift to add,
  a box dragged across the staves), and since Phase 7 the marking of a stretch in the strip above the upper staff
  of a line, drawn as a lavender band over the staves in scope; since implementation 04, Phase 1, the cursor
  dragged and dropped (`grab`, `grabbing`, across lines, the page scrolled near the window's edges, a seek on
  release; a press that does not move stays a click);
- `geometry.ts`: the research viewer's arithmetic (where the cursor is, the time under a click);
- `useFramesSheet.ts`: the loads, Sonnet's job followed on its stream (`event: sheet`), Sonnet started by
  itself on a new transcription, and an edit (one request whose answer is the sheet drawn again);
- since Phase 8: `FramesSheetToolbox.tsx` (Title, Key, Transpose, Lyrics, View), `FramesPreviewDialog.tsx` (the
  preview of a transposition), `FramesPdfDialog.tsx` (Print to PDF), `useFramesLyrics.ts` (the old Lyrics tab and
  its piece helpers on the sheet's `lyric` lines); the lyrics are drawn by the backend (`<text data-lyric>`), and
  the view picks, drags and lights them.

Hooks for the browser checks: `[data-frames-sheet]` (`data-source`, `data-llm`, `data-working`),
`data-note="<frame>:<midi>"` on each notehead, `[data-lit]`, `[data-frames-cursor]` (`data-ms`, `data-dragging`),
`[data-segment-state=working]`, `[data-revealing]`; since Phase 6 `[data-selected]` on the picked noteheads,
`[data-pick-box]`, `[data-frames-note-toolbox]`, and `sheet-undo`, `sheet-redo` (`data-testid`); since Phase 7
`[data-range-strip]`, `[data-range-band]` (`data-start`, `data-end`), `[data-frames-range-toolbox]`, and the
`data-testid` of each tool (`figure-4`, `beam-join`, `grace`, `ornament-trill`, `notes-remove`, `range-enhance`,
`stretch-words`, ...); since Phase 8 `[data-lyric]` (`data-lyric-lit`, `data-lyric-picked`), `[data-lyric-landing]`,
`[data-frames-sheet-toolbox]`, `[data-pdf-page]`, and `sheet-toolbox`, `sheet-print`, `line-space`, `piece-key`,
`pdf-download` (`data-testid`); since implementation 04 `[data-sheet-header]`, `[data-sheet-header-buttons]`,
`header-floating-toggle` (`data-testid`), `[data-floating-hide]`, `[data-floating-show]` (Phase 1), and
`[data-enhance-dialog]`, `[data-enhance-status]`, `song-run-*`, `song-confirm`, `stretch-confirm` (Phase 4). The checks are `npm run check:frames-sheet` (`--live` spends a few cents of Sonnet on a 40 s
clip), `npm run check:frames-edit` (picking, the hand, undo and redo, and the time of one edit) and
`npm run check:frames-tools` (every tool of the two toolboxes and the range selection; `--live` makes one stretch
request, about $0.01) and `npm run check:frames-toolbox` (Phase 8: the sheet toolbox, lyrics, the keyboard panel,
Print to PDF, the lyrics in Play mode), and since implementation 04 `npm run check:frames-page` (Phase 1: the header,
the floating bar hidden and shown, the wheel zoom, the cursor dragged across lines) and `npm run
check:enhance-dialog` (Phase 4: the dialog; a stand-in answers the requests that would start the AI).

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

- `aitu-backend/src/aitu_backend/sheet/README.md` sections 9 to 17: the engine, the AI step, the edits, the tools,
  the marks of the old sheets
- [`documentation/services/frontend/components.md`](../../documentation/services/frontend/components.md) section 3:
  the modules of the page
- [`../backend/time-model.md`](../backend/time-model.md): why the layout is what it is
- [annotations.md](annotations.md): the tools of the sheet
- [printing.md](printing.md): the same drawing, on paper
