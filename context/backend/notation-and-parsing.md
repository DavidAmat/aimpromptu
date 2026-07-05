# Notation and parsing

How aitu-backend turns text frames into a sparse-COO score. The format contract is
[shared/notation-spec.md](../shared/notation-spec.md); this file covers backend
ownership only.

## Input

`POST /sequence` accepts `sequence: list[str]` — one string per time frame. The
compose UI maps one line per frame; see [compose-panel.md](../frontend/compose-panel.md).

Parsing is in `sequence.py`:

- `parse_timeframe_notes(cell)` — splits on `||`, strips whitespace, reads leading `*`
  for onsets.
- Unknown note names → `ValueError` → HTTP 422.

## Onset normalization

`sequence_to_sparse_payload()` walks frames left to right, tracking `open_rows` (keys
still sounding from the previous frame):

1. Emit all onsets in the current frame (`onset[i] = rows[i]`).
2. For plain (sustain) tokens: skip if same row already onset this frame; skip if any
   onset exists anywhere in the frame (onset rule); else emit sustain (`onset[i] = -1`)
   only if the row was in `open_rows`; else promote to onset.

Cells are sorted by `(col, row)` before return.

## Output shape

`sequence_to_score()` wraps the sparse payload with metadata (`tempoBpm`,
`timeStepSeconds`, optional `title`, `lyrics`, `keySignature`):

- One hand: `matrix` only.
- Two hands: `r_matrix` from `sequence`, `l_matrix` from `leftSequence`; frame counts
  must match or `ValueError` → 422.

The `rows` note-name table is **not** included — the frontend rebuilds the canonical
88-key order.

## 88-key row order

`build_grand_piano_rows()` — `La-0`, `La#-0`, `Si-0`, then full chromatic octaves 1–7,
then `Do-8`. Mirrors `buildGrandPianoRows()` in the frontend.

## Where to look deeper

- [shared/notation-spec.md](../shared/notation-spec.md) — full contract
- [sequence-logic.md](../../documentation/services/backend/sequence-logic.md) — function-level detail
- [schemas.md](../../documentation/services/backend/schemas.md) — Pydantic models
- [api.md](api.md) — `POST /sequence` request/response
