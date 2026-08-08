# Documentation index

Single table of contents for `context/` and `documentation/`. One line per file.

## Root

| File | Description |
|------|-------------|
| [../README.md](../README.md) | Project entry: tagline, services, run locally, doc links |

## Platform (`context/`)

| File | Description |
|------|-------------|
| [00-documentation-instructions.md](00-documentation-instructions.md) | Where to put new docs; two-folder model; cross-linking rules |
| [00-index.md](00-index.md) | This file — map of all documentation |
| [00-project-complete-overview.md](00-project-complete-overview.md) | One-shot orientation for a fresh reader or LLM |
| [01-project.md](01-project.md) | What AImpromptu is, who uses it, problem domain |
| [02-tech-stack.md](02-tech-stack.md) | Locked versions from lockfiles |
| [03-services-overview.md](03-services-overview.md) | aitu-backend and aitu-frontend roles, ports, connection |
| [04-local-development.md](04-local-development.md) | Run both services locally |
| [05-deployment.md](05-deployment.md) | STUB: POC local-only; no deploy flow yet |
| *(skipped)* `06-*-infrastructure.md` | No cloud provider; POC is local-only |
| [07-database.md](07-database.md) | No database; file store `data/example-scores.json` only |
| *(skipped)* `08-security.md` | No auth or network security surface; local POC only |
| [09-coding-conventions.md](09-coding-conventions.md) | Style grounded in ESLint and Python/uv idioms; LLM agent config inventory |

## Implementations journal (`context/implementations/`)

| File | Description |
|------|-------------|
| [implementations/README.md](implementations/README.md) | Dated journal conventions for vibe-coded features |
| [implementations/00-implementation-index.md](implementations/00-implementation-index.md) | Master index sorted by date |

### Implementation plan (`context/implementations/plan/`)

| File | Description |
|------|-------------|
| [implementations/plan/README.md](implementations/plan/README.md) | How the plan is organized; epic list in implementation order |
| [implementations/plan/checklist.md](implementations/plan/checklist.md) | THE status lookup: every epic/story/task with checkboxes |
| [implementations/plan/system-prompt-workers.md](implementations/plan/system-prompt-workers.md) | System prompt for worker LLMs implementing tasks |
| `implementations/plan/epic-NN-*/` | 14 epic folders, each with an `epic-<shortname>-index.md`, story folders and task files |
| [implementations/progress/README.md](implementations/progress/README.md) | Progress journal written by workers, one report per task |
| [implementations/progress/2026-08-02-transcription-accuracy-session.md](implementations/progress/2026-08-02-transcription-accuracy-session.md) | Session: raw falling view, artifact filter, isochrony, Transkun, tempo-map groundwork |

### Time-based concept refactor (`context/implementations/time-based-concept/`)

Wall-clock matrix columns and figure-as-label rendering. Spans **two repos** (`aimpromptu` and `vexflow-v2`); all progress is tracked here.

| File | Description |
|------|-------------|
| [implementations/time-based-concept/README.md](implementations/time-based-concept/README.md) | Navigation + the cross-repo reporting rule |
| [implementations/time-based-concept/PRD.md](implementations/time-based-concept/PRD.md) | Why, what changes, what is out of scope, success criteria |
| [implementations/time-based-concept/decisions.md](implementations/time-based-concept/decisions.md) | D-01…D-31, the frozen decisions every task cites |
| [implementations/time-based-concept/contract.md](implementations/time-based-concept/contract.md) | Backend ↔ `@aimpromptu/grid-notation` data contract |
| [implementations/time-based-concept/plan.md](implementations/time-based-concept/plan.md) | Phases 0–8 with tasks and dependencies |
| [implementations/time-based-concept/checklist.md](implementations/time-based-concept/checklist.md) | THE status lookup for this refactor |
| [implementations/time-based-concept/system-prompt-worker.md](implementations/time-based-concept/system-prompt-worker.md) | Template system prompt for worker agents on this refactor |
| [implementations/time-based-concept/progress/README.md](implementations/time-based-concept/progress/README.md) | Where task reports go, including `vexflow-v2` work |
| [implementations/time-based-concept/progress/issues.md](implementations/time-based-concept/progress/issues.md) | Append-only log of anything that contradicts a frozen decision; a worker who writes here stops |
| [implementations/time-based-concept/user-reviews.md](implementations/time-based-concept/user-reviews.md) | What to open and click in the browser to try each group of tasks |

## Backend overview (`context/backend/`)

| File | Description |
|------|-------------|
| [backend/README.md](backend/README.md) | aitu-backend entry: parsing, API, notebooks |
| [backend/notation-and-parsing.md](backend/notation-and-parsing.md) | Text notation → sparse-COO (links to shared spec) |
| [backend/api.md](backend/api.md) | HTTP surface overview |

## Frontend overview (`context/frontend/`)

| File | Description |
|------|-------------|
| [frontend/README.md](frontend/README.md) | aitu-frontend entry |
| [frontend/app-shell.md](frontend/app-shell.md) | App.tsx: fetch scores, global layout state |
| [frontend/loaded-scores.md](frontend/loaded-scores.md) | ScoreStack + LayoutControls |
| [frontend/compose-panel.md](frontend/compose-panel.md) | SequenceComposer (POST /sequence) |
| [frontend/rendering-pipeline.md](frontend/rendering-pipeline.md) | matrixToNotation + PianoSheet (VexFlow) |
| [frontend/timestamps.md](frontend/timestamps.md) | UI rule: `mm:ss.cc`, frame labelled by start only, never wraps |

## Music (`context/music/`)

