> Context: [notation-and-parsing.md](../../../context/backend/notation-and-parsing.md) · [notation-spec.md](../../../context/music/notation-logic/02-notation-spec.md)

# Sequence logic — the text-notation parser

All text-notation logic lives in `aitu-backend/src/aitu_backend/matrix/text_notation.py` (it was
`sequence.py` before the Epic 1 restructure). Single source of truth for text parsing, onset
normalization and sparse-COO construction.

> **This serves `POST /sequence` only.** Text notation is no longer an entry point in the app —
> see the note at the top of [schemas.md](schemas.md). The parser is kept because it is correct,
> self-contained and cheap, and because the 88-key tables it grew are now in `matrix/keys.py` and
> used everywhere.

The 88-key tables moved to `aitu-backend/src/aitu_backend/matrix/keys.py`, where the whole project
now reads them. `text_notation.py` re-exports `CHROMATIC_NOTES` (as `CHROMATIC_ES`) and
`build_grand_piano_rows()` from there, so the names below still resolve.

## Constants

```python
CHROMATIC_NOTES = [
    "Do", "Do#", "Re", "Re#", "Mi", "Fa",
    "Fa#", "Sol", "Sol#", "La", "La#", "Si",
]
```

## build_grand_piano_rows()

Returns 88 strings: `La-0`, `La#-0`, `Si-0`, then for octaves 1–7 every chromatic note,
then `Do-8`. Asserts `len(rows) == 88`.

## parse_timeframe_notes(cell: str)

Returns `list[tuple[str, bool]]` — `(note_name, is_onset)`.

- Blank/whitespace → `[]`.
- Split on `||`, strip each token.
- Leading `*` → onset (`True`); otherwise sustain (`False`).
- Example: `"*Do-3 || Mi-3"` → `[("Do-3", True), ("Mi-3", False)]`.

Does not validate note names.

## sequence_to_sparse_payload(sequence, rows=None)

Core builder. Returns dict:

```python
{
    "format": "binary-coo",
    "shape": [88, len(sequence)],
    "rows": [...],
    "cols": [...],
    "onset": [...],
}
```

### Per-frame algorithm

For each column `col` and cell string:

1. Parse items → `(row_index, is_onset)`; unknown note → `ValueError`.
2. Partition into `onset_rows` and `plain_rows`.
3. `has_onset = bool(onset_rows)`.
4. **Onsets:** for each `r` in `onset_rows`, append `(col, r, r)`; add `r` to `next_open`.
5. **Sustains:** for each `r` in `plain_rows`:
   - Skip if `r in onset_rows` (already emitted as onset).
   - Skip if `has_onset` (onset rule — foreign onset ends all sustains).
   - If `r in open_rows`: append `(col, r, -1)`; add to `next_open`.
   - Else: promote to onset `(col, r, r)`; add to `next_open`.
6. `open_rows = next_open`.

Sort cells by `(col, row)`; unzip into parallel arrays.

### Onset rule examples

| Frames | Result |
|--------|--------|
| `*Re-4`, `Re-4`, `Re-4` | One note, 3 columns; cols 1–2 have `onset=-1`. |
| `*Re-4`, `*Re-4`, `*Re-4`, `*Re-4` | Four separate onsets. |
| `Re-4` (no prior onset) | Promoted to onset at col 0. |
| `*Do-4`, `Re-4` (sustain Re while Do onset) | Re sustain skipped (has_onset); only Do onset at col 0. |

## sequence_to_score(...)

Builds camelCase score dict for the frontend.

Parameters: `sequence`, `tempo_bpm`, `time_step_seconds`, optional `title`, `lyrics`,
`key_signature`, optional `left_sequence`.

Base fields always set: `title`, `tempoBpm`, `timeStepSeconds`, `matrixEncoding`:
`"sparse-coo"`, `lyrics`, `keySignature`.

**One hand** (`left_sequence is None`):

```python
score["matrix"] = sequence_to_sparse_payload(sequence)
```

**Two hands:**

```python
if len(left_sequence) != len(sequence):
    raise ValueError(...)
score["r_matrix"] = sequence_to_sparse_payload(sequence)
score["l_matrix"] = sequence_to_sparse_payload(left_sequence)
```

Does not include `rows` note table.
