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

# [ ] Phase 2: Part B, the backend

- [ ] 2.1 `config.llm_model` (`AITU_LLM_MODEL`), `.env.example`, `compose.yaml`.
- [ ] 2.2 `llm_models.py`: the table, `default`, `choices`, `resolve`, `provider`, `effort`, `prices`, `ratio`.
- [ ] 2.3 `sheet_llm` prices from the table, no crash without a price; `job`, `api/sheet.py` use the table.
- [ ] 2.4 `GET /llm/costs` adds `models` and `model`.
- [ ] 2.5 Comments and messages say "the LLM" / "the AI"; `ask_sonnet` renamed.
- [ ] 2.6 Tests.

# [ ] Phase 3: Part B, the frontend

- [ ] 3.1 The dialog's list and default from the backend; `AI_MODELS` removed.
- [ ] 3.2 Comments; the browser checks' stand-ins.
- [ ] 3.3 typecheck, `check:enhance-dialog`, `check:ai-history`.

# [ ] Phase 4: Part C, Simplify removed

- [ ] 4.1 Backend: the route, the job, the frames code, the costs keys, the test, the script.
- [ ] 4.2 Frontend: `simplify`, the navigation states.
- [ ] 4.3 Tests and checks.

# [ ] Phase 5: The docs and the closing

- [ ] 5.1 The setting named once (`02-tech-stack.md`, `ai/README.md`); "the LLM" / "the AI" elsewhere.
- [ ] 5.2 The code pages checked for the Simplify names.
- [ ] 5.3 `04-context.md` section 9; the folder's README.
- [ ] 5.4 `check-links.py`, `check-names.py`; the closing report.
