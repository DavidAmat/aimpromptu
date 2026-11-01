# 05, Phase 6: the range toolbox, copy and paste: report

Wave B (with Phases 3, 10, 11, 15). Written for: the join of wave B and the user's review. Done 2026-11-01.

## Docs changed

- `context/frontend/annotations-stretches.md`: new (113 lines). The range toolbox of the new sheet (*Frames*): the
  marking of a stretch, the frame numbers, the title bar's actions, the tabs Key, Clef, Octave, Copy and Paste,
  Delete these frames, the Record and Start-a-new-part actions. Replaces the old record.
- `context/archive/old-sheet-tools/annotations-stretches.md`: the old page (96 lines), moved with `git mv` (history
  kept). Its banner now points to the new page; its links repointed to `../../frontend/`. Its text is unchanged.
- `context/backend/editing.md`: a copy of picked notes (the frames it takes); a section **Delete these frames** (the
  route `/take-out`, its undo, its `409`s).
- `documentation/services/backend/editing-and-compose.md`: the copy of picked notes; a paragraph **Delete these
  frames** (`edits.take_out` → `paste.cut`, `record_version`, `notesRemoved`, the `409`s); the module path
  `../audio/timeline.py` made `audio/timeline.py`; the sentence on `history.restore` (its answer is the redo's number,
  not a `keptVersion`; that name is not in the code).

## What was stale

- The old page described the range toolbox of the old sheet (spacing, speed, the dragged octave lines), not the new one.
- The new range toolbox's title bar (**Delete these frames**, the two frame fields, the **Select the N notes** count,
  the **Use D major here** button) was told nowhere on a `context/` page; only the hub's bullets and the code comments.
- The compose doc had no take-out (`POST /take-out`, from commit ec9c510 of 2026-10-30) and said
  `keptVersion`, which the code does not return.
- `paste.py` has no commits since 2026-10-27, so the paste rules of the compose doc (sections 2 and 4) were kept as they
  are; each was checked against `editing/paste.py` and `part_sheet/edits.py`.

## Code and docs that disagree in a way that looks like a bug (for the user)

None found in this phase. Two things to know, not bugs:

- The copy of picked notes takes the frames to "the later of the column after the last picked note and the end of the
  longest picked note" (`FramesSheetPage.tsx`, `copySelection`). The old page said "to the end of the longest one":
  the new rule is the one written.
- `POST /sheet/{uuid}/take-out` accepts `end` ≤ `start` in the schema (only `end >= 1`); the service refuses it with
  `409` ("Mark a stretch first."). The docs say `409`, which is right.

## New terms for the glossary (for Phase 20)

- **Delete these frames**: the range toolbox's bin: the stretch taken out, its notes and audio with it.
- **Start a new part here**: the range toolbox's split (a project of parts).
- **Use D major here**: the button of the Key tab when another armadura prints fewer signs over the stretch.
- **Copy of picked notes**: the copy of the frames the picked notes cover, when no stretch is marked.
- The step label **Take out N s**: the undo label of Delete these frames.

## Not checked

- The marking gestures and the look of the stretch (click, drag, Shift-click, the lavender band, the grey line every
  100 frames): taken from the hub and the code comments, not re-read in `FramesSheetView.tsx`.
- The clef rule's behaviour (**Clefs by the rule**): named, not re-read (it is `rendering.md`'s subject).
- `GET /sheet/{uuid}/stretch`'s answer shape: named, not read in `reading.py`.
- The app was not run (the rules of the plan).
- `check-names.py` on the moved archive page and on the compose doc's section 8 (the removed staged session) lists names
  of removed code. Kept on purpose: history. The archive page also lists `RangeToolbox.tsx`, `useRangeActions.ts` and
  `DEFAULT_CLEF_RULE`, which are the old sheet's (removed 2026-10-27).

## Pending edits for shared files

