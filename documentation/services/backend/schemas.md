> Context: [notation-and-parsing.md](../../../context/backend/notation-and-parsing.md) · [notation-spec.md](../../../context/shared/notation-spec.md)

# Schemas

Pydantic models in `aitu-backend/src/aitu_backend/schemas.py`. JSON uses camelCase via
field aliases; `populate_by_name=True` accepts both forms on input.

## SparseMatrix

Binary matrix in COO form, sorted by `(column, row)`.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `format` | `"binary-coo"` | `"binary-coo"` | |
| `shape` | `int[]` | — | `[rowCount, columnCount]`; rowCount = 88. |
| `rows` | `int[]` | — | Row index of each active cell. |
| `cols` | `int[]` | — | Column index of each active cell. |
| `onset` | `int[]` | — | `rows[i]` for onset; `-1` for sustain. |

All three arrays must have equal length. Only active (value 1) cells are listed.

## MatrixScore

Sparse score plus rendering metadata. Frontend type mirror: `aitu-frontend/src/music/types.ts`.

| Field | JSON alias | Type | Notes |
|-------|------------|------|-------|
| `title` | `title` | `string?` | |
| `tempo_bpm` | `tempoBpm` | `float` | Required. |
| `time_step_seconds` | `timeStepSeconds` | `float` | Required. |
| `rows` | `rows` | `string[]?` | Optional note table; backend omits it. |
| `matrix_encoding` | `matrixEncoding` | `string` | Default `"sparse-coo"`. |
| `matrix` | `matrix` | `SparseMatrix?` | One hand (treble). |
| `r_matrix` | `r_matrix` | `SparseMatrix?` | Two hands — right/treble. |
| `l_matrix` | `l_matrix` | `SparseMatrix?` | Two hands — left/bass. |
| `lyrics` | `lyrics` | `string[]?` | One per time frame. |
| `key_signature` | `keySignature` | `string?` | VexFlow key spec. |

### Hand validation (`_check_hands`)

Exactly one form must be present:

- **One hand:** `matrix` set; `r_matrix` and `l_matrix` absent.
- **Two hands:** both `r_matrix` and `l_matrix` set; `matrix` absent.

If `r_matrix.shape[1] != l_matrix.shape[1]` → `ValueError` (misaligned frame counts).

`one_hand == two_hand` (both true or both false) → `ValueError`:
`Provide either matrix (one hand) or both r_matrix and l_matrix (two hands), never both or neither.`

## SequenceRequest

`POST /sequence` body.

| Field | JSON alias | Type | Required |
|-------|------------|------|----------|
| `sequence` | `sequence` | `string[]` | yes |
| `tempo_bpm` | `tempoBpm` | `float` | yes |
| `time_step_seconds` | `timeStepSeconds` | `float` | yes |
| `title` | `title` | `string?` | no |
| `lyrics` | `lyrics` | `string[]?` | no |
| `key_signature` | `keySignature` | `string?` | no |
| `left_sequence` | `leftSequence` | `string[]?` | no |

When `leftSequence` is omitted, `sequence_to_score()` emits `matrix` only. When present,
`sequence` → `r_matrix`, `leftSequence` → `l_matrix`.

## Example one-hand score

```json
{
  "title": "Sample",
  "tempoBpm": 60,
  "timeStepSeconds": 0.5,
  "matrixEncoding": "sparse-coo",
  "matrix": {
    "format": "binary-coo",
    "shape": [88, 8],
    "rows": [40, 44, 44, 47],
    "cols": [0, 0, 1, 2],
    "onset": [40, 44, -1, 47]
  },
  "keySignature": "C"
}
```

Row indices map to canonical 88-key order (`Do-4` ≈ row 40 depending on frame content).
