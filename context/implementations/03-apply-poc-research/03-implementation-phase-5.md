# 03: Phase 5 report: the new Sheet step (to see and to hear)

Plan: [`03-plan.md`](03-plan.md) section 7, Phase 5. Checklist: [`03-checklist.md`](03-checklist.md). Branch
`feat/migrate-new-logic` (`master` was already contained in the branch, nothing to merge). Written 2026-10-25 on the
Ubuntu machine. **State: built; the user's check in the browser is pending**, and the question of task 5.10 (merge
into `master` now or at the end) is asked in the walkthrough.

# 1. Summary

| Task | Result |
|---|---|
| 5.1 Study and question | Section 2. The user's answer (section 3): the 10 songs Sonnet wrote in Phase 4 show Sonnet's sheet; every other song keeps its data and shows the algorithm's sheet, with a button that runs Sonnet on the whole piece; new transcriptions go to Sonnet by themselves |
| 5.2 The flow | Four steps (Source, Audio, Notes, Sheet); the Sheet step opens when the notes are ready; an old `/hands` address opens `/sheet`; `GET /matrix/{uuid}/events` gives only saved hands (Notes Falling plays a new transcription in one colour); the negra choice is not on the new sheet |
| 5.3 Algorithm at once, Sonnet in the background | `aitu_backend/part_sheet/` (store, build, job) and `api/sheet.py`; the page `pages/piece/sheet/frames/`. A 40 s clip: the algorithm's sheet on screen 0.9 s after the step opened, Sonnet's first segment back at about 19 s, the whole clip in 91 s, $0.18. The segment at Sonnet has a pale veil; a segment that comes back is written column by column into blank staves (about 1.8 s); no text |
| 5.4 Hands in `notes.pmn` | At the end of the run (`job.commit`, `save_edit`); saved hands before it go to the part's history (`snapshot_notes`, with a reason) |
| 5.5 Stored, not asked again | `sheet.f1` (F1 frames text and a record line) beside `sheet.json`; in the file lists of duplicate, `.aitu` export and import, Save to library, and the history. The 10 viewer songs got the Phase 4 sheets (`scripts/import_llm_sheets.py`, after `make db-backup`) |
| 5.6 Playback | The cursor by the audio time (the research viewer's arithmetic), the noteheads of its column lit, a click on the sheet seeks; Play mode keeps the cursor's line in the middle |
| 5.7 The switch | Inside `SheetPage`: the new sheet first on the Sheet step, a version of My library and Play mode; **Edit in the old sheet** and **Back to the new sheet** on the floating bars; closed while Sonnet writes |
| 5.8 Browser checks | `check:frames-sheet` (new; `--live` spends a few cents); `check:play` on the new hooks; the old sheet's checks press the switch (`session.oldSheet`); `check:flow`, `check:journey`, `time:flow` rewritten for the new flow, not run (section 9) |
| 5.9 No tempo line | The new sheet has none |
| 5.10 Merge question | Asked in the walkthrough |

# 2. The study (task 5.1)

## 2.1 What exists

| Part | Where | What the phase found |
|---|---|---|
| The steps | `pieces/status.py` (`STEPS`), `api/pieces.py`; frontend `api/pieces.ts` (`PIECE_STEPS`), `PiecePage.tsx`, `StepTabs`, `components/piece/stepLabels.ts` | Five steps; each tab enabled from the backend's answer only. The Sheet step's state compared `sheet.json`'s `handsRevision` with `notes.pmn`'s; the Hands step needed every placed note to have a hand. The projects table keeps the step (`projects.step`, a check constraint on its values) |
| The Sheet step page | `SheetTab.tsx` -> `sheet/SheetPage.tsx` (3,262 lines) -> `TimeScoreView` (vexflow-v2) | One page with roles (`readOnly`, `play`, `passage`), used by six screens. It loads the default reading (the negra), the saved `sheet.json`, the lyrics, then `POST /time/{uuid}/score`, and owns every editing tool |
| The player | `components/time/ScorePlayer.tsx` | Reusable as it is: the recording, `onTime` on every animation frame, a `controlsRef` (seek, toggle), Space, headless for Play mode, a stop time |
| The jobs and their stream | `transcription/jobs.py`, `GET /matrix/progress/{jobId}` (SSE) | Keyed jobs (a second start returns the first), named messages (`reporter.send(name, payload)` -> `event: name`), every frame kept and replayed to a late reader, an owner. Fits Sonnet's job as it is |
| How parts are stored | `storage/paths.py`, `bundle.PART_FILES` (duplicate), `exchange.PART_FILES` (`.aitu`), `library/flow.VERSION_FILES` (Save to library, restore), `editing/history.py` (snapshots) | Four lists of part files to extend |
| Notes Falling | `pages/play/FallingView.tsx`, `GET /matrix/{uuid}/events` | The route coloured notes without a saved hand by the hand split |
| The rights | `auth/rights.py`, `project_rights` on every router | A version of My library is never written in place (403), it changes through **Edit**. A `/sheet/{audio_uuid}` route gets the check by itself |
| The browser checks | `aitu-frontend/scripts/` | 16 scripts select vexflow-v2 classes; `check:flow`, `check:journey`, `time:flow` walk the Hands step |

## 2.2 The data (read only, 2026-10-25)

| Layer | Parts | With saved hands | With `sheet.json` |
|---|---|---|---|
| My library (user 1, user 2) | 33 | 33 | 33 |
| Projects (user 1) | 13 (one with no notes) | 9 saved as a whole, 3 partly | 8 |
| Public, requests | 1, 2 | 2 | 3 |

`sheet.json` names its pile of gaps a negra in 36 of 43 sheets (vexflow-v2's default, D-09 as changed by
implementation 02) and a corchea in 7 (renamed by the user). 4 parts have lyrics (1 or 2 pieces each).

# 3. The user's answer, and what it changed

The question (plan task 5.1) offered: keep the data with no LLM, Sonnet again with new hands, or Sonnet again with
the saved hands kept. The user's answer, in short: "Keep all the data that we currently have for the songs that
have not been transcribed with Sonnet ... For the ones that we have, just use the Sonnet version to render it ...
on these songs that we have not used Sonnet on yet, you need to provide a button in the sheet step. It allows the
user to run the full piece, with all the new hand predictions and the new rendering of the music. Otherwise, it
will show the default one." What was built:

- **The 10 viewer songs** (versions of My library) got the sheets Phase 4 paid for, rebuilt from the run's files
  (`viewer-final/<part>.f1`, `summary.json`), with no request. Each was checked to still fit its notes (every onset
  cell once); its hands went into `notes.pmn` (the hands before are in the part's history), its sheet into
  `sheet.f1`. Backup first: `/mnt/ssd2/aimpromptu/.database-20261025-153945.tar.zst`.
- **Every other part** draws the algorithm's sheet from its saved hands, with two decisions of its `sheet.json`
  kept: the key (and key changes), and the reference figure only when the user renamed it (a corchea; the default
  negra is replaced by the pulse estimate, plan section 3.3). The rest of `sheet.json` is Phase 9's.
- **The button**, **Enhance with AI**, on the floating bar of the Sheet step of a part the user may change, with a
  confirmation (about $1 of the monthly credits; the hands now are kept in the history). On the owner's version of
  My library the button opens the edit copy (as **Edit**) and Sonnet starts there: the rights table forbids
  writing a library version in place, and **Save to library** then replaces the version.
- **New transcriptions** go to Sonnet by themselves. The first rule (no `sheet.json`, no saved hands) also matched
  three projects made before the phase (The Other Side, classical-mix, even-and-swung), so a new transcription is
  marked explicitly: `pipeline.clear_new_sheet` writes `sheet.pending` (transcription and video read), the page
  starts Sonnet when `llm.auto` is set, and the job removes the mark.

# 4. The backend

## 4.1 `part_sheet/store.py`: `sheet.f1`

The F1 frames text with one comment line on top (the F1 reader skips `#` lines):

```text
# aitu-sheet {"source":"llm","handsRevision":2,"windows":[[177,577,"llm"],...],"quarterMs":480.0,"reference":"llm",
#             "model":"claude-sonnet-5-5","prompt":"5","usd":0.6825,"requests":16,"written":"...","note":null}
F1 frames frameMs=40 quarterMs=480
key=2b clefs: R=treble L=bass
...
```

`source` is `llm` (every window), `mixed` or `algorithm` (no window: no key, no credits); `handsRevision` is the one
of `notes.pmn` the sheet was written for. `sheet.pending` is the mark of section 3. Paths:
`paths.part_frames_path`, `part_frames_pending_path`.

## 4.2 `part_sheet/build.py`: the sheet of a part at any moment

1. Stored and current (same `handsRevision`): as stored.
2. Stored for older notes or hands: `reapply` lays its decisions on the current notes: the algorithm on the current
   hands (with the stored armadura and reference figure) gives the notes; a note found at the same column, key and
   hand keeps its stored note (beam group, ornaments, 8va); a note found at the same column and key in the other
   hand keeps its tags without its beam group; a note the stored sheet did not have keeps the algorithm's note
   without a beam; clefs and armaduras stay; then `assemble` runs the rules (figures, grace notes, beam groups cut
   by the figures, spelling). The hand is always the one of `notes.pmn`. A stored `algorithm` sheet is computed again.
3. Nothing stored: `propose_frames` on `pipeline.starting_hands` with the decisions of section 3.

Answers are cached by the modification times of `notes.pmn`, `sheet.json` and `sheet.f1` (24 parts). `hands_of_sheet`
gives each live note the staff of the sheet note at its drawn column (the D-04 group start, as `frames.from_notes`)
and key. `draw(text, width)` is `render_frames` for a staff width of 60 to 320 staff spaces.

## 4.3 `part_sheet/job.py`: Sonnet in the background

`start(part)` submits a keyed job (`sheet-llm:<part>`, not on the GPU queue). The job reads the starting hands,
keeps a `LiveRun` (the sheet before the job and its windows during the reference request; then the algorithm with
Sonnet's reference figure; then the parts decided so far plus the algorithm's parts for the rest, assembled on
demand and cached by the number of parts), and sends `event: sheet` messages: `reference`, `windows` (the windows are
known), `window` (one more decided), `saved`. Two callbacks were added to the core's `write_frames` for it:
`on_start(algo, windows)` and `on_part(log, part)`; nothing else of the chain changed. At the end `commit` (under the
part's lock): when `notes.pmn` still has the notes revision the job read, the hands of the sheet go into
`notes.pmn` (`save_edit`, `hands_changed`; a snapshot first when the hands had been saved as a whole), and
`sheet.f1` records the new `handsRevision`; when the notes changed meanwhile, the sheet is stored for the old notes
(`handsRevision: null`) and laid on the new ones when drawn. A window that fails keeps the algorithm (Phase 4);
with no window written, the hands are not touched and `sheet.f1` holds the algorithm's sheet, so the page does not
start again by itself and keeps the button. Before each request the job checks that the part still has notes: a
deleted project stops the requests (`PartGone`), and nothing is stored.

`available()`: `ANTHROPIC_API_KEY` set and the SDK importable.

## 4.4 Routes and status

- `GET /sheet/{uuid}?width=N`, `POST /sheet/{uuid}/llm` (`api/sheet.py`, documented in
  `documentation/services/backend/endpoints.md` section 4.1). A part with no live notes answers an empty drawing
  (the page then shows the old sheet's empty state, with **Record a passage** and **Paste**).
- `pieces/status.py`: `STEPS = (source, audio, notes, sheet)`. The Sheet step is enabled when the notes are ready,
  `running` while Sonnet writes, `ready` with a stored `sheet.f1` or a current `sheet.json`, `stale` when only a
  stale `sheet.json` is left, `missing` otherwise; `details.legacy` is the state of `sheet.json` (the old sheet's
  banner). The computation of the hands step (`placed_note_ids`, about 25 ms a part) is gone. A project row still
  stored as `hands` is worked out again when listed (`api/projects.py`, `api/library.py`); the column's check keeps
  the value (no migration).
- `GET /matrix/{uuid}/events`: only saved hands (`_hand_labels` removed).
- Transcription and video read: `clear_new_sheet` (forget `sheet.f1`, write `sheet.pending`); the snapshots carry
  `sheet.f1`.

## 4.5 The image

The backend image runs uv's Python 3.12.13 (python-build-standalone in `/opt/python`, `UV_PYTHON_PREFERENCE=
only-managed`; downloaded once in its own layer, every later uv call offline) and has `anthropic` 2.2.0. `make up`
on 2026-10-25 restarted the app with it and with `ANTHROPIC_API_KEY` from `.env`.

# 5. The frontend

- `api/sheet.ts` (`sheetApi`), `api/pieces.ts` (four steps).
- `pages/piece/sheet/frames/`: `FramesSheetPage` (title lines from `sheet.json` when it has them, the player, the
  floating bar: Play, **Enhance with AI**, **Edit in the old sheet**), `FramesSheetView` (the SVG scaled to the
  page, and an overlay SVG in the same units: the pale veil of `working` segments, breathing between 55 and 72 %
  white; the reveal masks with the engine's staff lines, 13/180 of a staff space; the cursor; `[data-lit]` on the
  noteheads of the cursor's column), `geometry.ts` (from `viewer/index.html`), `useFramesSheet.ts` (the loads at the
  page's width in steps of 4 staff spaces, about 8.5 px a staff space; the job's stream; the start on `llm.auto`),
  `navigation.ts`.
- `SheetPage` is now the switch: `step.newSheet` (set by `SheetTab` and `PlayPage`) shows `FramesSheetPage`; the old
  page (`VexflowSheetPage`, unchanged otherwise) gets **Back to the new sheet** on its bars, and a bar with only
  that button while its sheet is not drawn (the stale banner).
- `SheetTab`: `newSheet`, the old sheet's state from `details.legacy`, **Enhance with AI** through the edit copy on
  a version of My library (`WRITE_WITH_SONNET` in the navigation state starts Sonnet in the copy).
- `NotesEditor`: **Continue to Sheet**; `App.tsx`: `/hands` redirects to `/sheet`; `PiecePage`: the amber dot of
  unsaved notes on the Notes tab.

# 6. Measurements

| What | Value |
|---|---|
| The algorithm's sheet of a library song, first time (host) | about 0.5 s (7 Years: the starting hands and `propose_frames`), then 0.1 ms from the cache |
| Draw a whole song (`render_frames`, host) | 31 to 42 ms; the SVG 330 to 400 KB, 48 KB with gzip (the JSON answers are compressed) |
| Sheet step of a library copy, first notehead on screen | 0.3 to 2.1 s (the copy's sheet stored; the first one includes the cache) |
| A 40 s clip, live (`check:frames-sheet --live`) | the algorithm's sheet 0.9 s after the step opened; Sonnet's first segment back at 18.9 s, the second at 47.3 s, done at 89.6 s; 223 of 223 notes with a hand; $0.1785 |
| Old Sheet step | unchanged (the old page loads only when opened) |
| The engine in the container, uv's Python (10 viewer songs, Sonnet's sheets, width 140, warm median) | 38 ms per song (max 59); Phase 3 measured 49 ms with Debian's Python and 36 ms on the host |

# 7. Checks

| Check | Result |
|---|---|
| Backend tests, the files changed by the phase (host, CPU) | `test_part_sheet.py` (new, 10 tests), `test_pieces.py`, `test_paste.py`, `test_passages.py`, `test_rights.py`, `test_projects.py`, `test_library.py`, `test_sheet_llm_frames.py`, `test_sheet_engrave_frames.py`: all pass |
| Backend, full run in the image on the CPU | 1,338 tests: 1,336 passed, 1 skipped (it needs a GPU), 1 failed: `test_the_worked_example_at_00_46_prints_three_equal_corcheas`, failing since Phase 0; 116 s. `test_transcription.py` lists `sheet.pending` among the files a transcription writes |
| `npx tsc -b`, `npm run lint` | clean |
| `check:history`, `check:note-names` (15), `check:geometry`, `check:cuts`, `check:notes`, `check:render` (60) | passed |
| `check:frames-sheet` (and `--live`) | all passed (section 6) |
| `check:play` | all passed (the lyrics of Play mode skipped: Phase 8) |
| `check:paste`, `check:transpose`, `check:lyrics`, `check:compose`, `check:library`, `check:public`, `check:projects` | passed (`check:library` after its Hands-step walk became a Notes-step one) |
| `check:requests` | not run: it refuses to start because 7 Years already has a public version (a condition of the data, before this phase) |
| `check:flow`, `check:journey`, `time:flow`, `check:passage`, `bench:sheet` | not run: they transcribe on the GPU (and now start Sonnet); rewritten or switched to the old sheet where they touched the Sheet step |
| `scripts/docs/check-links.py` | passed |

# 8. Notes for later phases

- **Phase 6 (the edit model).** `build.reapply` matches a stored sheet to the notes by drawn column and key. A
  paste or a promotion moves every column after its point, so the stored decisions there are lost (the algorithm's
  then); matching by note id (the notes keep their ids) is the fix when the edit model is built. The old sheet's
  hand moves (`PUT /time/{uuid}/hands`) already reach the new sheet through `notes.pmn`.
- **Save to library** needs the Sheet step `ready`: a new transcription can be saved once Sonnet has finished (or
  failed; the algorithm's sheet is then stored).
- **Lyrics, print, stretches** are not on the new sheet yet (Phase 8): Play mode shows no lyrics (4 parts have
  some); printing and marking a stretch (Copy, Add to a playlist) go through the old sheet.
- **The old sheet of a song Sonnet wrote** opens with its stale banner (its `sheet.json` was saved for the hands
  before Sonnet); **Write the sheet** draws it on the new hands.
- **Running Sonnet again** on a part it wrote is not offered (Phase 6 question). The job input shows no hands
  (`write_frames(hands=False)`, the research's best); Phase 6 decides `hands=True` for a run on the user's hands.
- **Cost** is recorded per run in `sheet.f1` (`usd`); the live clip cost $0.18 for 40 s.
- **A backend restart stops a run and loses it** (the job lives in memory; `sheet.f1` is written at the end). It
  happened once in this phase: an edit of `api/projects.py` reloaded the backend 4 minutes into the user's run on the
  edit copy of 99 Red Balloons, and the windows already paid for were lost. Fix to consider: write each decided
  window to disk and let a new run start from the first window not decided.
- **Enhanced with AI** (the user's request of 2026-10-25): the page says "AI", not "Sonnet" (the model may change).
  A sheet whose record source is `llm` or `mixed` shows the green badge **Enhanced with AI** beside its title, for
  good (a stale sheet laid on new notes keeps it; only a new transcription clears `sheet.f1`), and its button reads
  **Enhance it again with AI**, with a confirmation that a new run may give much the same result. The record counts
  the runs (`runs`). A new run on an enhanced sheet that does not finish every window keeps the earlier AI sheet
  whole (`job.commit`), so the mark and the AI's decisions are never lost to a failed run.
- **The Projects page** shows a spinner before the title of a project while a job works on it (`running`:
  `transcribing`, `reading`, `writing`), added after the user's request of 2026-10-25.
- **Checks that transcribe** (`check:flow`, `check:journey`, `time:flow`) now start Sonnet. `check:flow` and
  `time:flow` delete their pieces at the end, which stops Sonnet at its next request; `check:journey` waits for
  Sonnet to finish before **Save to library** (about $1 a run).
- The scratch scripts (the first browser look) are not kept; `check:frames-sheet` replaces them.

# 9. Documentation

- `aitu-backend/src/aitu_backend/sheet/README.md` section 12; `context/backend/README.md`.
- `context/frontend/projects.md` (the steps), `rendering.md` (the new sheet), `play-mode.md`, `README.md`,
  `pages.md`; `context/backend/pieces-and-revisions.md`; `context/07-database.md` (`sheet.f1`, `sheet.pending`);
  `documentation/services/backend/endpoints.md` (the `/sheet` routes, the status, the events' hands).
- [`03-plan.md`](03-plan.md) Phase 5 tasks, section 8, section 11; [`03-checklist.md`](03-checklist.md),
  [`README.md`](README.md), `../README.md`, `../../00-index.md`.
