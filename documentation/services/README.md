# documentation/services

Code-level detail per service. Overviews in [context/backend/](../../context/backend/README.md) and
[context/frontend/](../../context/frontend/README.md).

## Backend (`backend/`)

| File | Topic |
|------|-------|
| [endpoints.md](backend/endpoints.md) | The whole HTTP surface: `/audio`, `/matrix`, `/time`, `/audio/{uuid}/edits`, `/library`, `/youtube` |
| [time-matrix.md](backend/time-matrix.md) | Schema 2.0 field reference: the envelope, the figure ladder, passages, printed notes |
| [events-to-sheet.md](backend/events-to-sheet.md) | The derivation path: one stored file to a drawn staff, and why the steps are in that order |
| [transcription-pipeline.md](backend/transcription-pipeline.md) | Engines, thresholds, the artifact and leakage filters, the measurement behind each number |
| [hand-inference-second-pass.md](backend/hand-inference-second-pass.md) | The gated repair pass over the hand split |
| [rhythm-and-annotations.md](backend/rhythm-and-annotations.md) | `rhythm.json`: everything a reader decided that is not derivable |
| [editing-and-compose.md](backend/editing-and-compose.md) | The replacement splice, and the one place a piece may change length |
| [paths-and-data.md](backend/paths-and-data.md) | The storage tree: every path, `v<N>_f<frameMs>`, staging and history |
| [schemas.md](backend/schemas.md) | The 1.x models the text-notation MVP still uses |
| [sequence-logic.md](backend/sequence-logic.md) | `matrix/text_notation.py`: parsing and the COO builder |

## Frontend (`frontend/`)

| File | Topic |
|------|-------|
| [components.md](frontend/components.md) | The component tree, the routes and where each piece lives |
| [grid-notation.md](frontend/grid-notation.md) | How the sheet is drawn: `@aimpromptu/grid-notation`, the seam, the stale-`dist` trap |
| [score-pdf.md](frontend/score-pdf.md) | The PDF writer: SVG to operators, the embedded Bravura, how to check a bad file |

## What was removed with the code it described

The VexFlow-era pages — `piano-sheet.md`, `matrix-to-notation.md`, `notes.md` — described modules
that no longer exist and were deleted with them. The rendering they documented is now in
[grid-notation.md](frontend/grid-notation.md), and the package's own client documentation lives in
the sibling `vexflow-v2` checkout under `documentation/`.
