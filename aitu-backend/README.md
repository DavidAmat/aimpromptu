# aitu-backend

FastAPI service: piano matrix engine, audio ingestion and score documents for **aitu-frontend**.

**Documentation:** [context/backend/](../../context/backend/README.md)

```bash
uv sync && make serve   # http://127.0.0.1:8765
```

Interactive API docs: `/docs`.

## Module layout

```text
src/aitu_backend/
  api/            # FastAPI routers, one file per section
  matrix/         # piano matrix model, granularity, cleaning, hands, ops
  audio/          # upload, recording ingest, waveform, youtube
  transcription/  # audio -> note events -> matrix
  storage/        # paths, artifact repository, metadata files
  notation/       # matrix -> VexFlow-ready score format
  schemas/        # Pydantic models (camelCase on the wire)
  progress.py     # ProgressReporter: one code path for tqdm and SSE
  main.py         # thin app factory
```

Endpoints belonging to a later epic already exist and answer `501` naming that epic,
so the frontend can be wired against real routes.

## Development

```bash
uv sync            # install, including the dev dependency group
make hooks         # one-time: uv run pre-commit install
make lint          # flake8 + mypy
make format        # black
make test          # pytest
```

Pre-commit config lives at the repo root (`../.pre-commit-config.yaml`) and runs
black, flake8 and mypy over `aitu-backend/`. Commits go straight to `master`, so the
hooks are the only gate — install them before your first commit.

### Progress convention

Anything expected to run longer than ~10 s (transcription, long recomputes) takes a
`ProgressReporter` from `aitu_backend.progress` and reports through it. `TqdmProgress`
renders a terminal bar, `CallbackProgress` feeds the SSE stream, `MultiProgress` does
both, `NullProgress` is the silent default. Never call `tqdm` directly in feature code.
