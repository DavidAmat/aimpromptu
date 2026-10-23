# 03: Phase 0 report: the research folder on Ubuntu, the branch, the inventory

Plan: [`03-plan.md`](03-plan.md) section 7, Phase 0. Checklist: [`03-checklist.md`](03-checklist.md). Branch
`feat/migrate-new-logic`, made from `master` at `68b1674`. Done 2026-10-23 on the Ubuntu machine. No change to the
app: the phase wrote documents, one script (`aitu-frontend/scripts/baseline-sheets.mjs`) and screenshots.

# 1. Summary

| Task | Result |
|---|---|
| 0.1 The research folder | `/home/david/Documents/projects/music/poc-aitu-research` at git `a208a92`, 9.4 GB of `data/`. `uv sync` built the environment; the core tests pass (139 in 4.7 s, golden files included), and so does the whole research suite (367 in 14.9 s) |
| 0.2 The branch and the folder | `feat/migrate-new-logic`; this folder with `README.md`, `03-prompt.md`, `03-plan.md`, `03-checklist.md` and this report. The folder is the user's `03-apply-poc-research/`, not the plan's `03-new-sheet/` |
| 0.3 The inventory | Section 4: six screens draw their sheet through one page, `SheetPage`; two more draw it on their own (the Transpose preview, the PDF); 13 frontend files import `@aimpromptu/grid-notation`; 16 scripts select its classes |
| 0.4 The baseline | 22 screenshots in [`screenshots/phase-0/`](screenshots/phase-0/) (section 5); the counts of the checks (section 6) |

The inventory changed four places of the plan (plan section 11): the switch between the two engines belongs inside
`SheetPage`, the browser checks need new hooks, Phase 8 has three more screens, and `aitu_backend/hands/` stays.

# 2. The research folder on Ubuntu

The plan needs every later phase to read the research code and data on Ubuntu. Phase 0 checked that the copy made
from the Mac (plan section 10) is complete and runs.

| Check | Result |
|---|---|
| `git log -1` | `a208a92` "Phases 14 and 15; the migration plan for aimpromptu (05-final-report)", working tree clean |
| Size | 334 MB without `data/`, 9.4 GB in `data/` (the plan expected about 10 GB in all) |
| `uv sync` | the environment built from `uv.lock` (Python 3.12, verovio 6.3.0 among others) |
| `uv run pytest src/aitu_notation/tests` | **139 passed** in 4.7 s (the plan expected 139); `test_core_golden.py` reproduces the golden files of `tests/golden/` |
| `uv run pytest` (the whole research suite) | **367 passed** in 14.9 s |
| `sheet.pmn` against the backend | `notes.py`, `columns.py`, `dense.py` (against `aitu_backend/pmn/`) and `keys.py` (against `aitu_backend/matrix/keys.py`) are identical once imports and the one-line copy header are left out. The backend files last changed in `794eede` (2026-10-06), before the copy (`ac45f0c`, 2026-10-16). The core also has `load.py` and `_compat.py`, which have no backend twin; Phase 1 looks at them |
| The guidelines | `guidelines/communication-style.md` and `guidelines/communication-implementation-plans.md` are byte-identical to aimpromptu's `context/language/` copies, so the phases read the aimpromptu ones |

# 3. The branch and the folder

`git checkout -b feat/migrate-new-logic` from `master` at `68b1674` (the merge of 02 Phase 18). The plan uses one
branch for the whole migration (plan section 6.3), not the `feat/phase-N` branches of implementation 02.

The plan proposed `context/implementations/03-new-sheet/`. The user had already made
`context/implementations/03-apply-poc-research/` with the first message of this phase in it
(`03-apply-research-prompt.md`), so the phase used that folder. By the numbering rule of
[`../README.md`](../README.md) it is group 03 with one implementation, so the files sit at the top of the folder:

