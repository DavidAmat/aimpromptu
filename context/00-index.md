# Documentation index

Single table of contents for `context/` and `documentation/`. One line per file.

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
| [09-coding-conventions.md](09-coding-conventions.md) | Style grounded in ESLint and Python/uv idioms |

## Implementations journal (`context/implementations/`)

| File | Description |
|------|-------------|
| [implementations/README.md](implementations/README.md) | Dated journal conventions for vibe-coded features |
| [implementations/00-implementation-index.md](implementations/00-implementation-index.md) | Master index sorted by date |

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
| [shared/README.md](shared/README.md) | Cross-service capabilities |
| [shared/notation-spec.md](shared/notation-spec.md) | THE contract: text notation, onset rule, sparse-COO, two-hand, lyrics |

## Archive (`context/archive/`)

| File | Description |
|------|-------------|
| [archive/README.md](archive/README.md) | Historical context |
| [archive/docs-migration/](archive/docs-migration/) | Migration kit (plan, checklist, templates) |

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
| [../documentation/archive/vexflow-reference.md](../documentation/archive/vexflow-reference.md) | VexFlow API reference (migrated from aitu-frontend) |
