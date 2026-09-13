# Documentation index

Single table of contents for `context/` and `documentation/`. One line per file.

**New here?** Read [00-project-complete-overview.md](00-project-complete-overview.md) first, then
[backend/time-model.md](backend/time-model.md) — the second one is the idea every other file
assumes.

## Root

| File | Description |
|------|-------------|
| [../README.md](../README.md) | Project entry: what it does, the services, run locally, doc links |

## Platform (`context/`)

| File | Description |
|------|-------------|
| [00-documentation-instructions.md](00-documentation-instructions.md) | Where to put new docs; the two-folder model; cross-linking rules |
| [00-index.md](00-index.md) | This file — map of all documentation |
| [00-project-complete-overview.md](00-project-complete-overview.md) | One-shot orientation for a fresh reader or LLM |
| [01-project.md](01-project.md) | What AImpromptu is, who uses it, the problem it solves |
| [02-tech-stack.md](02-tech-stack.md) | Locked versions from lockfiles, and the standing technical decisions |
| [03-services-overview.md](03-services-overview.md) | The two services and the renderer: roles, ports, how they connect |
| [04-local-development.md](04-local-development.md) | Run it, test it, and the troubleshooting table |
| [05-deployment.md](05-deployment.md) | STUB: POC local-only; no deploy flow yet |
| *(skipped)* `06-*-infrastructure.md` | No cloud provider; POC is local-only |
| [07-database.md](07-database.md) | No database: the file store, what is kept and why so little |
| *(skipped)* `08-security.md` | No auth or network security surface; local POC only |
| [09-coding-conventions.md](09-coding-conventions.md) | Style grounded in ESLint and Python/uv idioms; LLM agent config inventory |

## Backend overview (`context/backend/`)

| File | Description |
|------|-------------|
| [backend/README.md](backend/README.md) | aitu-backend entry: the packages and what each is for |
| [backend/time-model.md](backend/time-model.md) | **The wall-clock model.** What replaced tempo, the five rules, what is dead |
| [backend/editing.md](backend/editing.md) | Re-recording a passage, and composing a piece from nothing |
| [backend/api.md](backend/api.md) | The HTTP surface: six routers and the shape of a session |
| [backend/notation-and-parsing.md](backend/notation-and-parsing.md) | The text-notation MVP path, kept but no longer an entry point |

## Frontend overview (`context/frontend/`)

| File | Description |
|------|-------------|
| [frontend/README.md](frontend/README.md) | aitu-frontend entry: the sections, the tabs, the data flow |
| [frontend/pages.md](frontend/pages.md) | Routes, the shell, and the "position has one home" rule |
| [frontend/rendering.md](frontend/rendering.md) | How the sheet is drawn, what the app does *not* decide, the stale-`dist` trap |
| [frontend/annotations.md](frontend/annotations.md) | Everything a reader can say about a piece, and where it goes |
| [frontend/printing.md](frontend/printing.md) | The PDF export: re-wrap to the paper, never scale; the margin is the control |
| [frontend/timestamps.md](frontend/timestamps.md) | UI rule: `mm:ss.cc`, frame labelled by start only, never wraps |

## Music (`context/music/`)

| File | Description |
|------|-------------|
| [music/notation-logic/02-notation-spec.md](music/notation-logic/02-notation-spec.md) | The text-notation contract, and the sparse-COO wire format every matrix still travels as |
| [music/transcription-quality.md](music/transcription-quality.md) | The four layers between audio and a printed figure; layer 4 is the one the wall clock removed |
| [music/piano_svg/01-piano-svg.md](music/piano_svg/01-piano-svg.md) | The 88-key SVG keyboard |

## Other context

| File | Description |
|------|-------------|
| [colors/color-palette.md](colors/color-palette.md) | The palette behind `ui/palette.ts` |
| [language/communication-style.md](language/communication-style.md) | How to write in this repository |
| [research/piano-transcription/piano-transcription-python-solutions.md](research/piano-transcription/piano-transcription-python-solutions.md) | The engine survey |

## Implementations journal (`context/implementations/`)

| File | Description |
|------|-------------|
| [implementations/README.md](implementations/README.md) | **Start here.** Every piece of planned work, numbered in the order it was opened, with its state |

### 01 — Epics master plan

