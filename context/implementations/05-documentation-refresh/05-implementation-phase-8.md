# 05, Phase 8: Undo, redo, the preview and the PDF: report

Wave D. Plan section 6, Phase 8; checklist 8.1 and 8.2. Docs only; no code read beyond the named files.

## Docs changed

- `context/frontend/printing.md`: rewritten for the new sheet. The dialog's controls with their defaults and limits, the
  lines to a page (the staff-space arguments of `GET /sheet/{uuid}/pages`), the pages drawn by the backend, the PDF
  writer in one paragraph. The old renderer's page (frame numbers, Bravura, 450 kB) is kept as one history section.
- `documentation/services/frontend/score-pdf.md`: rewritten for the current writer (`FramesPdfDialog.tsx`,
  `print/scorePdf.ts`, `drawPage.ts`, `pdf.ts`). The `width`/`height`/`first`/`gap` arithmetic of the page request, the
  glyphs as paths, the nine base fonts, no music font embedded, the selector `[data-pdf-page]`.
- `context/frontend/sheet-page.md`: new section 13, **Undo and redo** (the log `sheet.edits.json`, the buttons and the
  keys, what a step holds, the copies a paste, a promotion and a Revert keep, when the log starts again). The last
  "Where to look deeper" line now says "the PDF and its pages". The page is 217 lines, over the 200 of the plan.
- `context/implementations/05-documentation-refresh/05-inventory.md`: the four rows of these files (states, lines).

## What was stale

- `printing.md`: the PDF button "on the Piano Sheet tab's floating bar"; the old panel's "five lines to a page" with the
  frame-number strip as the main decision; Bravura as embedded; the sizes (450 kB, 60 kB) that no one measured here.
- `score-pdf.md`: the default selector `.grid-page` (now `[data-pdf-page]`); the file table listed
  `src/print/opentype.ts` and `public/fonts/bravura.otf`, and neither exists; the "Fonts in the file" section described
  a Bravura embedding that the writer no longer has (`PDF_BASE_FONTS` only).
- `sheet-page.md`: no section told the undo of the sheet (the backend log, 50 steps, the keys ⌘Z, ⇧⌘Z, ⌘Y).
- `endpoints.md`: checked, no change needed. `/undo`, `/redo` (lines 115 and 720), `/pages` (lines 136 and 783) and the
  paste's undo (line 775) are already told.

## Code and docs that disagree (for the user)

- `context/frontend/rendering.md` line 32 groups `FramesPreviewDialog.tsx` with the PDF dialog. The code says it is the
  preview of **Transpose** (its header; `Transpose` button; `data-transpose-dialog`). The PDF's pages are shown inside
  `FramesPdfDialog.tsx`. Pending edit E8.4 below fixes the wording.
- `context/frontend/rendering.md` line 50 says the browser checks cover "the frame marks on the sheet and on the printed
  pages". This phase did not verify it (see Not checked). If the frame marks do not print, that line is wrong.
- `aitu-frontend/src/hooks/useEditHistory.ts` (the generic undo hook) is used by the Notes step, the Audio step and
  `notes/noteEdits.ts`, not by the sheet. The sheet's undo is the backend log. Not a bug; it is easy to confuse.

## New terms for the glossary (Phase 20)

- **the sheet's log** (`sheet.edits.json`): the steps of undo and redo of a part's sheet.
- **Print to PDF**: the sheet's button that opens the PDF dialog; the dialog's title is **Download the sheet as a PDF**.
- **Size of the music** and **Space between lines**: the printed staff (5 to 8 mm) and the white between lines (1 to 20 mm).

## Not checked

- File sizes of a PDF. Removed from the docs, not measured (no running the app).
- Whether the frame marks and the cursor are drawn on the printed pages (see the disagreement above). The pages come from
  `render_pages` (`sheet/engrave/frames.py`, from line 1016); its body was not read.
- The folio's exact place on the page (the bottom margin); `drawPage.ts` was read by its function list and by its
  text, path and glyph paths only, not in full.
- `documentation/services/backend/paths-and-data.md`: the five names the checker lists in its other sections (`session.json`
  line 336, `/hf/hub` line 480, `scripts/migrate/to_database.py` line 513, `AITU_DATA_DIR` line 518, `bench_pieces.py` and
  `bench_payloads.py` line 532). They are not in Phase 8's part; Phase 13 or 20 should look at them.

## Pending edits for shared files

Owner in wave D: `paths-and-data.md` is Phase 13's file in D; `rendering.md` has no owner in D. Apply them at the join of
wave D, in this order.

- **E8.1** `documentation/services/backend/paths-and-data.md`, section 4.5, the table, first row. Replace the cell
  "A paste (Phase 8); a promotion of a re-recorded passage (Phase 9)" with "A paste; a promotion of a re-recorded
  passage (`edits.record_version`); the start of an AI run, for **Revert** (`edits.snapshot_before_run`); the Lab's step
  that makes a video into the piece (`video/piece.py`, `write`, when the part has notes)". The rest of the row stays.
- **E8.2** The same file, section 4.5, the paragraph that starts "**Putting a snapshot back**". Replace "the undo and the
  redo of a paste" with "the undo and the redo of a paste and of a promotion, the **Revert** of an AI run
  (`edits.revert_run`), and the rollback of a paste that fails (`editing/paste.py`)". The sentence "since implementation
  03 called by the sheet's log" stays.
- **E8.3** The same file, section 2.4, the sentence "**`sheet.edits.json`** is the part's log of steps
  (`part_sheet/edits.py`, at most 50)." Add after it: "It starts again when a whole AI run writes the sheet, and a new
  transcription deletes it (`part_sheet/store.py`)."
- **E8.4** `context/frontend/rendering.md`, line 32 (the list under the frontend files). Replace "and the dialogs
  `FramesPdfDialog.tsx`, `FramesPreviewDialog.tsx`: the tools and the runs, told in" with "and the dialogs
  `FramesPdfDialog.tsx` (Print to PDF, [printing.md](printing.md)) and `FramesPreviewDialog.tsx` (the preview of
  **Transpose**): the tools and the runs, told in".

No change needed in `endpoints.md`, `components.md`, `00-index.md` or `documentation/services/README.md` for this phase.

## Checks

- `check-links.py`: 542 files, 0 broken links.
- `check-names.py` on `printing.md`, `score-pdf.md`, `sheet-page.md`: 93 names, 1 missing, `public/fonts/bravura.otf` in
  `score-pdf.md` line 74. It is there on purpose, as the record of a removed font.

## Left for later phases

- Phase 13: the log of AI runs does not touch these files. Nothing for it here.
- Phase 20: `sheet-page.md` is 217 lines (over 200); the glossary terms above; the disagreements for the user above.
