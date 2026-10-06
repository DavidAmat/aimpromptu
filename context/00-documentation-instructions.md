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
| Planned a piece of work (brief, plan, checklist, phase reports) | `context/implementations/NN-group/NN-implementation/`, numbered by the rule in [implementations/README.md](implementations/README.md) |
| Wrote a stable how-to not tied to one entity | `documentation/implementations/<topic>/` |
| Fixed a bug / wrote a troubleshooting runbook | `documentation/issues/<area>/` |
| Changed stack, deploy flow, infra, data store, security, or conventions | the matching `context/0X-*.md` platform file |
| Found docs that are wrong-but-historical / never built | `context/archive/` (history, no banner) or `documentation/deprecated/` (a removed feature, banner required) |

## This repo's areas

**Platform files** (`context/00–09`): project, stack, services, local dev, deployment stub, database (file store), security (the users, the session cookie, the rights table, the home network; written by Phase 4 of implementation 02), coding conventions. Skipped: `06-*-infrastructure` (no cloud).

**The app and the language:**
- `context/app/` — [01-app-context.md](app/01-app-context.md), the app being built, in the user's words; its glossary is the vocabulary of every new page
- `context/language/` — how to write ([communication-style.md](language/communication-style.md)) and how to report on a plan ([communication-implementation-plans.md](language/communication-implementation-plans.md))
- `context/music-library/` — planned: the music library, its ontology and popularity (implementation 02, Phases 12 to 14)

**Service overviews:**
- `context/backend/` — aitu-backend: parsing, API, notation entry points
- `context/frontend/` — aitu-frontend: app shell, loaded scores, compose panel, rendering pipeline
- `context/music/notation-logic/` — the text-notation contract (`02-notation-spec.md`), which still
  owns the sparse-COO wire format and the 88-key row order

**Detail files:** `documentation/services/backend/` and `documentation/services/frontend/` mirror the above. Reference material: `documentation/archive/vexflow-reference.md`.

## Cross-linking

- Every `context/<area>/<entity>.md` ends with **Where to look deeper** → its `documentation/` detail and sibling entities.
- Every `documentation/` detail file opens with `> Context:` linking back up to its overview.

## Size and duplication

- Keep each `context/<area>/<entity>.md` ≤ ~200 lines; overflow goes to `documentation/`.
- Do **not** restate the notation contract outside `context/music/notation-logic/02-notation-spec.md` — link to it.
- Do **not** duplicate platform files (`00–09`) in entity files — link instead.

## After writing

1. Add the new file(s) to `context/00-index.md`.
2. Update `context/00-project-complete-overview.md` for anything platform-level.
3. Numbered platform files (`01–09`) are not frozen — any agent may add a sentence when it discovers a platform fact.

## Implementation folders

Planned work lives in `context/implementations/`, in groups: `01-mvp/` (closed) and
`02-private-web-app/` (live). Each implementation keeps its brief (`NN-prompt.md`), its plan, its
checklist (the status lookup) and one report per phase (`NN-implementation-phase-N.md`) in its own
folder, with a `README.md` that says its state. The numbering rule is in
[implementations/README.md](implementations/README.md). Phase reports and walkthroughs follow
[language/communication-implementation-plans.md](language/communication-implementation-plans.md).

An implementation is not documentation of the app. When a phase changes what the app is or does, it
updates the `context/` and `documentation/` pages it makes false, in the same phase.

## Checking the links

`python3 scripts/docs/check-links.py` checks every relative link of `context/`, `documentation/` and
every `README.md`, and exits non-zero on a broken one. Every phase leaves it passing. A file or
folder moved means its links are fixed in the same commit.

## When docs and code disagree

The documentation migration that created this system is complete; its kit is in
`archive/docs-migration/`. A page that cannot be made true without changing application code is not
patched around: the phase that finds it raises it in its walkthrough, and the plan says which phase
changes the code.

## Language

English output. Keep Spanish solfège note names (`Do`, `Re`, `Mi`, `Fa#`, `La#`, `Sol`, `Si`) and Spanish key-signature labels verbatim. Keep English music terms in English (onset, sustain, treble, bass clef, grand staff, beam, tie).
