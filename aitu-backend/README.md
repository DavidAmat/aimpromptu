# aitu-backend

FastAPI service. It runs the piano transcription model, stores the one file that cannot be
recreated, and derives everything else from it on demand: the wall-clock matrix, the distribution
of gaps, the figure of every note, and the score payload the browser draws.

It does no drawing.

**Documentation:** [context/backend/](../context/backend/README.md) ·
the model: [time-model.md](../context/backend/time-model.md)

```bash
uv sync && make serve   # http://127.0.0.1:8765
```

Interactive API docs: `/docs`.

## Module layout

```text
src/aitu_backend/
  api/            # FastAPI routers, one file per section
  audio/          # upload, recording ingest, waveform, youtube
  transcription/  # engines, filters, events -> the wall-clock matrix, jobs
  matrix/         # frame <-> ms, gaps, peaks, the figure ladder, passages, bands
  hands/          # which hand plays each onset: a beam search + a gated second pass
  notation/       # figures, tresillos, trills
  editing/        # the replacement splice, composing, staging, history
  storage/        # every filesystem path in one module; playground, library
  schemas/        # Pydantic models (camelCase on the wire)
  progress.py     # ProgressReporter: one code path for tqdm and SSE
  main.py         # thin app factory
```

**One file is stored per piece** — `data/audio/<uuid>/matrices/events.json`, the engine's notes in
seconds — plus `rhythm.json`, what the reader decided. Everything else is derived on every request,
which is why the column length is a query parameter rather than a migration.

## Development

```bash
uv sync            # install, including the dev dependency group
make hooks         # one-time: uv run pre-commit install
make lint          # flake8 + mypy
make format        # black
make test          # pytest — 769 passing
```

`pyproject.toml` sets `pythonpath = ["src", "."]`. The `"."` is load-bearing:
`tests/test_migration.py` imports `scripts.migrate_to_time_matrix` and `scripts/` has no
`__init__.py`, so without it collection fails before a single test runs.

Pre-commit config lives at the repo root (`../.pre-commit-config.yaml`) and runs
black, flake8 and mypy over `aitu-backend/`. Commits go straight to `master`, so the
hooks are the only gate — install them before your first commit.

### Progress convention

Anything expected to run longer than ~10 s (transcription, long recomputes) takes a
`ProgressReporter` from `aitu_backend.progress` and reports through it. `TqdmProgress`
renders a terminal bar, `CallbackProgress` feeds the SSE stream, `MultiProgress` does
both, `NullProgress` is the silent default. Never call `tqdm` directly in feature code.
