# Task 1.3.1 — Matrix schemas

Canonical data contracts for the piano matrix, defined once in Pydantic (`schemas/matrix.py`) and mirrored in TS (`src/music/types.ts`). camelCase on the wire (Pydantic aliases), as today.

Read first: `context/music/notation-logic/01-matrix-notation-logic.md` (including appendices) and `context/music/notation-logic/02-notation-spec.md`.

## Subtask 1.3.1.1 — PianoMatrix model

- Shape 88 x N; rows are keys `La-0` … `Do-8` (canonical order rebuilt on both sides).
- Cell semantics: `1` onset, `-1` sustain, `0` silence. Wire format stays sparse COO (`rows`, `cols`, `onset` where `onset[i] = rows[i]` for onset, `-1` for sustain), matching the existing contract.
- Fields: `format`, `shape`, `rows`, `cols`, `onset`.

## Subtask 1.3.1.2 — Matrix envelope metadata

Every exported/imported matrix JSON carries:

- `tempoBpm`, `timeStepSeconds`, `granularity` (one of `redonda|blanca|negra|corchea|semicorchea|fusa|semifusa`)
- `matrixProcessingStep`: `raw | collapsed | clean | two-hands`
- `sparse`: bool — whether the payload is sparse COO or a dense 0/1/-1 grid (`denseMatrix` field)
- `columnHeaders` (note names EN + ES) and `rowTimestamps` optional convenience fields for the dense export
- for two-hands: `rMatrix` + `lMatrix` instead of `matrix` (equal `shape[1]`)

## Subtask 1.3.1.3 — TS mirror and converters

- Mirror types in `src/music/types.ts`.
- Backend helpers: sparse<->dense conversion, plus (de)serialization used by download/upload endpoints in Epic 7.

## Acceptance

Round-trip test: dense json -> model -> sparse json -> model -> dense json is lossless.
