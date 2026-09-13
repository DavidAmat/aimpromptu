# Notation and parsing — the text-notation MVP

How aitu-backend turns text frames into a sparse-COO score. The format contract is
[02-notation-spec.md](../music/notation-logic/02-notation-spec.md); this file covers backend
ownership only.

> **This path is the project's original seed and is no longer an entry point.** Text notation and
> matrix JSON were removed from Upload / Input in P4.2, for one reason: a sheet is written from
> recorded onsets and neither of those has any. `POST /sequence` still runs and is still correct.
>
> The parser is kept because it is self-contained and cheap, and because the 88-key tables it grew
> are now in `matrix/keys.py` and used by everything. **What the app actually does** is in
> [time-model.md](time-model.md).

## Input

`POST /sequence` accepts `sequence: list[str]` — one string per time frame. One line per frame. The compose UI that produced them was deleted with the tempo model;
see [`archive/superseded/compose-panel.md`](../archive/superseded/compose-panel.md).

Parsing is in `matrix/text_notation.py` (it was `sequence.py` before the Epic 1 restructure):

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

`build_grand_piano_rows()`, now in `matrix/keys.py` — `La-0`, `La#-0`, `Si-0`, then full chromatic octaves 1–7,
then `Do-8`. Mirrored in the frontend by `music/noteNames.ts`.

## Where to look deeper

- [02-notation-spec.md](../music/notation-logic/02-notation-spec.md) — full contract
- [sequence-logic.md](../../documentation/services/backend/sequence-logic.md) — function-level detail
- [schemas.md](../../documentation/services/backend/schemas.md) — Pydantic models
- [api.md](api.md) — `POST /sequence` request/response
