# 04-6: A run left after a crash, the model of the AI in one place, Simplify removed: checklist

The plan is [`04-6-plan.md`](04-6-plan.md), the brief [`04-6-prompt.md`](04-6-prompt.md). One branch,
`feat/04-6-run-safety-and-model`. Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled,
`[ ]` not started.

## Decisions

- [x] The first discussion (user, 2026-11-03): plan section 2. `AITU_LLM_MODEL`; the Model selector kept, fed by
  the backend; a model never measured: ratio from the price; Simplify removed.

# [x] Phase 1: Part A, a run left `running`

- [x] 1.1 `runs.close_unfinished`: `running` becomes `stopped` with a note; batches not on the sheet become `error`.
- [x] 1.2 Called in `main.lifespan`; never raises.
- [x] 1.3 The note in the run's detail (`AiRun.note`).
- [x] 1.4 Tests (a log written `running`, the step run, the log `stopped`; a saved batch stays `ok`).
- [x] 1.5 Docs: `run-history.md`, `ai-levels.md` section 9, `paths-and-data.md`.
- [x] 1.6 The whole backend suite on CPU (1347 passed, 3 skipped). Report: [`04-6-implementation-phase-1.md`](04-6-implementation-phase-1.md).

# [x] Phase 2: Part B, the backend

- [x] 2.1 `config.llm_model` (`AITU_LLM_MODEL`), `.env.example`, `compose.yaml`.
- [x] 2.2 `llm_models.py`: the table, `default`, `choices`, `resolve`, `provider`, `effort`, `prices`, `ratio`.
- [x] 2.3 `sheet_llm` prices from the table, no crash without a price; `job`, `api/sheet.py` use the table.
- [x] 2.4 `GET /llm/costs` adds `models` and `model`.
- [x] 2.5 Comments and messages say "the LLM" / "the AI"; `ask_sonnet` renamed.
- [x] 2.6 Tests (`test_llm_models.py`, 5 test files changed); the whole backend suite on CPU (1355 passed, 3
  skipped). Report: [`04-6-implementation-phase-2.md`](04-6-implementation-phase-2.md).

# [x] Phase 3: Part B, the frontend

- [x] 3.1 The dialog's list and default from the backend; `AI_MODELS` removed.
- [x] 3.2 Comments; the browser checks' stand-ins.
- [x] 3.3 `npx tsc -b`, `check:enhance-dialog`, `check:ai-history` (all passed). Report:
  [`04-6-implementation-phase-3.md`](04-6-implementation-phase-3.md).

# [x] Phase 4: Part C, Simplify removed

- [x] 4.1 Backend: the route, the job, the frames code, the costs keys, the script; the test file renamed
  `test_sheet_stretch_one_hand.py` (its tests of the one-hand stretch and `like_before` kept).
- [x] 4.2 Frontend: `simplify`, the navigation states.
- [x] 4.3 Backend suite on CPU (1348 passed, 1 skipped, 2 Transkun tests failed on the CPU, unrelated); `npx tsc -b`;
  `check:enhance-dialog` (all passed). Report: [`04-6-implementation-phase-4.md`](04-6-implementation-phase-4.md).

# [x] Phase 5: The docs and the closing

- [x] 5.1 The setting named once (`02-tech-stack.md`, `ai/README.md`); "the LLM" / "the AI" elsewhere.
- [x] 5.2 The code pages checked for the Simplify names (and `04-context.md`, its Simplify marked removed).
- [x] 5.3 `04-context.md` section 9 (and 8.1, 8.3 no longer bind a model by name); the folder's README, `00-index.md`,
  `implementations/README.md`.
- [x] 5.4 `check-links.py` (0 broken links), `check-names.py` (no name of 04-6's code missing); the closing report:
  [`04-6-implementation-phase-5.md`](04-6-implementation-phase-5.md).
