# Database

No database. Scores are served from a single JSON file on disk.

## File store

| Property | Value |
|----------|-------|
| Path | `aitu-backend/data/example-scores.json` |
| Resolved by | `paths.scores_json_path()` in `paths.py` (repo root = parent of `src/`) |
| Consumed by | `GET /scores` in `main.py` |
| Format | JSON array of `MatrixScore` objects (camelCase fields) |

`POST /sequence` returns a score in the response body; it does **not** append to this file.

## Schema ownership

Pydantic models in `schemas.py` define the canonical shape. Frontend mirrors types in `src/music/types.ts`.
Field-level detail: [../documentation/services/backend/schemas.md](../documentation/services/backend/schemas.md).

## Migration policy

None — no DDL, no migrations. To add sample scores, edit `example-scores.json` manually or regenerate
via notebooks/API during development.

## Where to look deeper

- Path resolution: [../documentation/services/backend/paths-and-data.md](../documentation/services/backend/paths-and-data.md)
- Score contract: [shared/notation-spec.md](shared/notation-spec.md)
