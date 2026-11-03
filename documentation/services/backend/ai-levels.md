> Context: [context/ai/levels.md](../../../context/ai/levels.md) (what a level is, the catalog, the grid, the chords of the song) and [context/ai/README.md](../../../context/ai/README.md)

# The levels: the code of the catalog, the grid, the harmony, the hands and the chords

The levels of **Enhance with AI** (implementation 04-3, Phases 3 and 4; the chords of the song, implementation 04-5).
This page tells the files and functions. The run that writes a level (the plan, the batches, the check) is in
section 8; the history of runs in section 9.

Modules: `aitu-backend/src/aitu_backend/sheet/llm/catalog/` (the patterns), `sheet/llm/levels.py` (the catalog's
loading, the guide's chords, the prompts of a level), `sheet/levels/` (`grid.py`, `harmony.py`, `hands.py`: the
music analysis, no AI), `part_sheet/job.py` and `part_sheet/edits.py` (the level in place), `library/flow.py` (the
level copy), `api/sheet.py` (the routes), `storage/bundle.py` (the part's `chords`, the project's `levelOf`).

## 1. The catalog: `sheet/llm/catalog/`

- `patterns.json`: the keys `about` (the history of the catalog, text), `levels` (`easy`, `medium`, `hard`,
  `super hard`), `patterns` (the list) and `defaults` (`hand -> level -> [number, …]`, the approved sets, plus
  `about`). A pattern has `ref` (`left easy 1`), `hand` (`left`, `right`), `level`, `number`, `id` (a slug), `name`,
  `line` (one line of what it is), `source` (the piece), `bars`, and `f1` (the file of its first example).
