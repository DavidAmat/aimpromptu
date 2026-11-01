# 05, Phase 16: the notes and the hands (the Notes step, the piano roll, the hand split): report

Plan: [05-plan.md](05-plan.md), section 6, Phase 16.

## Docs changed

- `context/frontend/projects.md`, section 3 (Notes), owned here: the gesture table corrected (the arrow keys: Left and
  Right move 10 ms, Shift 100 ms; Up and Down move one key, Shift an octave; Shift-drag also changes the key); the
  claim "Until Sonnet decides them, the notes have no hand colours" replaced by the **Hand colours** switch (on by
  default, disabled until the piece has hands); the 60 fps claim turned into what the bench page covers.
- `documentation/services/backend/events-to-sheet.md`: section 3 adds the second test of an artifact
  (`require_coincident_attack`, 50 ms); section 5 says the default method is `refine` (`HandInferenceConfig.method`),
  the beam inside it.
- `documentation/services/backend/hand-inference-second-pass.md`: a section "Where the code is" (the files and the
  config names of `hands/`). The numbers were not touched.
- `context/music/piano_svg/01-piano-svg.md`: a section "Status (2026-11-01)": the four assets exist in
  `aitu-frontend/public/piano/`, drawn by `src/piano/Piano.tsx`; the places where the app differs from the brief
  (computed positions in `keyPositions.ts`, `<image>` not `<use>`, `keyColours`, the octave numbers).
- `context/music/notation-logic/02-notation-spec.md` (check only, three fixes): the grand-row builder named by its
  backend name; `POST /sequence` and `leftSequence` written as a deleted route (the builder still takes
  `left_sequence`); a line that the score metadata table is the old payload.
- `context/backend/piano-matrix-notation.md`: checked, no change.

## What was stale

- `projects.md`: "Until Sonnet decides them" (false since hand colours existed; the model name must not appear).
- `projects.md`: "Notes Falling" named as a Notes step view (it is a view of Play mode since implementation 02).
- `projects.md`: the arrow keys (the table said "Move in time by 10 ms, or by one key" without the Shift steps).
- `hand-inference-second-pass.md` and `events-to-sheet.md`: the code path of the default method was not named.
- `piano_svg/01-piano-svg.md`: a brief from 2026-07-27 in the future tense; the assets and the component are built.
- `notation-logic/02-notation-spec.md`: `POST /sequence` in the present tense (deleted in implementation 02, Phase 1).

## Code and docs that disagree in a way that looks like a bug (for the user)

- `aitu-backend/src/aitu_backend/matrix/hands.py`: `DEFAULT_METHOD = "beam"` and the docstring of `split_hands`
  ("`beam` (default)"). The code that runs takes the config's method when none is given, and that is `refine`
  (`hands/config.py`, `HandInferenceConfig.method`). Either the constant and the docstring are stale, or the
  constant should be used. Not changed (code).
- `piano/keyPositions.ts` calls its geometry "placeholder". If the illustrator's final art is not yet in
  `public/piano/`, the keyboard is still the placeholder. Open point for the user; not critical.

## New terms for the glossary (Phase 20)

- **Hand colours**: the switch of the Notes step that colours the rectangles by hand (blue right, green left, red no hand).
- **Artifact** (transcription): a note too short to have been played, dropped from the hand split (`transcription/artifacts.py`).
- **Refine** (hand method): the default hand split, the beam then the gated second pass.

## Not checked

- The numbers of `hand-inference-second-pass.md` (the benchmark table, 209 scenarios, 0.9641 and the rest): the
  benchmark repo `poc-piano-hand-prediction` is not in this checkout; not run (no run in this phase).
- `piano-matrix-notation.md`: the sizes (about 2,000 rectangles and 28,000 cells for 3.5 minutes; 38 KB median),
  the migration count (71,290 notes), and the 40 ms and 10 ms statements are not re-measured.
- The 60 fps and the 10,000-rectangle claim: the bench page exists (`pages/dev/RollBenchPage.tsx`); its result is not read.
- The gesture "one key sounds one note at a time" (`notes/noteEdits.ts`): not re-read, kept as it was.
- The git log since 2026-10-27 has no commit in the code paths of this phase (`hands/`, `pmn/`, `matrix/`,
  `api/matrix.py`, the Notes frontend), so the pages were checked against the code as it is, not against changes.

## Pending edits for shared files

- **E16.1** `documentation/services/backend/endpoints.md`, section 1 table, the row `GET /pieces/{uuid}/notes`
  (currently "The live notes as columns, with the revisions (implementation 08)."). Change the text to:
  "The live notes as columns, with the revisions and `stale` (true when the selected region changed after the
  transcription) (implementation 08)."
- `documentation/services/frontend/components.md`: no change needed. Every component named in its Notes rows exists
  (`NotesEditor.tsx`, `PianoRollCanvas.tsx`, `rollPaint.ts`, `RollTimeBar.tsx`, `notes/*.ts`). Its "gone" list names
  removed files on purpose.
- `context/00-index.md`: no new file, nothing to add.

## Left for later phases

- Phase 20: `context/frontend/projects.md` is about 293 lines, over the limit of about 200 (section 4 "The steps" is the
  long part; Phase 14 split the file, this phase kept its Notes part).
- Phase 20: the names flagged on purpose by `check-names.py` in this phase's files are removed code, named as history:
  `matrix/intervals.py`, `matrix/peaks.py`, `matrix/bands.py`, `TimeScorePayload` (events-to-sheet, the 03 Phase 10
  history), `music/matrixToNotation.ts` (02-notation-spec), `aitu-backend/scripts/bench_payloads.py`
  (piano-matrix-notation, deleted in 03 Phase 10). Keep them, or move them to the deprecated page.
- Phase 20: the glossary terms above.

## Checks

- `check-links.py`: my files have no broken link. Two broken links in `05-implementation-phase-7.md` (`annotations-sheet.md`)
  belong to Phase 7, which is in the same wave and still running; not mine.
- `check-names.py` on the six files: 8 missing names, each one a removed name named as history (above).