| File | What it is |
|---|---|
| `README.md` | The state of the implementation and every file |
| `03-apply-research-prompt.md` | The first message to the Phase 0 agent (the user's) |
| `03-prompt.md` | The brief in the user's words: a byte copy of the research's `05-final-report-prompt.md` |
| `03-plan.md` | The plan: a copy of the research's `05-final-report.md`, now the living plan, with a new header, the real folder name, the Phase 0 changes and a section 11 that lists the changes |
| `03-checklist.md` | The status lookup: the open decisions and one line per task |
| `03-implementation-phase-0.md` | This report |
| `screenshots/phase-0/` | The baseline |

`context/implementations/README.md` and `context/00-index.md` list the new group.

# 4. The inventory

The plan asked for a high-level map of everything that vexflow-v2 or `TimeScorePayload` does today, starting from
the code imports rather than the docs, so that later phases know their size. The map below comes from the import
graph of `aitu-frontend/src`, the routes of `aitu-backend/src/aitu_backend/api/time_score.py`, the callers of
`timeScoreApi`, and the pages of `context/frontend/`. It does not study any part deeply: each phase does that first.

## 4.1 The vexflow-v2 imports

13 files of `aitu-frontend/src` import `@aimpromptu/grid-notation`, as the plan counted. The dependency itself is in
`package.json` (`"@aimpromptu/grid-notation": "file:../../vexflow-v2"`) and is excluded from Vite's pre-bundling in
`vite.config.ts`; two scripts import it too (`check-note-names.ts`, `check-render.mjs`).

| File | Lines | What it takes from vexflow-v2 |
|---|---|---|
| `components/time/TimeScoreView.tsx` | 1,752 | `GridNotationRenderer`, `frameAtPoint`, `placeCursor`, `suggestClefChanges`, `suggestKeySignature`, `suggestOttavas`, the grand staff paddings, and the annotation types (spacing, staff gaps, clef changes, even spacing, fingers, frame windows, key changes, grace notes, lyrics, ottavas, passages, trills, the sparse matrix) |
| `components/time/ScorePdfDialog.tsx` | 317 | `installPrintStyles`, `GridNotationRenderer.renderPages`, `PagedRenderResult` |
| `pages/piece/sheet/SheetPage.tsx` | 3,262 | `clefAtFrame`, `ottavaAtFrame`, `resizeOttava`, `suggestClefRanges`, types |
| `pages/piece/sheet/RangeToolbox.tsx` | 654 | `applyClefRange`, `applyKeySignatureRange`, `applyOttava`, `clearClefRange`, `clearKeySignatureRange`, `clearOttavaRange`, `clefAtFrame`, `ottavaAtFrame` |
| `pages/piece/sheet/useNoteActions.ts` | 634 | `keySignatureAtFrame`, `pitchToStaffPosition`, the even spacing limits |
| `pages/piece/sheet/useRangeActions.ts` | 188 | `clefAtFrame`, `keySignatureAtFrame`, `ottavaAtFrame` |
| `pages/piece/sheet/NoteToolbox.tsx` | 356 | the even spacing limits, `FingerNumber` |
| `pages/piece/sheet/lyricsPieces.ts` | 262 | the lyric font sizes |
| `pages/piece/sheet/sheetEdits.ts`, `sheetConstants.ts`, `SheetToolbox.tsx` | 514, 222, 397 | types only |
| `music/renderOverrides.ts`, `music/transpose.ts` | 210, 179 | types only (`SparseMatrix`, key signatures) |
| `package.json`, `vite.config.ts` | | the dependency |

Two more files of the sheet use vexflow-v2 through `TimeScoreView`: `TransposeDialog.tsx` (the preview) and
`PianoToolboxes.tsx` (the keyboard panel, through `renderOverrides`).

## 4.2 The screens

`SheetPage` is one page with roles (`step.play`, `step.passage`, `step.readOnly`), and six screens use it. When it
draws with the new engine, all six change together; this is why the plan's switch between the engines (Phase 5,
task 7) is inside it.

