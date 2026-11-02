# 04-6: A run left after a crash, and the model of the AI in one place: the brief

Written 2026-11-02 by the orchestrator of implementation 05, from the user's answers to the closing report of
[05](../05-documentation-refresh/05-implementation-phase-20.md) (its section "Code and docs that disagree", items 4
and 1). Plan it with [`../../guidelines/guidelines-implementation-plan.md`](../../guidelines/guidelines-implementation-plan.md)
and report with [`../../guidelines/guidelines-communication-with-user.md`](../../guidelines/guidelines-communication-with-user.md).
Read [`04-context.md`](04-context.md) section 8 first.

## The user's words

> 3. Make sure that you implement a very easy way to stop if backend stops to mark the runs, write a hand off prompt
>    so that another AI session can take a look at this and implement it and update the docs accordingly
>
> 4. The documentation decision about which model we are going to use is likely to be changing a lot. Let's try not
>    to hardcode a given model, and let's try to simply say the LLM, the LLM judge, or whatever thing. Then we are
>    going to have, in the environmental variables, one that points to the model. Otherwise, we'll have many
>    duplications. It's better if we centralize all the logic, or the source of truth for which model we are going to
>    use, in a single place instead of scattering the hardcoding of the model name. Every time we want to change it,
>    we need to change it in all the places in the code and all the places in the documentation. This is not
>    feasible.

## Part A: a run left `running` when the backend stops

What the code does now (read 2026-11-02, check it again):

- A level run has a log, `ai-runs/<id>.json` in the part's folder (`part_sheet/runs.py`: `create` writes
  `"state": "running"`; `save`, `update`, `load`, `listing`). `part_sheet/job.py` `_level_work` sets the state
  (`running` at line ~885, `stopped` at ~954 only on a `BaseException` in the work, then `done`, `failed` or
  `waiting` at ~962). Each batch of the log also has a `status` (being written, written, kept as it was).
- When the backend process stops during a run (a crash, a restart, a reload after a `.py` edit: uvicorn `--reload`),
  nothing changes the log. It stays `running`, its batch stays "being written", and **History of AI runs** shows
  "The AI is writing" for a run that is not.
- `main.py` `lifespan` runs once at start (`ensure_database_tree`, `ensure_master_user`): the natural place.

What to build: the simplest thing that works. For example, at start, every log whose state is `running` becomes
`stopped` (and its batches being written become not written), with a short note such as "The backend stopped
during the run." No job can be running at start, so no lock is needed. Check also whether other stored marks of a
run in progress stay wrong after a restart (the whole run's segments `working`, `sheet.pending`), and say so.
Tests: a log written `running`, the start step run, the log `stopped`. Then the docs: `context/ai/run-history.md`,
`documentation/services/backend/ai-levels.md` (section 9, the log), `paths-and-data.md` if it lists the states.

## Part B: the model of the AI in one place

What the code does now: the model name is written in many places.

- Backend: `part_sheet/job.py` (`MODEL = "gpt-6.1-terra"`, `MODELS` with labels, effort and cost ratios, and
  about 25 docstrings and comments), `sheet_llm.py` (`MODEL = "claude-sonnet-5-5"`, the price tables), `api/sheet.py`
  (`AiModel = Literal[...]`, the default in comments), and comments in `part_sheet/store.py` (`ask_sonnet`),
  `storage/paths.py`, `pieces/status.py`, `transcription/pipeline.py`, `sheet/llm/guards.py`, `api/projects.py`.
- Frontend: `api/sheet.ts` (11 places), `EnhanceDialog.tsx` (the **Model** selector), comments in
  `FramesSheetView.tsx`, `useFramesSheet.ts`, `FramesSheetPage.tsx`; the browser checks under `aitu-frontend/scripts/`.
- Docs: `context/02-tech-stack.md`, `context/ai/README.md`, `context/04-local-development.md`, `09-coding-conventions.md`,
  `00-project-complete-overview.md`, `documentation/services/backend/ai-runs.md`, `ai-levels.md`, `endpoints.md`,
  the core README `sheet/README.md`. Find them all with
  `git grep -n -i -E "gpt-6|claude-sonnet|terra|sonnet" -- context documentation aitu-backend aitu-frontend`.

What to build:

1. **One source of truth** for the model of a run: a setting in the environment (a name such as
   `AITU_LLM_MODEL`, read in `aitu_backend/config.py`, listed in `.env.example` and `compose.yaml` with its
   default), used by every run. The choices of the dialog's **Model** selector, their labels, efforts and cost
   ratios also live in one place in the backend, and the frontend reads them from the backend (for example from
   `GET /sheet/{uuid}/llm/costs` or a small route) instead of a list of its own.
2. **No model name elsewhere**: the code's comments and messages say "the LLM" (the message "The part was deleted
   while Sonnet wrote its sheet." becomes "while the AI wrote"; `ask_sonnet` gets a neutral name). Names that are
   history (an implementation's record, a dated measure) may stay.
3. **The docs say "the LLM"** (or "the AI" on the pages about the app, the rule of
   `context/implementations/05-documentation-refresh/05-plan.md` section 4.3) and name the setting once, in
   `context/02-tech-stack.md` and `context/ai/README.md`; every other page links there. The model's name appears in
   the docs only as the setting's default, in one place.

Open points to settle with the user in the plan (short, the recommended option first): the setting's name; whether
the dialog keeps a **Model** selector or only shows the model of the setting; what a level run's estimate uses when
the model has no measured ratio.

## Part C (only if the user agrees): remove the dead Simplify run

The docs dropped Simplify on 2026-11-02 (the dialog no longer offers it). Its code has no caller in the app:
`POST /sheet/{uuid}/llm/simplify`, `job.start_simplify`, `frames.write_simplify`, `simplify_windows`,
`simplify_prompt`, `check_simplify`, `edits.apply_simplify`, the `simplify-*` keys of `job.costs`, `api/sheet.ts`
`simplify`, the `enhanceWithAi: simplify-*` states of `navigation.ts`, `tests/test_sheet_simplify.py`,
`scripts/simplify_gallery.py`. The prompt's rules of simplicity stay (the whole run uses them).

## Rules

- One branch, `feat/04-6-run-safety-and-model`, from `master`. Merge into `master` only at the user's ok.
- The app may be running and its backend reloads on a `.py` edit, which stops a running AI run: check
  `ps aux` and the backend logs before the first edit of `aitu-backend/src`.
- Never print or copy a key from `.env`.
- Tests on CPU (another project often holds the GPU); no AI request in the tests.
- `python3 scripts/docs/check-links.py` passes at the end; `scripts/docs/check-names.py` on each doc changed.
