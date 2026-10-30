# 04-3 · Phase 4: the levels in the app

Status: built on 2026-10-30 on branch `feat/04-3-phase-4` (from `master` `7f5c230`); the AI test on the first minute
of 99 Red Balloons is done (section 8, $0.88); waiting for the user's check in the browser and the decision about the
version saved before the beam fix.

Audience: the agents of this plan (this phase when the user answers, and Phase 5). Technical.

# 1. Study (task 4.1)

- `EnhanceDialog.tsx` had two tabs (A stretch: hand and words; The whole song: Simplify left, right, both, Write it all
  again), with costs from `GET /sheet/{uuid}/llm/costs`. On a version of My Library (`llm.viaEdit`) the whole song runs
  in the edit copy (`SheetTab.writeInCopy` -> `POST /projects/{id}/edit`, then the run named in the navigation
  state); the stretch tab is off there (`aiHere` false).
- `job.start_simplify` / `start_stretch`: one job key per part (`sheet-llm:<part>`), a `LiveRun` whose segments the
  page veils, `edits.apply_simplify` / `apply_stretch` store as one step.
- **Duplicate** (`bundle.duplicate_project`, `new_bundle_from`) copies the bundle with `based_on`. `rows.edit_copies`
  maps a version to **one** vault project with `based_on` = that version (a dict: the last row wins), and
  `flow.open_edit` returns it. A level copy made with Duplicate from an edit copy (99 Red Balloons `c0e39afe` is the
  edit copy of `b2db46eb`) would therefore be a second edit copy: **Edit** could open "· Easy" instead of the user's
  copy, and the song page's "editing" mark would point at it. This is why plan section 5.8 changed (section 2).
- Cost of a level of the whole song (Phase 3: $0.10 to $0.42 per batch with retries, about $0.20): 99 Red Balloons has
  13 batches for both hands (10 for one hand), so about $2.70 and 25 to 30 minutes per level.

# 2. The user's answers (2026-10-30)

| Question | Answer |
|---|---|
| Where a level of the whole sheet goes | A new project per level with its own link (not an edit copy): revision `0010` |
| Patterns when none is selected | The set approved in Phase 3 for that level |
| A level per hand in the dialog | Yes, the same level by default |
| AI tests | Only the first minute of 99 Red Balloons, hard for the right hand and medium for the left hand |

# 3. The level copy (revision `0010`)

- `projects.level_of` (String 36, no foreign key) and `ProjectFile.level_of` (`levelOf` in `project.json`, synced in
  `write_project`, `new_bundle_from` and `db.tools` reindex). `HEAD_REVISION = "0010"`. The real database moved on
  2026-10-30 after `make db-backup` (`/mnt/ssd2/aimpromptu/.database-20261030-145717.tar.zst`).
- `flow.level_copy(project_id, owner, title)`: the owner's vault project or My Library version only; a duplicate in
  the vault with `based_on = None`, `level_of = source.level_of or source.id` (a level of a level points at the same
  original), `origin = {"levelOf": source}`; a vault original's folders are copied (as Duplicate). Returns the copy id
  and the map of part ids.
