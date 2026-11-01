# 05, Phase 17: Recording in Sheet, passages, Compose and parts (wave C)

Plan: [05-plan.md](05-plan.md) section 6, Phase 17. Written for: the join of wave C and the next agent.

## Docs changed

- [recording-in-sheet.md](../../../context/frontend/recording-in-sheet.md): the floating bar's and the blank sheet's
  labels are the code's (**Record a passage at the end**, **Record a passage**); "the sheet is saved first when it has
  changes" replaced by the code's rule (the sheet is always saved); the Proposal's sheet toolbox tab is **View**, not
  "Layout".
- [playlists.md](../../../context/frontend/playlists.md) sections 1 and 2: "Choose a project" is plain text (not a label of
  the page); **Add the whole project** named as the button of a project with no sheet; the **+** above the list is named
  by its title, **Add a passage**.
- [editing.md](../../../context/backend/editing.md) (Recording in Sheet): the same label fix as above.
- [editing-and-compose.md](../../../documentation/services/backend/editing-and-compose.md) section 7: `tests/test_paste.py`
  has 17 test functions, not 16.

## What was stale

- The label of the floating bar's and the blank sheet's entry points (three pages said **Record a passage**, the code has
  **Record a passage at the end** on the bar; the blank sheet's is **Record a passage**).
- "The sheet is saved first when it has changes": `FramesSheetPage.tsx` `startPassage` says the sheet is always saved and
  nothing is saved first.
- The Proposal's sheet toolbox tab: **View** (`FramesSheetToolbox.tsx`), named "Layout" in one place of the page.
- The test count of `test_paste.py` (17).
- Checked and still true: the passage page's labels (Promote, Fit to the window, Replace the whole passage, Keep the
  original audio, Use my recording, Put it in, Write the proposal, Notes from, MIDI piano, Sound, No sound, Play the passage
  along, Close the recording, Discard this passage), the speed ×0.25 to ×4, the take's -1 dB peak and +40 dB gain limit
  (`audio/formats.py`), the title `<song> m:ss–m:ss`, the take names, the endpoints of `/passages` and of the parts
  (`api/passages.py`, `api/projects.py`), the compose page's labels and the parts panel (shown from two parts, labels
  **Rename**, **Move up**, **Move down**, **Join with “…”**, **Start a new part here** in the range toolbox).

## Code and docs that disagree in a way that looks like a bug (for the user)

- None found in this scope. Small wording mismatch only: the Promote dialog's title says "Put the take in" for a new
  passage; its button is **Put it in** (the doc names the button).

## New terms for the glossary (for Phase 20)

- **Current** and **Proposal**: already in the user's words of [01-app-context.md](../../app/01-app-context.md) (the
  Recording in Sheet section); no new entry, only a line that says what each shows on the page of a passage.
- **Take**: a recording (or a MIDI keys take) of a passage, a hidden project.
- **The window**: the part of the take the Current covers; it is dragged over the Proposal.
- **Put it in**: the one choice of a new passage (no take to fit over the song).

## Not checked

- Not run: no app started, no test run, no MIDI or microphone check (the rule: documentation workers read code and git).
- "Joins and splits are not on the sheet's undo" (editing-and-compose section 4): taken from the doc, not traced in
  `editing/parts.py`.
- "Save to library saves every part" (playlists section 2): Phase 14's `SaveToLibraryDialog`, not read.
- The secure-address claim (`http://ubuntu:5173`, the SSH tunnel to `localhost:5173`) in recording-in-sheet section 4:
  not compared with [04-local-development.md](../../../context/04-local-development.md).
- Test counts: counted by `grep -c "^def test_"`; parametrized cases not counted.

## Pending edits for shared files

- **E17.1** `context/frontend/projects.md`, section 6 (Recording in Sheet), the sentence that begins "**Record a passage**
  on the floating bar and on a blank sheet opens a new passage at the end." Change to: "**Record a passage at the end**
  (the floating bar) and **Record a passage** (a blank sheet) open a new passage at the end." Owner in wave C: 16 (the
  file is wave A's 14). Join C applies it.
- `documentation/services/backend/endpoints.md`: no change (sections 5 and 7 checked against `api/passages.py` and
  `api/projects.py`).
- `documentation/services/frontend/components.md`: no change (sections 3.1, 3.2 checked against
  `pages/piece/passage/PassagePage.tsx`, `pages/compose/ComposePage.tsx`, `PartsPanel.tsx`).
- `context/00-index.md`: no new page from this phase.

## Left for later phases

- Phase 20: the glossary terms above (Current, Proposal, Take, The window, Put it in) in `context/app/01-app-context.md`.
- Phase 20 (the whole-scope check): `documentation/services/backend/editing-and-compose.md` section 8 ("Removed in Phase
  9") names 8 removed files and one identifier that `check-names.py` lists as missing. That is the history of the removal,
  on purpose; leave it.
- Join C: the link check reports two broken links in `05-implementation-phase-7.md` (lines 60 and 61, `annotations-sheet.md`).
  That report is Phase 7's (wave C, not yet done); it is not this phase's file.