- `examples/*.f1`: the examples, in F1 frames text, both hands. The file names are `prelude-4-…`, `ballade1-…`,
  `ballade4-…` (the real pieces) and `drawn-left-…` / `drawn-right-…` (drawn for the project). `drawn-left-song-chords.f1`
  is left easy 1 (The song's chords, 2026-10-31).
- Counts: left easy 15, left medium 19, left hard 18, left super hard 2; right easy 10, right medium 17, right hard 20,
  right super hard 13; 114 in all.

`sheet/llm/levels.py`:

- `Pattern` (a dataclass): `ref`, `hand`, `level`, `number`, `name`, `line`, `example` (the F1 text). `Pattern.text(negras,
  strict)` gives the pattern for a prompt: its heading with `(Strict)` or `(Suggested)`, its line, and the start of its
  example (`EXAMPLE_NEGRAS` negras, both hands), with the notes of the other hand shown. Used by the run's system prompt.
- `load_patterns(catalog)` reads `patterns.json`; a pattern whose `f1` file is missing is left out. `catalog()` reads
  it once into `_catalog`. `catalog_rows()` gives the rows for the dialog (every field but `example`) and `defaults`
  (the `hand` keys of `STAFF` only: `about` is dropped).
- `run_refs(level, staffs, selected, words, *, exact)`: the refs of a run, in this order: the selected patterns, then the
  ones the words name (`refs_in`, the pattern of `left medium 2` or `medium 2`), kept only when known and of a hand
  rewritten. A hand with none of them gets the `defaults` of its level, unless `exact` (then it keeps none: `free`).
- `LEVELS = ("easy", "medium", "hard")`: the levels of a run. `super hard` is in the catalog and the regular
  expression of the refs (`_REF`), not a level of a run yet (the module says "super hard later").
- `CATALOG_DIR = Path(__file__).with_name("catalog")`.

Routes (`api/sheet.py`):

- `GET /sheet/levels/catalog` (`level_catalog`): `CatalogOut` = `patterns` (the rows of `catalog_rows`) and `defaults`.
- `GET /sheet/levels/catalog/{hand}/{level}/{number}.svg` (`level_drawing`): the example of one pattern, drawn by
  `frames_engine.render_frames(example, px_per_space=10.0, note_ids=False)`. The level in the URL is `super-hard` for
  super hard. Kept in memory once drawn (`_drawings`); `Cache-Control: max-age=86400`. 404 for an unknown ref.

## 2. The grid: `sheet/levels/grid.py`

Where a new note of a level may start, in frames of 40 ms (the module's docstring).

- Constants: `TOLERANCE = 1` (frames: how near a point a frame must be), `FIT_BEATS = 16` (the pulses over which a local
  tempo is fitted), `STEPS` (`negra` 0, `corchea` 1, `semicorchea` 2).
- `class Grid`: `corcheas` (the points), `division` (2 or 3 corcheas to a negra), `phase`, `quarter_ms`, `onsets`, `info`
  (the spreads and shares, for the log). Methods: `points(start, end, kind)` (the points of a kind in a range),
  `beat_of(frame)`, `kind_of(frame, tolerance)`, `on_grid(frame, kind, tolerance)`, `text(start, end)` (the grid as
  the prompt tells it).
- `song_grid(sheet, quarter_ms)`: builds the grid from the notes of both hands (ornament onsets left out). The pulse is
  tracked at the negra and at the corchea (`_track`), and the steadier one wins (`spread`); the division of a negra
  is 3 when `_share` of the onsets on its thirds beats the halves by more than 0.1. `_split(b, d)` splits each beat.

## 3. The harmony: `sheet/levels/harmony.py`

The chord of each stretch, from the notes, with no AI.

- Constants: `BASS_WEIGHT = 1.0` (the lowest left-hand note), `OUTSIDE = 0.6` (a note outside the chord costs this),
  `ROOT_BONUS = 0.15` (the bass is the root), `RICH_MARGIN = 0.12` (a seventh or a diminished chord must win by this over
  the best triad), `MIN_BEATS = 2` (a shorter chord joins the stretch before it when within `STAY = 0.2`), `KINDS`
  (`""` major, `m` minor, `7` dominant seventh, `dim` diminished, as the intervals from the root).
- `pitch_name(pc, key)`: a pitch class as a letter name (sharps or flats by the key). `class Chord`: `name(key)`,
  `tones()`.
- `_score`, `_best`: the weight per pitch class of a negra against each template on the 12 roots.
- `chords(sheet, grid, start, end)`: one `Chord` per negra of the grid, joined into stretches. Used by the plan's
  summary (`song_summary`) and by the check of an answer (`check_level`) in `sheet/llm/levels.py`.

## 4. The hands: `sheet/levels/hands.py`

How hard a passage is to play, per hand: the measures of the research (the tracker of the hand over the app's frames).

- Constants: `SPAN = 12` (an open hand, finger 1 to 5 over an octave, in semitones), `SHIFT = 3.0` (the fixed cost of
  any move), `FAST = 0.25` s (a move in less time), `BIG = 7` semitones (a move of more than a fifth),
  `REGULAR_WEIGHT = 0.3` (a move inside a repeated shape costs 30 % of its distance in the effort), `NAMES`.
- `name(midi)`, `columns(...)`, `melody(sheet, start, end)` (the top line of a hand), `class HandTrack`, `track(times,
  slices, span)` (the dynamic programme that places the hand over the notes), `_regular(tr)` (the regular moves),
  `class Measures` (the result: notes and columns per second, the span, the reach, the moves per negra, the big and
  fast moves, the share of regular moves, the effort, the pattern share), `_reach`, `_pattern`, `measure(...)` (the
  measures of one hand over a passage, with the grid), `place_line(sheet, staff, start, end, most)` (the placements,
  as text for a prompt).

## 5. The chords of the song

- `sheet/llm/levels.py`: `guide_chords(text)` reads every line whose words are all chord symbols (`_SYMBOL`: a root,
  an optional `#` or `b`, `m` (not `maj`), a kind: `maj7 7 sus4 sus2 4 2 dim aug 6 9 add9`, an optional bass). It
  returns `(root, pitch classes)`, once each. `C4` is the guitarists' Csus4. `guide_prompt(text)` is the section of the
  system prompt with the guide.
- `api/sheet.py`: `LevelRequest.chords` (up to 8000 characters; `None` means the chords saved with the part).
  `_chords(part_id, body)` saves the request's text in the part (`bundle.project_lock`, `bundle.write_project(touch=False)`)
  and returns it; every level route calls it through `_start_level`, and `run_llm_level_copy` calls it before the copy.
- `GET /sheet/{uuid}/chords` (`get_chords`): `PartChords` = `text` (`""` when none is saved).
- `storage/bundle.py`: the part's `chords` (`parts[].chords` in `project.json`, up to 8000 characters); see
  [paths-and-data.md](paths-and-data.md) section 2.1.
- Frontend: `api/sheet.ts` (`chords`); `pages/piece/sheet/frames/EnhanceDialog.tsx` (`chords` state, loaded when the
  dialog opens, the field **Chords of the song (optional)**, `data-testid="level-chords"`, sent as `chords` in the level
  choice).

## 6. The level in place and the level copy

- **In place**: `POST /sheet/{uuid}/llm/level` (`run_llm_level`): a range (`start`, `end`), at least one frame, the part
  writable (403) and no run busy (409, from `job.Busy`). It calls `_start_level` → `job.start_level(part_id, level,
  hand, start, end, patterns, words, exact, strict, first, chords, model, batches)` in `part_sheet/job.py`. The
  result is written with `part_sheet/edits.py` `apply_level` (one step of undo).
- **Level copy**: `POST /sheet/{uuid}/llm/level-copy` (`run_llm_level_copy`): only the user's own song (the part's
  `layer` in `vault` or `private`, else 403); the part has notes; the hand has notes (`levels.level_windows`, else 400).
  The title is `level_title(body)`: `<song> · Easy`, `<song> · Easy, left hand`, or `<song> · Right hard, left medium`
  (the `LEVEL_TITLES`). The copy comes from `library/flow.py` `level_copy(project_id, owner, title)`: the owner and the
  layer check (`Refused`), `bundle.duplicate_project(... layer="vault")`, then `based_on` is `None`, `level_of` is the
  original (`source.level_of or project_id`), and `origin` is `{"levelOf": project_id}`. The folders are copied with
  `folders.copy_project_folders` when the original is in `vault`; the metadata is shared (`metadata.homes`). The map of
  part ids (`old.id -> new.id`) gives the copy's part; the job then starts on it with `_start_level(part_id, body,
  None, None)`. The answer is `LevelCopyOut`: `jobId`, `projectId`, `partId`, `title`.
- Before a project is deleted, `release_levels(owner, project_id)` (`library/flow.py`) gives its level copies their
  metadata of their own (`metadata.release_levels`) and sets their `level_of` to `None`, so they stop pointing at it.
- Rows: `db/models.py` `projects.level_of` (`String(36)`, revision `0010`, [07-database.md](../../../context/07-database.md));
  `storage/bundle.py` `ProjectFile.level_of` (`levelOf` in `project.json`); `api/projects.py` `level_of` (the project list
  and its details).

## 7. The dialog and its catalog: `pages/piece/sheet/frames/`

- `PatternCatalog.tsx`: `PatternGallery` (the default export too): the four tabs of `LEVELS` (**Easy**, **Medium**,
  **Hard**, **Super hard**), the `HAND_LABELS` (**Left hand**, **Right hand**), the strictness of `STRICTNESS` (the
  ticks with **Strict** or **Suggested**), the drawing of each pattern from `drawingUrl`.
- `patterns.ts`: `drawingUrl(pattern)` (the route of section 1), `shortRef` (`medium 2`), `runTitle(run)` (the title of a
  run in the history: `Easy, left hand · easy 1 (Strict)`).
- `EnhanceDialog.tsx`: the levels part. Its `LEVELS` (`easy`, `medium`, `hard`), `handsOf(hand)`, the state `levels` (one
  per hand, the same by default), `chosen` (the ticks; `null` is the approved set of the level), `strict`, `shownLevels`
  (the tab each hand shows), `catalog` (from `api/sheet.ts` `levelCatalog`; without it the backend's `defaults` apply).
  Builds the `LevelChoice` (`right`, `left`, `hand`, `patterns`, `exact`, `strict`, `chords`).

## 8. The level run: the plan, the batches, the check

The concept is in [context/ai/level-run.md](../../../context/ai/level-run.md). This section tells the code.

### 8.1 `sheet/llm/levels.py`: the prompts

- `PROMPT_DIR` = `sheet/llm/prompt/levels/`. `LEVEL_VERSION` is the text of its `VERSION` file (`7`). Every run's log
  stores it as `prompt`.
- The prompt files: `shared.md` (the task, the sheet's rules, what a level is, "never harder", Strict and Suggested,
  the register, the rules of the run, what the app keeps and changes, the patterns, the F1 input, the plan request, the
  batch request, how to answer); `easy.md`, `medium.md`, `hard.md` (one section per hand, `## The right hand at <level>`
  and `## The left hand at <level>`, read by `_hand_part`); `feedback.md` (the problems of a reply, `{errors}`, sent
  back to the AI); `answer.md` (the user's answer to a batch, for `write_again`, the history's batch again).
