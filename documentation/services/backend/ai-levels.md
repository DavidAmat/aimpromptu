> Context: [context/ai/levels.md](../../../context/ai/levels.md) (what a level is, the catalog, the grid, the chords of the song) and [context/ai/README.md](../../../context/ai/README.md)

# The levels: the code of the catalog, the grid, the harmony, the hands and the chords

The levels of **Enhance with AI** (implementation 04-3, Phases 3 and 4; the chords of the song, implementation 04-5).
This page tells the files and functions. The run that writes a level (the plan, the batches, the check) is in
Phase 12's sections below; the history of runs in Phase 13's.

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

## 8. The later sections

Phase 12 adds the level run (the plan, the batches, the check, `start_level`'s `_level_work`, the prompt files of
`sheet/llm/prompt/levels/`, the constants of `levels.py`). Phase 13 adds the log of a run and its routes.

## Where to look deeper

- [context/ai/levels.md](../../../context/ai/levels.md): what a level is, the catalog, the grid, the chords
- [ai-runs.md](ai-runs.md): the jobs and the routes that every run shares, the model client
- [paths-and-data.md](paths-and-data.md): the part's `chords`, the project's `levelOf`
- [sheet-f1.md](sheet-f1.md): the F1 format of the examples
