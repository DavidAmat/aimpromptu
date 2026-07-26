> Context: [api.md](../../../context/backend/api.md) · [notation-spec.md](../../../context/music/notation-logic/02-notation-spec.md.md)

# Endpoints

FastAPI app: `aitu-backend/src/aitu_backend/main.py`. Title: "AImpromptu Backend API".

## GET /health

**Response** `200`:

```json
{ "status": "ok" }
```

No parameters. Used for liveness checks.

## GET /scores

Reads `data/example-scores.json` via `scores_json_path()`.

**Response** `200`: JSON array of `MatrixScore` objects (camelCase, `null` fields omitted).

**Errors:**

| Status | Detail |
|--------|--------|
| 404 | File missing — message suggests running `notebooks/dummy-matrix/01-generate-dummy-matrix.ipynb` or creating the file. |
| 500 | `JSONDecodeError`, root is not an array, or `MatrixScore.model_validate` fails. |

## POST /sequence

Converts written time-frame notation into a sparse 88-key score.

### Request body

Content-Type: `application/json`. Model: `SequenceRequest`.

```json
{
  "sequence": ["*Do-4 || *Mi-4", "*Re-4", "Re-4"],
  "tempoBpm": 60,
  "timeStepSeconds": 0.5,
  "title": "My passage",
  "lyrics": ["Ho", "la", "la"],
  "keySignature": "G",
  "leftSequence": ["*Do-3", "*Re-3", "Re-3"]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `sequence` | `string[]` | yes | One entry per time frame. |
| `tempoBpm` | `number` | yes | |
| `timeStepSeconds` | `number` | yes | |
| `title` | `string` | no | |
| `lyrics` | `string[]` | no | One per frame; `""` = no syllable. |
| `keySignature` | `string` | no | VexFlow spec (`C`, `G`, `Bb`, …). |
| `leftSequence` | `string[]` | no | Left hand; same length as `sequence`. |

### Response `200`

`MatrixScore` — same shape as `/scores` items. Fields see [schemas.md](schemas.md).

### Errors `422`

Raised when `sequence_to_score()` raises `ValueError`:

| Cause | Example detail |
|-------|----------------|
| Unknown note | `Unknown note 'Xy-9'. Expected one of: La-0 ... Do-8` |
| Hand frame mismatch | `Right and left hand must have the same number of time frames so they align (8 vs 7).` |

Pydantic request validation errors (missing required fields, wrong types) also return 422
with FastAPI's default body.

### Response validation

The handler builds a dict then `MatrixScore.model_validate(payload)`. If the payload
violates hand rules (e.g. both `matrix` and `r_matrix`), validation fails with 500 —
should not occur from `sequence_to_score()` itself.

## CORS

```python
allow_origins=["*"]
allow_credentials=False
allow_methods=["*"]
allow_headers=["*"]
```

Local POC only.
