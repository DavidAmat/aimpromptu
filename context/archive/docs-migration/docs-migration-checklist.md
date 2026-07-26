# AImpromptu — Docs Migration Checklist

Status: `[ ]` open · `[~]` in progress · `[x]` done · `[!]` blocked.
Tasks are ordered by dependency. IDs are stable; reference them in `deletions-log.md` and agent prompts.

## Phase 0 — Foundations & rename (main thread, no sub-agents)

| ID | Area | Source / touch | Verify against | Produce | Action | Exit |
|----|------|----------------|----------------|---------|--------|------|
| [x] P0-1 | Git root | workspace root | — | `git init`; root `.gitignore` (must NOT ignore `context/`,`documentation/`) | init | `git status` clean-ish; docs paths not ignored |
| [x] P0-2 | Backend rename | `piano-matrix-generation/` incl. `src/piano_matrix_generation/`, `pyproject.toml`, `Makefile`, `main.py` L8-10/97, `notebooks/02`, `README.md`, `uv.lock` | plan §5 | folder `aitu-backend/`, module `aitu_backend` | rename+edit | `uv sync && make serve` boots; `/health`,`/docs`,`POST /sequence` OK |
| [x] P0-3 | Frontend rename | `piano-matrix-notation/` `package.json`, `README.md`, `App.tsx` L13, `vite-env.d.ts` L4-5 | plan §5 | folder `aitu-frontend/`; env var `VITE_MATRIX_API_URL`→`VITE_AITU_API_URL` | rename+edit | `npm install && npm run build` passes; `npm run dev` reads backend via new var |
| [x] P0-4 | Project terms | `TODO.md`, both READMEs, new root `README.md` | plan §5 | consistent AImpromptu/aitu naming | edit | no stray `piano-matrix*`/`music-rendering`/`VITE_MATRIX_API_URL` in live files |
| [x] P0-5 | Notebooks reorg | `aitu-backend/notebooks/*.ipynb` | plan §5 | `notebooks/<theme>/…` subfolders; fix `02` import | move+edit | one folder per POC; import resolves; no deep-read |
| [x] P0-6 | Commit sample data | `aitu-backend/data/example-scores.json` | — | tracked file | `git add`+commit | file tracked in backend subrepo |
| [x] P0-7 | Move system prompt | `docs-migration.md` (root) | — | `context/archive/docs-migration/docs-migration.md` | move | file relocated into kit |
| [x] P0-8 | Scaffold | — | plan §2 | empty `context/` + `documentation/` trees, one-line README per leaf | create | tree matches §2; leaf READMEs present |

## Phase 1 — Foundational platform context

| ID | Area | Source / touch | Verify against | Produce | Action | Exit |
|----|------|----------------|----------------|---------|--------|------|
| [x] P1-1 | Doc instructions | plan §1.5 | — | `context/00-documentation-instructions.md` | create | decision table lists REAL areas (backend/frontend/shared) |
| [x] P1-2 | Index seed | all planned files | plan §2 | `context/00-index.md` | create | every planned file has a one-liner |
| [x] P1-3 | Complete overview | kit draft `00-project-complete-overview.md` | code | `context/00-project-complete-overview.md` | migrate draft | orients a fresh LLM in one paste |
| [x] P1-4 | Project | READMEs, `TODO.md` | — | `context/01-project.md` | create | what/who/problem domain |
| [x] P1-5 | Tech stack | `pyproject.toml`,`uv.lock`,`package.json`,`package-lock.json`,`.python-version`,`vite.config.ts` | lockfiles | `context/02-tech-stack.md` | create | locked versions from lockfiles, not guessed |
| [x] P1-6 | Services overview | both READMEs, `main.py`, `App.tsx` | code | `context/03-services-overview.md` | create | roles, ports (8765), how they connect |
| [x] P1-7 | Local dev | both `Makefile`s, `package.json` scripts | code | `context/04-local-development.md` | create | real commands: `uv sync`/`make serve`, `npm install`/`npm run dev` |
| [x] P1-8 | Deployment stub | — | — | `context/05-deployment.md` | stub | one line: POC, local-only, no deploy yet |
| [x] P1-9 | Database (short) | `paths.py`, `data/example-scores.json` | code | `context/07-database.md` | create | "no DB; file store" + pointer |
| [x] P1-10 | Conventions | `eslint.config.js`, `pyproject.toml`, code style | configs | `context/09-coding-conventions.md` | create | only rules enforced by config or visibly followed |
| [x] P1-11 | Skips note | — | — | one-liner in `00-index.md` for skipped `06`,`08` | note | justification recorded |