- `instructions(level)`: `shared.md`, then the level's file; when the two hands differ, the head of the two hands and
  the part of each hand. `hand_levels(level)` gives `{staff: level}`; `level_name(level)` gives the words of the level.
- `system_prompt(level, patterns, staffs, strict, guide)`: `instructions` + the run's patterns (each `Pattern.text`,
  with `(Strict)` or `(Suggested)`) + the Strict lines + the "No pattern" line for a `free` hand + the guide's chords
  (`guide_prompt`). The same for every request of a run.
- `plan_prompt(...)`, `song_summary(...)` (the stretches: `windows_of` with `SUMMARY_MS`, `chords`, `measure_text`,
  `melody`, `simple_stretches`/`simple_text`, `like_before`), `read_plan(...)` (the sections, the problems),
  `read_rules(reply)` (the `rule <ref>:` lines). `Section` (`line()`), `Rule` (`line()`, `to_json()`).
- `batch_prompt(...)`: the batch's sections, in the order of [context/ai/level-run.md](../../../context/ai/level-run.md)
  (the grid is `Grid.text(start, end)`, the hands are `measure_text`, the context and the look-ahead are `_slice` of
  the sheet, the earlier passage is `like_before`).
- `Pattern` (`text(negras, strict)`), `load_patterns`, `catalog()`, `catalog_rows()`, `run_refs(...)`, `refs_in(words)`,
  `strict_refs(strict, hand)`.

