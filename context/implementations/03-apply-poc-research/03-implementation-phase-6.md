# 03: Phase 6 report: editing the new sheet (the edit model, hands, undo)

Plan: [`03-plan.md`](03-plan.md) section 7, Phase 6. Checklist: [`03-checklist.md`](03-checklist.md). Branch
`feat/migrate-new-logic` (fast-forwarded to `master`'s merge commit of Phase 5; no other change on `master`).
Written 2026-10-25 on the Ubuntu machine. **Built; waiting for the user's check in the browser.**

# 1. Summary

| Task | Result |
|---|---|
| 6.1 Study | Section 2: the old editor keeps every reading decision in one page value saved by **Save**, writes six edits to the recording at once (a hand move among them), and has one undo history in the page, lost on a reload. The new sheet had no editing |
| 6.2 The edit model | `aitu_backend/part_sheet/edits.py`: an edit writes the hands into `notes.pmn` and stores `sheet.f1` laid again on them, in one write under the part's lock; every edit is one step of the part's log `sheet.edits.json`; undo and redo walk it in the backend. Routes `POST /sheet/{uuid}/hands`, `/undo`, `/redo`, each answering the sheet drawn again (section 4) |
| 6.3 The hand tool and the question | Notes are picked on the sheet (a click, ⌘ or Shift, a box); the note toolbox of the new sheet has **Hand: Right / Left**; Undo and Redo on the floating bar and the keys. A note that changes staff gets the clefs and 8va of the clef rules around it (`build.fit_clefs`). The user's answer: an AI run again may change any hand; on a sheet the AI enhanced it reads the current hands as a suggestion (section 3) |
| 6.4 The time of one edit | About a quarter of a second from the click to the new drawing on the page (section 6); the engine **stays in the backend** |

# 2. The study (task 6.1)

## 2.1 The old editor (vexflow-v2)

| Part | Where | What the phase found |
|---|---|---|
| The reading decisions | `sheetEdits.ts` (`SheetEdits`, 22 fields: figures, key and key changes, clefs, 8va, trills, lyrics, fingers, beam breaks and joins, spacing, notes off the page, grace notes, ...) | One value in the page, so that undo is "the value before". Written into `sheet.json` only by **Save** (`PUT /time/{uuid}/rhythm`); a dot on Save says there are changes |
| Undo and redo | `hooks/useEditHistory.ts` | A reducer over that value: one press of the browser's event loop is one step, at most 100 steps, labels per field ("Fingering", "Beam"). A step may carry two backend calls (`effects.undo`, `effects.redo`); the state moves only when the call succeeded. The history lives in the page: a reload loses it |
| Edits written to the recording | `SheetPage.tsx` | Six: a note added on the keyboard panel, a hand move, a notes transposition, a paste, a promotion of a re-recorded passage (undo by `restoreVersion` of the part's history), and Remove all (no undo) |
| The hand move | `SheetPage.moveSelected`, `PUT /time/{uuid}/hands` (`api/time_score.py`) | The notes are named by column and row of the old split; the route writes the hand on the note id in `notes.pmn` (`save_edit`, `hands_changed`, `sheet_follows`), first saving every note's hand when the hands were never saved as a whole. The step carries the call with the old hands and the call with the new ones. Fingers, figures and beam breaks of the moved notes move with them in the page value |
| The two selections | `TimeScoreView.tsx` (vexflow-v2) | Noteheads (click, ⌘-click, a rubber band) open the note toolbox; a stretch of columns (click above the staves) opens the range toolbox |
| The panels | `ui/Toolbox.tsx`, `toolboxPlacement.ts`, `NoteToolbox.tsx` | A draggable panel beside the notes, rows of a short label and controls; **Hand** is a `Segmented` Right / Left |

## 2.2 The new sheet before this phase

The Phase 5 page (`pages/piece/sheet/frames/`) drew the SVG of the backend and its cursor; a click moved the
recording. Each notehead carries `data-note="<frame>:<midi>"` (the drawn column and the sounding key) but nothing
says its hand or its printed name. The backend's sheet of a part (`part_sheet.build.current`) is the stored
`sheet.f1` when it was written for the current `handsRevision`, or laid again on the current hands (`reapply`), or
the algorithm's. A hand moved in the old sheet already reached the new one through `notes.pmn` (Phase 5 report
section 8).

## 2.3 What this decided

- **The truth an edit changes** is the one of plan section 3.7: the hands in `notes.pmn`; the reading in
  `sheet.f1`. The page never holds a decision of its own: there is nothing to save, so the new sheet has no **Save**.
- **Undo in the backend**, not in the page. A step is checked against the stored truth when it is walked (a hand
  changed since by something else stays), it survives a reload, and Phase 7's reading edits fit the same step
  (a line patch of `sheet.f1`).
- **The whole sheet drawn again**, not one segment: a hand move changes the figures of its neighbours (a figure is
  the note's length up to the next note of its hand) and may add a clef change, and the whole sheet draws in about
  50 ms. `render_frames(segment=...)` stays available if a song ever needs it.

# 3. The user's answer, and what it changed

The question (plan task 6.3): when the user moved notes to the other hand and later runs the AI again, what happens
to the moves? Options: keep them (the AI must keep them; a line in the prompt); the AI may change them (it sees every
current hand as a suggestion); the AI starts from zero (as Phase 5: no hands shown, the moves lost). The user chose
**the AI may change them** (2026-10-25).

- `job.start` runs `write_frames(hands=True)` on a sheet the AI enhanced (a run again): the input shows the current
  hands, which are the AI's own plus the user's moves. A first run (the hands are the hand split's or old Predict
  hands) still reads the notes without hands, as the research recommends (showing Opus the algorithm's hands moved it
  from 98.8 % to 95.1 % of the notes in the printed hand).
- `window_prompt` adds one line under the target when it shows hands: "The target shows the current hand of each
  note (written in an earlier run; the user may have moved some). Read them as a suggestion: keep the hands that
  follow the rules, and change any that does not." The cached instructions (version 5) did not change; the record of
  such a run says `prompt: "5+hands"`.
- **Checked with real requests** (`scratchpad` script, nothing stored): 7 Years with its AI hands, 3 right-hand
  melody notes of the first window moved to the left hand on purpose, then 2 windows with the hands shown. Both
  windows were accepted at the first check; Sonnet put the 3 notes back in the right hand and changed no other hand of
  the 137 notes in the windows; 2 requests, $0.0624.
- The run's end (`job.commit`) starts the log of steps again (`edits.forget`): its hands replace the ones the steps
  name.
- **No edit while the AI writes the sheet**: the routes answer `409`, the page disables the toolbox and the arrows
  with the reason in their tooltip. The job writes the hands of every note at its end, so a hand moved during the
  run would be lost; and the user's rule (plan 3.7) allows edits only where the AI has decided. Allowing edits on the
  decided segments during a run is possible (the job would compare the hands it read with the hands at its end and
  keep the ones changed meanwhile), but not needed now.

# 4. The backend

## 4.1 `part_sheet/edits.py`

`move_hands(part, refs, hand)` under `pipeline.piece_lock`:

1. The refs (`"<frame>:<midi>"`, the noteheads' `data-note`) become note ids: the live notes by drawn column (the
   D-04 group start, `drawn_columns`) and sounding key, as `build.hands_of_sheet` reads them. A ref with no note is
   counted in `unmatched`.
2. When the hands were never saved as a whole (`saved_hands.hands_complete`), every note first gets the hand the
   sheet draws now (`hands_of_sheet` of the current sheet), so the notes the user did not touch keep their staff
   (the old route does the same with the split).
3. The moved notes get the hand; `save_edit(notes_changed=False, hands_changed=True, sheet_follows=True)`.
4. A stored sheet the AI wrote (record source `llm` or `mixed`) is laid again on the new hands (`build.reapply`) and
   stored for the new `handsRevision`, with its record (the windows, the AI mark, the cost) unchanged. A sheet the
   algorithm wrote is not stored: it is computed from the notes and their hands.
5. One step goes into `sheet.edits.json`: the label ("Move 3 notes to the left hand"), each changed note's hand
   and `hand_guessed` before and after, and the change of `sheet.f1` (the hash of the text before and after, one line
   patch each way). The redo list is cleared; 50 steps are kept.

`undo` and `redo` walk the last step. A note is set back only when its decided hand is still the one the step left
(a guessed hand counts as none: `save_edit`'s quick rule marks the notes without a hand as guessed once the hands
were saved as a whole, and the first test found it). `sheet.f1` is patched only when its hash and its
`handsRevision` are the ones the step left; otherwise the sheet is laid again on the hands when drawn (case 2 of
`build`). The log is forgotten by `job.commit` (an AI run wrote the hands and the sheet) and `store.clear` (a new
transcription). It is not in the file lists of duplicate, export, Save to library or the history: a copy starts
without steps.

The line patch was first a full `difflib` diff (30 ms on a song); an edit changes one stretch, so the patch is now
the common start and end left out and one replacement (0.4 ms).

## 4.2 Clefs around a moved note (`build.fit_clefs`)

The first browser run moved the D5 of 7 Years (the right hand's melody) to the left hand: the note kept the bass
clef with five ledger lines above the staff, because `reapply` keeps the stored clefs. The AI's checker forbids
four or more (rule clef.L3), so an edit could leave a sheet the AI would never write, and a passage moved in a box
would be worse. The old sheet has the same fault for one note (its clef rule needs four chords).

`reapply` now collects the notes that are on another staff than in the stored sheet, or new to it, and
`fit_clefs` runs the algorithm's rule (`proposal.frames.clefs_and_ottavas`, the clef rules version 4) on a copy of
the sheet. For each staff with such a note, on the stretch of columns around it where the rule's clef and 8va
differ from the stored ones, the rule's replace them (the clef changes at the stretch's start and end connect it to
the stored clefs); the rest of the sheet keeps its stored clefs and 8va. D5 now gets a small treble clef in the
left hand (checked zoomed in against the data, section 7). It also removes an 8va carried into the bass clef by a
moved note, which `frames.check` forbids. Test: `test_a_high_run_moved_to_the_left_hand_gets_the_treble_clef_for_its_stretch_only`.

## 4.3 Routes and answers (`api/sheet.py`)

- `POST /sheet/{uuid}/hands?width=N` `{notes, hand}`, `POST /sheet/{uuid}/undo?width=N`, `/redo`: the answer of
  `GET /sheet/{uuid}` (the sheet drawn again for that width) plus `moved` and `unmatched`, or `walked` (the step's
  label). `409` while the AI writes; the rights check of every `POST` (a version of My library answers `403`).
- `GET /sheet/{uuid}` also answers `notes` (each drawn note: `ref`, `hand`, `pitch` as printed, from
  `build.drawn_notes`), `editable` (write access and no AI run) and `history` (`undo`, `redo` labels).
- `documentation/services/backend/endpoints.md` section 4.1.

# 5. The frontend

- `FramesSheetView.tsx`: with `onPick`, a click on a notehead (within 6 px; a notehead is about 8 px wide) picks it
  and moves the recording to it, ⌘/Control or Shift adds it (or takes it away when already picked), a box dragged
  across the staves (5 px of movement starts it) picks every notehead whose centre is inside; a click off the notes
  drops the pick and moves the recording, as before. Picked heads carry `data-selected` (dark Lavender, the colour of
  a selection in the app); lit heads (the cursor's column) are blue over it.
- `FramesNoteToolbox.tsx`: the old panel (`Toolbox`), titled with the printed name in solfège (`Re 5`, from the
  backend's `pitch`) or "N notes", the time under it; the row **Hand** with `Segmented` Right / Left (mixed when the
  notes are in both hands). Disabled with the reason while the AI writes.
- `FramesSheetPage.tsx`: the picked refs (pruned to the notes the sheet still holds after an edit), the toolbox
  opened beside them (measured when a pick starts), Undo and Redo on the floating bar with the step's label in the
  tooltip ("Undo: Move a note to the left hand"), ⌘Z / ⇧⌘Z / Control-Y and Escape. Play mode and a version of My
  library pick nothing.
- `useFramesSheet.ts`: `edit(call)` sends one edit at a time and puts its answer on the page; a failure is shown in
  a warning above the sheet.
- `api/sheet.ts`: `SheetNote`, `SheetHistory`, `SheetEdited`, `sheetApi.moveHands`, `sheetApi.walk`.

# 6. Measurements: the time of one edit, and where the engine runs (task 6.4)

**In the page** (`npm run check:frames-edit`, a copy of 7 Years, 1,458 notes, Chromium at 1440 px, the app in its
containers, 10 moves of one note between the hands, from the click to the frame after the new SVG is in the page):

| | Median |
|---|---|
| Total | 231 ms (187 to 310) |
| Backend (request sent to first byte back) | 155 ms |
| Transfer of the answer (about 540 KB, gzipped on the wire) | 1 ms |
| The page (reading the answer, the new SVG put in and painted) | 74 ms |

**In the backend** (host, warm, median of 3 runs on 3 AI sheets: 7 Years, Hips Don't Lie, Shut Up and Dance):

| Step | ms |
|---|---|
| Read `notes.pmn` | 4.3 |
| The sheet now (`build.current`) | 7.5 |
| Find the notes of the refs | 1.6 |
| `save_edit`: the notes the sheet places | 8.8 |
| Lay the sheet again on the new hands, with the clefs (`reapply`; half of it is `propose_frames`) | 62.7 |
| Write the F1 text | 2.3 |
| The patch for undo | 0.4 (30.3 with a full diff) |
| Draw the whole sheet (`render_frames`) | 49.9 |

**Decision: the engine stays in the backend.** One edit reaches the page in about a quarter of a second. A
TypeScript engine in the browser would remove the drawing (about 50 ms) and the transfer (a few ms on the local
network), but not the rules that lay the sheet on the new hands (figures, grace notes, beam groups, spelling, the
clefs: about 65 ms), which would need the whole core ported, with its golden files, for at most a third of the
time. The cost of the page itself (about 74 ms: parsing and painting a 400 to 550 KB SVG) is the same either way.
If Phase 7 finds an edit that must feel instant (a drag), the first step is to draw only the systems of the edited
stretch (`render_frames(segment=...)`) and replace them in the page.

# 7. Checks

| Check | Result |
|---|---|
| `tests/test_sheet_edits.py` (new, 8 tests) | The drawing names each notehead with its hand and printed name; a hand move on the algorithm's sheet (written into the notes, nothing stored, undo exact, redo); on the AI's sheet (stored current, the AI mark and windows kept, undo restores the stored text exactly); undo leaves a hand changed since by something else; an AI run starts the steps again and a run again shows the hands with the suggestion line; no edit while the AI writes (`409`); unknown refs counted; a high run moved to the left hand gets the treble clef for its stretch only (`frames.check` clean) |
| Backend, full run in the image **on the CPU** | 1,349 tests: 1,347 passed, 1 skipped (it needs a GPU), 1 failed: `test_the_worked_example_at_00_46_prints_three_equal_corcheas`, failing since Phase 0 |
| `flake8`, `black` on the new and changed files | clean |
| `npx tsc -b`, `npx eslint src` | clean |
| `npm run check:frames-edit` (new) | All 14 passed: a click picks a note and opens the toolbox titled Re 5, Control-click adds one, **Left** moves it (the backend agrees), the sheet keeps its AI mark, Undo names the step, Control-Z, Control-Shift-Z, Undo after a reload, a box picks 11 notes; 10 moves timed |
| `npm run check:frames-sheet`, `npm run check:play` | All passed (the lyrics of Play mode skipped until Phase 8, as in Phase 5): a click off the notes still moves the cursor, Play mode picks nothing |
| The drawings | The moved D5 of 7 Years, before and after, zoomed in at 2x and compared with the data: before, a blanca on the treble staff; after, a redonda in the left hand after a small treble clef, the right-hand note before it a redonda (its next right-hand note is now later), the rest of the line unchanged |
| A real AI run with the hands shown | 2 windows of 7 Years, section 3: accepted at the first check, $0.0624 |
| `scripts/docs/check-links.py` | 413 files checked, 0 broken links |

# 8. The audio after a jump (the user's report during the check)

The user found that on 7 Years, after moving the cursor and playing, a passage sometimes did not match the notes,
while playing from the start matched everywhere. The notes and the cursor were right: the audio element landed in
the wrong place. A part without cuts played its stored file, here an MP3 of variable bitrate (frames of 32 to
320 kbps) whose only seek table is a Xing header of 100 points; Chromium jumps inside it by guessing the byte of a
time. Measured in Chromium (an audio element captured after each jump and matched to an exact decode of the file):
the MP3 landed 28 to 659 ms behind the time it reported, depending on the place (150 s: 533 ms at both jumps there;
30 s: 28 ms); a constant-bitrate MP3, within one frame (24 ms); a FLAC, exactly where asked at every jump (the same
83 ms of measuring delay everywhere).

The fix (`audio/piece_audio.listen_copy`, `GET /audio/{uuid}/file`): a part without cuts whose stored file is not
WAV or FLAC plays a lossless FLAC copy (`cache/<part>/listen-<stored name>.flac`, 16-bit, its own rate and channels),
decoded by the same ffmpeg that wrote the engine's audio; made on the first play (0.4 s for 7 Years, 12.6 MB against
the MP3's 7.3 MB) and kept. `?original=true` (the Audio tab, downloads) still serves the stored file. Every player
reads this address (the new and old sheets, Play mode, the Notes step, the video pages). The same measurement on the
file the app now serves: 10 of 10 jumps exact. Test: `test_a_compressed_original_plays_as_a_lossless_copy_and_downloads_as_it_is`.

# 9. Notes for later phases

- **Phase 7 (the tools).** A tool is a function of `part_sheet/edits.py` that changes `notes.pmn` or `sheet.f1` under
  the part's lock and records one `_Step` (hands before and after, a line patch of `sheet.f1`), a route of
  `api/sheet.py` that answers `_answer(...)`, and a row of `FramesNoteToolbox.tsx` that calls it through
  `useFramesSheet`'s `edit`. A **reading edit on a sheet the algorithm wrote** must store it: today an `algorithm`
  record is computed again from the notes, not read, so the record needs a source for "the algorithm's, edited by
  the user" (and `build._compute` must read it as stored). The labels say what the user did ("Move 3 notes to the
  left hand").
- **The range toolbox** (a stretch of columns) is not on the new sheet yet; Phase 7 adds the second selection
  (click above the staves) beside the notes' one.
- **Matching a stored sheet to the notes** is still by drawn column and key (`build.reapply`): a paste moves the
  columns after it, so the stored decisions there are lost (Phase 5 report section 8).
- **The old sheet's undo and the new one are separate**: a hand moved in the old sheet reaches the new sheet through
  `notes.pmn` but is not a step of the new log (and the other way round).
- **Edits during an AI run** are closed (section 3); opening them on the decided segments is the job's comparison of
  the hands it read with the hands at its end.
- **The toolbox placement** follows the old one (to the right of the notes, or to the left when there is no room):
  for a note at the end of a line it covers the notes before it on that line; it can be dragged.
- The scratch scripts (the timing of each step, the AI run with the hands shown) are not kept; their numbers are in
  sections 3 and 6.

# 10. Documentation

- `aitu-backend/src/aitu_backend/sheet/README.md` section 13; `part_sheet/__init__.py`; `context/backend/README.md`.
- `documentation/services/backend/endpoints.md` (the routes table and section 4.1); `context/07-database.md`
  (`sheet.edits.json`).
- `context/frontend/annotations.md` (section "The new sheet"), `context/frontend/rendering.md` (the files, the hooks,
  the checks, the engine decision).
- [`03-plan.md`](03-plan.md) section 3.7, Phase 6 tasks, the Phase 7 note, section 8, section 11;
  [`03-checklist.md`](03-checklist.md), [`README.md`](README.md), `../README.md`, `../../00-index.md`.
