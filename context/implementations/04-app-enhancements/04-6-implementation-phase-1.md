# 04-6, Phase 1: a run left `running` when the backend stops

Plan: [`04-6-plan.md`](04-6-plan.md) sections 3.1 and 4.1. Branch `feat/04-6-run-safety-and-model` (made from
`feat/05-docs-refresh`, which holds the brief's commit `9a4ca9e`; `master` does not have it yet).

## 1. What was built

- `part_sheet/runs.py`: `close_unfinished()`, `_logs()`, `_saved_batches()`, `STOPPED_NOTE`, a module logger. It
  reads every `ai-runs/*.json` under `users/`, `public/` and `requests/` (`root.glob("**/parts/*/ai-runs/*.json")`; on
  the real database: 10 logs, 0.01 s). A log with `state` `running` gets `stopped` and `note`; each batch `ok` or
  `open` whose `(start, end)` is not in a record `levels` entry of the same `run` with status `ok` gets `error`. Each
  log is in its own `try`: a bad log is logged (`log.exception`) and skipped.
- `main.py` `lifespan`: `runs.close_unfinished()` after `ensure_master_user()`, before the preload.
- Frontend: `AiRun.note` (`api/sheet.ts`), shown under the run's title in `AiRunDetail.tsx` (`data-run-note`).
- Tests (`tests/test_sheet_levels_app.py`):
  - `test_a_run_the_backend_did_not_finish_is_marked_stopped_when_it_starts`: a real level run with a stand-in, first
    batch then waiting (batch 1 saved); the log edited as a crash during batch 2 leaves it (`running`, batch 2 `ok`
    but not saved); `close_unfinished` → `stopped`, the note, statuses `["ok", "error"]`; a `done` log not touched;
    the listing says `stopped`; a second call closes 0.
  - `test_the_backend_start_closes_a_run_left_running`: `TestClient(create_app())` runs the lifespan; the log is
    `stopped` after it.
  - `test_a_log_that_cannot_be_read_does_not_stop_the_start`.
- Docs: `context/ai/run-history.md` section 2 (the `stopped` row, a paragraph on a backend that stops),
  `documentation/services/backend/ai-levels.md` 9.1 (`close_unfinished`), 9.2 (a process that stops sets nothing),
  9.5 (the note), `paths-and-data.md` (the `ai-runs` line).

## 2. Findings

- **A batch marked written that is not on the sheet.** The brief expected batches "being written" in the log. In
  fact `on_talk` writes a conversation only when it ends, so `open` is never stored (a batch written again is saved
  only at its end too). The real wrong mark was a different one: a level run saves its notes (`edits.apply_level`)
  only at its end, or at the wait after batch 1, so after a crash the log holds batches `ok` (**Written**) whose
  notes never reached `notes.pmn`. `close_unfinished` makes them `error` (**Not written**), using the record's
  `levels` entries of the run as the list of saved batches. They keep their conversation, so **Write this batch
  again** works on them.
- **Other marks checked** (plan 3.1): the job, the live sheet (the segments `working`), `_meta` (Revert) and
  `_stop_asked` are in memory and go with the process; `sheet.pending` is removed when a whole run starts
  (`store.taken`), so it never starts a run again after a crash; a level copy made before its job stays as a project
  holding the song as it was. None of these stays wrong. A whole run and a stretch save nothing before their end, so a
  crash loses them silently (no log); this is how they always worked (04-context section 7).
- The first edit of `src/` reloaded the backend container (it mounts this working tree); checked before: no run going,
  no log `running`. The reload ran `close_unfinished` on the real database: nothing to close, a clean start.
- `uv run` synced the host environment once (`openai` added to `pyproject.toml` by `9a4ca9e`).

## 3. Checks

- `pytest` (CPU): the whole suite, exit 0: 1347 passed, 3 skipped.
- `npm run typecheck`: passes.
- `python3 scripts/docs/check-links.py`: 0 broken links. `check-names.py`: `run-history.md` and `ai-levels.md` 0
  missing; `paths-and-data.md` 4 missing, all from before this work (lines 514 to 533).
