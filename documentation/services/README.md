# documentation/services

Code-level detail per service. Overviews in [context/backend/](../../context/backend/README.md) and [context/frontend/](../../context/frontend/README.md).

## Backend (`backend/`)

| File | Topic |
|------|-------|
| [endpoints.md](backend/endpoints.md) | /health, /scores, /sequence |
| [schemas.md](backend/schemas.md) | SparseMatrix, MatrixScore, SequenceRequest |
| [sequence-logic.md](backend/sequence-logic.md) | sequence.py parsing and COO builder |
| [paths-and-data.md](backend/paths-and-data.md) | paths.py, example-scores.json |

## Frontend (`frontend/`)

| File | Topic |
|------|-------|
| [grid-notation.md](frontend/grid-notation.md) | How sheet music is drawn: `@aimpromptu/grid-notation`, `GridScore`, persistence |
| [components.md](frontend/components.md) | The component tree and where each piece lives |

The VexFlow-era pages — `piano-sheet.md`, `matrix-to-notation.md`, `notes.md` —
described modules that no longer exist and were removed with them. The rendering
they documented is now in
[grid-notation.md](frontend/grid-notation.md), and the package's own client
documentation lives in the sibling `vexflow-v2` checkout under `documentation/`.
