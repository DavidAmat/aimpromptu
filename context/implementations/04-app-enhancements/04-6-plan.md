# 04-6: A run left after a crash, the model of the AI in one place, Simplify removed: plan

The brief, with the user's words, is [`04-6-prompt.md`](04-6-prompt.md). The status of every task is in
[`04-6-checklist.md`](04-6-checklist.md). Each phase writes `04-6-implementation-phase-N.md`. The guidelines:
[`guidelines-implementation-plan.md`](../../guidelines/guidelines-implementation-plan.md) and
[`guidelines-communication-with-user.md`](../../guidelines/guidelines-communication-with-user.md). Read
[`04-context.md`](04-context.md) section 8 first.

# 1. Context

Three small pieces of work, found by the closing report of the documentation refresh
([05, Phase 20](../05-documentation-refresh/05-implementation-phase-20.md), "Code and docs that disagree"):

- **Part A.** When the backend process stops during a level run (a crash, a restart, a reload after a `.py` edit),
  the run's log `ai-runs/<id>.json` stays `running`, and **History of AI runs** shows "The AI is writing" for a run
  that is not.
- **Part B.** The model's name is written in about 240 places of the code and the docs. The user wants one setting
  in the environment and "the LLM" (or "the AI") everywhere else.
- **Part C.** The Simplify run has no caller in the app since the docs dropped it on 2026-11-02; its code goes.

# 2. The user's answers (2026-11-03)

