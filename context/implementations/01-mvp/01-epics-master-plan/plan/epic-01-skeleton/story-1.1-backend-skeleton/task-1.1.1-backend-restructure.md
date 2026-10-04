# Task 1.1.1 — Backend restructure

Reshape `aitu-backend/src/aitu_backend/` so later epics have an obvious home for their code. Keep the service functional at every step (`/health`, `/scores`, `/sequence` keep working).

## Subtask 1.1.1.1 — Module layout

Create packages (empty `__init__.py` plus a short docstring each):

```text
src/aitu_backend/
  api/            # FastAPI routers, one file per section (audio, matrix, notation, library, youtube)
  matrix/         # piano matrix model, granularity, cleaning, hands, ops (Epic 2)
  audio/          # upload, recording ingest, waveform, youtube (Epic 3)
  transcription/  # audio -> note events -> matrix (Epic 4)
  storage/        # artifact repository, metadata files, paths (Epics 1.4 and 5)
  notation/       # matrix -> VexFlow-ready score format (Epic 9)
  schemas/        # Pydantic models (Story 1.3)
```

`main.py` becomes a thin app factory that includes routers from `api/`.

## Subtask 1.1.1.2 — Migrate existing logic

- Move `sequence.py` parsing into `matrix/text_notation.py` (it stays the single source of truth for text notation parsing).
- Move current `schemas.py` content into `schemas/score.py`.
- Keep `paths.py` but move into `storage/paths.py`; update imports.
- `data/example-scores.json` and `GET /scores` keep working (they become the seed of the future library).

## Subtask 1.1.1.3 — Router wiring

One APIRouter per `api/` file with a URL prefix (`/audio`, `/matrix`, `/notation`, `/library`, `/youtube`). Add placeholder endpoints returning `501` bodies where the real implementation belongs to a later epic, so the frontend shell can already be wired against real routes.

## Acceptance

- `uv run pytest` (add a minimal test for `/health` and `/sequence` round-trip).
- `curl /health` ok; existing frontend page still renders scores.
