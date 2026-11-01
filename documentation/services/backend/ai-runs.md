> Context: [context/ai/README.md](../../../context/ai/README.md) and [context/ai/whole-run.md](../../../context/ai/whole-run.md)

# The AI runs: the code of the jobs, the model client, the prompts and the routes

Every run of **Enhance with AI** on a part is a background job of `part_sheet/job.py`. The job asks the model
through one `complete(system, messages) -> text` function, reads the answers with the checker of
`sheet/llm/`, and writes the result into the part's files. This page tells the code of the **whole run** (the
hands and the reading of the whole song, implementation 03, Phase 5). Sections 7 and 8 tell a stretch and Simplify.
The levels and the history of runs are added by Phases 11 to 13.

Modules: `aitu-backend/src/aitu_backend/part_sheet/job.py` (the jobs), `sheet/llm/frames.py` (the windows and the
checks), `sheet/llm/prompt/frames/` (the prompt), `sheet_llm.py` (the model client), `api/sheet.py` (the routes).

## 1. The model client: `sheet_llm.py`

`sheet/llm/frames.py` imports no SDK. The product passes it a `complete` function.

| Name | What it is |
|---|---|
| `sheet_llm.OpenAIComplete` | The client of the OpenAI models (the Responses API, the key `OPENAI_API_KEY` from the environment or `.env`, read by `_openai_key`). Each request is one call with the system prompt cached: `cache_key` is `<part id>\|<kind of run>`. Used by every run on GPT-6.1 Terra or GPT-6.1 Sol |
| `sheet_llm.ClaudeComplete` | The client of Claude (`ANTHROPIC_API_KEY`, the official SDK, streaming, retries). Used only when the user chooses **Sonnet 5.5** in the dialog |
| `sheet_llm.NoCredits`, `SkipWindow` | A run stops for no credits; a refusal (a declined request) fails one window only |
| `Call` | One request's tokens, seconds and US dollars; `ask.calls` and `ask.usd` add them up for the run |

The model table is `part_sheet/job.py`:

- `MODEL = "gpt-6.1-terra"` and `EFFORT = "medium"`: the model of a run when none is chosen.
- `MODELS`: the three choices the dialog offers, each with its label, its effort, and the cost and the time of one
  request compared with Terra (the measured ratios; the dialog shows them).
- `model_of(model)` returns the choice or Terra; an unknown name raises `ValueError`.
- `available(model)` is the check before a run: the key and the SDK of that provider. A run asked when it is not
  available answers `409` ("This AI is not set up on this machine.").
- `_complete(part_id, kind, model)` builds the client of a run.

Keys are never written in the docs or in the code: only the names of the settings.

## 2. The job: `part_sheet/job.py`

| Function | What it does |
|---|---|
| `start(part_id, *, complete=None, model=None, batches=None)` | Starts the whole run on a part, or returns the job already running (one job per part, key `KEY = "sheet-llm:{}"`). `complete` replaces the model (tests). `batches` makes that many windows of about the same time |
| `work` (inside `start`) | The job's body, below |
| `LiveRun`, `live(part_id)` | The sheet of the moment while the run works: the page reads it through `GET /sheet/{uuid}` |
| `stop(part_id)` | Asks the run to stop; `_check_stop` raises `Stopped` before the next request |
| `commit(part_id, sheet, text, record, notes_revision, changes=...)` | Writes the hands into `notes.pmn`, the sheet into `sheet.f1` and the record into the store, under the part's lock |
| `costs(part_id)` | What each run would cost, about: requests, US dollars and minutes (the constants `USD_*` and `SECONDS_*`) |
| `batch_plan`, `BATCH_MAX_S`, `BATCH_MIN_S` | The batches the dialog draws on the sheet (the route `GET /llm/batches`) |
| `PartGone`, `Stopped` | A part deleted during a run stops the requests (`PartGone`); a stop asked by the user ends the run (`Stopped`) |

