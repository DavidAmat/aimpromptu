# HTTP API

FastAPI app in `main.py`. Default `127.0.0.1:8765`; interactive docs at `/docs`.
CORS allows all origins (local POC).

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness — `{"status": "ok"}`. |
| `GET` | `/scores` | Load persisted scores from `data/example-scores.json`. |
| `POST` | `/sequence` | Convert text notation → `MatrixScore` (same shape as `/scores` items). |

## POST /sequence (overview)

Request body (`SequenceRequest`, camelCase):

| Field | Required | Notes |
|-------|----------|-------|
| `sequence` | yes | Right hand / one-hand frames. |
| `tempoBpm` | yes | |
| `timeStepSeconds` | yes | |
| `title` | no | |
| `lyrics` | no | One entry per frame. |
| `keySignature` | no | VexFlow spec. |
| `leftSequence` | no | Left hand (bass); same frame count as `sequence`. |

Returns `MatrixScore` with `response_model_exclude_none=True`.

422 cases: unknown notes, mismatched hand frame counts, invalid hand matrix combination
(enforced again by `MatrixScore` validator on response).

## GET /scores errors

| Status | Cause |
|--------|-------|
| 404 | `data/example-scores.json` missing. |
| 500 | Invalid JSON, not an array, or Pydantic validation failure. |

## Where to look deeper

- [endpoints.md](../../documentation/services/backend/endpoints.md) — params, 422 detail, response fields
- [schemas.md](../../documentation/services/backend/schemas.md) — model definitions
- [paths-and-data.md](../../documentation/services/backend/paths-and-data.md) — scores file path
- [shared/notation-spec.md](../shared/notation-spec.md) — notation contract