### 8.2 `sheet/llm/levels.py`: the check and the run

- `check_level(reply, target, *, level, staffs, grid, cs, allowed, start, end, strict, explain, guide)` returns a
  `Batch`: `errors` (the problems, in plain words), `sheet` (the parsed notes), `declared` (`Declared`), `measures`,
  and the counts `melody`, `melody_dropped`, `new_notes`. It runs the checks of the context page, in this order: the
  format (`F1 frames`, the hands, the frames inside the batch), the melody (`melody`, `hidden_line` for a riff,
  `_far_above` for an artifact, `MELODY_DROP_SHARE`), the harmony (`chords`, the bass of each chord, `OUTSIDE_SHARE`,
  `_guide_column` for the guide's chords), the notes per column and the span (`LIMITS`), the hand motion (`measure`,
  `moves_q`, `reach`), the patterns declared (`read_declared`, the Strict rule, `KEEP`, `FREE`), the simple stretches
  and the onsets (`simple_stretches`, `_plain_cols`, `RHYTHM_SHARE`), the grid (`Grid.on_grid`), the steady rhythm
  (`steady` of `Limits`), and the explain line.
- `read_declared(reply)` reads `# pattern`, `# not melody`, `# artifact`, `# explain:` and `# rule:` lines (`Declared`).
- `write_level(current, complete, grid, *, level, staffs, patterns, sid, words, windows, plan, span, max_checks, on_plan,
  on_batch, strict, rules, on_talk, written_before, done_before, first_index, count, guide)` runs the plan (unless
  `plan` is given), then the batches, in memory. A reply that fails is sent back with `level_feedback`, up to
  `MAX_CHECKS`. A batch that fails keeps no answer; a `SkipWindow` fails that batch only; any other exception (the AI
  is not available, the stop of the user) sets the batch to `error` and ends the batches.
  It returns a `LevelRun` (`level`, `staffs`, `plan`, `plan_log`, `batches`, `written`, `rules`, `talks`). `Talk`
  keeps one conversation (`to_json()`) for the log; `on_talk`, `on_plan` and `on_batch` report each one as it ends.
- `level_windows(current, staffs, start, end, batches)`: the batches of a run (`LEVEL_MS` and `LEVEL_ONSETS`, or
  `split_windows` for a batch count). `splice(current, written, windows, staffs, reading=...)` puts the accepted batches
  into the sheet.
