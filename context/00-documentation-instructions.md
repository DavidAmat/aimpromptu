# Documentation instructions

How the AImpromptu (aitu) documentation system works and where to put new material.

## Two folders

| Folder | Purpose |
|--------|---------|
| `context/` | LLM-first overviews: what something is and how it flows. Short, dense, cross-linked. |
| `documentation/` | Engineer-first detail: endpoints, field names, file paths, exact commands, runbooks. |

**Rule of thumb:** *what is it / how does it flow* → `context/`. *Exact paths, params, columns, commands* → `documentation/`.

## Decision guide

| I just… | Put it in |
|---------|-----------|
| Built a new feature / entity | `context/<area>/<entity>.md` (overview) **and** `documentation/services/<service>/<topic>.md` (code detail), cross-linked both ways |
| Vibe-coded a feature and want the prompt/plan/iteration trail | `context/implementations/YYYY-MM-DD/<slug>/` |
| Wrote a stable how-to not tied to one entity | `documentation/implementations/<topic>/` |
| Fixed a bug / wrote a troubleshooting runbook | `documentation/issues/<area>/` |
| Changed stack, deploy flow, infra, data store, security, or conventions | the matching `context/0X-*.md` platform file |
| Found docs that are wrong-but-historical / never built | `archive/` (no banner) or `deprecated/` (banner required) per plan §1.4 |

## This repo's areas

**Platform files** (`context/00–09`): project, stack, services, local dev, deployment stub, database (file store), coding conventions. Skipped: `06-*-infrastructure` (no cloud), `08-security` (local POC, no auth surface).

**Service overviews:**
- `context/backend/` — aitu-backend: parsing, API, notation entry points
- `context/frontend/` — aitu-frontend: app shell, loaded scores, compose panel, rendering pipeline
- `context/shared/` — cross-service contract (`notation-spec.md` is the single source for text notation, onset rule, sparse-COO, two-hand, lyrics)

**Detail files:** `documentation/services/backend/` and `documentation/services/frontend/` mirror the above. Reference material: `documentation/archive/vexflow-reference.md`.

## Cross-linking

- Every `context/<area>/<entity>.md` ends with **Where to look deeper** → its `documentation/` detail and sibling entities.
- Every `documentation/` detail file opens with `> Context:` linking back up to its overview.

## Size and duplication

- Keep each `context/<area>/<entity>.md` ≤ ~200 lines; overflow goes to `documentation/`.
- Do **not** restate the notation contract outside `context/music/notation-logic/02-notation-spec.md.md` — link to it.
- Do **not** duplicate platform files (`00–09`) in entity files — link instead.

## After writing

1. Add the new file(s) to `context/00-index.md`.
2. Update `context/00-project-complete-overview.md` for anything platform-level.
3. Numbered platform files (`01–09`) are not frozen — any agent may add a sentence when it discovers a platform fact.

## Prime directive

Documentation work is **markdown only**. The Phase 0 rename is the only sanctioned code change. If docs cannot align with code without changing application code, surface an open question — do not patch code in a docs migration.

## Language

English output. Keep Spanish solfège note names (`Do`, `Re`, `Mi`, `Fa#`, `La#`, `Sol`, `Si`) and Spanish key-signature labels verbatim. Keep English music terms in English (onset, sustain, treble, bass clef, grand staff, beam, tie).
