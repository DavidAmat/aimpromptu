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
| [matrix-to-notation.md](frontend/matrix-to-notation.md) | Sparse decode → VexPiece timeline |
| [piano-sheet.md](frontend/piano-sheet.md) | VexFlow rendering |
| [notes.md](frontend/notes.md) | 88-key map, KEY_SIGNATURES |
| [components.md](frontend/components.md) | App, ScoreStack, SequenceComposer, LayoutControls |
