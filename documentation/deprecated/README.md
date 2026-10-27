# documentation/deprecated

Features or decisions that were built then removed or superseded. Every file requires a deprecation banner at the top.

| File | Removed with |
|---|---|
| [notation-and-parsing.md](notation-and-parsing.md) | The text-notation MVP (`/scores`, `/sequence`), implementation 02 Phase 1 |
| [schemas.md](schemas.md) | The same: `MatrixScore`, `SequenceRequest`, `SparseMatrix` of `schemas/score.py` |
| [sequence-logic.md](sequence-logic.md) | The same: the parser behind `/sequence` (kept in the code as a test builder) |
| [grid-notation.md](grid-notation.md) | The vexflow-v2 renderer of the old sheet (`@aimpromptu/grid-notation`, `TimeScoreView`), implementation 03 Phase 10 |
| [time-matrix.md](time-matrix.md) | The same: the schema 2.0 payload it drew (`TimeScorePayload`, the ladder, passages, printed notes) and the `/time` routes that served it, implementation 03 Phase 10 |
