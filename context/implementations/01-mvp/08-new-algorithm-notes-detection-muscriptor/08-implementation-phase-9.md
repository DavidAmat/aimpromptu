# 08 Phase 9: The checks, the documentation, and closing

The plan is [`08-plan.md`](08-plan.md) section 12, Phase 9, and decision Q-4 (section 11). The status
lookup is [`08-checklist.md`](08-checklist.md). This report closes implementation 08: what was done,
the choices made inside the phase, the measurements, and what is left open.

# 1. What was done

| Task | Result |
|---|---|
| 9.1 the whole flow | `npm run time:flow` (`aitu-frontend/scripts/time-flow.mjs`): the flow walked in a headless Chromium on three temporary pieces, each step timed from the press of its button to its result on screen. 31 to 60 s from the piece to a saved piano sheet (section 3). Raw answer: [`measurements/phase-9-flow.json`](measurements/phase-9-flow.json) |
| 9.2 documentation | Three new overview pages: `context/backend/muscriptor.md`, `context/backend/pieces-and-revisions.md`, `context/frontend/flow-page.md`. Rewritten: `context/04-local-development.md` (containers first, the tunnel, the checks). Updated: `02b-local-setup.md` (section 12, AImpromptu on Ubuntu), `00-project-complete-overview.md`, `01-project.md`, `02-tech-stack.md`, `03-services-overview.md`, `07-database.md`, `00-index.md`, `backend/README.md`, `backend/api.md`, `backend/piano-matrix-notation.md`, `frontend/README.md`, `frontend/pages.md`, `documentation/services/backend/endpoints.md`, `transcription-pipeline.md`, `paths-and-data.md`, `documentation/services/frontend/components.md`, the root `README.md`, `aitu-backend/README.md`, `aitu-frontend/README.md` |
| 9.3 Q-4 | The Playground's Piano Roll tab removed: `pages/playground/PianoRollPage.tsx`, `components/notes/RollNote.tsx` and `components/notes/HandlessStrip.tsx` deleted (only that page used them). `/playground/piano-roll` redirects to `/piece`. The two "Open the Piano Roll" links of Video to Notes now open the Notes tab of the piece they wrote. Notes Falling stays |
| 9.4 closing | The folder README marked complete, with where the result is documented; the row of `../README.md` updated; the plan (sections 7.2, 12 Phase 9, 14) and the checklist |

Checks after the changes, all passing: frontend `tsc -b`, `npm run lint`, `npm run build`,
`check:render` (60), `check:history`, `check:note-names` (15), `check:geometry`, `check:cuts`,
`check:notes`, and `check:flow` (79 of 79, no console error, no failed request). No backend code
changed in this phase; `make test-backend` gives 1,039 passed and 1 failed (the known
`test_the_worked_example_at_00_46_prints_three_equal_corcheas`, Phase 0 report 2.1), as in Phase 8.

# 2. Choices made inside the phase

## 2.1 What went with the old Piano Roll

The old page carried three things that nothing else used, and they were removed with it:

- `RollNote.tsx` (its memoized SVG rectangle) and `HandlessStrip.tsx` (its strip of notes without a
  hand). The Hands tab has its own on the canvas.
- In `NoteSelectionToolbox`, the hand buttons (`onMoveHand`, `movingHand`, `handError`) and the walk
  through the notes without a hand (`review`). Notes Falling never passed them, so its panel is
  unchanged: Delete and Put back.
- In `playback/noteVisuals.ts`, the `missingHand` drawing rule (solid red). The canvas paints that
  case itself (`rollPaint.ts`).

The route stays as a redirect, so an old bookmark opens the working piece instead of "Not found".
`GET /matrix/{uuid}/events` and `PUT /matrix/{uuid}/events/removed` stay: Notes Falling uses them.

## 2.2 How the flow is timed

`time:flow` walks the flow the way a reader does, through the page, not the API: it presses
**Transcribe** after the waveform is drawn, follows the live view, presses **Predict hands** and
**Save** on the Hands tab, then opens the Sheet tab, presses **Write the sheet** and **Save**. Each
time is measured on the script's clock between a press and what the page shows (the first note in the
live bar, the **Play** button of the saved notes, "Predicted in", the first notehead, the banner
gone). The three pieces follow the rule of the Phase 8 report (section 2.4): nothing touches a
library piece.

1. **Superestrella**: its `original.mp3` uploaded as a new piece, as `check:flow` does.
2. **A library piece**: a copy of the folder of The Winner Takes It All (`fb0b0989`, 5:56, the
   longest piece, transcribed by ByteDance, no hands) under a new uuid, as `bench:sheet` does. It is
   opened from the library list of the Source tab, which checks that a piece opens on the step it
   reached (Notes), and is transcribed again with MuScriptor (the confirmation is pressed).
3. **A new YouTube URL**: Yann Tiersen's "Comptine d'un autre été, l'après-midi"
   (`znfYwABeSZ0`, 2:21, solo piano, not in the library), downloaded on the Source tab.

All three are deleted at the end (`--keep` keeps them).

**Two measuring mistakes, found and fixed on the way.** The first run reported the first note 1.6 s
after **Transcribe** on a new piece, against 0.2 s on the library piece. The backend sends the first
note 0.27 s after the request (measured on the stream directly), and the page shows it 0.34 s after
the press. The 1.6 s came from the script: it waited up to 1.5 s for a "Transcribe again?" dialog that
only a piece with current notes shows. It now waits for whichever comes first, the dialog or the
Notes tab. The script also first counted orange pixels for the first note, which counted the old
ByteDance notes the library piece shows until the stream starts; it now reads the note count of the
live bar.