- `guide_chords(text)` and `guide_prompt(text)`: see [section 5](#5-the-chords-of-the-song).

### 8.3 `sheet/levels/`: the measures the run uses (no AI)

- `grid.py`: `song_grid(sheet, quarter_ms)` builds the `Grid`; `TOLERANCE`, `FIT_BEATS`, `STEPS`.
- `harmony.py`: `chords(sheet, grid, start, end)`; `BASS_WEIGHT`, `OUTSIDE`, `ROOT_BONUS`, `RICH_MARGIN`, `MIN_BEATS`.
- `hands.py`: `measure(...)` (the `Measures`: `moves_q`, `reach`, and the rest), `melody(sheet, start, end)`,
  `place_line(...)`; `SPAN`, `SHIFT`, `FAST`, `BIG`, `REGULAR_WEIGHT`.

### 8.4 `part_sheet/job.py`: the job

- `start_level(part_id, *, level, hand, start, end, patterns, words, exact, complete, model, batches, strict, first,
  chords)`: checks the hand (`HANDS`), `Busy` when the AI works on the part, `ValueError` when the hand has no notes
  there. It logs the run (`runs.create`: the request, `windows`, `strict`, `prompt`, `chords`) and submits `_level_work`.
  `first=True` (both routes pass it) writes only the first batch when there are two or more; the run waits.
- `_level_work(part_id, reporter, log, todo, *, complete)`: reads the plan and the rules back from the log for a
  run that goes on; calls `levels.write_level`; `on_talk` keeps the usage (`usd`, `requests`) and the rules in the log;
  the state is `running`, `stopped`, `waiting` or `done`/`failed`; the accepted batches are stored by
  `edits.apply_level` as one step (`level`, the label `Level <name> with AI, <hand>`, the history entry). The job's
  `done` summary gives `level` (`ok`, `failed`, `stale`, `gone`), `hand`, `levelName`, `usd`, `batches`, `total`, `run`,
  and `waiting` or `note` when set.
- `continue_level(part_id, run_id)` writes the other batches of a waiting run. `again_batch(...)` writes one batch again
  with the user's answer. See [section 9](#9-the-history-of-runs-and-the-later-sections).
- `_complete(part_id, kind, model)`: the client of the run (`OpenAIComplete` with `cache_key=<part>|<kind>`, or
  `ClaudeComplete` for an Anthropic model, `llm_models.provider`). `_level_complete(part_id, level, model)` names the run by `level_name`.
- The model: the setting's or the one chosen, from the table of `llm_models.py` (`resolve`, `ratio`;
  [ai-runs.md](ai-runs.md) section 1). Constants: `USD_LEVEL_PLAN` 0.015, `USD_LEVEL_BATCH` 0.025, `SECONDS_LEVEL_PLAN` 10, `SECONDS_LEVEL_BATCH` 45.
- `level_cost(current, hand, start, end)`: the estimate of a level run (the plan, then the batches); `costs(part_id)`
  gives it for each hand (`level-right`, `level-left`, `level-both`) in the dialog's numbers.
- `batch_plan(part_id, *, run, hand, start, end, batches, model)`: the batches the dialog's preview shows (`run` `level`
  or `stretch` or `all`); `BATCH_MAX_S` 90, `BATCH_MIN_S` 3; the count is between the two, and the cost is scaled by the
  model's ratio (`llm_models.ratio`).

### 8.5 `api/sheet.py`: the request

- `Level` (`Literal["easy", "medium", "hard"]`); `LevelRequest` (the fields: `right`, `left` (each level, `easy` by
  default), `hand` (`both`, `right`, `left`), `start`, `end`, `patterns` (up to 200 refs), `words` (up to 1000
  characters), `exact`, `strict` (up to 200 refs), `chords` (up to 8000 characters; `None` = the saved ones), and the
  model and `batches` of `RunChoice`). `LevelRequest.level()` gives one level, or `{right, left}` when they differ.
- `LEVEL_TITLES` and `level_title(body)` name a level copy (`Easy`, `Easy, left hand`, `Right hard, left medium`).
- `_chords(part_id, body)` saves the request's chords with the part; `_start_level(part_id, body, start, end)` calls
  `job.start_level(..., first=True)`, and maps `Busy` to 409 and `ValueError` to 400.