| File | Description |
|------|-------------|
| [music/notation-logic/01-matrix-notation-logic.md](music/notation-logic/01-matrix-notation-logic.md) | The piano matrix: appendices incl. B (sustains) and C (duration approximation) |
| [music/notation-logic/02-notation-spec.md](music/notation-logic/02-notation-spec.md) | The notation contract |
| [music/notation-logic/03-editing-logic.md](music/notation-logic/03-editing-logic.md) | Editing rules over the matrix |
| [music/transcription-quality.md](music/transcription-quality.md) | The four layers between audio and a printed figure, and what each gets wrong |
| [music/piano_svg/01-piano-svg.md](music/piano_svg/01-piano-svg.md) | The 88-key SVG keyboard |

## Shared (`context/shared/`)

| File | Description |
|------|-------------|
| [shared/README.md](shared/README.md) | Cross-service capabilities index |
| [shared/notation-spec.md](shared/notation-spec.md) | THE contract: text notation, onset rule, sparse-COO, two-hand, lyrics |

## Archive (`context/archive/`)

| File | Description |
|------|-------------|
| [archive/README.md](archive/README.md) | Historical context; pointer to docs-migration kit |

### Docs migration kit (`context/archive/docs-migration/`)

| File | Description |
|------|-------------|
| [archive/docs-migration/documentation-migration-plan.md](archive/docs-migration/documentation-migration-plan.md) | Migration plan and target tree |
| [archive/docs-migration/docs-migration-checklist.md](archive/docs-migration/docs-migration-checklist.md) | Phase checklist with task IDs |
| [archive/docs-migration/project-context.md](archive/docs-migration/project-context.md) | Agent orientation primer |
| [archive/docs-migration/deletions-log.md](archive/docs-migration/deletions-log.md) | Append-only log of consumed/moved sources |
| [archive/docs-migration/docs-migration.md](archive/docs-migration/docs-migration.md) | Original system prompt (historical) |
| [archive/docs-migration/agent-prompt-phase1-template.md](archive/docs-migration/agent-prompt-phase1-template.md) | Phase 1 agent template |
| [archive/docs-migration/agent-prompt-phase2-template.md](archive/docs-migration/agent-prompt-phase2-template.md) | Phase 2 agent template |
| [archive/docs-migration/00-project-complete-overview.draft.md](archive/docs-migration/00-project-complete-overview.draft.md) | Kit draft (superseded by active overview) |

## Documentation tree (`documentation/`)

| File | Description |
|------|-------------|
| [../documentation/README.md](../documentation/README.md) | Layout of the detail tree |
| [../documentation/services/README.md](../documentation/services/README.md) | Service detail index |

### Backend detail (`documentation/services/backend/`)

| File | Description |
|------|-------------|
| [../documentation/services/backend/endpoints.md](../documentation/services/backend/endpoints.md) | /health, /scores, /sequence: params, 422 cases, response shape |
| [../documentation/services/backend/schemas.md](../documentation/services/backend/schemas.md) | SparseMatrix, MatrixScore, SequenceRequest (camelCase JSON) |
| [../documentation/services/backend/sequence-logic.md](../documentation/services/backend/sequence-logic.md) | sequence.py: parsing, onset normalization, COO builder |
| [../documentation/services/backend/paths-and-data.md](../documentation/services/backend/paths-and-data.md) | paths.py + data/example-scores.json |
| [../documentation/services/backend/transcription-pipeline.md](../documentation/services/backend/transcription-pipeline.md) | audio → hands: order, artifact/leakage/isochrony parameters, engines, /events and /runs |
| [../documentation/services/backend/time-matrix.md](../documentation/services/backend/time-matrix.md) | Schema 2.0 field reference: frameMs columns, the figure ladder, passages (stub, filled in per phase) |

### Frontend detail (`documentation/services/frontend/`)

| File | Description |
|------|-------------|
| [../documentation/services/frontend/matrix-to-notation.md](../documentation/services/frontend/matrix-to-notation.md) | Sparse decode → note events → durations/dots → timeline |
| [../documentation/services/frontend/piano-sheet.md](../documentation/services/frontend/piano-sheet.md) | VexFlow: staves, beam rule, accidentals, dots, lyrics, wrap, grand staff |
| [../documentation/services/frontend/notes.md](../documentation/services/frontend/notes.md) | 88-key builder, Spanish→VexFlow map, KEY_SIGNATURES |
| [../documentation/services/frontend/components.md](../documentation/services/frontend/components.md) | SequenceComposer, LayoutControls, ScoreStack, App wiring |

### Other (`documentation/`)

| File | Description |
|------|-------------|
| [../documentation/issues/README.md](../documentation/issues/README.md) | Troubleshooting runbooks |
| [../documentation/issues/piano-matrix-sustains-and-phantom-onsets.md](../documentation/issues/piano-matrix-sustains-and-phantom-onsets.md) | Held chords printing short; chords with a note too many |
| [../documentation/issues/rhythm-figures-and-tempo.md](../documentation/issues/rhythm-figures-and-tempo.md) | An evenly played passage printing as mixed corcheas/semicorcheas |
| [../documentation/implementations/README.md](../documentation/implementations/README.md) | Stable topic-based how-tos |
| [../documentation/deprecated/README.md](../documentation/deprecated/README.md) | Superseded or removed features (banner required) |
| [../documentation/archive/README.md](../documentation/archive/README.md) | Historical reference |
| [../documentation/archive/vexflow-reference.md](../documentation/archive/vexflow-reference.md) | Archived VexFlow EasyScore notes (superseded by piano-sheet.md) |

## Subrepo pointers

| File | Description |
|------|-------------|
| [../aitu-backend/README.md](../aitu-backend/README.md) | Backend entry → links to `context/backend/` |
| [../aitu-frontend/README.md](../aitu-frontend/README.md) | Frontend entry → links to `context/frontend/` |