| Screen | Route | Files | Draws through | Moved in |
|---|---|---|---|---|
| Sheet step of a project | `/projects/<id>/sheet` | `SheetTab.tsx` | `SheetPage` | 5 (view), 6 and 7 (editing) |
| A version of My library, read only | `/projects/<versionId>/sheet` | `SheetTab.tsx` | `SheetPage`, read only | 5 |
| Play mode, Sheet view (a project, a version, an integrated playlist, a songs playlist) | `/play/<id>`, `/play/playlist/<id>` | `pages/play/PlayPage.tsx` | `SheetPage`, play role | 5 (drawn), 8 (cursor in the middle, lyrics by frames) |
| Recording in Sheet: the Current and the Proposal | `/projects/<id>/passages/<passageId>` | `pages/piece/passage/PassagePage.tsx` (1,073 lines) | `SheetPage`, passage role; the Proposal has its own sheet toolbox (Key, Transpose, Layout) | 8 |
| From other projects | `/projects/compose` | `pages/compose/ComposePage.tsx` | `SheetPage` of the source part | 8 |
| The requests review: Conversation (an excerpt) and Sheet (Proposed and Now, **Comment on this stretch**) | `/requests/<id>`, `/requests/<id>/sheet`, the admin twins | `pages/requests/Conversation.tsx`, `RequestSheet.tsx` | `SheetPage`, read only | 8 |
| Transpose preview | a dialog of the sheet toolbox | `TransposeDialog.tsx` | `TimeScoreView` alone | 7 or 8 |
| Print to PDF | a dialog of the floating bar | `ScorePdfDialog.tsx` | `GridNotationRenderer.renderPages`, then vector PDF (`documentation/services/frontend/score-pdf.md`) | 8 |
| Notes Falling (a view of Play mode) | `/play/<id>?view=falling` | `pages/play/FallingView.tsx` | no sheet; hand colours from `notes.pmn` | 5 (no hand colours before the LLM decides) |
| Hands step | `/projects/<id>/hands` | `HandsTab.tsx` (9 lines) over `NotesEditor.tsx` (899 lines, `step="hands"`); `POST /pieces/{id}/hands/predict` | the roll, no sheet | 5 (out of the flow), 10 (code) |

Two projects of the Personal Vault stopped at the Hands step (Chopin Prelude `aa331c8b`, Come on Eileen `538ae69c`).
Phase 5 decides how a project whose step is `hands` opens once that step is gone.

## 4.3 The tools of the Sheet step

The tools are described in [`../../frontend/annotations.md`](../../frontend/annotations.md) and its three pages. Each
row names the saved field (`sheet.json`, `schemas/rhythm.py::SavedRhythm`) or the route it writes.