- `POST /sheet/{uuid}/llm/level` (`run_llm_level`): 409 when the AI is not set up, 400 without a range (`start`, `end`,
  `end > start`), 403 on a sheet that cannot be changed. Answers `{jobId, status}`.
- `POST /sheet/{uuid}/llm/level-copy` (`run_llm_level_copy`): the same body without a range; answers `LevelCopyOut`
  (`jobId`, `projectId`, `partId`, `title`). Its checks and the copy are in section 6.
- `GET /sheet/levels/catalog`, `GET /sheet/levels/catalog/{hand}/{level}/{number}.svg`: section 1.

## 9. The history of runs: the log, the states, the later answers

The page of this part is [context/ai/run-history.md](../../../context/ai/run-history.md). The log of a level run is
written to the part's folder, `ai-runs/<id>.json`. The routes are in `api/sheet.py`; the list of the runs and the
functions of the log are in `part_sheet/runs.py`.

### 9.1 `part_sheet/runs.py`: the log

- `_dir(part_id)`: `paths.part_frames_path(part_id).parent / "ai-runs"`, that is `parts/<partId>/ai-runs/`. A run's
  file is `<12 hex characters>.json`; `_ID` checks the id before a file is opened.
- `create(part_id, request, system)`: a new run, `state` `running`, `kind` `level`, the `request`, the `system` prompt,
  `plan` `None`, `batches` `[]`, `rules` `[]`, `usd` 0.0, `requests` 0. Written at once. The id is `uuid4().hex[:12]`.
- `save(part_id, run)`: sets `updated`, writes `<id>.json.tmp`, then replaces `<id>.json`. Under the module lock.
- `update(part_id, run, talk)`: a `levels.Talk` with `k` below 0 is the plan (`run["plan"]`); any other replaces the
  batch of the same `k` in `run["batches"]`, sorted by `k`; then `save`.
- `load(part_id, run_id)`: the log, or `None` (a bad id, no file, a file that does not read).
- `_short(run)`: what the list shows: `id`, `log` (`True`), `created`, `state`, `level`, `hand`, `patterns`, `strict`,
  `words`, `model`, `batches` (`k`, `start`, `end`, `status` of each), `total` (the windows of the request), `usd`.
- `listing(part_id)`: the logs in the folder, then the record's `levels` entries whose `run` has no log (`id`
  `record-N`, `log` `False`, the plan and `declared` from the record). Sorted by `created`, the latest first.
- `close_unfinished()` (implementation 04-6): called once by `main.lifespan`, after `ensure_master_user`, when no job
  can be running. It reads every `ai-runs/*.json` under `users/`, `public/` and `requests/` (`_logs`). A log with
  `state` `running` gets `state` `stopped` and `note` `STOPPED_NOTE` ("The backend stopped during the run."); each of
  its batches `ok` or `open` whose `(start, end)` is not in a record `levels` entry of this run with status `ok`
  (`_saved_batches`) gets `status` `error`. Returns the number of runs closed and logs it. A log that does not read
  or write is logged and left as it is: the start never fails for a log.

### 9.2 `part_sheet/job.py`: the states of a run, and the two jobs

- `_level_work` (the job of `start_level` and `continue_level`) sets `state` to `running` when it starts. At the end:
  `stopped` if a Stop was asked, else `waiting` if a batch was accepted, the windows are not all done and no Stop was
  asked, else `done` if a batch was accepted or was done before, else `failed`. A `BaseException` in the work sets
  `stopped` and saves. A process that stops (a crash, a reload) sets nothing: `runs.close_unfinished` closes that log
  at the next start (9.1). The job's summary has `waiting: true` for the waiting state, and `run` (the id).
- `continue_level(part_id, run_id, *, complete=None)`: `LookupError` ("No such run.") when there is no log;
  `ValueError` ("This run is not waiting for you.") unless `state` is `waiting`; `Busy` when the part has a job. Its
  batches are the windows not in the log's batches. It calls `_level_work` with the stored request, plan and rules.
