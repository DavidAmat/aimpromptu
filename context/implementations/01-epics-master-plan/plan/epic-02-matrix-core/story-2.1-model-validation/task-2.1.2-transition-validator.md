# Task 2.1.2 — Transition validator

`matrix/validator.py`: enforce the per-row Markov transition rules. Runs after imports, edits, merges — any mutation.

## Subtask 2.1.2.1 — Rules

For each row, scanning columns left to right (initial state 0):

- from `0`: allowed next `0` or `1` (never `-1` — `[0, -1]` is impossible)
- from `1`: allowed next `1` (re-onset), `-1` (sustain) or `0` (release)
- from `-1`: allowed next `1`, `-1` or `0`

## Subtask 2.1.2.2 — API

- `validate(matrix) -> list[Violation]` with row (key name), column, found transition.
- `normalize(matrix) -> PianoMatrix` for tolerant ingestion: orphan `-1` promoted to `1` (mirrors the existing text-notation normalization), collisions resolved per the notation spec.
- Strict mode raises; used in tests and after user edits.

## Acceptance

Unit tests covering every legal/illegal pair plus normalization cases from `02-notation-spec.md`.
