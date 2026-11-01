# 05, Phase 5: the note toolbox

Wave A. The plan is [05-plan.md](05-plan.md) section 6, Phase 5. Only documentation changed; no code, test or data.

## Docs changed

- [context/frontend/annotations-notes.md](../../frontend/annotations-notes.md): new, 88 lines. The note toolbox of the new
  sheet: picking, the title bar, the rows (figures, finger, alteration, hand, beam, grace, duplicate, unite, marks, take
  off), the chord keyboard, and the routes and functions each edit goes through.
- [context/frontend/annotations.md](../../frontend/annotations.md): the hub, 142 lines (was 276). Its old-sheet sections
  moved to the archive; its note bullets became one pointer; its intro and "Where to look deeper" rewritten.
- `context/archive/old-sheet-tools/annotations-notes.md`: the old note page, moved with `git mv`; its links fixed.
- `context/archive/old-sheet-tools/annotations-hub-old-sheet.md`: new. The old sheet's page, defaults, selections, undo,
  saving and column address, moved from the hub; links fixed.
- [context/backend/editing.md](../../backend/editing.md): a section "The note edits" before "Undo" (the routes, the
  reading actions, the notes written in `notes.pmn`, one step of undo each).

## What was stale

- The hub's old-sheet sections (about 150 lines: the page, defaults, selections, "Taking it back", "Keeping it", the
  column address) described the removed sheet. Archived.
- The old note page told the Save button, `PUT /time/{uuid}/hands` and `NoteToolbox.tsx`, all gone.
- The note toolbox's Alteration, Duplicate, Unite and Grace rows, and the chord keyboard, were told nowhere.
- `editing.md` told paste and undo only; the note routes were told in no `context/` page.

## Code and docs that disagree in a way that looks like a bug

- Plan section 6, Phase 5 names `aitu-backend/src/aitu_backend/editing/marks.py` for the note toolbox. It is the
  `sheet.json` marks module of the old sheet, used by `editing/paste.py`; no note edit uses it. The plan should drop it
  from Phase 5 (the note edits are in `part_sheet/reading.py` and `part_sheet/edits.py`).
- `documentation/services/frontend/components.md` lines 243 and 508 still name `NoteToolbox`, `RangeToolbox`,
  `SheetToolbox`. Probably the "Removed" section; not checked (see below).

## New terms for the glossary (Phase 20)

- **Chord keyboard**: the keyboard of the note toolbox, the picked notes' column, lit in the hands' colours.
- **Alteration**: the spelling of a note by hand (the same key under another name).
- **Duplicate**, **Unite**: the two note edits that change how many notes a chord has and how long they are.
- **Back to the figures of the rule** (⌫): the figure given back to the rule.

## Not checked

- "A note's printed length runs to the next onset of its hand" (the Hand row): carried from the old page. `note_ends`
  exists in `part_sheet/edits.py`; the rule itself was not read.
- Beam rules: the UI's test (`beamable`) and the docstring of `join_beam` were read; `_run` and `_beam_check` were not.
- Unite's figure: from the docstring of `unite_notes`, not from the arithmetic.
- The Enhance button's condition (`aiHere`, `sheet.llm.canRun`): read in the page, not traced further.
- `check-names.py` on the archive files lists 6 names (old files, the old `/time/{uuid}/default-reading` route). Expected
  in history. The three live files list none.
- The app was not run (the rules of the plan).

## Pending edits for shared files

1. `documentation/services/backend/endpoints.md`, section 4.1 table, after the row of `POST /sheet/{uuid}/remove` add:
   - `| POST | \`/sheet/{uuid}/duplicate\` | Phase 5: **Duplicate** of the note toolbox: \`{notes, figure}\` (\`figure\` 2 to 64, shorter than each note's own); each picked note played again at that figure, filling its own time; one step of undo; the sheet drawn again. 400 for a figure not shorter. |`
   - `| POST | \`/sheet/{uuid}/unite\` | Phase 5: **Unite** of the note toolbox: \`{notes}\`; consecutive chords of one hand with the same keys become one chord of the figure that fills their time; one step of undo. |`
   - `| POST | \`/sheet/{uuid}/take-out\` | Phase 5: **Delete these frames** of the range toolbox: \`{start, end}\`; their notes and audio taken out, everything after moved earlier; one step of undo; answers \`notesRemoved\`. 409 when a paste cannot be made. |`
   - Check first (join): if Phase 6 adds the same `take-out` row, keep one.
2. `documentation/services/frontend/components.md`, line 224: replace the row text by
   `| \`frames/FramesNoteToolbox.tsx\`, \`readingTools.ts\` | The note toolbox: figures, alteration, finger, hand, beam, grace, duplicate, unite, marks, take off the page; its chord keyboard (\`ChordKeys\`); what the toolboxes share (\`readingTools.ts\`) |`
   and keep \`FramesRangeToolbox.tsx\` as its own row (Phase 6 owns it): `| \`frames/FramesRangeToolbox.tsx\` | The range toolbox (titled *Frames*) |`.
3. `context/00-index.md`, line 76 (`frontend/annotations.md`): the description becomes
   `**The Sheet step**: the hub of the new sheet's tools (the note, range and sheet toolboxes, undo, the AI mark); the old sheet's sections are in the archive`.
4. `context/00-index.md`, line 77 (`frontend/annotations-notes.md`): the description becomes
   `The note toolbox of the new sheet: figures, alteration, fingers, hand, beams, grace notes, duplicate, unite, marks, take off the page, the chord keyboard`.
5. `context/00-index.md`, the Archive table (line ~263): add a row
   `| \`archive/old-sheet-tools/\` | The old sheet's toolbox pages and the hub's old-sheet sections: \`annotations-notes.md\`, \`annotations-hub-old-sheet.md\` (the record of the vexflow-v2 sheet, implementation 03, Phase 10) |`
   (a folder, with no README: the join may link the two files instead).

## Left for later phases

- Phase 6: the hub's range-toolbox bullets (**The range toolbox**, **Mark a stretch**, the "one selection at a time" line)
  move into `context/frontend/annotations-stretches.md`; the hub's sentence "Both pages still tell the old sheet…" is
  removed then.
- Phase 7: the hub's sheet-toolbox bullets (**The sheet toolbox**, **Lyrics blocks**, **Print to PDF**, **The keyboard
  panel**) move into `annotations-sheet.md`; the same sentence goes.
- Phases 9 and 10: the hub's **Enhance with AI** bullets (of a stretch, the whole song, **Enhance it again**) move to
  `context/ai/`. The note toolbox's Enhance button (in `annotations-notes.md`) then links to the stretch page.
- Phase 4: the hub's **Undo and Redo** and **No Save button** bullets fit `sheet-page.md` better; decide there.
- Phase 20: the glossary terms above; the archive row (pending edit 5).
