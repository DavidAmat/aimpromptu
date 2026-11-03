# 04-6, Phase 5: the docs and the closing

Plan: [`04-6-plan.md`](04-6-plan.md) section 4.4. Branch `feat/04-6-run-safety-and-model`. Docs only: no file of
`aitu-backend/src` other than a `.md` changed (the backend reloads on `.py` edits only), so no check of the running app
was needed.

## 1. The model named once (Part B)

- **[`context/ai/README.md`](../../ai/README.md)**, "The model and the cost": the setting `AITU_LLM_MODEL`, the
  default of `config.py` (`DEFAULT_LLM_MODEL`, with its name: the one place in the docs that names it), the table of
  `llm_models.py`, the list read from `GET /llm/costs`, a model never measured (its prices; no price: $0 and a
  warning), the keys. "Words the app uses": the docs of the code say "the LLM".
- **[`context/02-tech-stack.md`](../../02-tech-stack.md)**: the SDK row and the "AI (Enhance with AI)" row name the
  setting and the table, no model; the default and the choices are linked to `ai/README.md`. The old line "Terra since
  04-3 Phase 5; before that Sonnet 5.5" went (it is in `04-context.md` section 8.1 and the 04-3 records).
- "The LLM" / "the AI" and a link instead of a model's name: `00-project-complete-overview.md`, `00-index.md`,
  `01-project.md`, `03-services-overview.md` (and a new row for `llm_models.py`), `04-local-development.md`,
  `05-deployment.md`, `09-coding-conventions.md` (the rule: no model's name in code or comments), `ai/whole-run.md`,
  `ai/level-run.md` (the ratios now `llm_models.MEASURED_WITH` and `llm_models.ratio`, no names), `backend/README.md`,
  `aitu-backend/README.md` (a line for `llm_models.py`), `sheet/README.md`, `implementations/README.md`.
- **`documentation/services/backend/ai-runs.md`** section 1: the table of `job.py` (`MODEL`, `EFFORT`, `MODELS`,
  `model_of`, all gone in Phase 2) replaced by `llm_models` (`TABLE`, `Model`, `default`, `choices`, `resolve`,
  `provider`, `effort`, `prices`, `cost`, `ratio`, `MEASURED_WITH`, `TYPICAL_REQUEST`), `sheet_llm.price`, and
  `available` and `_complete` of `job.py`. **`ai-levels.md`**: the constants line and the ratio of `batch_plan`.
  **`endpoints.md`**: the body of `POST /llm` (a model of `models`, none: the setting, another: 422), `GET /llm/costs`
  (`models`, `model`), and "Sonnet decides the hands" → "the AI decides the hands".

**Kept, as history** (plan section 4.2): `00-index.md` and `01-project.md` on implementation 03 ("the LLM step with
Sonnet 5.5", "the AI (then Sonnet 5.5)"), `tests/golden/sheet/README.md` (the golden answers were written by Sonnet
5.5), `sheet/llm/guards.py` (a measure of phase 14), `sheet/README.md` line 183 (the songs sent to Anthropic in 03
Phase 4), `llm_models.MEASURED_WITH`, and every implementation record. The one change of a record: `04-context.md`
sections 8.1 and 8.3, which bound "every AI run uses GPT-6.1 Terra" as a decision: they now say the model is the
setting (section 9), its default the one 04-3 chose.

`git grep -n -i -E "gpt-6|claude-sonnet|claude-opus|terra\b|sonnet"` on `context` (without the implementation records
and the archive), `documentation` and the READMEs: only `ai/README.md` (the default) and the history above. On
`aitu-backend/src` and `aitu-frontend/src`: only `config.DEFAULT_LLM_MODEL`, the table, and `guards.py` (history).

## 2. The Simplify names (Part C)

- `sheet/README.md`: `frames.check_simplify` taken out of the `llm` row; the line on what implementation 04 changed
  and the line of section 14 say Simplify was removed in 04-6.
- `ai-runs.md`, `endpoints.md`: no Simplify name left. `write_frames(..., simplify, ...)` stays in `ai-runs.md`: it is
  the whole run's rules of simplicity (`check_answer(simplify=True)`), which stay.
- `04-context.md`: sections 1 to 7 are the record of 04 and keep Simplify; a line at the top says it was removed, and
  the code table, the route sketch, the costs, the gallery script, the test file and the two open points of Simplify
  say "removed in 04-6" (the test file: renamed).
- `00-index.md` line 136 ("the Enhance with AI dialog with Simplify left, right or both") is the history of 04: kept.

## 3. `04-context.md` section 9, the README of the folder

- Section 9: what changed (Parts A, B, C), the decisions that bind (where a model's name may be written, how to add a
  model, the dialog sends a model only when chosen), the open points (the fresh backend image without `openai`, the
  two Transkun tests on the CPU, a level copy left after a crash).
- [`README.md`](README.md): the state line names 04-6, and a row for each phase report. `00-index.md`: the 04-6 row
  (plan, checklist, reports, done). `implementations/README.md`: 04-6 in the list and the table.

## 4. Checks

- `python3 scripts/docs/check-links.py`: **555 files checked, 0 broken links**.
- `python3 scripts/docs/check-names.py` on the 21 docs changed: 2043 names, 35 not found before this report; none of
  them is a name of 04-6's code. They are branch names (`feat/04-6-run-safety-and-model`, `feat/04-logo` ...), names
  that were already missing (`/docs`, `TimeScoreView`, `api/time_score.py`, the slash commands of
  `09-coding-conventions.md`), and, in `04-context.md`, the Simplify names now marked removed (they are the record of
  04). With this report: 22 docs, 2113 names, 41 not found; the 6 more are this report naming removed names
  (`model_of`) and quoting the ones already missing.

## 5. Needed later

- The merge of `feat/04-6-run-safety-and-model` into `master`, at the user's ok (plan section 2).
- `docker compose build backend`, so that a fresh backend container has `openai` (Phase 4 report, section 3), at a
  time the user chooses (it restarts the app).
