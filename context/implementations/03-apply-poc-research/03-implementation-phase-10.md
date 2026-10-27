# 03: Phase 10 report: vexflow-v2 removed, documentation, closing

Plan: [`03-plan.md`](03-plan.md) section 7, Phase 10. Checklist: [`03-checklist.md`](03-checklist.md). Branch
`feat/migrate-new-logic` (level with `master` at the start, `6280e92`: nothing to merge). Written 2026-10-27 on the
Ubuntu machine. **Built and checked by the agent; checked by the user in the browser (2026-10-27: "all good") and
merged into `master`.**

# 1. Summary

| Task | Result |
|---|---|
| 10.1 Removal | `@aimpromptu/grid-notation` gone from the frontend (dependency, lock, image build, compose context, Vite); the old page and its 13 modules; `api/timeScore.ts`; the Hands mode of the notes editor and **Predict hands**; every `/time` route; `notation/`, the negra ladder and its four helpers; the score payload. About 18,600 lines of code and tests removed (section 3) |
| 10.2 Documentation | The backend, frontend and platform pages made true (section 6); the vexflow-v2 renderer page moved to `documentation/deprecated/` |
| 10.3 Checks and screenshots | Section 5; the 22 screens again in [`screenshots/phase-10/`](screenshots/phase-10/), beside Phase 0's |
| 10.4 Licenses | The inventory is `aitu-backend/src/aitu_backend/sheet/README.md` section 8 (section 7 here) |

# 2. The study (2026-10-27)

**Frontend.** A reachability walk from `src/main.tsx` (relative imports): `HandsTab.tsx`, `granularities.ts` and
`useNoteSelection.ts` were already drawn nowhere. Six files imported vexflow-v2 directly and all were reached only
through `SheetPage.tsx`, which held the old page `VexflowSheetPage` (lines 321 to 3,297, drawn nowhere since 8B) next
to the step types and the one-line `SheetPage` that draws `frames/FramesSheetPage`. Three helpers shared with the new
page imported its types (`music/transpose.ts`, `music/renderOverrides.ts`, `sheet/sheetConstants.ts`). Of
`api/timeScore.ts` only one call was still made by the new page: the pasted lyrics words (`GET`/`PUT
/time/{uuid}/lyrics`, kept in `project.json`); its types `FigureName`, `KEY_SIGNATURES`, `KEY_LABELS`, `LyricLine` and
`PassageRef` were still used.

**Backend.** An import walk from `aitu_backend.main` after the `/time` router is taken out: `notation/` and
`matrix/{ladder,peaks,intervals,bands,passages}.py` were still reached only through
`transcription/time_pipeline.py`, whose score payload builder imported them; the hand split in the same module
(`TimeHands`, `impose_granularity_and_split`, `pin_hands`) is what `pipeline.starting_hands` uses.
`schemas/time_matrix.py` still gave six names to live code (`DEFAULT_FRAME_MS`, `FigureName`, `FIGURE_NEGRAS`,
`PrintedHand`, `FigureOverride`, `BeamBreak`, through `schemas/rhythm.py`, `part_sheet/build.py`, `legacy.py`,
`editing/passages.py`).

**The database** (read only): `projects.step` is `sheet` for 42 projects, `notes` for 5, `audio` for 1 and empty for 5;
none holds `hands`. The column's check still allows it.

**Old-sheet leftovers outside the plan's list**, each found by following a removed name:

- the Sheet step's state still came from the old sheet's rule (`pieces/status._legacy_sheet`): a `sheet.json` saved
  for older hands made the step `stale` ("The notes or the hands changed since this sheet was saved"), which the new
  sheet never is, and `SheetTab` passed that state to the page;
- the promote, promotion facts and split routes took the page's unsaved `sheet.json`; the new page never sends one;
- the PDF writer fetched and parsed `bravura.otf` (513 kB) for every print, although the new sheet's glyphs are
  outlines and no Bravura text is ever written;