| Point | Answer |
|---|---|
| The setting's name | `AITU_LLM_MODEL` |
| The dialog's **Model** selector | Kept. Its choices (label, effort, cost and time ratios, prices) live in one table of the backend; the default is the setting; the frontend reads the list from the backend |
| The estimate of a model never measured | The cost ratio comes from the price table, against the model the estimates were measured with; the time ratio is 1. With no price either: ratio 1, and the run's cost counts as 0 with a warning in the backend log, instead of a crash |
| Part C, remove Simplify | Yes |
| The branch | `feat/04-6-run-safety-and-model`, made from `feat/05-docs-refresh` (it holds the brief's commit `9a4ca9e`, which `master` does not have yet). Merged into `master` only at the user's ok |

# 3. What the code does now (checked 2026-11-03)

## 3.1 The marks of a run in progress

| Mark | Stored? | After a restart |
|---|---|---|
| The log's `"state": "running"` (`part_sheet/runs.py`, set in `job._level_work`) | yes, in `ai-runs/<id>.json` | **wrong**: stays `running` |
| A batch of the log `"open"` (being written) | no: `on_talk` writes a conversation only when it ends; a batch written again is saved only at its end | right (never stored) |
| A batch of the log `"ok"` (written) that is not on the sheet | yes | **wrong**: a level run saves its notes on the sheet only at its end (`edits.apply_level`), or at the wait after batch 1. A crash in between leaves batches marked written whose notes never reached `notes.pmn` |
| The job, the live sheet (`LiveRun`, the segments `working`), `_meta` (Revert), `_stop_asked` | no, in memory | right: gone; the page sees no run |
| `sheet.pending` (the page starts a whole run by itself) | yes | right: removed when the run starts (`store.taken`), so a crash during the run never starts it again by itself |
| A level copy (`library.flow.level_copy`) | yes, a new project | made before the job starts; after a crash it stays, holding the song as it was. Not a mark of a run; said in the report |

## 3.2 The model

- `part_sheet/job.py`: `MODEL`, `EFFORT`, `LEVEL_MODEL`, `MODELS` (label, effort, cost and time ratios), `model_of`,
  `available` (a name that starts with `claude` asks Anthropic), `_complete`, the estimates (`USD_*`, measured with
  GPT-6.1 Terra), about 25 docstrings.
- `sheet_llm.py`: `MODEL` (the default of `ClaudeComplete`), `PRICES`, `OPENAI_PRICES`; `openai_price` raises
  `KeyError` for a model with no price, so a new model in the setting would stop every request.
- `api/sheet.py`: `AiModel = Literal[...]`, three names.
- Frontend: `api/sheet.ts` `AiModel`, `AI_MODELS` (the list again), `EnhanceDialog.tsx` (`useState("gpt-6.1-terra")`).

# 4. Design

## 4.1 Part A: the start step

- `runs.close_unfinished() -> int`, called by `main.lifespan` after `ensure_master_user`. No job runs at start, so
  no lock. It reads every `ai-runs/*.json` under `users/`, `public/` and `requests/` of `.database/` (10 logs today,
  0.01 s), and for each log with state `running`:
  - `state` becomes `stopped`, `note` "The backend stopped during the run.";
  - each batch `ok` whose notes are not on the sheet becomes `error` (the page says "Not written"); a batch is on
    the sheet when an entry of the record's `levels` with this run's id holds it as `ok`. A batch `open` (never
    stored today) becomes `error` too.
  - The log is written again; the backend log says how many runs it closed.
- A log it cannot read is left alone. The step never raises: a start must not fail for a log.
- The page: `AiRun.note` shown under the run's title in the detail of the history.
- The batch kept "Not written" keeps its conversation, so **Write this batch again** still works on it.

## 4.2 Part B: one setting, one table

- `config.llm_model()`: `AITU_LLM_MODEL`, default `gpt-6.1-terra` (the only place in the code where the default's
  name is written). `.env.example` lists it with its default; `compose.yaml` passes it on (`${AITU_LLM_MODEL:-}`),
  so the default is not written a second time.
- A new module `aitu_backend/llm_models.py`, the one table: for each model its label, provider (`openai` or
  `anthropic`), effort, prices (input, output, cache write, cache read per million tokens), and the cost and time
  ratios measured in 04-3 Phase 5 (none for a model never measured). Functions:
  - `default()` the setting; `choices()` the table, with the setting's model first and added when it is not in the
    table (label: its name; provider: `anthropic` for a `claude-` name, else `openai`; effort `medium`);
  - `resolve(name | None)` the model of a run (`None`: the setting; a name not in `choices()`: `ValueError`);
  - `provider(name)`, `effort(name)`, `prices(name) -> tuple | None`;
  - `ratio(name)`: the measured ratios, else the cost ratio from the prices against `MEASURED_WITH` (the model the
    `USD_*` estimates were measured with, a dated measure: its name may stay) and time 1; no price: 1 and 1.
- `sheet_llm.price` and `openai_price` read the table; no price: 0 and a warning in the backend log.
  `ClaudeComplete` and `OpenAIComplete` take the model from the caller (no default model of their own).
- `job.py`: `MODELS`, `MODEL`, `EFFORT`, `LEVEL_MODEL`, `model_of` go to `llm_models`; `available` and `_complete`
  ask `llm_models.provider`. `api/sheet.py`: `AiModel` becomes `str`, checked by `llm_models.resolve` (an unknown
  model: 422).
- `GET /sheet/{uuid}/llm/costs` adds `models` (value, label, in the table's order, the setting's first) and `model`
  (the setting). The frontend's `AI_MODELS` goes; the dialog starts on `costs.model`.
- Comments and messages say "the LLM" (backend) or "the AI" (messages the page shows); `ask_sonnet` becomes
  `ask_ai`. Names that are history (a measure, an implementation's record, a script that ran a comparison) stay.

## 4.3 Part C: Simplify removed

The route `POST /sheet/{uuid}/llm/simplify`, `job.start_simplify`, `frames.write_simplify`, `simplify_windows`,
`simplify_prompt`, `check_simplify`, `like_before`, `like_columns`, `Change`, `Simplified` (if nothing else uses
them), `edits.apply_simplify`, `SIMPLIFY_LABELS`, the `simplify-*` keys of `job.costs`, `USD_BATCH`,
`SECONDS_BATCH`, `LiveRun.advanced` only if Simplify alone uses it (level runs use it: it stays), `api/sheet.ts`
`simplify`, the `enhanceWithAi: simplify-*` states of `navigation.ts`, `tests/test_sheet_simplify.py`,
`scripts/simplify_gallery.py`. The rules of simplicity in the prompt stay (the whole run uses them), and so does the
record's `simplified` field (old sheets hold it). Each name is checked with `git grep` before it goes.

## 4.4 The docs

- Part A: `context/ai/run-history.md`, `documentation/services/backend/ai-levels.md` section 9,
  `documentation/services/backend/paths-and-data.md` if it lists the states.
- Part B: the setting named once in `context/02-tech-stack.md` and `context/ai/README.md` (with the default model,
  the one place in the docs); every other page says "the LLM" or "the AI" and links there. Found with
  `git grep -n -i -E "gpt-6|claude-sonnet|terra|sonnet" -- context documentation` (implementation records stay).
- Part C: the docs already dropped Simplify; the code pages (`ai-runs.md`, `endpoints.md`, `sheet/README.md`) are
  checked for the names removed.
- `04-context.md` section 9 sums up 04-6. `python3 scripts/docs/check-links.py` passes; `scripts/docs/check-names.py`
  on each doc changed.

# 5. Phases

| Phase | Work | Checks |
|---|---|---|
| 1 | Part A: `runs.close_unfinished`, the call in `lifespan`, the note in the detail, tests, the docs of Part A | backend tests on CPU; `npm run typecheck` |
| 2 | Part B, backend: `config.llm_model`, `llm_models.py`, `sheet_llm`, `job`, `api/sheet.py`, the costs route, comments and messages, `.env.example`, `compose.yaml`; tests | backend tests on CPU |
| 3 | Part B, frontend: the list from the backend, the dialog, comments, the browser checks' stand-ins | `npm run typecheck`, `npm run check:enhance-dialog`, `npm run check:ai-history` |
| 4 | Part C: Simplify removed, backend and frontend | backend tests, typecheck, `check:enhance-dialog` |
| 5 | The docs of Parts B and C, `04-context.md` section 9, the README of the folder, the closing report | `check-links.py`, `check-names.py` |

# 6. Rules

- The app runs in containers that mount this working tree: the backend reloads on every `.py` edit, which stops a
  running AI run. Before the first edit of `aitu-backend/src` in a session: `ps aux`, `docker logs
  aimpromptu-backend-1`, and no log in `running` (checked 2026-11-03: none, 10 logs).
- Never print or copy a key from `.env`. Tests on CPU, with stand-ins for the AI (no request, no credits).
- No browser check on a real library piece: the checks use their own temporary copies.
- No edit of `src/` while a browser check runs (both services reload).

# 7. Risks

- **The record of saved batches.** Part A decides "on the sheet" from the record's `levels` entries; a run whose
  saving failed half-way could be wrong by one batch. Low: `apply_level` writes the entry and the notes together.
- **The default model's name in tests.** Tests that assert the default read it from `config.llm_model()`, so a
  change of the setting does not break them.
- **A model named in the setting with no key** (an Anthropic name and no `ANTHROPIC_API_KEY`): the routes already
  answer 409 "This AI is not set up on this machine".

# 8. Changes during the work

(Each phase adds its changes here.)

- **Phase 1 (2026-11-03).** The log never stores a batch `open`: the wrong mark after a crash is a batch `ok` whose
  notes are not on the sheet (a level run saves only at its end or at the wait). `close_unfinished` makes those
  `error`. Also a test of the wiring: `TestClient(create_app())` runs the start. Report:
  [`04-6-implementation-phase-1.md`](04-6-implementation-phase-1.md).
- **Phase 2 (2026-11-03).** The table also holds models kept for their price only (`choice` off: a model the
  server-side fallback may answer with, an old comparison); they are not offered and a run cannot ask for them. The
  cost ratio of a model never measured is the price of a typical request of 04-3 Phase 5 (6,500 tokens read, 3,000
  written, 1,850 output) against `MEASURED_WITH`. `price` replaces `openai_price`; the clients take their effort from
  the table. `aitu-backend/README.md` and `sheet/README.md` name the models: Phase 5. Report:
  [`04-6-implementation-phase-2.md`](04-6-implementation-phase-2.md).
