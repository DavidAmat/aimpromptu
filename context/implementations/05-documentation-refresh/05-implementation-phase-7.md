# 05, Phase 7: the sheet toolbox: Info, Key, Transpose, Lyrics, View: report

Wave C (with Phases 4, 12, 16, 17). Written for: the join of wave C and the user's review. Done 2026-11-01.
The plan is [05-plan.md](05-plan.md) section 6, Phase 7. Only documentation changed; no code, test or data.

## Docs changed

- `context/frontend/annotations-sheet.md`: new (179 lines), replaces the old record. The sheet toolbox of the new sheet:
  opening it, **Info**, **Key**, **Transpose** (Notes and Figures, with the preview), **Lyrics** (the words, the pool,
  dragging onto the sheet), the lyrics toolbox of a picked piece, **View**, the keyboard panel, Print to PDF (a pointer
  to `printing.md`), and what was dropped from the old **Layout**.
- `context/archive/old-sheet-tools/annotations-sheet.md`: the old page (147 lines), moved with `git mv` (history kept).
  Its banner now points to the new page; its links repointed to `../../frontend/`. Its text is unchanged.
- `endpoints.md` and `components.md`: checked, no change (see Pending edits).

## What was stale

- The old page told the old sheet's **Layout** tab, the trills, the old `SheetToolbox.tsx` and `TransposeDialog.tsx`. The
  new sheet has **View** (Zoom, Space between lines) and no trills. The new page tells the new one.
- The old **Lyrics** tab's picked-piece toolbar is no longer in the sheet toolbox: the tab is opened with
  `pickedTools={false}` (`FramesSheetToolbox.tsx`). Picked pieces are edited in the lyrics toolbox beside them
  (`FramesLyricsToolbox.tsx`). The new page says so.
- The old page said the Transpose **From** figure is the last **To** kept in `sheet.json` (`figuresFrom`). The sheet
  toolbox passes `figuresFrom={null}` (`FramesSheetToolbox.tsx`), so **From** starts on negra each time the tab opens.
  The new page says what the code does.

## Code and docs that disagree in a way that looks like a bug (for the user)

- `figuresFrom` (`schemas/rhythm.py`, read in `part_sheet/build.py`) is never set by any code, and the sheet toolbox
  never passes it. The Transpose figures tab therefore never remembers its last **To**, as the old page said it did.
  Either the memory was dropped on purpose (the user's Phase 8 answers) or the field is dead. Not decided here.

## New terms for the glossary (for Phase 20)

- **Info** (the tab of the title, subtitle and artist; named **Title** until 2026-10-30).
- **Armadura of the piece** (the Key tab's field).
- **Lyrics pool**, **Add to the pool**, **Merge** (in the pool), the green tick.
- **Lyrics toolbox** (the controls beside a picked lyrics piece).
- **Piano toolbox** (the keyboard panel, titled *Piano*; opened by *Show the keyboard*).
- **Figures** (Transpose by figures; **From** and **To** rows of figure icons).

## Not checked

- The rules of the pool and the picked pieces (the tick box, Merge, Split, the drag onto the sheet, the 120 ms a
  character) are told from the header comments of `LyricsTab.tsx` and `lyricsPieces.ts` and from `lyricsPieces.ts`'s
  constants. `useFramesLyrics.ts` (its drop and refusal rules) was only searched, not read in full.
- "Command-Z brings back every note and figure exactly" (both transpositions) is carried over from the old page and not
  checked in the code this phase.
- "An empty **Title** shows the project's name": only the field's placeholder is in the code read (`pieceLabel`). Not
  checked whether the PDF or the sheet print the project's name in that case.
- The Shift key adding a lyrics piece to the picks is told from the hub, not from the code.
- `FramesPreviewDialog.tsx` (the dialog's words and its **Transpose** and **Cancel**) was not read; its text is the
  one the components page already gives.
- The figure ladder's bounds (redonda to fusa) are read from `TransposeTab.tsx`; the backend's `FIGURES` was not read.

## Pending edits for shared files

**E7.1 `context/frontend/annotations.md`** (the hub; no owner in wave C, so this is a pending edit). Two changes:

1. Line 9. Replace the text
   "`[annotations-sheet.md](annotations-sheet.md): the **sheet toolbox**, still told in the section below until it is rewritten (implementation 05, Phase 7).`"
   by "`[annotations-sheet.md](annotations-sheet.md): the **sheet toolbox**, the lyrics on the sheet, the keyboard panel and Print to PDF.`".
   Keep the rest of the line
   as it is.
2. In the section "The Sheet step's tools" (the bullets of the page), delete the four bullets whose first words are
   **The sheet toolbox** (the sliders icon of the floating bar), **Lyrics blocks**, **Print to PDF** and **The keyboard
   panel** (`⋯` → *Show the keyboard*). Put in their place, at the same spot, one bullet:
   `- **The sheet toolbox**, the lyrics on the sheet, Print to PDF and the keyboard panel: [annotations-sheet.md](annotations-sheet.md).`
   The bullets **Copy and paste**, **A read-only sheet**, **The page of a passage** and the two **Not on the new sheet**
   bullets stay where they are.

   Check for the join: the hub's "Where to look deeper" already links `annotations-sheet.md`; that link stays.

**E7.2 `context/00-index.md`**, the row of `frontend/annotations-sheet.md` (line 81). Replace the description by
"The sheet toolbox of the new sheet: Info, Key, Transpose, Lyrics, View; the keyboard panel; Print to PDF". The link
does not change.

**No change for** `documentation/services/backend/endpoints.md`: the routes `POST /sheet/{uuid}/reading` (its sheet
actions `titles`, `piece-key`, `line-space`, `lyrics`, `figures`), `POST /sheet/{uuid}/transpose`, `GET /sheet/{uuid}/stretch`
and `GET`/`PUT /sheet/{uuid}/words` are already told in sections 4.1 ("The sheet toolbox (Phase 8)", "The words
(Phase 10)") and in the table of section 1.

**No change for** `documentation/services/frontend/components.md`: `FramesSheetToolbox.tsx`, `TransposeTab.tsx`,
`LyricsTab.tsx`, `lyricsPieces.ts`, `FramesLyricsToolbox.tsx`, `useFramesLyrics.ts`, `lyricsText.ts` and `PianoToolboxes.tsx`
are already in the rows of the page's table.

## Checks

- `check-links.py`: 534 files checked, 1 broken link, in `context/ai/level-run.md:27` (`run-history.md`). It is another
  wave's file, not written here; not fixed. My files have no broken link.
- `check-names.py context/frontend/annotations-sheet.md`: 31 names, 0 missing.
- `check-names.py` on the archive page: 4 missing names (`SheetToolbox.tsx`, `TransposeDialog.tsx`, twice). They are
  the old sheet's removed code, named in the banner and the record on purpose. Left as they are.

## Left for later phases

- Phase 8: `printing.md` (the section Print to PDF of `annotations-sheet.md` points to it), and the undo line of
  `sheet-page.md` if it is still needed there.
- Phase 20: the glossary terms above; the closing check of the old-sheet archive row, when the inventory is final.