1. `context/frontend/annotations.md` (the hub; no owner in wave B). Its three range-toolbox texts move to
   `annotations-stretches.md`:
   a. The first bullet of the intro list (the one that starts `- [annotations-stretches.md]`
      and [annotations-sheet.md]`): replace its text by
      `- [annotations-stretches.md](annotations-stretches.md): the **range toolbox**, copy and paste, **Delete these frames**. [annotations-sheet.md](annotations-sheet.md): the **sheet toolbox**, still told in the section below until it is rewritten (implementation 05, Phase 7).`
      (This removes the sentence "Both pages still tell the old sheet…".)
   b. In section "The new sheet", the bullet `- **Mark a stretch**: …` (it ends with "…Each toolbox hands its selection
      to the other from its title bar."): replace the whole bullet by
      `- **Mark a stretch**: a click, a drag or Shift-click in the strip above the upper staff; the range toolbox opens beside it. One selection at a time: picking notes drops the stretch, and the other way round. The detail is in [annotations-stretches.md](annotations-stretches.md).`
   c. The bullet `- **The range toolbox**: **Key** (…` (its tabs, through "A tab with a dot means the stretch already carries that setting."): replace the whole bullet by
      `- **The range toolbox** (*Frames*): the frame numbers, **Which staff**, the tabs **Key**, **Clef** and **Octave**, its title bar's actions. Detail in [annotations-stretches.md](annotations-stretches.md).`
   d. The bullet `- **Copy and paste** (Phase 8B): …` (through "…a blank sheet … says *Nothing to write yet.*"): replace the
      whole bullet by
      `- **Copy and paste** (Phase 8B): copy with ⌘C, the toolboxes' title bars or the read-only panel; paste with ⌘V or the floating bar. Detail in [annotations-stretches.md](annotations-stretches.md) and [annotations-notes.md](annotations-notes.md).`
      The bullets **Record a passage at the end** and the blank sheet's empty state stay out of this page: the
      Recording in Sheet page tells them (Phase 17).
   Keep the file's style (bold labels, one bullet each).
2. `context/00-index.md`, line 80 (`frontend/annotations-stretches.md`): the description becomes
   `The range toolbox of the new sheet (*Frames*): the frame numbers, Which staff, Key, Clef, Octave, the title bar's actions, Copy and Paste, Delete these frames`.
3. `context/00-index.md`, the Archive table (the row that lists `archive/old-sheet-tools/annotations-notes.md`): add
   `[archive/old-sheet-tools/annotations-stretches.md](archive/old-sheet-tools/annotations-stretches.md)` to the cell
   of the links, and to the description: "the old sheet's range toolbox" after "the old sheet's toolbox pages".
4. `context/00-index.md`, line 48 (`backend/editing.md`): the description becomes
   `Paste, Delete these frames, and Recording in Sheet: the length rule, the promotions, the undo`.
5. `documentation/services/frontend/components.md`, line 259: the row `frames/FramesRangeToolbox.tsx` gets the text
   `The range toolbox (titled *Frames*): Which staff, Key, Clef, Octave, and the title bar's actions (Record this passage, Start a new part here, Delete these frames, Copy this stretch, Enhance, Select)`,
   and a new row after it:
   `| \`frames/FrameRangeFields.tsx\` | The two frame-number fields of the range toolbox's first line (implementation 04-3, Phase 2b) |`
6. `documentation/services/backend/endpoints.md`, the row of `POST | \`/sheet/{uuid}/paste\``: append to its text
   ` 404 when the copied passage cannot be read; 409 when the AI writes the sheet or the paste is refused.`
   (The rows of `/take-out`, `/stretch` and `/paste` already exist, from the join of wave A.)

## Left for later phases

- Phase 10: the hub's **Enhance with AI** of a stretch (the bullet `- **Enhance with AI** of a stretch`) and the
  title bar's AI button of the range toolbox move to the AI pages; `annotations-stretches.md` names it only as "told in
  annotations.md" (its table row), to be re-pointed then.
- Phase 17: the blank sheet's **Record a passage** and the floating bar's **Record a passage at the end** (the page of a
  passage), and **Start a new part here** in `playlists.md` (its split).
- Phase 20: the glossary terms above; the archive row (pending edit 3).

Commit: `Docs 05, Phase 6: the range toolbox, copy and paste` (the files named one by one).

## Note for the join

Commit `cfb4479` (this phase) also carries, in `05-checklist.md`, the ticks of Phases 3 and 11 that those agents had
written to the shared file but not yet committed. They were not mine to commit; the join of wave B should read the
checklist as it is and check that the two reports exist.
