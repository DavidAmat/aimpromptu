# 05, Phase 1: the inventory and the name check: report

Plan: [`05-plan.md`](05-plan.md) section 6, Phase 1. Tasks: [`05-checklist.md`](05-checklist.md) 1.1 to 1.3.
Written for: the next agent (Phase 2) and the user who reviews the phases.

## Docs changed

- `scripts/docs/check-names.py` (new): checks the names in backticks of the documentation against the code. Paths,
  routes and identifiers, as the plan's section 6 describes. It always exits 0.
- `context/00-documentation-instructions.md`: a paragraph about `check-names.py` beside the links check.
- `context/implementations/05-documentation-refresh/05-inventory.md` (new): 61 files in scope. Each row has the
  lines, the last change in git, the owner phase (plan section 7), the missing names and the H1 title. Every State is
  `to check`. Ends with the code changed since 2026-10-28, per folder.
- Checklist and this report: Phase 1 ticked.

No page of `context/` or `documentation/` was rewritten. Phase 1 changes no page of the owners.

## What was stale

The checker's first count is 204 missing names in 61 files (from 3,856 names checked). The files with the most:

| File | Missing |
|---|---:|
| `documentation/services/frontend/components.md` | 85 |
| `context/02b-local-setup.md` | 29 |
| `documentation/services/backend/editing-and-compose.md` | 10 |
| `documentation/services/backend/transcription-pipeline.md` | 8 |
| `documentation/services/backend/paths-and-data.md` | 6 |
| `documentation/services/backend/endpoints.md` | 6 |

Most of the 70 identifiers are old names: components and functions the code no longer has, such as
`TimeScoreView`, `VexflowSheetPage`, `MatrixGrid`, `NoteToolbox`, `RangeToolbox`, `SheetToolbox`, `transposeKey`.
The owner phases check each one. Most of the 118 paths are either files that moved or names of runtime files
(`sheet.json`, `.database/`, `project.json`); see "Not checked" for the rule on runtime files.

## Code and docs that disagree in a way that looks like a bug

None found in this phase: Phase 1 reads no code for behaviour. The names that are missing are candidates for the
owner phases to look at, not bugs.

## New terms for the glossary (for Phase 20)

None.

## Not checked

- The checker reads inline code only (between single backticks). Fenced code blocks are skipped on purpose: they hold
  shell commands and sample output.
- The rules of the checker are looser than the plan's wording, in three places:
  - An identifier also includes `camelCase` (`sheetButtons`, `usePassageClipboard`), not only `snake_case`,
    `CamelCase` and `name()`. The frontend's names need it.
  - A path that is not in git (a runtime file) passes when its file name occurs as a literal in the code roots.
    This is loose: `sheet.json` passes because the code names it, not because the file exists.
  - Machine paths (`/home/`, `/mnt/`, `/work/`, `/Volumes/`...), URLs, npm scope names (`@aimpromptu/...`) and
    `node_modules` are not checked at all.
- Routes are checked by their last literal part only (`runs` for `/sheet/{uuid}/llm/runs`). A route whose last
  part is a common word (`docs`, `stretch`) passes when that word occurs anywhere in `api/`. Each phase must read its
  own routes in `api/`.
- Identifiers are searched with `git grep -w --untracked` in `aitu-backend/src`, `aitu-frontend/src`,
  `aitu-backend/tests`, `aitu-frontend/scripts`, `scripts`, and the root `compose.yaml`, `Makefile`,
  `aitu-backend/pyproject.toml`, `aitu-frontend/package.json`. A name in another folder is reported as missing.
- The per-folder code summary counts every changed file in the repository: the implementation folders and the
  gallery images are in it too. Read the `aitu-backend/src/`, `aitu-frontend/src/` and test rows for the code.
- The counts are a first count, from one run on the whole scope. Each owner phase re-runs the checker on its files.

## Left for later phases

- Phase 2 (sheet-f1 and the time docs): the missing names are 2 in `context/backend/time-model.md`, 6 in
  `documentation/services/backend/time-matrix.md` and 6 in `rhythm-and-annotations.md`. Run
  `python3 scripts/docs/check-names.py <doc>` on each to see them.
- Phase 20 checks the whole scope again with `check-names.py` (the counts above are the baseline).
- `check-links.py` passes: 505 files, 0 broken links, at the end of this phase.