- `again_batch(part_id, run_id, k, words, *, complete=None)`: `LookupError` when there is no log, or batch `k` has no
  `target` and no `messages` ("This batch has no conversation to answer."); `ValueError` ("Write your answer to the AI
  first.") for empty words; `Busy`. The work: the notes of the part (`pipeline.load_note_events`), the sheet as it stood
  before batch `k` (the current notes, with the batch's hands replaced by the `target`), `levels.Talk` from the log,
  `levels.write_again`. A failed run of the work answers `level` `failed`.
  - Accepted: the batch replaces its stretch of its hands, one step of undo labelled `Batch {k + 1} written again with
    AI`; the log's batch and its rules are the new ones (the rules of `source` `batch {k + 1}` are replaced).
  - Refused: the sheet does not change; the log keeps the old `status`, `explain`, `rules` and `declared`.
  - Both: `answers` gets `{words, at}`; `usd` and `requests` are added; `runs.save`. A waiting run keeps `waiting`.
- The summary of `again_batch` has `again` (`k + 1`), `run`, `batches` (1 or 0), `total` 1, `hand`, `levelName`, `usd`,
  and `waiting` when the run waits.

### 9.3 `sheet/llm/levels.py`: `write_again`

- `write_again(complete, system, talk, words, before, grid, *, level, staffs, allowed, strict, max_checks, guide)`
  returns the conversation as it is now (`Talk`) and the last check (`Batch`). The conversation goes on: the earlier
  messages, then the answer, the prompt file `prompt/levels/answer.md` (its `{words}` is the user's answer, stripped).
- Each reply is checked by `check_level` (with `explain=True` and the guide of the chords). A refused reply is fed back
  by `level_feedback`. At most `MAX_CHECKS` (3) replies. A feedback that no reply answered is removed.
- `status`: `failed` when the last check has errors, else `ok`. When `ok`, `explain`, `rules` and `declared` are the
  reply's. The new `Talk` starts with `status` `open`.

### 9.4 `api/sheet.py`: the four routes

- `GET /sheet/{audio_uuid}/llm/runs` (`llm_runs`): `runs.listing`. `GET .../llm/runs/{run_id}` (`llm_run`): `runs.load`;
  404 "No such run." when there is none.
- `POST .../llm/runs/{run_id}/continue` (`continue_llm_run`): 403 when `_writes` is false; `continue_level`: `LookupError`
  404, `Busy` or `ValueError` 409; 202 `{jobId, status}`.
- `POST .../llm/runs/{run_id}/batches/{k}/again` (`run_batch_again`), body `BatchAgainRequest` (`words`, 1 to 1000
  characters): 403; `again_batch`: `LookupError` 404, `Busy` 409, `ValueError` 400; 202 `{jobId, status}`.
- All four call `_notes_or_404` first: 404 when the audio or its notes are missing.
- `k` counts from 0 (the first batch is `k` 0).

### 9.5 The page

- `pages/piece/sheet/frames/AiHistoryPanel.tsx` (`AiHistoryPanel`, `STATE_WORDS`): the list; `AiRunDetail.tsx`
  (`AiRunDetail`, `BatchBlock`, `STATUS_WORDS`): one run (with its `note`, `data-run-note`, when the log has one), its
  answer box and **Write this batch again**, and
  **Go on with the other N batches**; `AiRunPanel.tsx`: the title **Check batch 1** and the **History** button;
  `batches.ts` (`BATCH_COLOURS`); `FramesSheetPage.tsx`: **History of AI runs** in `sheetButtons` (when `offerAi`).
- `api/sheet.ts`: `aiRuns`, `aiRun`, `continueRun`, `runBatchAgain`. `patterns.ts`: `runTitle`, the title of a run.

## Where to look deeper

- [context/ai/run-history.md](../../../context/ai/run-history.md): the history, the waiting state, an answer, a batch
  written again, Go on
- [context/ai/level-run.md](../../../context/ai/level-run.md): the plan, the batches, the check, Strict and Suggested
- [context/ai/levels.md](../../../context/ai/levels.md): what a level is, the catalog, the grid, the chords
- [ai-runs.md](ai-runs.md): the jobs and the routes that every run shares, the model client
- [paths-and-data.md](paths-and-data.md): the part's `chords`, the project's `levelOf`
- [sheet-f1.md](sheet-f1.md): the F1 format of the examples