## Phase 2 — Area agents (2a first; 2b/2c parallel)

| ID | Area | Source / touch | Verify against | Produce | Action | Exit |
|----|------|----------------|----------------|---------|--------|------|
| [x] P2a | Shared notation spec | both READMEs, `sequence.py`, `matrixToNotation.ts`, `TODO.md` | code | `context/music/notation-logic/02-notation-spec.md.md` (+ `shared/README.md`) | consolidate | single source; text notation, onset rule, sparse-COO, two-hand, lyrics all correct vs code |
| [x] P2b-1 | Backend overview | `sequence.py`,`schemas.py`,`main.py`,`paths.py`,`README.md` | code | `context/backend/{README,notation-and-parsing,api}.md` | migrate+create | ≤~200 ln each; links to shared spec + down to docs |
| [x] P2b-2 | Backend detail | same | code | `documentation/services/backend/{endpoints,schemas,sequence-logic,paths-and-data}.md` | migrate+create | endpoint params, 422 cases, field names, onset normalization all code-verified |
| [x] P2b-3 | Backend README rewrite | `aitu-backend/README.md` | — | short pointer README → root docs | rewrite | no duplicated spec; links to `context/backend/` |
| [x] P2c-1 | Frontend overview | `App.tsx`,`ScoreStack.tsx`,`SequenceComposer.tsx`,`LayoutControls.tsx`,`README.md` | code | `context/frontend/{README,app-shell,loaded-scores,compose-panel,rendering-pipeline}.md` | migrate+create | structured by UI area (Appendix C); ≤~200 ln each |
| [x] P2c-2 | Frontend detail | `matrixToNotation.ts`,`PianoSheet.tsx`,`notes.ts`,components | code | `documentation/services/frontend/{matrix-to-notation,piano-sheet,notes,components}.md` | migrate+create | beam rule, key-sig accidentals, dotted decomposition, grand-staff wrap code-verified |
| [x] P2c-3 | VexFlow ref migrate | `aitu-frontend/documentation/vexflow/README.md` | — | `documentation/archive/vexflow-reference.md` | move (cross-git copy + `git rm`) | logged; original removed |
| [x] P2c-4 | Frontend README rewrite | `aitu-frontend/README.md` | — | short pointer README | rewrite | no duplicated spec |

## Phase 3 — Index, READMEs, root meta

| ID | Area | Source / touch | Produce | Exit |
|----|------|----------------|---------|------|
| [x] P3-1 | Final index | all files | finalized `context/00-index.md` | every real file present, one-liner each |
| [x] P3-2 | Root README | project | root `README.md`: AImpromptu tagline + intended users (branding) + two services + run both | links into `context/00-*`; concise branding for user to tweak |
| [x] P3-3 | LLM provider inventory | `.claude/settings.local.json` | note in `09` / `implementations/`; recommend (don't build) commands | inventory recorded |

## Phase 4 — Cleanup

| ID | Check | Exit |
|----|-------|------|
| [x] P4-1 | Stray names | `git grep -n piano_matrix_generation` / `-ni piano-matrix` / `-n VITE_MATRIX_API_URL` → only in `context/archive/` |
| [x] P4-2 | Dead links | no links to `docs/`, old folder names, or moved paths |
| [x] P4-3 | Code diff scoped | only the authorized rename changed code/config; nothing else |
| [x] P4-4 | Archive kit | this folder lives at `context/archive/docs-migration/` |
| [x] P4-5 | Overview + index current | `00-index.md` and `00-project-complete-overview.md` match the final tree |
