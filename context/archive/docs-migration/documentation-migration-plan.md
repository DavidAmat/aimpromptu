# AImpromptu (aitu) — Documentation Migration Plan

> Planner artifact. This run produced a **plan + kit only**; nothing was renamed, moved,
> git-init'd, or staged. Execution is deferred to the phases below, pending your validation.
> Source system prompt: `docs-migration.md` (repo root) — move into this folder in Phase 0.

## 0. Decisions locked by the user (2026-07-05)

1. **Docs home = root umbrella + git-init.** ONE `context/` + `documentation/` tree at the
   workspace root, covering both services. The root (`music-rendering/`, becoming **AImpromptu**)
   is `git init`'d so the docs are version-controlled. The two subrepos keep their own histories.
2. **Deep rename**, including the Python module. `piano-matrix-generation → aitu-backend`
   (module `piano_matrix_generation → aitu_backend`), `piano-matrix-notation → aitu-frontend`,
   project `music-rendering → AImpromptu (aitu)`. This is a **functional change** and must be
   re-verified (§ Phase 0 exit).
3. **This run = kit only.** The rename, git-init, scaffolding, and doc migration are all described
   here but NOT yet executed.

## 1. What the project is (high level)

Two independent git repos under a non-git workspace root:

| Service | Current folder → new | Stack | Role |
|---|---|---|---|
| Backend | `piano-matrix-generation/` → `aitu-backend/` | Python 3.12, FastAPI, Pydantic 2, uvicorn, `uv`; module `piano_matrix_generation` → `aitu_backend` | Parses custom Spanish-solfège piano notation → compact sparse-COO JSON score. `POST /sequence`, `GET /scores`, `GET /health`. Notation-agnostic; emits no VexFlow. |
| Frontend | `piano-matrix-notation/` → `aitu-frontend/` | React 19, TypeScript, Vite 8, VexFlow 5 | Renders the JSON as sheet music. Owns ALL rendering: beams, dotted-note decomposition, key signatures, lyrics, one-hand treble and two-hand braced grand staff. |

**The domain in one paragraph.** A user writes music in a line-per-time-frame text notation using
Spanish solfège (`Do`, `Re`, `Mi`, … + scientific octave, `*` = onset/struck, plain = sustain,
`||` = chord, blank = silence). The backend converts that to a sparse `(rows, cols, onset)` COO
matrix over the 88 keys × N time frames and ships it as JSON. The frontend decodes it, rebuilds
durations, and renders staff notation with VexFlow. Scores are **one hand** (treble `matrix`) or
**two hands** (`r_matrix` treble + `l_matrix` bass, equal frame counts, braced grand staff).
Optional `lyrics` are time-frame-indexed (drawn even over sustains/silences), and an optional
`keySignature` drives VexFlow's accidental display.

POC status: **local-only**. No cloud, no deploy pipeline, no AI, no auth/security surface, no
database (a single `data/example-scores.json` file store). Those platform files are stubbed or
skipped with a one-line justification, per user instruction.

## 2. Target structure (adapted to this repo)

Root umbrella, git-init'd:

```
music-rendering/  (→ AImpromptu; new git root)
├── README.md                     # root: what AImpromptu is, the two services, how to run both
├── .gitignore                    # must NOT ignore context/ or documentation/
├── context/
│   ├── 00-documentation-instructions.md
│   ├── 00-index.md
│   ├── 00-project-complete-overview.md
│   ├── 01-project.md
│   ├── 02-tech-stack.md
│   ├── 03-services-overview.md
│   ├── 04-local-development.md    # run backend (uv/make serve) + frontend (npm dev) together
│   ├── 05-deployment.md           # STUB: POC, local-only. One-line note; no deploy flow yet.
│   ├── 07-database.md             # SHORT: no DB; file store data/example-scores.json only.
│   ├── 09-coding-conventions.md   # grounded in eslint.config.js + Python/uv idioms
│   ├── implementations/
│   │   ├── README.md
│   │   └── 00-implementation-index.md
│   ├── backend/                   # aitu-backend overview (≤~200 lines/file)
│   │   ├── README.md
│   │   ├── notation-and-parsing.md
│   │   └── api.md
│   ├── frontend/                  # aitu-frontend, structured by UI area (Appendix C)
│   │   ├── README.md
│   │   ├── app-shell.md           # App.tsx: fetch /scores, global layout state
│   │   ├── loaded-scores.md       # ScoreStack + LayoutControls
│   │   ├── compose-panel.md       # SequenceComposer (POST /sequence)
│   │   └── rendering-pipeline.md  # matrixToNotation + PianoSheet (VexFlow)
│   ├── shared/
│   │   ├── README.md
│   │   └── notation-spec.md       # THE contract: text notation, onset rule, sparse-COO,
│   │                              #   two-hand, lyrics. Single source; both services link here.
│   └── archive/
│       ├── README.md
│       └── docs-migration/        # THIS kit (once migration is done)
├── documentation/
│   ├── README.md
│   ├── services/
│   │   ├── README.md
│   │   ├── backend/
│   │   │   ├── endpoints.md        # /health, /scores, /sequence: params, 422 cases, response shape
│   │   │   ├── schemas.md          # SparseMatrix, MatrixScore, SequenceRequest (camelCase JSON)
│   │   │   ├── sequence-logic.md   # sequence.py: parsing, onset normalization, COO builder
│   │   │   └── paths-and-data.md   # paths.py + data/example-scores.json
│   │   └── frontend/
│   │       ├── matrix-to-notation.md  # sparse decode → note events → durations/dots → timeline
│   │       ├── piano-sheet.md      # VexFlow: staves, beam rule, accidentals, dots, lyrics, wrap, grand staff
│   │       ├── notes.md            # 88-key builder, Spanish→VexFlow map, KEY_SIGNATURES table
│   │       └── components.md       # SequenceComposer, LayoutControls, ScoreStack, App wiring
│   ├── issues/README.md
│   ├── implementations/README.md
│   ├── deprecated/README.md
│   └── archive/
│       ├── README.md
│       └── vexflow-reference.md    # migrated from aitu-frontend/documentation/vexflow/README.md
└── aitu-backend/ , aitu-frontend/  (own .git each)
```

**Skipped platform files (with justification):**
- `06-<cloud>-infrastructure.md` — no cloud provider; POC is local-only.
- `08-security.md` — no auth/network/secret surface locally; user asked to skip.
- `05-deployment.md` — kept as a one-line stub only (no deploy exists yet).

## 3. Staging note — no `docs/` staging folder needed