| Tool | Where | Writes | Moved in |
|---|---|---|---|
| The defaults of a first write: the figures from the highest pile of gaps (the negra choice), the key with the fewest accidentals, the left-hand clef rule, the octave brackets of high runs | `SheetPage`, `TimeScoreView` (`suggest*`), `GET /time/{uuid}/default-reading` | `anchorMs`, `anchorFigure`, `keySignature`, `clefChanges`, `ottavas` | 2 (the algorithm decides), 5 (negra choice removed) |
| The line above each passage that names the main figure and a tempo (`corchea = 217 ms · ≈138 BPM`, screenshot 04) | `matrix/ladder.header_label`, drawn by vexflow-v2 | nothing | 5 (not drawn) |
| Note toolbox: the seven figures | `NoteToolbox.tsx`, `useNoteActions.ts` | `overrides` | 7 |
| Note toolbox: fingers 1 to 5 | same | `fingers` | 7 |
| Note toolbox: hand Right / Left | same | `PUT /time/{uuid}/hands` (on `notes.pmn`) | 6 |
| Note toolbox: beam join and break | same | `beamJoins`, `beamBreaks` | 7 |
| Note toolbox: even spacing (=, +, −) | same | `evenSpacings` | 7 (may not make sense: to the user) |
| Note toolbox: decoration (Piano Edit), cue size, trill, take off the page | same | `graceNotes`, `cueRanges`, `trills`, `hiddenNotes` and `PUT /time/{uuid}/removed` on Save | 7 |
| Note toolbox: the note's name in the title (`Do-# 3`) | `pitchToStaffPosition`, `keySignatureAtFrame` | nothing | 7 (spelling of plan section 3.4) |
| Range toolbox: Key, Key for this passage | `RangeToolbox.tsx`, `useRangeActions.ts` | `keyChanges` | 7 |
| Range toolbox: Clef | same | `clefChanges` | 7 |
| Range toolbox: Octave, and a bracket on the page (pull an end, drop on another line, hide) | same, `resizeOttava` | `ottavas` | 7 |
| Range toolbox: Spacing, Speed | same | `spacings`, `speedChanges` | 7 (may not make sense without compases: to the user) |
| Range toolbox: Copy, Record this passage, Start a new part here | same | `POST /time/{uuid}/paste`, passages, parts | 8 |
| Sheet toolbox: Title, Key | `SheetToolbox.tsx` | `title`, `subtitle`, `artist`, `keySignature` | 8 |
| Sheet toolbox: Transpose → Notes | `TransposeTab.tsx`, `music/transpose.ts` | `POST /time/{uuid}/transpose` | 8 |
| Sheet toolbox: Transpose → Figures (the user's override of the reference figure) | same | `figuresFrom`, `overrides` | 7 or 8 |
| Sheet toolbox: Lyrics (the pool, pieces dragged onto frames) | `LyricsTab.tsx`, `lyricsPieces.ts` | `lyrics`; the pool in `project.json` (`PUT /time/{uuid}/lyrics`) | 8 |
| Sheet toolbox: Layout (space between notes, between lines, one line spread on its own, size of marks, zoom, frame numbers, hide decorative notes, group under 8va) | `SheetToolbox.tsx` | `noteSpacing`, `lineSpacing`, `staffGaps`, and others | 8 |
| The keyboard panel (reads the playhead; a click adds or takes off a note) | `PianoToolboxes.tsx` | `PUT /time/{uuid}/notes` | 8 |
| Find trills | `SheetPage.tsx`, `GET /time/{uuid}/trills` (`notation/trills.py`) | `trills` | 8 |
| Undo and redo, Save, the stale sheet banner, Remove all, restore a version | `sheetEdits.ts`, `SheetPage.tsx` | `PUT`/`DELETE /time/{uuid}/rhythm`, `POST .../versions/{v}/restore` | 6 |
| The two selections (noteheads, a stretch on the frame ruler), the corner marks, the playhead | `TimeScoreView` (`frameAtPoint`, `placeCursor`) | nothing | 5 (playhead), 6 (selections) |

The exact list of `sheet.json` fields (`SavedRhythm`): `schemaVersion`, `hand`, `frameMs`, `title`, `subtitle`,
`artist`, `keySignature`, `keyChanges`, `clefChanges`, `anchorFigure`, `anchorMs`, `speedChanges`, `overrides`,
`beamBreaks`, `beamJoins`, `hiddenNotes`, `fingers`, `trills`, `graceNotes`, `lyrics`, `lyricsPool`, `figuresFrom`,
`cueRanges`, plus the layout fields read by the frontend. The research's map of each field onto the new sheet is
`synthesis/06-modules.md` §6.6; Phase 9 measures which fields the database uses.

## 4.4 The backend

| Part | Files | What it does for vexflow-v2 | Fate |
|---|---|---|---|
| The score routes | `api/time_score.py` (1,319 lines) | `GET`/`POST /time/{uuid}/score` return `TimeScorePayload`; `GET .../default-reading` (the negra), `GET .../peaks` and `POST .../ladder-preview` (**no caller in the frontend**, only tests), `GET .../trills`, `GET`/`PUT`/`DELETE .../rhythm` (`sheet.json`), `PUT .../hands`, `PUT .../removed`, `PUT .../notes`, `POST .../transpose`, `POST .../paste`, `GET`/`PUT .../lyrics`, `POST .../versions/{v}/restore` | the drawing routes go in 10; the editing routes are rewritten on the edit model (6 to 8) |
| The payload | `schemas/time_matrix.py` (`TimeScorePayload`, `FigureLadder`), `transcription/time_pipeline.py::to_score_payload` (438 lines) | builds what vexflow-v2 draws | 10 |
| The negra ladder | `matrix/ladder.py` (255), with `peaks.py`, `intervals.py`, `bands.py`, `passages.py` | the figures from one length; the passage header | 10 (for the sheet) |
| `notation/` | `figures.py`, `tuplets.py`, `trills.py`, `transpose.py`, `decorative.py` (866 lines) | figures, tresillos, trills, transposition, decorative notes | 10, after Find trills and Transpose move (8) |
| The hand split | `hands/` (the beam search, about 4,200 lines), `POST /pieces/{id}/hands/predict` | the Hands step | **the beam search stays** (the algorithm and the LLM step start from its split, `hand_sheet`); Predict hands goes in 10 |
| `sheet.json` writers | `api/passages.py`, `api/projects.py`, `api/time_score.py`, `editing/history.py`, `editing/marks.py`, `editing/parts.py`, `editing/passages.py` (the take's sheet written in the passage's key and figure), `editing/paste.py`, `storage/exchange.py` (`.aitu`), `transcription/pipeline.py` | keep the marks with their columns through paste, promotion, split and join, history, export | 6 and 9 (the new sheet is stored beside `sheet.json` and must follow the same writes) |

## 4.5 Checks, tests and documents that depend on vexflow-v2

**Browser checks.** 16 scripts of `aitu-frontend/scripts/` find the sheet by vexflow-v2 classes (`.grid-note-target`,
`.grid-notehead`, `.grid-frame-ruler`, `.grid-onset-group`, `.grid-lyric*`, `.grid-clef-change`): `check-render`,
`check-note-names`, `check-flow`, `check-paste`, `check-passage`, `check-compose`, `check-play`, `check-public`,
`check-requests`, `check-journey`, `check-sheet-toolbox`, `bench-sheet`, `time-flow`, `sheet-library`, `screenshot`
(its example), and the new `baseline-sheets`. Each moves to `data-*` hooks of the new view with its screen (plan,
Phase 5 task 8).

**Backend tests** tied to the old sheet: `test_time_score_payload.py`, `test_time_score_api.py`,
`test_time_matrix_schema.py`, `test_time_pipeline.py`, `test_notation_trills.py`, `test_notation_tuplets.py`,
`test_decorative.py`, `test_matrix_peaks.py`, `test_matrix_bands.py`, `test_hands_on_wall_clock.py`; the score routes
are also called by `test_pieces.py`, `test_muscriptor_engine.py`, `test_video_piece.py`, `test_rights.py`, and
Predict hands by `test_pieces.py` and `test_library.py`.

**Documents** that describe vexflow-v2 or its payload (Phase 10 rewrites what the phases before did not):
`context/frontend/rendering.md`, `printing.md`, `annotations*.md`, `projects.md`, `play-mode.md`, `README.md`;
`context/backend/time-model.md`; `documentation/services/frontend/grid-notation.md`, `score-pdf.md`, `components.md`;
`documentation/services/backend/endpoints.md`, `events-to-sheet.md`, `time-matrix.md`, `rhythm-and-annotations.md`;
and the platform pages that name the package (`context/00-*`, `01-project.md`, `02-tech-stack.md`,
`03-services-overview.md`, `04-local-development.md`, `09-coding-conventions.md`, `app/01-app-context.md`, the
repository `README.md`).

# 5. The baseline screenshots

`node aitu-frontend/scripts/baseline-sheets.mjs` (new) takes them, at 1440 x 900 in the light theme unless said.
Real pieces are only opened. Every screen that needs a click works on a temporary copy of Superestrella
(`POST /projects/{id}/duplicate`), and the copy and the passage made on it are deleted at the end ("Left behind: 0
projects, 0 passages"). Phase 10 runs it again with `--out .../screenshots/phase-10` to compare.

| File | Screen |
|---|---|
| `01-projects.png` | Projects: the step each project reached (Hands is one of the five steps) |
| `02-notes-step.png` | Notes step of Superestrella: the roll with no hands |
| `03-hands-step.png` | Hands step: the roll coloured by hand, **Predict hands** |
| `04-sheet-step.png` | Sheet step of Superestrella: the title lines, the scrub bar, the line `corchea = 217 ms · ≈138 BPM`, the sheet, the floating bar |
| `05-sheet-step-full.png` | The same, the whole page (1440 x 3238) |
| `06-library-version.png` | The version of 7 Years in My library (one of the 10 viewer songs), read only |
| `07-library-version-dark.png` | The same in the dark theme |
| `08-play-sheet.png` | Play mode, Sheet view, 7 Years |
| `09-play-falling.png` | Play mode, Notes Falling, 7 Years (the start: no note on screen yet) |
| `10-play-integrated.png` | Play mode of the integrated playlist "Elefants - Oques Grasses Playlist": each part under its subheader |
| `11-note-toolbox.png` | The note toolbox on one note (`La-# 6`) |
| `12-range-toolbox.png` | The range toolbox (*Frames*) on a stretch, Key tab |
| `13-range-octave.png` | The range toolbox, Octave tab |
| `14-sheet-toolbox-transpose.png` | The sheet toolbox, Transpose tab |
| `15-transpose-preview.png` | Transpose figures (negra to corchea), Preview: the sheet drawn in the dialog |
| `16-sheet-toolbox-lyrics.png` | The sheet toolbox, Lyrics tab |
| `17-sheet-toolbox-layout.png` | The sheet toolbox, Layout tab |
| `18-keyboard-panel.png` | The keyboard panel |
| `19-find-trills.png` | Find trills: the suggestions panel |
| `20-print-pdf.png` | Print to PDF: 8 A4 pages, 3 lines a page |
| `21-recording-in-sheet.png` | Recording in Sheet: the page of a passage with its Current drawn |
| `22-compose.png` | From other projects: the sheet of the source project |

Three limits of the baseline:

- The requests review (`Conversation.tsx`, `RequestSheet.tsx`) is not in it: the database held no request on
  2026-10-23 (`GET /requests` answered `[]`), and making one needs a second user and a public song. Phase 8 makes one
  with temporary users, as `check:requests` does.
- The stretch of screenshot 21 is short (0:01 to 0:02): the first frame ruler of the page covers only the first group,
  and the script marks 5 % to 95 % of it. The page and its Current are shown, which is what the baseline needs.
- The full-page capture (05) logs `availableWidth must be at least 240 pixels` from vexflow-v2 once: Chromium sizes
  the page for the capture, and the renderer refuses the width it sees for a moment. The same page opened normally
  logs nothing (04), and the picture is complete. It is not a bug of the app.

# 6. The checks (the reference for later phases)

| Check | Result |
|---|---|
| Backend, full run **on the CPU** (the app's own backend held 11 GB of the GPU, its MuScriptor worker) | 1,148 tests: 1,144 passed, 1 skipped (the real-model test needs a GPU), 3 failed: the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas` (it fails on `master` since 02 Phase 0) and the two Transkun tests that fail only without a GPU. 02 Phase 17: 1,140 |
| `npm run lint` | passed |
| `npx tsc -b` | passed |
| `check:history`, `check:note-names` (15 passed), `check:geometry`, `check:cuts`, `check:notes` | passed |
| `scripts/docs/check-links.py` | passed (section 7) |

The browser checks (`check:*` with Playwright) were not run: the phase changed no app code, and the screenshot script
opened every screen they cover. The checks that transcribe (`check:passage`, `check:flow`, `time:flow`) also need
the GPU.

# 7. Documentation

- This folder (section 3).
- [`../README.md`](../README.md): group 03 in the table and in "What is being built now?".
- [`../../00-index.md`](../../00-index.md): the implementation part lists group 03 and its files.
- `scripts/docs/check-links.py`: passed after the changes.

# 8. Notes for later phases

- **Needed later, at Phase 4 task 1**: the user creates the API key in the Claude Console organization linked to the
  Max 5x credits and puts `ANTHROPIC_API_KEY` in `.env` on Ubuntu. Not raised now: no phase before 4 calls the API.
- The app is running (`make up`, backend with reload, page on 5173), and its backend keeps MuScriptor on the GPU
  (11 GB). Backend tests run on the CPU while it does.
- `baseline-sheets.mjs` prints the copy's id, and its last lines count any project left with the title prefix
  `baseline-sheets` and any passage still open; both were 0.
- The research viewer songs (`viewer/server.py`, `SONGS`) include `1a16a836` (7 Years, a version of My library);
  Phases 2 to 5 can use it as the first song in the app.