| File | Description |
|------|-------------|
| [implementations/01-epics-master-plan/README.md](implementations/01-epics-master-plan/README.md) | Status in one look |
| [implementations/01-epics-master-plan/plan/README.md](implementations/01-epics-master-plan/plan/README.md) | How the plan is organised; the epic list in implementation order |
| [implementations/01-epics-master-plan/plan/wall-clock-rewrite.md](implementations/01-epics-master-plan/plan/wall-clock-rewrite.md) | **Read before touching the plan.** What the refactor changed for the remaining epics, the splice rule, the verdict per epic |
| [implementations/01-epics-master-plan/plan/checklist.md](implementations/01-epics-master-plan/plan/checklist.md) | THE status lookup: every epic, story and task with checkboxes |
| [implementations/01-epics-master-plan/plan/system-prompt-workers.md](implementations/01-epics-master-plan/plan/system-prompt-workers.md) | System prompt for worker LLMs implementing tasks |
| `implementations/01-epics-master-plan/plan/epic-NN-*/` | 14 epic folders, each with an index, story folders and task files |
| [implementations/01-epics-master-plan/progress/README.md](implementations/01-epics-master-plan/progress/README.md) | The progress journal: one report per task |
| [implementations/01-epics-master-plan/progress/RETROSPECTIVE.md](implementations/01-epics-master-plan/progress/RETROSPECTIVE.md) | **The journal, closed.** What the fourteen epics cost, what was cancelled, what held |
| [implementations/01-epics-master-plan/progress/2026-08-10-time-based-concept-closed.md](implementations/01-epics-master-plan/progress/2026-08-10-time-based-concept-closed.md) | The wall-clock refactor from start to close |
| [implementations/01-epics-master-plan/progress/plan-resume/README.md](implementations/01-epics-master-plan/progress/plan-resume/README.md) | The work committed after the refactor closed, reported late by Epic 14 |
| [implementations/01-epics-master-plan/progress/user_review/README.md](implementations/01-epics-master-plan/progress/user_review/README.md) | What to open and click, per epic |

### 02 — VexFlow migration — CLOSED

| File | Description |
|------|-------------|
| [implementations/02-vexflow-migration/README.md](implementations/02-vexflow-migration/README.md) | Why we built our own renderer instead of drawing with VexFlow |
| [implementations/02-vexflow-migration/01-system-prompt-vexflow-v2.md](implementations/02-vexflow-migration/01-system-prompt-vexflow-v2.md) | The brief that created `@aimpromptu/grid-notation` |

### 03 — Time-based concept refactor — CLOSED 2026-08-10

Wall-clock matrix columns and figure-as-label rendering. Spanned **two repositories**; all progress
is tracked here. **The plan is closed** — this folder is history, but `decisions.md` stays binding.

| File | Description |
|------|-------------|
| [implementations/03-time-based-concept/CLOSURE.md](implementations/03-time-based-concept/CLOSURE.md) | **Start here.** Why it closed, what shipped, what was dropped, the duplicated P8 numbering |
| [implementations/03-time-based-concept/README.md](implementations/03-time-based-concept/README.md) | Navigation + the cross-repo reporting rule |
| [implementations/03-time-based-concept/PRD.md](implementations/03-time-based-concept/PRD.md) | Why, what changes, what is out of scope, success criteria |
| [implementations/03-time-based-concept/decisions.md](implementations/03-time-based-concept/decisions.md) | **D-01 … D-34, frozen and still binding.** Every task cites these |
| [implementations/03-time-based-concept/contract.md](implementations/03-time-based-concept/contract.md) | Backend ↔ `@aimpromptu/grid-notation` data contract |
| [implementations/03-time-based-concept/plan.md](implementations/03-time-based-concept/plan.md) | Phases 0–8 as planned. Historical |
| [implementations/03-time-based-concept/checklist.md](implementations/03-time-based-concept/checklist.md) | The final state of every box, with the two cancellations |
| [implementations/03-time-based-concept/progress/README.md](implementations/03-time-based-concept/progress/README.md) | Where task reports go, including `vexflow-v2` work |
| [implementations/03-time-based-concept/progress/issues.md](implementations/03-time-based-concept/progress/issues.md) | Append-only log of anything contradicting a frozen decision |
| [implementations/03-time-based-concept/user-reviews.md](implementations/03-time-based-concept/user-reviews.md) | **What to open and click to see all of it.** Kept current |

## Archive (`context/archive/`)

| File | Description |
|------|-------------|
| [archive/README.md](archive/README.md) | Historical context; pointer to the docs-migration kit |
| [archive/superseded/README.md](archive/superseded/README.md) | **Documents describing a model or screen the app no longer has**, with where each current answer lives |
| `archive/superseded/` | `01-matrix-notation-logic.md`, `03-editing-logic.md`, `app-shell.md`, `compose-panel.md`, `loaded-scores.md`, `rendering-pipeline.md` |
| `archive/docs-migration/` | The completed documentation migration kit: plan, checklist, templates, deletions log |

