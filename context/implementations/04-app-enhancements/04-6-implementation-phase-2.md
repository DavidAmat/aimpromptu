# 04-6, Phase 2: the model of the LLM in one place, the backend

Plan: [`04-6-plan.md`](04-6-plan.md) sections 3.2 and 4.2. Branch `feat/04-6-run-safety-and-model`. Before the first
edit of `src/`: `ps aux`, `docker logs aimpromptu-backend-1` (only health checks for 3 hours), and no log `running`
in the real database (`/mnt/ssd2/aimpromptu/.database`, 10 logs). The backend reloaded twice on the edits, cleanly.

## 1. What was built

- **`config.py`**: `DEFAULT_LLM_MODEL = "gpt-6.1-terra"` (the one place of the code that names the default) and
  `llm_model()` (`AITU_LLM_MODEL`, empty or unset: the default); the variable in the module's table.
- **`aitu_backend/llm_models.py`** (new), the one table. `Model(label, provider, effort, prices, choice, measured)`;
  `TABLE` holds the three choices of the dialog (Terra, Sol, Sonnet 5.5, with the ratios measured in 04-3 Phase 5)
  and three models kept for their price only (`choice` off: Luna, Sonnet 5, Opus 5.5; the old `PRICES` and
  `OPENAI_PRICES` had them: a fallback of Anthropic's server-side fallback, an old comparison). Functions:
  `default()`, `choices()` (the setting's first, added as `{value: name, label: name}` when the table does not offer
  it), `resolve(name | None)` (`ValueError` for a name not in `choices()`), `provider`, `effort` (a model not in the
  table: provider from the name, `claude...` is `anthropic`; effort `medium`), `prices` (exact name, else the longest
  table name it starts with followed by `-`, for dated names), `cost` (no price: 0 and `log.warning`), `ratio`
  (measured; else the price of `TYPICAL_REQUEST` against `MEASURED_WITH`, time 1; no price: 1 and 1).
  `MEASURED_WITH = "gpt-6.1-terra"` (the model the `USD_*` estimates were measured with: a dated measure).
- **`sheet_llm.py`**: `MODEL`, `EFFORT`, `OPENAI_EFFORT`, `PRICES`, `OPENAI_PRICES`, `openai_price` removed; `price`
  calls `llm_models.cost` (both clients use it). `ClaudeComplete(model=...)` has no default model; both clients take
  `effort=None` and then ask `llm_models.effort(model)`. The module docstring names no model.
- **`part_sheet/job.py`**: `MODEL`, `EFFORT`, `LEVEL_MODEL`, `LEVEL_EFFORT`, `MODELS`, `model_of` removed;
  `available`, `_complete` ask `llm_models.resolve` and `provider`; the log of a level run stores
  `llm_models.resolve(model)`; `batch_plan` multiplies by `llm_models.ratio`. Comments say "the LLM"; the message of
  `PartGone` says "while the AI wrote its sheet".
- **`api/sheet.py`**: `AiModel = Annotated[str, AfterValidator(_offered)]` (`_offered` calls `resolve`): an unknown
  model answers 422 in a body (`RunChoice`) and in the query of `GET /llm/batches`. `GET /llm/costs` adds `models`
  (`choices()`) and `model` (`default()`); the page reads the costs by key, so the two new keys change nothing there
  until Phase 3.
- **Renamed**: `store.ask_sonnet` → `store.ask_ai` (its caller `transcription/pipeline.py`). Comments in
  `api/matrix.py`, `api/projects.py`, `editing/history.py`, `part_sheet/__init__.py`, `build.py`, `store.py`,
  `pieces/status.py`, `sheet/llm/chain.py`, `sheet/llm/frames.py`, `storage/paths.py` say "the LLM" (internals) or
  "the AI" (what the page shows, the API's docstrings).
- **Kept as history**: `sheet/llm/guards.py` (the Sonnet subagents of the research's phase 14), `sheet/llm/prompt/VERSION`
  (the measured phase 7 prompt), `scripts/llm_gallery.py` and `scripts/llm_sheet.py` (the comparison of 03 Phase 4;
  `test_key` now passes `model="claude-sonnet-5-5"` as it can no longer rely on a default),
  `scripts/import_llm_sheets.py` (`RESEARCH_MODEL`, the model the imported research sheets were written with).
  Test names such as `test_sonnet_writes_the_sheet_...` stay: they are not code nor docs a reader of the app uses.
- **`.env.example`**: `AITU_LLM_MODEL=` with what an empty value means and where the table is. **`compose.yaml`**:
  `AITU_LLM_MODEL: ${AITU_LLM_MODEL:-}` (the default not written a second time; `docker compose config` passes).
- **Left for Phase 5** (docs): `aitu-backend/README.md` lines 56-57 and `src/aitu_backend/sheet/README.md` (they name
  the models).

## 2. Findings

- **The token mix of a request.** The run logs store no token counts, so the "typical request" of `ratio` comes from
  04-3 Phase 5 (Terra at medium: about 6,500 tokens read from the cache, 3,000 written, 1,850 output). With it the
  price ratio of Sol is 2.0 (measured 1.8), of Opus 5.5 4.0, of Luna 0.1: close enough for an estimate.
- **The default effort of `OpenAIComplete` was `max`**; now it is the table's (`medium` for every OpenAI model). The
  app always passed the effort, so no run changes; the test of the request now checks `medium`.
- **A model in the setting with no key**: `available` asks the provider of the resolved model, so a `claude-` name
  in `AITU_LLM_MODEL` without `ANTHROPIC_API_KEY` answers 409 "This AI is not set up on this machine" (tested).
- **The container reads `AITU_LLM_MODEL` only when it is created again** (`docker compose up -d`), as every other
  variable; until then it uses the default. Needed later, only if the user changes the setting: no action now.
- **The `client` fixture of `test_part_sheet` replaces `job.available`** with a stand-in that says yes; the new test
  of the 409 keeps the real one from import time.

## 3. Checks

- New `tests/test_llm_models.py` (8 tests): the setting and its default; the choices (the setting first, a
  price-only model not offered and refused); a model not in the table (first choice, provider and effort guessed,
  ratio 1, cost 0 with a warning, the OpenAI client at `medium`); the ratios (measured, from the prices); dated
  names; `GET /llm/costs` gives `models` and `model` (and follows the setting); the routes take the setting's model
  and answer 422 for one not offered; a Claude model without its key answers 409.
- Changed: `test_sheet_simplify.py` (the two new keys of the costs), `test_sheet_batches.py` (the default from `config.llm_model()`, the comparison of costs against an explicit
  model, `llm_models.resolve`), `test_sheet_llm_openai.py` (`price`, no crash without a price),
  `test_sheet_llm_frames.py` (the model passed), `test_sheet_levels_app.py` (the setting's model and the table's
  effort).
- The model tests (6 files): 71 passed. In the container: `choices()` gives the three choices of today, `ratio` as
  above, `job.available()` true.
- The whole backend suite on CPU: see section 4.

## 4. The whole suite

- `pytest` (CPU, `-o addopts=""` for the summary line): exit 0, **1355 passed, 3 skipped** (Phase 1: 1347; the 8 new
  tests). The first run failed one test: `test_sheet_simplify.py::test_the_routes_of_the_dialog` checks the exact keys
  of `GET /llm/costs`; `models` and `model` added to its set (the file goes in Phase 4).
- `pyproject.toml`: the comment on `anthropic` names no model (changed after the run: `uv run` reads the file).