- `metadata.homes`: a level copy's metadata is its original's. `edited_songs` resolves level copies whose original is
  an edit copy (its version's song) or a version of My Library (its song); `tags_of_projects` and
  `set_project_tags` read and write the original's own rows for an original with no song; `copy_project_tags` skips
  a duplicate of a level copy (it keeps `level_of`, so it shares too).
- `flow.release_levels(owner, project_id)` before a project or a version is deleted (`DELETE /projects/{id}`,
  `flow.delete_version`): its level copies get the shared metadata as their own rows and `level_of = None` (DB and
  `project.json`), as an edit copy whose version is deleted. **Save to library** clears `level_of` with `based_on`.
- `GET /projects` rows: `levelOf` and `levelSong` (the link of the original's song); the Filter's artist of My
  projects reads `levelSong.artists` too (`ProjectsPage.artistsOf`).

# 4. The catalog (task 4.2, backend)

- `aitu_backend/sheet/llm/catalog/patterns.json` (113 patterns: `ref`, `hand`, `level`, `number`, `id`, `name`,
  `line`, `source`, `bars`, `f1`) and `examples/*.f1` (the first example of each pattern, 85 KB), copied from
  `gallery/04-3-phase-2/`. `defaults`: right easy 2, 1; medium 1, 14, 13; hard 1, 17, 15, 4; left easy 2, 1, 3, 12;
  medium 15, 2, 10, 7; hard 11, 2, 3, 16 (not tested in Phase 3: the hard form of the medium set).
- `levels.CATALOG_DIR`, `load_patterns()` (reads both the catalog and a gallery folder), `catalog()` (cached),
  `catalog_rows()`, `run_refs(level, staffs, selected, words)` (selected + named in the words, only of the hands
  rewritten; a hand with none gets its level's defaults).
- Routes: `GET /sheet/levels/catalog`, `GET /sheet/levels/catalog/{hand}/{level}/{number}.svg` (`render_frames` of
  the example, kept in memory, `Cache-Control: max-age=86400`). Declared before `/{audio_uuid}`.

# 5. The run and its storing (tasks 4.3, 4.4)

- `levels.level_windows(current, staffs, start, end)`: the batches of the whole song or of a range (the first and the
  last batch stretched to the range's ends). `levels.splice(current, written, windows, staffs)`: the sheet with the
  rewritten hands of the accepted batches replaced. `write_level(..., span=, on_plan=)`: a range plans only its own
  stretch; an error of the plan request (no credits) ends the run with nothing written.
- `job.start_level(part, level, hand, start, end, patterns, words)`: the job key of the part (one AI run at a time),
  `LiveRun` with the batches as segments (the staff of a one-hand run veiled); events `level`, `plan`, `batch`,
  `saved`; the sheet of the moment after each batch (`_level_preview`: the accepted answers drawn by `levels.drawn`
  with the other hand's notes). The summary: `level` (`ok`, `failed`, `stale`, `gone`), `batches`, `total`,
  `levelName`, `usd`, `note`.
- `edits.apply_level`: the storing of `apply_stretch` made common (`_store_written`): over `[first accepted batch,
  last accepted batch)`, the drawn notes not in the spliced sheet marked removed and the new ones added
  (`change_notes`, at the onset of their column, as long as their figure), the hand of every note the sheet draws
  written into `notes.pmn` (notes moved to the other hand too), the sheet laid with `build.reapply` and the AI's
  figures kept as set by hand (a note the rule would make a decoration note keeps the AI's figure), one step
  ("Level easy with AI, both hands"). A batch that failed keeps its notes. `record.levels` (new field of
  `store.Record`): `level`, `hand`, `start`, `end`, `range`, `prompt` (`LEVEL_VERSION`), `patterns`, `words`, `plan`,
  `batches` (`[start, end, status, replies]`), `declared`, `usd`, `requests`, `written`.
- Routes: `POST /sheet/{uuid}/llm/level` (a range, write rights), `POST /sheet/{uuid}/llm/level-copy` (the whole
  sheet: `flow.level_copy`, then `start_level` on the copy's part; in `READ_ROUTES`, the owner of the song only, else
  403). Title: `<title> · Easy`, `· Right hard, left medium`, `· Easy, left hand`. `GET .../llm/costs` adds
  `level-<hand>` and, with `?start&end`, `level-stretch-<hand>` (`job.level_cost`: $0.05 + $0.20 per batch).

# 6. The dialog (task 4.2, frontend)

- `EnhanceDialog.tsx`: A stretch: Which hand, then **How**: Your words / A level. The whole song: **A level** first in
  the list (Simplify stays the default choice of an enhanced sheet, so the dialog never preselects the dearest run),
  then **The whole sheet / Right hand only / Left hand only**. A level: one Easy/Medium/Hard selector per hand
  rewritten, the patterns line ("Left: easy 2, easy 1, easy 3, easy 12 · Right: hard 1, hard 17, ..."), **Patterns**
  (the catalog), the words (optional, "At frame 112 use hard 3."), the cost and the minutes (2 per request). The
  whole song: "A new project in My projects, named with the level. This sheet stays as it is."
- `PatternCatalog.tsx`: the hands rewritten (left first), pills Easy / Medium / Hard / Super hard (opens on the
  hand's level), each pattern with its checkbox, `<level> <number> · name`, line, source and bars, and the drawing
  (`patterns.ts: drawingUrl`). The selection of a hand replaces its defaults.
- `FramesSheetPage`: `sendStretchLevel` (the hook's `level`, in place) and `sendSongLevel` (`sheetApi.levelCopy`, then
  the sheet of the new part opens; the page follows the running job as after a reload). On a version of My Library a
  level goes straight into its new project (no edit copy).
- `useFramesSheet`: `level()`; the end notices ("The AI could not write this level. The sheet stays as it was.",
  "The AI wrote 3 of 4 parts at the level; the others stay as they were.").
- Also fixed: `FrameRangeFields columns={sheet?.columns ?? []}` (a `tsc -b` error already on `master`, from Phase 2b).

# 7. Checks

| Check | Result |
|---|---|
| `tests/test_sheet_levels_app.py` (new: catalog, defaults, routes, a run of both hands stored with a stand-in, a range of one hand, a run that fails, the level routes and the level copy) | 7 passed |
| `tests/test_folders_and_metadata.py` (new test: the level copy's metadata, Edit, deleting the original, Save to library) | 9 passed |
| `tests/test_rights.py` (the level routes in rows 1 to 3) | 13 passed |
| Full backend suite, in the container on the CPU | all passed except the two Transkun tests, which need the GPU (they fail on `master` the same way) |
| `tsc -b`, `eslint src` | clean |
| `check:enhance-dialog` (extended: the level of the whole song, the catalog and its drawings, a pattern added, the body of `level-copy`; a level of a stretch and the body of `level`) | all passed |

The stand-in test of a run replaces `check_level` with one that accepts every answer it can read (the check is Phase
3's, tested in `test_sheet_levels.py`), so the storing is tested on the test part's own notes: every batch leaves out
the left hand's upper notes and its last note, moves the first right-hand note to the left hand and adds a note an
octava under the first left-hand note; after the run every live note of `notes.pmn` has the hand the stored sheet
draws it in (`hands_agree`, the check of Phase 3 report section 16), undo gives back the notes and hands, redo the
level.

# 8. The AI test: the first minute, hard for the right hand and medium for the left hand (task 4.5)

The user's choice (2026-10-30): only the first minute, at hard for the right hand and medium for the left hand.

- **Setup**: a temporary copy of `c0e39afe` made with `flow.level_copy` (so it is not a second edit copy):
  `05e89c47` "99 Red Balloons — Nena · first minute (test)", split at 60 s through the app (`POST
  /projects/{id}/parts/{part}/split`): part 1 has 580 notes, f33-f1497, the AI's sheet of the original kept. Then
  `POST /sheet/05e89c47.../llm/level-copy {right: hard, left: medium, hand: both}` through the app: the level copy
  `99381667` "... · Right hard, left medium", job `ae7cee8f`.
- **Cost and time**: estimate $0.85; measured **$0.877**, 9 requests (the plan, then 4 batches with 3, 2, 1 and 2
  replies), 8 minutes. All 4 batches accepted.
- **The plan the AI wrote**: S1 f33-f355 `L=keep` (held fifths and small chords), S2 f355-f812 left medium 2, S3
  f812-f1498 left medium 15 (the riff and the chorus: an octava bass, then two beamed corcheas of the chord; the top
  notes of the left-hand chords go to the right hand as the riff); the right hand hard 1 all through.
- **Declared**: the six high chords of the riff (D#7-E7 at f863 and f990, D#6-E6 at f926) as artifacts; accompaniment
  notes under held melody notes and E4 octava doublings as not melody.
- **Measures of the first minute** (f33-f1498): left hand from chords of up to 7 notes over 36 semitones (reach 36,
  0.69 moves per negra, 5.6 notes/s) to at most 3 notes within 12 semitones (reach 27, 0.55 moves per negra, 3.65
  notes/s); right hand from up to 6 notes over 15 semitones (0.40 moves per negra) to up to 3 notes within 10
  semitones (0.12). Decoration notes 35 -> 6.
- **Stored**: 442 live notes, every one with the hand the stored sheet draws it in (`notes.pmn` and the Notes tab
  agree); the undo step "Level hard for the right hand and medium for the left hand with AI, both hands".

**A fault found zoomed in**: the stored level had no beam groups (every corchea with its own flag). The run stored the
answers as written (an answer has no beams: the app draws them by its rules, Phase 3), and `splice` cleared the beams
of the new notes. Fixed: `job._level_drawn` (used for the sheet of the moment and for what is stored) draws the
accepted answers with `levels.drawn` and `splice(..., reading=True)` keeps their beam groups (numbered after the rest
of the sheet) and decoration notes; the AI's figures are kept as set by hand except on decoration notes. Checked on
the same notes in memory (`screenshots/04-3-phase-4/level-with-beams.png`): 262 of 333 short notes in 52 beam groups
(stored before the fix: 0); the original has 339 of 493 in 57.

**The user moved the level copy meanwhile**: while the agent looked at it, the user used **Save to library** on
`99381667` (it is now the version "medium" of the song 99 Red Balloons, id 19, version 34, `level_of` cleared as
designed) and exported it. That version was stored before the fix, so it still has no beams; it is a piece of My
Library, so the agent did not change it (a question for the user in the walkthrough).


# 9. The version "medium" drawn again, and the notation after every AI change (the user, 2026-10-30)

- **The version "medium"** (`99381667`, saved by the user before the fix): at the user's request its reading was drawn
  again with the fixed path (scratch `rebeam.py`: the stored notes as the answer, `job._level_drawn` on the original
  first minute, `build.reapply` on its notes, the AI's figures kept; a dry run first). Same notes, staffs and hands
  (442 of 442 agree); 53 beam groups (before: 0); 7 decoration notes by the rule (before: 6); one step of undo "The
  level's beam groups drawn again". Its old `sheet.f1` is kept in `/home/app/04-3-phase-4/backup/` (on the host
  `/mnt/ssd2/aimpromptu/home/04-3-phase-4/backup/`).
- **The rule** (user: "after the enhancement, we will force all of the music notation to be rewritten after the
  changes"). Study: every AI path already ends with `build.reapply` (figures, spelling, decoration notes, clefs and
  8va of changed notes run again), but `reapply` gave a note new to the stored reading, or on another staff, no beam
  group. This affected the notes Simplify adds or moves, and a note moved to the other hand by an edit. Fixed in
  `reapply` (`_beam_as_rule`): a changed note joins the beam group of its column when the column has one; a beam
  group of the rule whose notes all have none, one of them changed, becomes theirs; a stored beam decision is never
  changed. Test `test_notes_new_to_the_stored_sheet_get_the_beam_groups_of_the_rule`. The steps after every AI
  change are written in the docstring of `part_sheet/edits.py` and in plan section 6.
- Sheets stored before keep their readings (a note already in the stored reading is a decision): the 23 notes Simplify
  added to 99 Red Balloons on 2026-10-28 are not beamed again unless a later change touches them.
- Checks after the change: full backend suite (all passed but the two Transkun tests that need the GPU);
  `check:frames-edit` fails one step, "a box dragged across the staves picks the notes in it" (3 notes, more than 3
  expected, at the start of 7 Years), twice; 7 Years is drawn identically with and without the new step, so this
  failure does not come from it (left for Phase 5).

# 10. Needed later

- Phase 5: the core's `README.md` (the level run, the catalog folder), `context/frontend/annotations.md` and
  `rendering.md` (the dialog), `context/music-library/private-library.md` (the level copy's metadata).
- The level of a level copy shares the original's song; **Save to library** of a level copy lets the user choose the
  song (a version "Easy"): not tested with the AI.
- The temporary copy `05e89c47` ("99 Red Balloons — Nena · first minute (test)") stays until the user has checked the
  level made from it; then it can be deleted (its level copy keeps sharing the song's metadata, because its
  `level_of` is `c0e39afe`).
