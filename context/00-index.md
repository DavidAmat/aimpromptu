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
| [../documentation/implementations/README.md](../documentation/implementations/README.md) | Stable topic-based how-tos |
| [../documentation/deprecated/README.md](../documentation/deprecated/README.md) | Superseded or removed features (banner required) |
| [../documentation/archive/README.md](../documentation/archive/README.md) | Historical reference |
| [../documentation/archive/vexflow-reference.md](../documentation/archive/vexflow-reference.md) | Archived VexFlow EasyScore notes (superseded by piano-sheet.md) |

## Subrepo pointers

| File | Description |
|------|-------------|
| [../aitu-backend/README.md](../aitu-backend/README.md) | Backend entry → links to `context/backend/` |
| [../aitu-frontend/README.md](../aitu-frontend/README.md) | Frontend entry → links to `context/frontend/` |
