# 08 Phase 7: The Notes tab: the live piano roll visualization and the editor

The plan is [`08-plan.md`](08-plan.md) section 9.5, and section 12, Phase 7. The status lookup is
[`08-checklist.md`](08-checklist.md). This report is for the agents of later phases: what was built,
the choices made inside the phase, the measurements, and what Phases 8 and 9 must know.

# 1. What was done

| Task | Result |
|---|---|
| 7.1.1 typed arrays | `src/notes/rollNotes.ts`: `RollNotes`, one typed array per field (`id`, `key`, `onMs`, `lenMs`, `hand`, `flags`, `spawn`), a slot per note, `id -> slot` map. Two indexes rebuilt once after a change: by onset (a range query is one binary search) and by key (hit test, same-key neighbours). `subscribe`/`commit` tell the canvas to paint |
| 7.1.2 painting | `components/notes/PianoRollCanvas.tsx` and `rollPaint.ts`: two canvases. Lower: rows, time grid, ruler, keyboard, rectangles of the visible range only. Upper: playhead, lit keys, sounding notes, band. One `requestAnimationFrame` loop that runs only while something moves (live stream, reveal, playback) and asks for exactly one frame (section 2.7) |
| 7.1.3 keyboard | Drawn on the canvas, one row per key (section 2.1). During playback the keys of the sounding notes are lit in their colour on the upper canvas |
| 7.2.1 stream queue | `src/notes/liveFeed.ts` (`LiveFeed`) and `useLiveTranscription.ts`: `chunk` frames go into a queue, drained once per animation frame; a rectangle that arrives closed grows from left to right over 250 ms; open notes are drawn up to the frontier |
| 7.2.2 progress bar | `components/notes/RollTimeBar.tsx`: smoothed between chunks by `ProgressEstimator` (the idea of MuScriptor's `progress.ts`, own code), "1:32 / 3:09 · 600 notes · 0:12 elapsed · about 14 s left", then "Transcribed in 0:25" as a chip. The time taken is measured on the backend's clock (progress frame timestamps) |
| 7.2.3 final replace | After `done`, `refresh()`, then `GET /pieces/{uuid}/notes` replaces the streamed notes in place (same ids; the lag correction moves them a few ms); the view stays where the live view ended |
| 7.3.1 playback | `useCutPlayer(audioApi.fileUrl(uuid), [], frames)` reused. The playhead is moved in the time ruler (press, drag) or on the bar under the roll (the scrub bar); **Follow playhead** turns the page when the playhead leaves the view, and jumps to it when playback starts outside the view |
| 7.3.2 cuts | Nothing to jump: since the Phase 6 change (plan section 9.2) `GET /audio/{uuid}/file` serves the edited audio once cuts are saved, which is in the time of the notes. Checked on the piece of `check:flow`, which has a 38 s cut: the playhead keeps the pace of the audio from the ruler's position |
| 7.4.1 selection | Click, Command-click (add or remove), drag on empty space (band, with Command or Shift it adds), Command-A, Escape |
| 7.4.2 move and resize | Drag a rectangle (Shift: also the key), drag its left or right edge (6 px), arrow keys (10 ms, Shift 100 ms; up and down one key, Shift an octave). Moves snap by 10 ms steps; the same-key rule of the backend runs on the page too (section 2.4) |
| 7.4.3 delete and add | Delete or Backspace; double-click on empty space adds 250 ms on that key |
| 7.4.4 undo and redo | `useEditHistory<{ over }>`, one step per gesture, named ("Undo: move 3 notes"). Undo also works after a save (section 2.4) |
| 7.4.5 save | `noteEdits.toOperations` turns the difference into `restore`, `move`, `delete`, `add`, `hand` with `baseRevision` and `baseHandsRevision`; 409 says the notes changed elsewhere and offers **Reload the notes**; 422 shows the backend's words. The save bar, the leave dialog and `beforeunload` come from `useUnsavedChanges` |
| 7.5.1 10,000 rectangles | 60 fps, 0 dropped frames in every scenario (section 3.1) |
| 7.5.2 100 chunks per second | 60 fps, 0 dropped frames, and also at 200 per second (section 3.1) |

Checks: frontend `tsc -b`, `npm run lint`, `npm run build`, `check:render` (60), `check:history`,
`check:note-names` (15), `check:geometry`, `check:cuts`, the new `check:notes` (50 checks: arrays,
rows, live feed, edits, operations) and `check:flow` (52 checks, section 3.2) all pass. No backend
file changed, so the backend tests were not run again.

# 2. Choices made inside the phase

## 2.1 One row per key, fitted to the piece, and the keyboard on the canvas

The plan (section 5) named `piano/Piano.tsx`, the SVG keyboard of the old piano roll
visualization, where a black key's lane is narrower and overlaps the two white lanes beside it. A
click on that overlap is ambiguous, and lighting a key means a React render. The Notes tab draws
the keyboard on the canvas instead, as the MuScriptor examples do: one row of the same height per
key, the black keys dark, the name of every C. A rectangle never covers the row of another key, and
the lit keys are painted on the upper canvas with the sounding notes.

With all 88 keys in a 600 px panel a row is 6 px. The rows therefore show the keys the piece uses
with 2 keys of margin, at least 36 rows (`rollView.widenKeys`). The range only grows while the page
is open, so the rows never jump back; the live view starts with C2 to C7 and widens as notes arrive.
On Superestrella the gain is small (it uses almost the whole keyboard); narrower pieces gain more.

## 2.2 The colours

A dark panel, as the plan and the examples ask (`semantic.roll` in `ui/palette.ts`). The notes are
orange, not the red of the examples: on this app red means "no hand" (Phase 6 report 2.9) or
"marked to come off", and blue and green are the two hands. The selection is lavender, as on the
other views. A sounding note keeps the rule of the Phase 6 report (2.9): black, with a thick border
in its colour and its name in white when the row is tall enough. `colourBy: "hand"` is already
implemented (right blue, left green, no hand red, a dashed border for `FLAG_GUESSED`) for Phase 8.

## 2.3 The playhead and the double-click

Plan section 9.5 gave the double-click two jobs ("double-click to seek" and "double-click on empty
space adds a rectangle"). The double-click adds a note, as the gesture table says. The playhead is
moved in the time ruler (press or drag, the Audio tab's rule) and on the bar under the roll, which
is the progress bar during the transcription and the scrub bar afterwards.

## 2.4 The edits are overrides on the saved notes

`src/notes/noteEdits.ts`. The page loads the saved notes once (`NotesBase`, never changed) and
holds its changes as `Overrides`: `id -> note` for every note it moved, deleted (kept with
`deleted: true`) or added (negative ids). One undo step holds one small map, not a copy of the
piece; "unsaved" is a comparison of two maps; save is the difference as operations.

- **Undo after a save.** After a save the saved overrides become the page's, and `idMap` records the
  backend id of each added note. Undoing a saved delete gives `restore` (and a `move` if the note
  was also moved); undoing a saved add gives `delete` of its new id. Checked in `check:notes` and
  `check:flow`.
- **The same-key rule on the page.** After a move, a resize or an add, on the keys it touched, a
  note that runs into the next onset of its key is shortened to it, only in pairs where one note
  was touched (the backend's rule, Phase 5 report 2.6). Two onsets of one key closer than 0.5 ms
  are refused with a short message (a Snackbar), and nothing changes.
- **Moves keep the old sub-10 ms offsets.** A drag moves by whole steps of 10 ms from where the note
  was, not onto a 10 ms grid: MuScriptor onsets carry the lag correction (for example 3,055 ms), and
  snapping them to the grid would move every touched note by 5 ms.
- **What the backend changed beyond the operations** (`changed` of the PATCH answer: a hand given by
  the quick rule to an added note, a note it shortened) is laid over the page's notes
  (`mergeChanged`). When anything differs, the undo history starts again from there; when nothing
  differs (the usual case), it is kept.
- The notes are read again only when the backend has a newer revision than the page (a new
  transcription), not after the page's own save, so a save does not reset the view or the history.

## 2.5 The live view

- Rectangles are drawn only up to the drawn frontier, which eases toward the last reported time
  (`upToMs`, or the smoothed chunk estimate when it is further). A rectangle that arrives closed
  also grows over 250 ms. Together they give the growing rectangles of the examples, even though a
  message carries several notes at once.
- The view follows the frontier at two thirds of its width while **Follow** is on; a sideways swipe
  or a drag of the notes turns it off.
- **A reload during a transcription** receives every frame sent so far (Phase 4) and draws them on
  the next frame: 460 notes back 0.1 s after the reload, the time taken still counted from the
  backend's clock, the view catching up and continuing live. Checked by hand with a script, not in
  `check:flow`.
- Nothing plays during the transcription; **Play** appears with the saved notes.

## 2.6 Stale notes

When the selected region changed after the transcription, the tab shows the notes read-only (drag
moves the view) with a banner and **Go to the Audio tab**; **Play** is disabled, because the audio
of the piece no longer matches them.

## 2.7 The animation loop asked for two frames (found by the measurement)

The first measurement of the live scenario dropped about one frame in ten, whatever the message
rate, while each frame took 0.1 ms to paint. The cause: when the feed's notes were committed during
a frame, the store's listener asked for a new frame while the loop was about to ask for its next
one, so a second paint chain started and ran beside the first. The loop now marks itself as running
and asks once, at its end. The fix also made the benchmark's message timer reach its full rate.
This affected the real live view too, not only the benchmark.

## 2.8 Smaller points

- `useEditHistory.stage(label)` accepts no effects, so a step is named without a backend call.
  `check:history` still passes.
- `FloatingBar` (the save bar, also used by the piano sheet) keeps itself inside the window when its
  width changes: a longer summary pushed its **Save** button past the right edge.
- `PiecePage.refresh()` reads the audio with the status, so the header's length follows saved cuts
  (it said 3:09 on a piece of 2:31).
- `LaterStepTab` now serves only Hands and Sheet.
- The canvas exposes `data-view-start`, `data-px-per-sec` and `data-keys`, and the bar
  `data-bar="position"` and `data-bar="details"`, for the checks in a headless browser.
- `/dev/roll-bench` exists in development builds only (`import.meta.env.DEV`, lazy import); it is not
  in the production bundle.

# 3. Measurements

## 3.1 The two targets

`npm run bench:roll` opens `/dev/roll-bench` in a headless Chromium for each scenario, 6 s each, on
a synthetic piece of 200 s (10,000 rectangles is 50 per second). Headless Chromium on this machine
paints the canvas in software, with no GPU, so a browser with a screen is faster. Raw answer:
[`measurements/phase-7-roll.json`](measurements/phase-7-roll.json).

| Scenario | What moves | Frames per second | Dropped frames | Paint per frame, median / p95 / max |
|---|---|---:|---:|---|
| `play` | 10,000 rectangles, playback followed | 60 | 0 of 360 | 0.1 / 0.2 / 6.8 ms |
| `scroll` | 10,000 rectangles, the view moved on every frame | 60 | 0 of 360 | 0.8 / 1.1 / 4.4 ms |
| `whole` | 10,000 rectangles all in view, moved on every frame | 60 | 0 of 360 | 2.7 / 3.0 / 11.8 ms |
| `live` | 100 messages per second, 10 rectangles each, parsed from JSON | 60 | 0 of 360 | 1.2 / 2.1 / 8.7 ms |
| `idle` | the live view with no message (baseline) | 60 | 0 of 360 | 0.3 / 0.4 / 9.3 ms |

A dropped frame is a gap of more than 1.5 refreshes (25 ms). No task of 50 ms or more in any
scenario. Before the fix of section 2.7 the `live` scenario dropped 33 of 328 frames and reached
only 84 of the 100 messages per second.

With the same fix, messages at 10, 50, 100 and 200 per second all gave 60 fps and 0 dropped frames
(paint p95 0.9, 1.5, 2.1 and 3.8 ms).

## 3.2 The flow in a browser

`npm run check:flow` on 2026-09-30: 52 of 52 checks, no console error, no failed request. The Notes
tab part, on a temporary copy of Superestrella with a 38 s cut (151 s piece):

| What | Value |
|---|---|
| Live view, 3 s after the first message | 0 then about 6,600 orange pixels drawn; bar "0:00 / 2:31" then "0:26 / 2:31" |
| Transcription, click to saved notes | about 21 s ("Transcribed in 0:20" to "0:21"), 1,015 notes, `muscriptor-large` |
| Move +200 ms, resize -100 ms, add, delete, Save | the backend has exactly those values; notes revision 1 to 2 |
| Play after a press in the ruler | started 49 ms after the press, from 970 ms (aimed at 947 ms); then 1,200 ms of audio in 1,206 ms |

On the whole Superestrella (189 s, no cut): 1,351 notes, the same count as the Phase 4 run, the live
view at "1:32 / 3:09 · 600 notes · 0:12 elapsed" after 12 s, transcribed in about 25 s.

Play from the Notes tab starts in 0.1 to 0.2 s after the press, measured on the piece with cuts
(`538ae69c`, edited FLAC) and the original MP3 alike.

# 4. Notes for later phases

**Every phase.** Nothing of Phases 3 to 7 is committed yet. `npm run check:flow` walks the flow page
end to end, the Notes tab included (about 90 s with the transcription). `npm run bench:roll` repeats
the measurements of section 3.1.

**Phase 8 (the Hands tab).**
- Reuse `PianoRollCanvas` with `colourBy="hand"`: the colours, the red of a note without a hand and
  the dashed border of a guessed hand (`FLAG_GUESSED`, from `NotesBase.guessed`) are painted
  already, and the lit keys take the hand colour. A hand filter (both, right, left) is a new prop
  of `paintBase`/`paintOverlay`: skip the slots whose `hand` does not match.
- The editor model already carries hands: a hand change is an override with another `hand`, and
  `toOperations` sends it as `hand` operations. **Predict hands** answers one hand per id; lay it as
  overrides (unsaved), and **Save** sends it. The Notes tab page code (`NotesTab.tsx`) can be
  factored into a shared editor hook when the Hands tab needs the same save, undo and keys.
- `mergeChanged` resets the undo history when the backend gives an added note a hand (the quick
  rule runs once the hands were saved as a whole). If that is too often on the Hands tab, keep the
  backend's hands in a separate map instead.
- The same-key rule and the operations are checked by `npm run check:notes`; add the hand cases
  there.

**Phase 9.**
- Q-4: the old Piano Roll (`pages/playground/PianoRollPage.tsx`, `RollNote.tsx`) can go; its hand
  panel (`NoteSelectionToolbox`) is still used by Notes Falling.
- `useCutPlayer` is used by the Notes tab with no cuts; its name says more than it does there.
- The time ruler and the bar are the only ways to move the playhead on the Notes tab; if the user
  wants the double-click to seek too, it must give up adding notes (section 2.3).

# 5. Files

New, frontend: `src/notes/rollNotes.ts`, `src/notes/rollView.ts`, `src/notes/liveFeed.ts`,
`src/notes/useLiveTranscription.ts`, `src/notes/noteEdits.ts`,
`src/components/notes/PianoRollCanvas.tsx`, `src/components/notes/rollPaint.ts`,
`src/components/notes/RollTimeBar.tsx`, `src/pages/piece/NotesTab.tsx`,
`src/pages/dev/RollBenchPage.tsx`, `scripts/check-notes.ts`, `scripts/bench-roll.mjs`.

Changed, frontend: `src/App.tsx` (the Notes tab, the bench route), `src/layout/routes.ts`
(`devRollBench`), `src/api/pieces.ts` and `src/api/index.ts` (`PieceNotes`, `piecesApi.notes`, every
operation, the PATCH answer), `src/ui/palette.ts` (`semantic.roll`), `src/hooks/useEditHistory.ts`
(`stage` without effects), `src/components/common/FloatingBar.tsx` (stays in the window),
`src/pages/piece/PiecePage.tsx` (refresh reads the audio), `src/pages/piece/LaterStepTab.tsx`
(Hands and Sheet only), `scripts/check-flow.mjs` (the Notes tab), `package.json` (`check:notes`,
`bench:roll`), `README.md`.

Documents: this report, `measurements/phase-7-roll.json`, the checklist, the plan (sections 5, 7.1,
9.5, 10.5 and 14).

# 6. After the user's first check: the Hands tab (Phase 8, Story 8.1, done early)

The user opened the Hands tab and found the Phase 6 placeholder: no way to predict the hands, no
progress, no colours. They asked for a **Predict hands** button with a progress bar, the hand
colours on the piano roll visualization once hands exist (with a way to hide them), and progress
bars that do not span the whole page when they stand on their own. This is Story 8.1 of the plan,
so it was built now. Story 8.2 (the Sheet tab) is still Phase 8.

## 6.1 What was built

| Part | Result |
|---|---|
| The editor shared | `pages/piece/NotesTab.tsx` became `NotesEditor.tsx` with `step: "notes" \| "hands"`; `NotesTab.tsx` and `HandsTab.tsx` are one line each. The Hands step has every edit of the Notes step, plus the hand tools |
| Predict hands | Saves what is unsaved first, then `POST /pieces/{uuid}/hands/predict/job` (new, 202), follows `GET /matrix/progress/{jobId}` (`hooks/followJob.ts`, an async flow, no effect), lays the answer over the notes as unsaved changes (`noteEdits.applyPrediction`), one undo step. **Predict every note again** is `replace: true`. An info line says the time, how many notes change hand and how many could not be placed |
| The progress | Real, not estimated. `hands/progress.py` is a hook the beam loop (every 16 groups) and the refine rounds (every 8 targets) call; `impose_granularity_and_split` listens to it inside its `two-hands` stage, now in hundredths (beam 0 to 60, refine 60 to 100; measured: the beam is half to two thirds of the time). The page shows `events` as 0 to 10% and `two-hands` as 10 to 100%, with the seconds taken (`components/piece/StepProgress.tsx`). The transcription's own pipeline gains the same finer `two-hands` stage |
| Unplaced notes | `hands_of_split(..., guess_unplaced=False)` for the prediction only: a note the split cannot place is `-` (the Phase 6 rule), counted in the answer's new `unplaced`. The sheet's first hand move keeps the quick rule |
| Hand tools | **To right hand**, **To left hand**, keys R and L (`noteEdits.setHands`); the filter **Both hands**, **Right**, **Left** (the other hand faint and not pickable, notes without a hand always shown); a warning with **Select them** for the red notes; **Continue to Sheet** when the Sheet step is enabled |
| Colours | `colourBy="hand"` once any live note has a hand, on both steps; before the first prediction the notes stay orange (all red read as an error). The Notes step has a **Hand colours** switch, on by default, remembered in the browser (`localStorage`, a convenience only) |
| Progress bars | `ui/progress.ts` `progressSx`: full width up to 520 px for a bar that stands alone. Applied to `ProgressBanner`, the YouTube page and the four video pages. The bar under the piano roll visualization keeps the roll's width, because it is its time axis |

## 6.2 Checks and measurements

- Backend: 2 new tests in `tests/test_pieces.py` (the job reports increasing `two-hands` frames up to
  100 and its `done` frame equals the direct answer; a 10 ms note gets `-` and `unplaced: 1`).
  `make test-backend`: 1,038 passed, 1 failed (the known one).
- Frontend: `check:notes` 58 checks (8 for hands), `check:flow` 63 checks with the Hands tab
  (progress bar seen, prediction in 0.6 to 0.7 s on the 151 s piece, both colours drawn, R and L,
  Save writes 1,014 of 1,015 hands, the Hands step stays `missing` while one note has no hand, the
  switch on the Notes tab), lint, build, `check:history`.

## 6.3 The GPU in the container was lost once

During this work `GET /matrix/engine` reported "No CUDA GPUs are available", and inside the
container `nvidia-smi` said "Failed to initialize NVML: Unknown Error", while the host saw the GPU.
This is the known Docker behaviour after the host's service manager reloads (for example after an
update): running containers lose their GPU device. `docker compose up -d --force-recreate backend`
gave it back. **Every phase:** when a transcription ends at once with no notes, check
`GET /matrix/engine` first.

# 7. After the user's second check: the floating toolbar and the keyboard

The user asked, on the Hands tab:

- **The keyboard keeps the pressed keys after a pause.** The keys of the notes under the playhead
  are now lit whenever the playhead is shown, playing or paused; only the black "sounding" drawing
  of the rectangles is kept for playback (`paintOverlay`, `sounding` vs the lit keys).
- **The selected notes light their keys** in the selection's lavender (the sounding keys are drawn
  over them). `selectedKeysOf` caches the keys per selection and notes version.
- **The floating bar is the editor's toolbar**, always open on the Notes and Hands steps, in this
  order: Play/Pause (Play always follows the playhead again; the Follow toggle remains only in the
  live view), Undo, Redo, Delete, then on the Hands step **To Left**, **To Right**, a small button
  with the count of notes without a hand (its tooltip explains them) and, once pressed, the arrows
  and "2 / 5" to go through them one at a time (giving a hand or deleting moves on to the next);
  the selection's short Spanish name ("Do# 3", or "3 notes: Do 3 · Mi 3 · Sol 3",
  `spanishNoteShort`); **Save**. The "Unsaved: …" words are gone from the bar; the leave dialog
  still uses them, and the Save button carries them in its tooltip and in `data-unsaved` (for the
  checks).
- Removed from the page: the Play, Follow, Delete, Undo, Redo and hand buttons of the top row, the
  explanatory texts, the warning about notes without a hand, and the bottom Save button. The
  prediction's result is a small chip beside **Predict hands**.

`check:flow` has 66 checks now (Spanish name, the selected key lit, keys lit after a pause, the
arrows over the notes without a hand), all passing.

# 8. After the user's third check: the tick of the Hands tab

The user's rule: once the hands are predicted and saved, the Hands tab is ticked; an unsaved change
(a note to the other hand, a delete) removes the tick until **Save**.

- **Backend.** Before, the Hands step was ready only when every live note had a hand, so one note
  the split could not place (a 10 ms note) kept it `missing` after Predict and Save. Now
  "complete" counts only the notes the piano sheet places at 40 ms: `saved_hands.placed_ids` (the
  matrix's `event_ids`, about 20 ms), cached as `pipeline.placed_note_ids` (split cache key
  `(uuid, frameMs, mtime, "placed")`). It is used by the status (`details.unplaced`, and `saved`),
  by `save_edit` (`handsNotesRevision`), by `split_of` (the saved hands are painted, no inference)
  and by the quick rule, which no longer guesses a note the sheet cannot place (a note added in the
  same edit, with no id yet, still gets one). This reverses the Phase 6 rule that such notes keep
  the step from being ready; they stay red and counted on the Hands tab. New test
  `test_a_note_the_sheet_cannot_place_does_not_keep_the_hands_from_being_ready`; `make
  test-backend`: 1,039 passed, 1 failed (the known one).
- **Frontend.** `StepTabs` takes `unsaved`: that step shows a pencil (`EditOutlined`, warning
  colour) and the tooltip "Unsaved changes: press Save to complete this step". `PiecePage` passes
  `hands` while the Notes or Hands tab reports unsaved changes. `check:flow`: 69 checks (the
  pencil after Predict, the tick and an enabled Sheet tab after Save, with one unplaced note).

# 9. The logo and the browser icon (the user's request, outside the plan)

The top bar shows the official logo `aitu-frontend/public/logo-final-2.svg` (34 px high) instead of
the blue "AImpromptu" text (`layout/AppLayout.tsx`). The browser icon is the same mark:
`public/favicon.svg` (square, black, white in dark mode), `public/favicon-32.png` and
`public/apple-touch-icon.png` (black on a white rounded tile, rendered with Playwright's Chromium,
for Safari and the home screen), all linked in `index.html`. The earlier `public/logo_final.png`
is no longer used and was left in place for the user to keep or delete.

# 10. Phase 7 closed

Closed on 2026-10-01 at the user's request. Phase 7 is done; Phase 8 Story 8.1 (the Hands tab) is
done early (sections 6 to 8). What is left of Phase 8 is Story 8.2, the Sheet tab: `RhythmPage`
inside the flow page in place of `LaterStepTab` (the last use of it), the stale banner with
**Write the sheet** required again (Phase 5 report, section 4), and the time of a hand move on the
piano sheet measured part by part against 300 ms (plan section 9.7). Nothing of Phases 3 to 8 is
committed yet. If a transcription ends at once with no notes, check `GET /matrix/engine` for a
lost GPU first (section 6.3).
