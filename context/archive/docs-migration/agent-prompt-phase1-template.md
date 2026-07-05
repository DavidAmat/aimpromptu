# Agent prompt — Phase 1 (foundational platform context)

Task ID: all tasks from Phase 1

You are writing ONE foundational `context/` file for **AImpromptu (aitu)**, a two-service POC
(`aitu-backend` = Python/FastAPI; `aitu-frontend` = React/TS/Vite/VexFlow).

## Read first (in order)
1. `context/archive/docs-migration/project-context.md` — the orientation primer. Do not re-explore from scratch.
2. `context/archive/docs-migration/documentation-migration-plan.md` §2 (target tree), §4 (universal rules).
3. The specific source files for your task (see the checklist row for your Task ID). Check line counts
   before reading; **never deep-read** `notebooks/*.ipynb`, `data/example-scores.json`, lockfiles, or
   `node_modules`/`.venv`.

## Rules (binding)
- **English** output. Keep Spanish solfège note names (`Do`,`Re`,`Mi`,`Fa#`,`La#`,`Sol`,`Si`) and
  Spanish key-signature labels verbatim; keep English music terms English.
- **Code-truth wins.** Verify every claim against code. The READMEs are good but are a starting point.
- **No secrets** — env var names only.
- **No emojis / no narrative / terse and skimmable.**
- `context/` files are short and high-level ("what it is / how it flows"). Exact commands, versions,
  field names still belong here for platform files 02/04, but any deep per-entity detail goes to `documentation/`.
- Do **not** duplicate the notation contract — that lives in `context/shared/notation-spec.md` (Phase 2a);
  reference it.
- **Never change application code.** The Phase-0 rename is the only sanctioned code change; if it hasn't
  run, stop and say so. Markdown only here.

## Produce
- The file named in your checklist row, in the exact location from plan §2.
- If your task is a SKIP/STUB (`05`,`06`,`08`), write one factual line stating why it's skipped/stubbed.

## Wrap up
1. Add/adjust your file's one-line entry in `context/00-index.md`.
2. If you discovered a platform-level fact that belongs in another `0X` file, add one sentence there
   (and to the index) — the numbered files are not frozen.
3. Append any consumed/moved source to `context/archive/docs-migration/deletions-log.md`.
4. Flip your row in `docs-migration-checklist.md` to `[x]` (or `[!]` + reason if blocked).
5. In your final reply: list files written, any open question, and the safe default you took.
