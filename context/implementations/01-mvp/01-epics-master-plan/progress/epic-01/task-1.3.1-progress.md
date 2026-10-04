# Task 1.3.1 — Matrix schemas · progress report

Status: **done**. Date: 2026-07-26.

## Summary

**`schemas/matrix.py`** — the canonical piano-matrix contracts:

| Model / constant | Contents |
|------------------|----------|
| `Granularity` | `redonda … semifusa` str enum, `.beats` (negra = 1.0) and `.seconds(bpm)` |
| `GRANULARITY_BEATS` | 4 / 2 / 1 / 0.5 / 0.25 / 0.125 / 0.0625 |
| `GRANULARITY_HIERARCHY` | coarse -> fine; Task 2.2.1 walks it one step at a time |
| `GRANULARITY_CODES` | `gr gb gn gc gsc gf gsf` + the reverse map (feeds Task 1.3.2's `v2_gn`) |
| `MatrixProcessingStep` | `raw / collapsed / clean / two-hands` |
| `Hand` | `single / left / right` |
| `ONSET / SUSTAIN / SILENCE` | `1 / -1 / 0` |
| `SparseCooMatrix` | 88 x N COO, validated |
| `KeyLabel` | `{es, en, row}` — the EN + ES header the Matrix tab shows |
| `PianoMatrixEnvelope` | the full export/import envelope |

`SparseCooMatrix` validates what the old `SparseMatrix` only documented: exactly 88 rows,
parallel array lengths, in-range `rows`/`cols`, and `onset[i] ∈ {rows[i], -1}`.

**`matrix/keys.py`** — the 88-key tables in one place: `build_grand_piano_rows()` (Spanish,
moved here from `text_notation.py`, which now imports it), `build_grand_piano_rows_en()`
(`A0` … `C8`), `es_to_en`, `note_to_row`, `row_to_midi` / `midi_to_row` (row 0 = MIDI 21),
and `MIDDLE_C_ROW` — the Appendix D two-hands threshold, ready for Task 2.4.1.

**`matrix/convert.py`** — `sparse_to_dense`, `dense_to_sparse`, `to_dense_envelope`,
`to_sparse_envelope`, `dense_column_headers`, `dense_row_timestamps`, `empty_dense`,
`time_step_for`.

**TS mirror** — `src/music/types.ts` gains `Granularity`, `GRANULARITY_BEATS`,
`GRANULARITY_HIERARCHY`, `GRANULARITY_CODES`, `MatrixProcessingStep`, `Hand`, `KeyLabel`,
`PianoMatrixEnvelope`, `ONSET`/`SUSTAIN`/`SILENCE`. `src/api/matrix.ts` no longer declares its
own copies — it imports and re-exports from `music/types.ts`, so there is exactly one TS
definition per backend model.

## The one design decision worth reading

**The dense and sparse forms are transposed relative to each other, deliberately.**

- Sparse COO stays **88 x N** (row = key, col = frame): the existing notation contract, and what
  `scipy.sparse` will persist in Task 1.4.1.
- Dense is **N x 88** (row = time frame, col = key).

The task file forced this: it asks the dense export to carry `columnHeaders` (note names EN + ES)
and `rowTimestamps`. Headers per *column* can only be key names if the columns are keys — which
also matches the Epic 7 grid ("key columns EN+ES, frame rows with timestamps"). `matrix/convert.py`
owns the flip and nothing else needs to know. Both the module docstring and the TS type carry an
explicit orientation warning, because this is the single easiest thing to get wrong later.

The envelope also gained `denseRMatrix` / `denseLMatrix`, absent from the task file: two-hands
matrices need a dense form too, and one `denseMatrix` field cannot hold both.

## Errors found and how they were solved

1. **`pydantic.mypy` `init_typed = true` rejects alias kwargs.** `PianoMatrixEnvelope(tempoBpm=60,
   …)` type-checks as `Missing named argument "tempo_bpm"` even though it works at runtime under
   `populate_by_name=True`. Rather than loosen the plugin, the tests now use **snake_case kwargs in
   Python and camelCase only in JSON payloads** — a better convention anyway. Later workers: build
   models with field names, or go through `model_validate({...camelCase...})`.
2. **`np.nonzero` ordering.** `dense_to_sparse` relies on `np.nonzero` returning row-major order,
   which on an N x 88 array is exactly frame-major = the `(col, row)` sort the COO contract
   requires. Pinned by `test_coo_arrays_come_back_sorted_by_column_then_row`, which feeds
   deliberately unsorted cells in and asserts sorted cells out.
3. **Duplicate key tables.** `text_notation.py` had its own `CHROMATIC_NOTES` and
   `build_grand_piano_rows`. Both now come from `matrix/keys.py`; `CHROMATIC_NOTES` remains as an
   alias so nothing breaks.

## Deviations from the task file

- Added `matrix/keys.py` (not requested) — EN names, MIDI mapping and the middle-C row had to live
  somewhere, and duplicating them per epic is exactly what this story exists to prevent.
- Added `denseRMatrix` / `denseLMatrix` (see above).
- `columnHeaders` is `list[KeyLabel]`, not `list[str]`: the task says "note names EN + ES", which
  needs two fields per key.
- The legacy `SparseMatrix` / `MatrixScore` in `schemas/score.py` are **untouched**. `/scores` and
  `/sequence` still use them. `SparseCooMatrix` is the same wire shape with real validation;
  Epic 9 decides whether `MatrixScore` folds into the envelope.

## Verification

```
pytest        # 32 passed (20 new in tests/test_matrix_schemas.py)
mypy          # Success: no issues found in 26 source files
flake8, black # clean
npx tsc -b, npm run lint   # clean
```

The acceptance round-trip is `test_envelope_round_trip_dense_sparse_dense_is_lossless`:
dense json -> model -> sparse json -> model -> dense json, asserting the grid, the 88 headers and
the timestamps all come back identical.

## Manual trial for the supervisor

No UI yet. To eyeball the contract:

```bash
cd aitu-backend && uv run python -c "
from aitu_backend.matrix.convert import to_dense_envelope
from aitu_backend.matrix.text_notation import sequence_to_sparse_payload
from aitu_backend.schemas.matrix import PianoMatrixEnvelope, SparseCooMatrix
m = SparseCooMatrix.model_validate(sequence_to_sparse_payload(['*Do-4','Do-4','*Re-4','*Mi-4']))
env = PianoMatrixEnvelope(tempo_bpm=60, time_step_seconds=0.25, granularity='semicorchea',
                          matrix_processing_step='clean', matrix=m)
d = to_dense_envelope(env)
print(d.row_timestamps)                       # [0.0, 0.25, 0.5, 0.75]
print([r[39] for r in d.dense_matrix])        # [1, -1, 0, 0]  -> row 39 is Do-4
"
```

## For the next worker

- **Task 1.3.2**: `GRANULARITY_CODES` already exists — import it, do not redefine the codes.
- **Task 1.4.1**: persist the **sparse** form. `scipy.sparse` wants 88 x N, which is what
  `SparseCooMatrix` already is; no transposition on the storage path.
- **Task 2.1.1**: `matrix/keys.py` is your key mapping; `MIDDLE_C_ROW` is the Task 2.4.1 threshold.
- **Task 2.2.1**: `GRANULARITY_HIERARCHY` is ordered coarse -> fine, so a collapse from
  semicorchea to negra is two steps backwards through it.
- Keep `src/music/types.ts` in step with `schemas/matrix.py` — they are one contract in two languages.