## Documentation tree (`documentation/`)

| File | Description |
|------|-------------|
| [../documentation/README.md](../documentation/README.md) | Layout of the detail tree |
| [../documentation/services/README.md](../documentation/services/README.md) | Service detail index |

### Backend detail (`documentation/services/backend/`)

| File | Description |
|------|-------------|
| [../documentation/services/backend/endpoints.md](../documentation/services/backend/endpoints.md) | The whole HTTP surface, route by route, and what each obeys |
| [../documentation/services/backend/time-matrix.md](../documentation/services/backend/time-matrix.md) | Schema 2.0 field reference: envelope, ladder, passages, printed notes, layout hints |
| [../documentation/services/backend/events-to-sheet.md](../documentation/services/backend/events-to-sheet.md) | The derivation path, step by step, with the reason for each ordering |
| [../documentation/services/backend/transcription-pipeline.md](../documentation/services/backend/transcription-pipeline.md) | Engines, thresholds, the artifact and leakage filters, the measurement behind each number |
| [../documentation/services/backend/hand-inference-second-pass.md](../documentation/services/backend/hand-inference-second-pass.md) | The gated repair pass over the hand split |
| [../documentation/services/backend/rhythm-and-annotations.md](../documentation/services/backend/rhythm-and-annotations.md) | `rhythm.json` field by field: everything a reader decided |
| [../documentation/services/backend/editing-and-compose.md](../documentation/services/backend/editing-and-compose.md) | The replacement splice, and the one place a piece may change length |
| [../documentation/services/backend/paths-and-data.md](../documentation/services/backend/paths-and-data.md) | The storage tree: every path, `v<N>_f<frameMs>`, staging and history |
| [../documentation/services/backend/schemas.md](../documentation/services/backend/schemas.md) | The 1.x models the text-notation MVP still uses |
| [../documentation/services/backend/sequence-logic.md](../documentation/services/backend/sequence-logic.md) | `matrix/text_notation.py`: parsing, onset normalisation, the COO builder |

### Frontend detail (`documentation/services/frontend/`)

| File | Description |
|------|-------------|
| [../documentation/services/frontend/components.md](../documentation/services/frontend/components.md) | The component tree, the routes, and where each piece lives |
| [../documentation/services/frontend/grid-notation.md](../documentation/services/frontend/grid-notation.md) | The renderer seam: every option passed in, and what went with the old editor |
| [../documentation/services/frontend/score-pdf.md](../documentation/services/frontend/score-pdf.md) | The PDF writer: SVG to operators, the embedded Bravura, how to check a bad file |

### Other (`documentation/`)

| File | Description |
|------|-------------|
| [../documentation/issues/README.md](../documentation/issues/README.md) | Troubleshooting runbooks |
| [../documentation/issues/piano-matrix-sustains-and-phantom-onsets.md](../documentation/issues/piano-matrix-sustains-and-phantom-onsets.md) | Held chords printing short; chords with a note too many |
| [../documentation/issues/hand-split-ledger-lines.md](../documentation/issues/hand-split-ledger-lines.md) | A hand printed far outside its own staff under a pile of ledger lines |
| [../documentation/issues/rhythm-figures-and-tempo.md](../documentation/issues/rhythm-figures-and-tempo.md) | **Retired.** An evenly played passage printing as mixed figures — the bug class the wall clock removed |
| [../documentation/implementations/README.md](../documentation/implementations/README.md) | Stable topic-based how-tos |
| [../documentation/deprecated/README.md](../documentation/deprecated/README.md) | Superseded or removed features (banner required) |
| [../documentation/archive/README.md](../documentation/archive/README.md) | Historical reference |
| [../documentation/archive/vexflow-reference.md](../documentation/archive/vexflow-reference.md) | Archived VexFlow EasyScore notes |

## The renderer's own documentation

`@aimpromptu/grid-notation` is documented in the sibling checkout, not here:
`../vexflow-v2/documentation/` — seven numbered files from quick start through annotations,
playback and integration.

## Subrepo pointers

| File | Description |
|------|-------------|
| [../aitu-backend/README.md](../aitu-backend/README.md) | Backend entry → links to `context/backend/` |
| [../aitu-frontend/README.md](../aitu-frontend/README.md) | Frontend entry → links to `context/frontend/` |
