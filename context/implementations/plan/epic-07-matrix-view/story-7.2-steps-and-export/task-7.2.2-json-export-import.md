# Task 7.2.2 — JSON export and import

Every step view has a download button; the Input tab (Task 6.1.1) consumes the uploads.

## Subtask 7.2.2.1 — Export

Two formats per matrix (backend builds them on demand — dense is never stored server-side):

- dense: full 0/1/-1 grid + metadata (BPM, granularity, `matrixProcessingStep`, column headers, row temporal annotations)
- sparse: COO payload + same metadata; `sparse: true`

Two-hands exports carry `rMatrix`/`lMatrix` clearly labeled. One self-contained JSON = portable across sessions.

## Subtask 7.2.2.2 — Import

Upload endpoint validates against Task 1.3.1 schemas, normalizes via the validator, stores sparse-side, and loads it as the working artifact at its declared step.

## Acceptance

Round-trip: export dense and sparse, re-import both, grids identical.