- `pressedBox` (the old sheet's toolbox placement), `split_events` (the old Transpose preview), and the decoration
  keyboard of `PianoToolboxes.tsx`;
- **a real waste**, found by the test migration: after a transcription the job warms the hand split
  (`pipeline.warm_split`) under the old sheet's cache key (`split_of`), while the new sheet reads
  `inferred_split(keep_saved=True)`, so the first sheet of a new transcription computed the split again (0.3 to 4.3 s
  on the songs measured in implementation 02).

No product question came out of the study: every item either served only the old sheet or is kept by an earlier
decision (Phase 9: the old `sheet.json` is still read).

# 3. What was removed

## 3.1 Frontend

| What | Detail |
|---|---|
| The package | `@aimpromptu/grid-notation` from `package.json`, its `../../vexflow-v2` entry of `package-lock.json`, the build of vexflow-v2 in `aitu-frontend/Dockerfile`, the `vexflow` build context of `compose.yaml`, the `optimizeDeps` exclusion of `vite.config.ts`, the `make build` note |
| The old page | `VexflowSheetPage` (`SheetPage.tsx` is now the step types and `SheetPage`), `components/time/TimeScoreView.tsx` (1,752 lines), `ScorePdfDialog.tsx`, `sheet/{NoteToolbox,RangeToolbox,SheetToolbox,SheetFloatingBar,TransposeDialog}.tsx`, `{useNoteActions,useRangeActions,sheetEdits}.ts`, `music/renderOverrides.ts`, `music/granularities.ts`, `hooks/useNoteSelection.ts` |
| The step types | `SheetStep.newSheet` (the switch), `PassageView.anchorMs` (the old page's figure) and `onSheet` (its unsaved sheet), `onSplit`'s sheet argument; `frameWindow` is typed locally |
| `api/timeScore.ts` | Removed; `FigureName`, `KEY_SIGNATURES`, `KEY_LABELS`, `KeySignatureName`, `LyricLine`, `PassageRef` moved to `api/sheet.ts`, with `sheetApi.words` and `saveWords` (`/sheet/{uuid}/words`) |
| The Hands step | `HandsTab.tsx`; the Hands mode of `NotesEditor.tsx` (Predict hands, To right and To left, the hand filter, the review of notes without a hand); `piecesApi.predictHands`; `noteEdits.setHands`, `applyPrediction`, `idsWithoutHand`. The route `/projects/<id>/hands` still opens the Sheet step (old links) |
| Shared helpers | `sheetConstants.ts` keeps the hand colours, the keyboard legend, `formatSeconds`, `SoundingNote`, `PrintedHand`; `music/transpose.ts` keeps `intervalWords` and the figure ladder; `PianoToolboxes.tsx` keeps the keyboard panel; `toolboxPlacement.pressedBox` removed |
| The PDF | `print/opentype.ts`, `public/fonts/bravura.otf` and its license, the embedded font path of `print/drawPage.ts` and `print/scorePdf.ts` (base fonts only) |
| Scripts | `check-render.mjs` (`check:render`), `check-note-names.ts` (`check:note-names`), `sheet-library.mjs`; `baseline-sheets.mjs` and `check-journey.mjs` moved to the new sheet's hooks; `check-play.mjs` no longer writes an old `sheet.json`; `check-notes.ts` lost the prediction checks |

## 3.2 Backend

| What | Detail |
|---|---|
| `api/time_score.py` | Every `/time` route: `score` (GET and POST), `peaks`, `default-reading`, `ladder-preview`, `trills`, `rhythm` (GET, PUT, DELETE), `hands`, `removed`, `notes`, `transpose`, `paste`, `versions/{v}/restore`, `lyrics`. The words are `GET`/`PUT /sheet/{uuid}/words` in `api/sheet.py` (same body, same file) |
| Predict hands | `POST /pieces/{uuid}/hands/predict` and `/job`, their models; `READ_ROUTES` lost them and the two `/time` POSTs |
| Modules | `notation/` (5 modules), `matrix/ladder.py`, `peaks.py`, `intervals.py`, `bands.py`, `passages.py` |
| `transcription/time_pipeline.py` | Keeps `TimeHands`, `impose_granularity_and_split`, `pin_hands`; the payload, the envelope, the layout hints, the attack times and `trim_to_music` removed |
| `schemas/time_matrix.py` | Keeps the six names above; the payload, envelope, ladder, passage, printed note and layout models removed |
| Routes of the old page | `PromoteIn.sheet`, `PromotedOut.sheet`, `SplitIn.sheet` (the editing functions keep their optional `sheet` argument: tests use it) |
| The Sheet step's state | `running` while the AI writes, `ready` once `sheet.f1` or an old `sheet.json` is stored, `missing` otherwise; no `stale`, no `details.legacy`, no `revisions.sheetHands`; `PATCH /pieces/{uuid}/notes` has no `sheetStale` |
| `transcription/pipeline.py` | `warm_split` warms `inferred_split(keep_saved=True)` (the new sheet's); `split_events` removed |

**Kept on purpose:** `aitu_backend/hands/` (the starting hands); `schemas/rhythm.py`, `pipeline.load_rhythm` and
`editing/marks.py` (an old `sheet.json` is still read, Phase 9); `split_of`, `hands_of` and `run_pipeline` (no caller
in the app, but the tests use them as the shared split); `hands` in the `projects.step` check (no row holds it).

## 3.3 Size

| Part | Files changed | Lines removed | Lines added |
|---|---|---|---|
| `aitu-frontend` | 57 | 11,686 | 307 |
| `aitu-backend/src` | 25 | 3,849 | 138 |
| `aitu-backend/tests`, `scripts` | 23 | 3,082 | 297 |
| Documentation (`context/`, `documentation/`, READMEs) | 46 | 1,368 | 928 |

Also: `followJob.ts` (its last user was Predict hands), and the stale comments of `PiecePage`, `StepTabs`,
`SheetTab`, `FramesSheetPage`, `NotesOnFrame` and two backend docstrings, found by the documentation pass. One more
change of the Sheet step's state: while the notes are not ready, the step is `stale` when any sheet is stored
(`sheet.f1` now counts, as `sheet.json` did), `missing` otherwise.

# 4. Tests

The test migration (section 2 of the work, done by a helper session and reviewed here):

- Deleted, they tested only removed code: `test_time_score_payload.py`, `test_time_score_api.py`,
  `test_notation_trills.py`, `test_notation_tuplets.py`, `test_decorative.py`, `test_matrix_peaks.py`,
  `test_matrix_bands.py`; the scripts `bench_payloads.py` and `bench_pieces.py` (Predict hands and the `/time` sheet).
- Trimmed: `test_time_matrix_schema.py` (the six names that stay), `test_time_pipeline.py` (the split),
  `test_hands_on_wall_clock.py` (its own `onset_columns`).
- Adapted: `test_saved_rhythm.py` (the model and `load_rhythm` instead of the route), `test_pieces.py` and
  `test_library.py` (hands as `hand` operations; `sheet.json` written directly; the Sheet step `ready` where it was
  `stale`; the Predict hands tests removed), `test_rights.py` (the `/sheet` routes), `test_parts.py`,
  `test_passages.py`, `test_paste.py` (the undo through `history.restore`; the paste through `POST /sheet/{x}/paste`),
  `test_video_piece.py`, `test_muscriptor_engine.py` (the split warmed once for the new sheet's reader);
  `bench_stream.py` times `GET /sheet`.
- New: the words routes (round trip, pool kept, 404) in `test_sheet_toolbox.py`.

# 5. Checks

| Check | Result |
|---|---|
| Backend, full run in the image on the CPU (another project holds the GPU) | 1,251 tests collected (1,397 in Phase 9: the deleted old-sheet tests); 2 failed, the two `test_transcription_transkun.py` tests that load a checkpoint saved on CUDA (as in every phase since 0). `test_the_worked_example_at_00_46_prints_three_equal_corcheas`, failing since Phase 0, was in a deleted file. After the last status change, `test_pieces`, `test_library`, `test_part_sheet`, `test_sheet_toolbox` again: passed |
| `ruff --select F` on `src`, `tests`, `scripts` | clean |
| `npx tsc -b`, `npm run lint`, `vite build` | clean; the build has no vexflow-v2 |
| `check:history`, `check:geometry`, `check:cuts`, `check:notes` | passed (`check:notes` without the prediction checks) |
| The frontend image | `docker compose build frontend` without the vexflow-v2 context: built; the container recreated with a fresh packages volume (`--renew-anon-volumes`: compose had kept the old `node_modules` with the package) |
| Browser checks, one after another | `check:frames-sheet`, `frames-edit` (10 hand moves, median 239 ms), `frames-tools`, `frames-toolbox`, `play`, `paste`, `compose`, `library`, `projects`, `public`, `requests -- --name "Bonfire Heart"`, `passage -- --played`: all passed, first run |
| The PDF (the writer changed) | `check:frames-toolbox`'s file (7 Years, 4 A4 pages, 62 kB): `pdffonts` lists the eight Times and Helvetica faces and Symbol, nothing embedded; page 1 rendered by poppler and looked at zoomed: title, lyrics, armadura, beams, grace notes, the page number |
| Not run | `check:flow`, `check:journey`, `time:flow`: they transcribe on the GPU, which another project holds. `check:journey` was moved to the new hooks without a run |
| Screenshots | `node scripts/baseline-sheets.mjs --out .../screenshots/phase-10`: 22 of 22, no console error, no failed request, nothing left behind |
| `scripts/docs/check-links.py` | 418 files, 0 broken links |

**The screenshots against Phase 0** ([`screenshots/phase-0/`](screenshots/phase-0/) and
[`screenshots/phase-10/`](screenshots/phase-10/), same numbers): 01 the steps are four (Source, Audio or Video,
Notes, Sheet); 03 the Hands address opens the Sheet step; 04 to 08 and 10 the new sheet everywhere, no line naming the
figure and a tempo, no corner marks, the floating bar with **Enhance with AI**; 11 the note toolbox with the chord
keyboard, Hand, figures, fingers, beams, grace note and ornaments; 12 and 13 the range toolbox with Both / Right /
Left and Key, Clef, Octave; 15 the preview drawn by the backend; 17 the View tab; 19 the more actions menu (Find trills
gone); 20 the print dialog with Size of the music and Space between lines; 21 and 22 the new sheet on the page of a
passage and in From other projects.

# 6. Documentation

Done by two helper sessions (backend pages; frontend and platform pages) from a shared list of what changed, then
reviewed here; the stale lines they found outside their lists were fixed here.

- Moved to `documentation/deprecated/` with a dated banner: `grid-notation.md` (the vexflow-v2 renderer) and
  `time-matrix.md` (schema 2.0); a short true `documentation/services/backend/time-matrix.md` stays at the old path
  (what `schemas/time_matrix.py` still holds, how D-09 changed).
- `context/backend/time-model.md`: D-09 told as a sequence (the reader named the negra; implementation 02 named it by
  default; implementation 03 gives it to the AI or the algorithm, with Transpose figures as the override); rule 3
  confirmed and extended (no compases, tempo, puntillos or silencios).
- `documentation/services/backend/endpoints.md` (no `/time`, no Predict hands, `/sheet/{uuid}/words`, the status
  fields, `READ_ROUTES`), `events-to-sheet.md` (ends at the hand split, then points to the core's README),
  `rhythm-and-annotations.md`, `editing-and-compose.md`, `paths-and-data.md`, `transcription-pipeline.md`;
  `context/backend/api.md`, `README.md`, `pieces-and-revisions.md`, `piano-matrix-notation.md`; `context/07-database.md`
  (the `hands` value of the step check).
- `context/frontend/rendering.md` (rewritten: the backend draws the SVG), `README.md`, `projects.md` (four steps),
  `annotations*.md`, `printing.md`, `recording-in-sheet.md`; `documentation/services/frontend/components.md`,
  `score-pdf.md`; the old sheet's sections kept as the record, marked removed in Phase 10.
- Platform: `context/00-index.md`, `00-project-complete-overview.md`, `01-project.md`, `02-tech-stack.md`,
  `02b-local-setup.md`, `03-services-overview.md`, `04-local-development.md` (the checks; `make build` needs no
  vexflow-v2), `09-coding-conventions.md`, `app/01-app-context.md` (dated notes; the user's words unchanged),
  `music/notation-logic/02-notation-spec.md`, `00-documentation-instructions.md`; the root `README.md`,
  `aitu-frontend/README.md`, `aitu-backend/README.md`; the archive pages' links to the moved page.
- `aitu-backend/src/aitu_backend/sheet/README.md` section 8 (licenses).
- Not changed: `context/language/communication-style.md` still names "VexFlow / grid-notation" in its description of
  the project; it is the user's guideline, so the walkthrough raises it instead.

# 7. Licenses (task 10.4)

The app runs on the home machines and is not distributed, so nothing is owed today. The inventory, with the action
each row needs before a release, is section 8 of `aitu-backend/src/aitu_backend/sheet/README.md`: the Verovio rules of
`engrave/vrv.py` (LGPL-3.0: a legal check or a rewrite from the description), the Leipzig glyphs (SIL OFL 1.1: keep
the notice), prompt Example 1 (Beethoven Op. 2 No. 2 from an encoding with no license file: replace or confirm),
Example 2 (NIFC Chopin, CC BY 4.0: attribution), Examples 3 and 4 (short transcriptions of two commercial pop songs:
replace before the prompt itself is published), the pulse weights (learned partly on CC BY-NC-SA data: confirm or fit
again), the lyrics fonts (OFL, notices already shipped). Bravura left with the old sheet in this phase.

# 8. Notes for later

- The `hands` value of the `projects.step` check can go with the next database revision that has another reason to
  exist.
- `split_of`, `hands_of`, `run_pipeline` and `placed_note_ids` serve only tests now; a later cleanup can move those
  tests onto `inferred_split`.
- `editing/marks.py` and the reader of `sheet.json` go together, when the user decides the old marks no longer need
  to be read (Phase 9, section 7).