The events of a run are sent on the job's stream as `event: sheet` (`EVENT = "sheet"`), with a `phase`:
`reference`, `windows` (the count), `window` (done of total, with `status`), `saved` (with `source`).

### The job's body (`start`, function `work`)

1. Reads the notes with their starting hands (`pipeline.starting_hands`). Stops if the part has no notes.
2. Keeps the current sheet (`build.current`) and its marks (`build.user_marks`). When the part was enhanced before,
   the current hands are shown to the model as a suggestion (`shown`, the prompt mark `+hands`); a first run reads
   the notes without hands.
3. Makes the `LiveRun` of the part, then calls `sheet.llm.frames.write_frames` with `asked` as `complete`. `asked`
   checks the stop, and raises `PartGone` when the part no longer exists.
4. When the part has no event left at the end, the result is `source: "gone"` and nothing is stored.
5. Otherwise the sheet is kept with the user's marks (`build.with_marks`) and the titles and settings of the sheet
   (`carry_extras`), written as F1 (`f1.write(sheet, mode="frames")`), and a `store.Record` is made:
   - `source`: `llm` (every window by the model), `mixed` (some windows kept the algorithm), `algorithm` (none);
   - `windows`: the window list with its status; `quarter_ms`, `reference` (`user`, `song` or the source of the
     reference figure);
   - `model`, `prompt` (`PROMPT_VERSION`, `+hands` when shown), `usd`, `requests`, `written`, `note`, `edited`.
6. `commit` runs. The notes the model left out or added (`song.changes()`) go through `edits.change_notes`, as one
   step of undo. An earlier enhanced sheet is kept whole when this run did not finish (no credits, no network).
7. Sends `phase: saved`, and returns `{source, windows, usd}` as the job's result.

A run that finds no window written by the model (no credits, no network) keeps the algorithm's sheet and the
hands as they were; the page does not start again by itself.

## 3. The windows, the prompt and the check: `sheet/llm/frames.py`

| Name | Role |
|---|---|
| `write_frames(notes, complete, *, sid, hands, quarter_ms, windows, max_checks, guards, simplify, on_start, on_window, on_part)` | The whole chain (below). Returns a `FramesSong` (`.sheet`, `.text`, `.parts`, `.windows` (the `WindowLog`s), `.reference`, `.quarter_ms`, `.changes()`) |
| `reference_prompt`, `read_reference`, `gap_peaks` | The reference figure: one request with the peaks of the gaps between onsets, in words; the reply `quarterMs=NNN` between `REFERENCE_MS` (150 to 2000 ms) |
| `windows_of(sheet)` | The windows: 12 to 16 s (`WINDOW_MS`), at most `MAX_ONSETS` (200) onsets, each ending after the longest pause in that range and not inside a beam group |
| `split_windows(sheet, count)` | The batches the user chose: `count` windows of about the same time (`SPLIT_SLACK`) |
| `window_prompt(...)` | The message of one window: the target (the notes with the figures the rules give), the look-ahead (`LOOKAHEAD_MS`, 4 s), the decided context (`CONTEXT_MS`, 4 s) and the places to check |
| `places(notes, quarter_ms)` | The places the app finds for the model to check: `far_quick` and `broken_octaves` |
| `check_answer(reply, target, ...)` | The checker of one reply: the problems (an empty list accepts it) and the parsed answer |
| `beam_floor`, `beam_overlaps` (`sheet/llm/guards.py`, `guard_errors`) | The phase 14 guards: at least 30 % of 20 or more eighths carry a beam tag; a beam group whose figures do not fit its positions |
| `feedback(errors)` (`prompt/feedback.md`) | The user message after a rejected reply: one line per problem |
| `Part`, `assemble`, `placed` | A window's decided notes; the sheet built from the parts and the rules of the app |

The chain of `write_frames`:

1. The reference figure, unless it is given (`quarter_ms`, named by the user or by a song's record).
2. The algorithm (`proposal.frames.propose_frames`) with the reference figure. Its parts are the fallback of each
   window.
3. The windows (`windows_of`, or the batches of `split_windows`). They depend only on the notes, so they are known
   before the first request.
4. Each window: one conversation (`window_prompt`, the model's reply). The checker (`check_answer`) and, with
   `guards=True`, `guard_errors` list the problems. A rejected reply gets `feedback(errors)` as the next message, and
   the model answers again: at most `MAX_CHECKS` (3) replies per window. A window that passes becomes a `Part` with
   `source: "llm"`; a window that fails every check keeps the algorithm's part (`source: "algorithm"`) and the next
   window starts without its context.
5. `assemble` joins the parts with the rules: figures, grace notes, beam groups cut by the figures, spelling, and the
   8va lines joined (`join_ottavas`, `OTTAVA_JOIN_MS`).

The model decides the hands, the beam groups, the clefs and the 8va lines, the ornaments, the armadura of a passage
and the reference figure. The app computes the figures, the grace notes and the spelling. Every answer is kept whole;
the decided context of window k is the end of answer k-1.

## 4. The prompt: `sheet/llm/prompt/frames/`

| File | What it is |
|---|---|
| `VERSION` | The version of the prompt: `PROMPT_VERSION = "7"` in `frames.py` (the stored `prompt` of a record) |
| `instructions.md` | The system prompt: the same for every request of every song (cached). Its examples are checked by `test_the_prompt_examples_pass_the_checker` |
| `feedback.md` | The message after a rejected reply |

The folder `sheet/llm/prompt/` (without `frames/`) holds the frozen prompt of the research's bars chain
(`prompts.py`, `PROMPT_VERSION = "2026-10-23"`); the whole run does not read it.

Version history: 4 (the clef rules of phase 14), 6 (the decoration-note rule of implementation 04; the section
"Simplicity"), 7 (implementation 04-3, 2026-10-30: the octave as a third or a fifth, when the user asks for it).

## 5. The routes: `api/sheet.py`

| Route | What it does |
|---|---|
| `POST /sheet/{uuid}/llm` | Starts the whole run, body `RunChoice` (`model`, `batches`; both optional). Answers `202` with `jobId` and `status`. `409` when the AI is not set up |
| `GET /matrix/progress/{jobId}` | The job's stream: `event: sheet` at each change of the sheet, then `event: done` |
| `POST /sheet/{uuid}/llm/stop` | Stops the run after the request it waits for. `409` when none runs; `403` when the sheet cannot be changed here |
| `POST /sheet/{uuid}/llm/revert` | Body `version` (the snapshot taken before the run). Puts the part back as it was (`edits.revert_run`), one step of undo. `404` for an unknown version |
| `GET /sheet/{uuid}/llm/costs` | What each run would cost, about (`job.costs`); with `start` and `end`, also a level of a range |
| `GET /sheet/{uuid}/llm/batches?run=all` | The batches a run would make, drawn on the sheet while the dialog is open (`job.batch_plan`) |

`GET /sheet/{uuid}` answers the state of the run on the part with the sheet (`_llm_state`: `running`, `done` or
`none`, and whether the part is edited through the copy of **Edit**).

## 6. The stored result

- `notes.pmn`: the hands of the sheet (the numeric truth). Its history gets the hands saved before the run
  (`editing/history.py`, the snapshot before the run, `history.restore` for **Revert**).
- `sheet.f1`: the sheet, with its record (`part_sheet/store.py`, `Record`, `store.save`, `store.load`). The record's
  `enhanced` flag is the AI mark the lists show (`components/piece/AiMark.tsx`).
- The page lays a stored sheet again on the current notes (`part_sheet/build.py`, `reapply`, `forget`), so a run
  that ends after an edit of the notes keeps its reading.

## 7. A stretch: `job.start_stretch`, `frames.write_stretch`

Context: [context/ai/stretch-and-simplify.md](../../../context/ai/stretch-and-simplify.md). Implementation 03, Phase 7
(the user's words); 04, Phase 4 (one hand); 2026-10-30 (the batches).

| Name | Role |
|---|---|
| `job.start_stretch(part_id, *, start, end, instruction, staff, picked, complete, model, batches)` | The job. Refuses a second job on the part (`Busy`). Makes the batches (`frames.split_windows` over the hands of the stretch when `batches` is more than 1), then `write_stretch` for each, in order. A batch that raises `ValueError` (no note of the hand) is skipped. The loop stops at a batch whose log says `error`. The answer goes to `edits.apply_stretch` when one batch was accepted; otherwise the summary says `failed`. Its `done` summary: `stretch` (`ok`, `failed`, `stale`), `usd`, `batches` (accepted), `total` |
| `frames.write_stretch(current, notes, complete, *, start, end, instruction, staff, picked, sid)` | One window conversation of the stretch. The target is the stretch as it is now (`stretch_of`: the notes of the hands asked for, with the clefs, the armadura and the ornaments of the stretch; the user's marks removed by `_strip_marks`). The context is the four seconds before (`CONTEXT_MS`), the look-ahead the four after (`LOOKAHEAD_MS`). With `staff` 1 or 2, the other hand is `fixed`. Returns `(sheet or None, WindowLog)` |
| `frames.stretch_request(instruction, *, staff, picked, start, end)` | The section "The user's request: it comes before everything else": the words (at most `REQUEST_CHARS`, 1,000), the purpose (a simpler sheet, uniform patterns), what was picked (names like `f120 C5`, at most `PICKED_NAMED`, 40), and what the answer may change. Without words, the section says to keep every note |
| `frames.check_answer(reply, target, *, drop, free, hand)` | The checker. `drop` (words given) accepts notes of the target left out; `free=(start, end)` accepts notes added inside the stretch. `hand` refuses a note written in the other hand. Without `drop`, a note left out is refused |
| `frames.beam_floor(sheet)` | The beam check of the answer (`guards=True`); a failure gets the same retry as a checker error |
| `frames.splice(current, answer, start, end, *, keep)` | The stretch put into the sheet: its columns, the clefs and the armadura in force at `end` come back after it; `keep` (1 or 2) keeps the other hand's notes, beams and clefs |
| `edits.apply_stretch(part_id, sheet, *, notes_revision, start, end, words, usd, requests, model, staff)` | Stores the run as one step: the notes left out removed and the notes added written in `notes.pmn`, the sheet in `sheet.f1` with the figures the AI wrote set as by hand (`fix`), and `[start, end, words, usd, written]` appended to `Record.stretches`. Returns `False` when the notes changed meanwhile (`stale`) |

Constants: `MAX_CHECKS = 3` replies per window (`frames.py`); `job.SECONDS_STRETCH = 30` and `job.USD_STRETCH = 0.015`,
the estimate of `job.costs` (`stretch`: one request).

Route: `POST /sheet/{uuid}/llm/stretch`, body `StretchRequest` (`api/sheet.py`): `start`, `end` (`end` after `start`,
else `400`), `staff` (`both`, `right`, `left`), `notes` (refs `<frame>:<midi>`, at most 2,000), `instruction` (at most
1,000 characters), and the choices of `RunChoice` (`model`, `batches`). `409` when the model has no key or another job
works on the part; `403` when the sheet cannot be changed here. The stretch's range is read by
`GET /sheet/{uuid}/stretch` (the armadura) and its estimate by `GET /sheet/{uuid}/llm/costs?start=&end=`.

Tests: `tests/test_sheet_reading.py` (the tools of Phase 7); `npm run check:frames-tools` (aitu-frontend; `--live`
makes one stretch request).

## 8. Simplify: `job.start_simplify`, `frames.write_simplify`

Context: [context/ai/stretch-and-simplify.md](../../../context/ai/stretch-and-simplify.md). Implementation 04, Phase 4.
The dialog no longer calls the route: a hand is simplified as a level of that hand ([ai-levels.md](ai-levels.md) and [level-run.md](../../../context/ai/level-run.md)).

| Name | Role |
|---|---|
| `job.start_simplify(part_id, *, hand, complete)` | The job. `hand` is `right` (staff 1), `left` (staff 2) or `both` (`job.HANDS`); another name, or a hand with no notes, is `ValueError` (`400`). `Busy` when a job runs. The model is always `_complete(part_id, "simplify")`: GPT-6.1 Terra, no choice. Its `done` summary: `simplify` (`ok`, `none`, `stale`, `failed`, `gone`), `hand`, `added`, `leftOut`, `usd`, and `note` when a batch said why it stopped |
| `frames.write_simplify(current, notes, complete, *, staff, sid, max_checks, on_start, on_batch) -> Simplified` | The loop over the batches of `simplify_windows`. Each batch: `like_before` (the earlier passage most like it), `like_columns`, `simplify_prompt` (the changes so far, the like passage, the end of the previous batch, the places), the reply through `check_simplify`, its retries (at most `MAX_CHECKS`). A failed batch keeps its notes; an error (no credits, no network) stops the rest. Returns `Simplified` (`sheet`, `changes`, `windows`, `added`) |
| `frames.simplify_windows(sheet, staff)` | The batches of one hand (or both, `staff=None`): `windows_of(span=SIMPLIFY_MS, max_onsets=SIMPLIFY_ONSETS)`, so 24 to 32 s and at most 300 onsets, each ending after a pause of that hand |
| `frames.simplify_prompt(...)` | The message of a batch: "the rules of simplicity only", the hands and the figures fixed, the changes so far with their reasons, the like passage with its changes, the decided context, the target, the places to check, the look-ahead, and the answer format (`# leave out f120 G2: why`, `# add f240 D1: why`, `# no change`) |
| `frames.check_simplify(reply, target, *, like, aligned)` | The checker: the change lines (`_CHANGE`), a note left out that is a note of the target, a note added in a column of the target within an octave, then `simplicity` (the limits: a note left out keeps a note of its column within `NEAR`, 12 semitones; a note added is near one and has a name of its pattern; at most `CHANGE_SHARE`, a tenth, of the target's notes, at least `CHANGE_MIN`, 4) and `renamed` (a name changed only when the like passage has it at the same place) |
| `edits.apply_simplify(part_id, simplified, *, notes_revision, hand, left, added, usd, requests, model, lines)` | Stores the run as one step: the notes left out removed and the added ones written (`change_notes`), the sheet laid again on them (`build.reapply`), `Record.simplified` appended (`[hand, added, left out, usd, written, change lines]`). Returns the counts, or `None` when the notes changed meanwhile |

The batch constants (`frames.py`): `SIMPLIFY_MS = (24000, 32000)`, `SIMPLIFY_ONSETS = 300`, `SIMPLIFY_CONTEXT_MS =
8000`, `LIKE_GRAM = 4`, `LIKE_SHARE = 0.3`, `SAME_PLACE = 2`. The rules are the prompt's `simple.1` to `simple.4`
(section "Simplicity" of `prompt/frames/instructions.md`, prompt version 7). The estimate: `job.costs` (`simplify-left`,
`simplify-right`, `simplify-both`: one request per batch, `USD_BATCH`, a `USD_CACHE` for the first request).

Route: `POST /sheet/{uuid}/llm/simplify`, body `{hand: both | right | left}`. `409` when the AI is not set up or a job
runs; `403` when the sheet cannot be changed here; `400` for a hand with no notes.

Tests: `tests/test_sheet_simplify.py`; gallery `scripts/simplify_gallery.py`; browser check `npm run
check:enhance-dialog` (no AI request).

## Where to look deeper

- [context/ai/whole-run.md](../../../context/ai/whole-run.md): the same run as the user sees it
- `sheet-f1.md` (wave A, Phase 2): the F1 format the model writes and the sheet is read from
- [paths-and-data.md](paths-and-data.md): the files of a part