## 2.3 The documentation

The pages that describe one entity follow the two-folder rule of
[`00-documentation-instructions.md`](../../00-documentation-instructions.md): an overview in
`context/` (what it is and how it flows, under 200 lines) and the exact routes, fields and paths in
`documentation/`. The engine and the steps got their own overview pages because no existing page
could hold them; the flow page likewise. `piano-matrix-notation.md` (Phase 2) was already current
apart from two sentences. The container commands stay in `04-local-development.md`, which already
was the page of commands, and `02b-local-setup.md` got a section on how the two machines are used
for this project, because its default rule ("edit on the Mac") no longer holds here.

# 3. Measurements

## 3.1 The whole flow

`npm run time:flow` on 2026-10-01, through the running containers, MuScriptor `large` (cuda,
float16) on the RTX 4090, headless Chromium at 1440 x 900. No console error and no failed request on
any piece.

| | Superestrella (upload) | The Winner Takes It All (library copy) | Comptine (new YouTube URL) |
|---|---:|---:|---:|
| Length | 3:09 | 5:56 | 2:21 |
| The piece in | 0.2 s (upload) | 0.2 s (library click to the Notes tab) | 3.8 s (Download to the Audio tab) |
| First note in the live view | 0.35 s | 0.23 s | 0.34 s |
| Transcribe to the saved notes on screen | 27.4 s | 51.5 s | 21.4 s |
| Transcription on the backend's clock | 0:26 | 0:50 | 0:21 |
| Notes | 1,351 | 2,553 (ByteDance had 2,692) | 1,014 |
| Predict hands, press to answer | 0.9 s | 2.4 s | 1.4 s |
| Notes without a hand after it | 1 | 0 | 6 |
| Save the hands | 0.09 s | 0.12 s | 0.10 s |
| Sheet tab to **Write the sheet** ready | 0.14 s | 0.17 s | 0.14 s |
| **Write the sheet** to the first piano sheet | 0.62 s | 0.99 s | 0.55 s |
| Save the reading | 0.16 s | 0.16 s | 0.21 s |
| Whole walk | 33.0 s | 60.0 s | 31.1 s |

The transcription is about 85% of the walk. It runs at 7 x real time on every piece, as Phase 1
measured. Every other step is under 2.5 s, and under 1 s on a piece of 3 minutes or less.

## 3.2 The flow check

`npm run check:flow` after the removal: 79 of 79 checks, no console error, no failed request. The
Piano Roll page was not part of `check:flow`, so the number of checks is unchanged.

# 4. What is left open

- **Nothing of Phases 3 to 9 is committed.** The changes of this implementation are in the working
  tree of `aimpromptu` (and one file in `vexflow-v2`, Phase 8 section 6.2, plus an older unrelated
  `package-lock.json` change there). The user decides when to commit.
- **`b99bc3ae` (Phase 8 section 2.4).** The piece reads every step `ready`, with its hands saved
  (`saved: true`), and draws as before. The Mac's copy of its original `matrices/` files was never
  copied to `.run/b99bc3ae-from-mac/`, so an exact restore is still possible but optional.
- **The Sheet tab has no leave dialog** (Phase 8 section 2.1). It would need `RhythmPage` to know
  whether the reading on screen differs from the saved one.
- **A hand move on the largest piece** (4,295 notes) takes about 600 ms, against 250 to 270 ms on a
  piece of 3 to 4 minutes (Phase 8 section 3.3). The user chose not to change how `vexflow-v2`
  draws.
- The Playground's "Create segment" still copies the audio, beside the cuts of the Audio tab (Phase 6
  section 4). It is a separate feature of the Input page and was left as it is.
- **Small differences between the reports and the code**, found while writing the detail pages and
  now written as the code does it: only `GET /audio/{uuid}/file` sends `Cache-Control: no-cache`
  (the Phase 6 report said every audio answer); not every path is built in `storage/paths.py`
  (its own docstring still says so); the ByteDance checkpoint is given as 164, 165 or 172 MB in
  different places.
- `context/implementations/README.md` lists no row for `07-enhancing-the-sheet/`, which exists. It
  is not part of this implementation and was left as it is.

# 5. Files

New: `aitu-frontend/scripts/time-flow.mjs`, `context/backend/muscriptor.md`,
`context/backend/pieces-and-revisions.md`, `context/frontend/flow-page.md`,
`measurements/phase-9-flow.json`, this report.

Deleted: `aitu-frontend/src/pages/playground/PianoRollPage.tsx`,
`aitu-frontend/src/components/notes/RollNote.tsx`, `aitu-frontend/src/components/notes/HandlessStrip.tsx`.

Changed, frontend: `src/App.tsx` (the redirect), `src/layout/routes.ts` (no Piano Roll route or
tab), `src/components/notes/NoteSelectionToolbox.tsx`, `src/playback/noteVisuals.ts`,
`src/pages/video/VideoNotesPage.tsx` (the links), comments in `src/hooks/usePlayedNotes.ts`,
`src/components/video/NotesOnFrame.tsx`, `src/layout/PlaygroundLayout.tsx`,
`src/pages/playground/NotesFallingPage.tsx`, `package.json` (`time:flow`).

Changed, documents: the pages listed in section 1 (9.2), the plan, the checklist, the folder README
and `../README.md`.