The user listed `EXISTING_DOC_LOCATIONS: nothing`. In practice the entire legacy doc corpus is:
two **current, high-quality** READMEs (backend + frontend) and one reference file
`aitu-frontend/documentation/vexflow/README.md` (150 lines). There is no scattered/stale mess to
stage. So we **skip the `docs/` staging step**. Instead:
- The two READMEs are *consumed by reference* (code-truth verified) into `context/` + `documentation/`,
  then rewritten as short pointers to the new tree (they stay as each subrepo's entry README).
- The vexflow reference is migrated to `documentation/archive/vexflow-reference.md`.

> **Cross-git caveat:** the vexflow file lives inside the `aitu-frontend` subrepo git; the new docs
> live in the root umbrella git. Moving it across the boundary cannot preserve git history — do a
> plain copy into the root tree and `git rm` the original in the subrepo. Log it in `deletions-log.md`.

## 4. Universal rules (binding for every agent)

1. **Output language: English.** Keep Spanish solfège note names verbatim (`Do`, `Re`, `Mi`, `Fa#`,
   `La#`, `Sol`, `Si`) and any Spanish key-signature labels that match code identifiers. Keep every
   English musical term in English (onset, sustain, treble, bass clef, grand staff, beam, tie).
2. **Code-truth always wins.** The READMEs are excellent but are a starting point; verify each claim
   against `sequence.py` / `schemas.py` / `matrixToNotation.ts` / `PianoSheet.tsx` / `notes.ts`.
3. **No duplication.** The notation contract lives once in `context/music/notation-logic/02-notation-spec.md.md`; both
   services link to it instead of re-explaining it. Don't restate platform files in entity files.
4. **One file = one topic.** Split rendering vs API vs notation; keep each `context/<area>/*.md` ≤ ~200 lines.
5. **Cross-link both ways.** Every `context/<area>/<entity>.md` ends with "Where to look deeper" →
   its `documentation/` detail + sibling entities. Every `documentation/` file opens with `> Context:` up-link.
6. **Archive vs Deprecated** per §1.4 of the system prompt. Banner on `deprecated/` only.
7. **Never touch application code — except the one authorized rename.** The deep rename (Phase 0) is
   the *only* sanctioned code/config change and must be verified. After Phase 0, docs work is
   markdown-only. Any other needed code change → open question.
8. **No secrets.** Reference env var **names** only (`VITE_MATRIX_API_URL`, `HOST`, `PORT`).
9. **No emojis, no marketing tone, no narrative.** Terse, factual, skimmable.
10. **Surface gaps as open questions;** take the safe default (stub/archive, never delete blind).
11. **Update platform files as you learn.** Any Phase-2 agent that discovers something platform-level
    (a new tech-stack fact, a convention) updates the matching `context/0X-*.md` **and** `00-index.md`
    — the numbered files are not frozen after Phase 1.

## 5. The deep rename (Phase 0) — exact scope

**Backend (`piano-matrix-generation/` → `aitu-backend/`):**
- Rename folder; rename `src/piano_matrix_generation/` → `src/aitu_backend/`.
- `pyproject.toml`: `name = "aitu-backend"`; update `description`; `[tool.hatch.build.targets.wheel]
  packages = ["src/aitu_backend"]`; `[...sdist] include = ["src/aitu_backend", ...]`.
- Imports in `main.py` (lines 8–10, 97), and any in `schemas.py`, `sequence.py`, `paths.py`, `__init__.py`:
  `piano_matrix_generation` → `aitu_backend`.
- `Makefile` line 10: `uvicorn aitu_backend.main:app`.
- `notebooks/02-88-keys-matrix.ipynb`: one `piano_matrix_generation` import → `aitu_backend`.
- `README.md`: title + references.
- Regenerate `uv.lock` via `uv lock` (name change). `.python-version` untouched.

**Frontend (`piano-matrix-notation/` → `aitu-frontend/`):**
- Rename folder.
- `package.json`: `"name": "aitu-frontend"`.
- `README.md`: title + references to the other service.
- **Env var rename (resolved Q2): `VITE_MATRIX_API_URL` → `VITE_AITU_API_URL` everywhere it appears** —
  `src/App.tsx` (line 13, the `import.meta.env` read + fallback comment) and `src/vite-env.d.ts`
  (lines 4–5, the JSDoc + the typed member). It is not set in any `.env` file today, so no `.env`/`.env.example`
  change is needed; if one is added later it uses the new name. Verify the frontend still reads the backend URL.

**Backend housekeeping (resolved Q4, Q6):**
- **Reorganize `notebooks/` into thematic POC subfolders** (one folder per POC theme), e.g.
  `notebooks/dummy-matrix/01-generate-dummy-matrix.ipynb` and `notebooks/88-keys-matrix/02-88-keys-matrix.ipynb`
  (name folders after each notebook's theme; keep a `.gitkeep` if a folder would otherwise be empty). This is
  the standing convention going forward: **each new thematic POC gets its own `notebooks/<theme>/` subfolder.**
  Fix the `aitu_backend` import in `02-88-keys-matrix.ipynb` after the move; do NOT deep-read the notebooks —
  just confirm the import line resolves.
- **Commit `data/example-scores.json`** into the backend subrepo (it is currently untracked); it is the sample
  served by `GET /scores`.

**Project-wide:**
- References to `music-rendering` / `piano-matrix-*` in `TODO.md`, both READMEs, and the new root `README.md` → AImpromptu / aitu-backend / aitu-frontend.
- `docs-migration.md` (root) → moved into this kit folder as the historical ask.

**Phase 0 exit (verification — this is a functional change):**
- Backend: `cd aitu-backend && uv sync && make serve` boots uvicorn on `127.0.0.1:8765`; `GET /health`
  and `GET /docs` respond; `POST /sequence` on a sample body returns a score.
- Frontend: `cd aitu-frontend && npm install && npm run build` (tsc + vite) passes; `npm run dev` serves
  and talks to the backend using `VITE_AITU_API_URL` (with the `http://127.0.0.1:8765` fallback).
- `git grep -n piano_matrix_generation` / `git grep -ni "piano-matrix"` / `git grep -n VITE_MATRIX_API_URL`
  return **only** intentional historical mentions inside `context/archive/` (none in live code/config).
- Notebooks live under `notebooks/<theme>/`; `data/example-scores.json` is tracked by the backend git.

## 6. Gap analysis

| Area | Source | Has docs? | Quality | Verdict |
|---|---|---|---|---|
| Shared notation contract (text notation, onset rule, sparse-COO, two-hand, lyrics) | both READMEs, `sequence.py`, `matrixToNotation.ts` | yes (in READMEs) | up-to-date | **consolidate** into `context/music/notation-logic/02-notation-spec.md.md` (single source) |
| Backend — sequence logic | `sequence.py` (178 ln) | partial | good | migrate + code-verify → `documentation/services/backend/sequence-logic.md` |
| Backend — schemas | `schemas.py` (95 ln) | partial (code map only) | ok | create → `.../backend/schemas.md` |
| Backend — endpoints | `main.py` (105 ln) | yes (README API) | good | migrate → `.../backend/endpoints.md` |
| Backend — paths + data | `paths.py`, `data/example-scores.json` | none | — | **create from code** → `.../backend/paths-and-data.md` |
| Backend — notebooks | `notebooks/<theme>/*.ipynb` | none | — | reorganize into thematic subfolders (Phase 0); one-line mention + the "one folder per POC" convention in `context/backend/README.md`; do NOT deep-read notebooks |
| Frontend — matrix→notation pipeline | `matrixToNotation.ts` (251 ln) | yes | good | migrate + verify → `.../frontend/matrix-to-notation.md` |
| Frontend — VexFlow rendering | `PianoSheet.tsx` (382 ln) | yes (README) | good | migrate → `.../frontend/piano-sheet.md` (heaviest detail file) |
| Frontend — notes/key sigs | `notes.ts` (109 ln) | partial | ok | create → `.../frontend/notes.md` |
| Frontend — compose panel | `SequenceComposer.tsx` (254 ln, uncommitted) | partial | ok | **create from code** → `context/frontend/compose-panel.md` + components.md |
| Frontend — layout/score-stack/app | `LayoutControls.tsx`, `ScoreStack.tsx`, `App.tsx` | partial | ok | create → `context/frontend/{app-shell,loaded-scores}.md` |
| VexFlow reference | `aitu-frontend/documentation/vexflow/README.md` (150 ln) | yes (legacy) | reference | migrate → `documentation/archive/vexflow-reference.md` |
| Tech stack / local dev / conventions | lockfiles, `eslint.config.js`, Makefiles | none (scattered) | — | create → `context/02,04,09` |

## 7. Phases & order of execution

- **Phase 0 — Foundations & rename (main thread, no sub-agents).**
  `git init` root; `.gitignore` that does not exclude `context/`/`documentation/`; execute the deep
  rename (§5) and verify both services boot/build; scaffold the empty `context/` + `documentation/`
  skeleton (one-line README per leaf); move `docs-migration.md` into this kit folder. Blocks everything.
- **Phase 1 — Foundational platform context.** `context/00-documentation-instructions.md`, `00-index.md`
  (seed), `00-project-complete-overview.md` (finalize the draft in this kit), `01-project.md`,
  `02-tech-stack.md`, `03-services-overview.md`, `04-local-development.md`, `07-database.md` (short),
  `09-coding-conventions.md`; stub `05-deployment.md`; note skips for `06`/`08`. Must precede Phase 2.
- **Phase 2 — Area agents (parallelisable). Also write `context/music/notation-logic/02-notation-spec.md.md` FIRST within
  this phase** (task 2a) because 2b/2c both link to it.
  - 2a `shared-notation-spec` — the contract (do this before/early).
  - 2b `backend` — `context/backend/*` + `documentation/services/backend/*`.
  - 2c `frontend` — `context/frontend/*` + `documentation/services/frontend/*` + migrate vexflow ref.
- **Phase 3 — Index, READMEs, root meta.** Finalize `00-index.md`, root `README.md`, inventory
  `.claude/settings.local.json`, recommend (don't build) any slash-commands/skills.
- **Phase 4 — Cleanup.** No stray `piano-matrix*` / `piano_matrix_generation` in live code; no dead
  links; the only code diff vs the pre-migration state is the authorized rename; archive this kit under
  `context/archive/docs-migration/`.

For a project this small, Phases 1–3 could be compressed, but keeping them separate lets the Phase-2
area work run in parallel against a stable Phase-1 base.

## 8. Validation checklist (run per legacy file before calling it "active")

- [ ] Every factual claim re-checked against the implementing code (imports, endpoint names, field
      names, the onset rule, the beam rule, key-signature behavior).
- [ ] Spanish note names / key labels preserved verbatim; English music terms kept English.
- [ ] No secret values; env var **names** only.
- [ ] Correct destination per the §2 tree; ≤ ~200 lines for `context/<area>/*`.
- [ ] Cross-links both ways added.
- [ ] `00-index.md` and (if platform-level) the matching `0X` file updated.
- [ ] `deletions-log.md` entry for any consumed/moved/deleted source.

## 9. Acceptance criteria

1. Deep rename executed and **both services verified** to boot/build (Phase 0 exit).
2. `context/` + `documentation/` populated per §2; every file listed in `00-index.md` with a one-liner.
3. `00-project-complete-overview.md` orients a fresh reader in one paste.
4. The notation contract exists once in `context/music/notation-logic/02-notation-spec.md.md`; both services link to it.
5. No `docs/` staging left; vexflow reference migrated and original `git rm`'d (logged).
6. No dead links; no stray old names in live code/config (incl. `VITE_MATRIX_API_URL`); only the
   authorized rename + housekeeping changed code.
7. Notebooks organized under `notebooks/<theme>/`; `data/example-scores.json` committed.
8. This kit archived under `context/archive/docs-migration/`.

## 10. Resolved decisions (all open questions answered 2026-07-05)

No open questions remain. The answers below are binding and already folded into §5, §6, §9:

1. **Git layout.** Git-init the root; it carries only a root `README.md` + `.gitignore` (plus the docs
   trees). The two subrepos stay **nested independent git repos** (not submodules).
2. **Env var.** Rename `VITE_MATRIX_API_URL` → **`VITE_AITU_API_URL`** project-wide. It is not set in any
   `.env` today, so only `src/App.tsx` and `src/vite-env.d.ts` change.
3. **Python module.** `piano_matrix_generation` → **`aitu_backend`**.
4. **Notebooks.** Reorganize `notebooks/` into **one thematic subfolder per POC** (e.g.
   `notebooks/dummy-matrix/`, `notebooks/88-keys-matrix/`); this is the standing convention for future POCs.
   Fix imports after moving; do not deep-read.
5. **Working-tree code.** Docs describe the **working tree** (two-hand support included), not `HEAD`.
6. **Sample data.** **Commit** `data/example-scores.json` in the backend subrepo.
7. **Root README.** Include AImpromptu **branding** — a one-line tagline and intended users — on top of the
   factual "two services + how to run". The Phase-3 agent drafts concise wording (see the template) for you
   to tweak; no blocking input needed.
