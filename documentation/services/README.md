# documentation/services

Code-level detail per service. Overviews in [context/backend/](../../context/backend/README.md) and
[context/frontend/](../../context/frontend/README.md).

## Backend (`backend/`)

| File | Topic |
|------|-------|
| [endpoints.md](backend/endpoints.md) | The whole HTTP surface: `/audio`, `/matrix`, `/pieces`, `/sheet`, `/passages`, `/projects`, `/youtube` |
| [time-matrix.md](backend/time-matrix.md) | What stays of schema 2.0 (`schemas/time_matrix.py`): the frame length, the figure names, the marks an old `sheet.json` holds |
| [events-to-sheet.md](backend/events-to-sheet.md) | The derivation path: one stored file to the hand split the new sheet starts from, and why the steps are in that order |
| [transcription-pipeline.md](backend/transcription-pipeline.md) | Engines, thresholds, the artifact and leakage filters, the measurement behind each number |
| [hand-inference-second-pass.md](backend/hand-inference-second-pass.md) | The gated repair pass over the hand split |
| [rhythm-and-annotations.md](backend/rhythm-and-annotations.md) | `sheet.json` (was `rhythm.json`): everything a reader decided that is not derivable |
| [editing-and-compose.md](backend/editing-and-compose.md) | The replacement splice, and the one place a piece may change length |
| [paths-and-data.md](backend/paths-and-data.md) | The storage tree: `.database/`, the project bundle, the audio store, staging and history |
| [schemas.md](../deprecated/schemas.md) | Deprecated: the models of the deleted text-notation MVP |
| [sequence-logic.md](../deprecated/sequence-logic.md) | Deprecated: `matrix/text_notation.py`, now a builder of test matrices |
| [time-matrix.md](../deprecated/time-matrix.md) | Deprecated: the old sheet's score payload (the envelope, the figure ladder, passages, printed notes), removed in implementation 03, Phase 10 |

## Frontend (`frontend/`)

| File | Topic |
|------|-------|
| [components.md](frontend/components.md) | The component tree, the routes and where each piece lives |
| [score-pdf.md](frontend/score-pdf.md) | The PDF writer: SVG to operators, the embedded Bravura, how to check a bad file |
| [grid-notation.md](../deprecated/grid-notation.md) | Deprecated: the vexflow-v2 renderer of the old sheet, removed in implementation 03, Phase 10 |

## What was removed with the code it described

The VexFlow-era pages (`piano-sheet.md`, `matrix-to-notation.md`, `notes.md`) described modules
that no longer exist and were deleted with them. The renderer that replaced them,
`@aimpromptu/grid-notation` from the sibling `vexflow-v2` checkout, was itself removed in
implementation 03, Phase 10 (2026-10-27): its page is kept as
[deprecated/grid-notation.md](../deprecated/grid-notation.md). The sheet is now laid out and drawn by
the backend (`aitu_backend/sheet/`, see its `README.md`) and shown by `frames/FramesSheetPage`; the
overview is [context/frontend/rendering.md](../../context/frontend/rendering.md).
