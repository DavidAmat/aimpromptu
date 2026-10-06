# aitu-backend

FastAPI service. It runs the piano transcription model (MuScriptor `large`, on the GPU), stores the
one file that cannot be recreated, and derives everything else from it on demand: the wall-clock
matrix, the distribution of gaps, the figure of every note, and the score payload the browser draws.
It also keeps a revision per step of a piece, so the flow page knows which step is out of date.

It does no drawing.

**Documentation:** [context/backend/](../context/backend/README.md) ·
the model: [time-model.md](../context/backend/time-model.md) ·
the engine: [muscriptor.md](../context/backend/muscriptor.md) ·
the steps: [pieces-and-revisions.md](../context/backend/pieces-and-revisions.md)

In the container (the usual way, from the repository root): `make up`, and `make test-backend` for
the tests. Natively:

```bash
uv sync --extra muscriptor && make serve   # http://127.0.0.1:8765
```

Interactive API docs: `/docs`.

## Module layout

```text
src/aitu_backend/
  api/            # FastAPI routers, one file per section
  audio/          # upload, recording ingest, waveform, youtube, cuts and the frame table
  transcription/  # engines (MuScriptor first), the GPU queue, the live stream, the lag
                  # correction, filters, events -> the wall-clock matrix, jobs, saved hands
  pieces/         # the state of each step of a piece; the note operations
  pmn/            # the piano matrix notation: the sparse form and every adapter
  matrix/         # frame <-> ms, gaps, peaks, the figure ladder, passages, bands
  hands/          # which hand plays each onset: a beam search + a gated second pass
  notation/       # figures, tresillos, trills
  editing/        # the replacement splice, composing, staging, history
  storage/        # every filesystem path in one module; the project bundle, the audio store
  db/             # SQLAlchemy models, Alembic migrations, the master user, backup/check/reindex
  schemas/        # Pydantic models (camelCase on the wire)
  progress.py     # ProgressReporter: one code path for tqdm and SSE
  config.py       # the AITU_* settings
  main.py         # thin app factory
```

**One file of notes is stored per part:** `parts/<partId>/notes.pmn` in the project bundle, the
engine's notes with ids, hands and revisions. Beside it are `sheet.json`, what the reader decided,
and `timeline.json`, which audio the part plays. Everything else is derived on every request,
which is why the column length is a query parameter rather than a migration.

Everything the app stores is in `.database/` at the repository root (`AITU_DATABASE_DIR` moves it):
the SQLite file `aitu.sqlite`, the project bundles, and the audio store `audio/<sha256>.<ext>`.
Layout and the `make db-backup`, `db-restore`, `db-check` and `db-reindex` targets:
[context/07-database.md](../context/07-database.md). `data/` is the store before implementation 02,
Phase 3, read only by the migration ([data/README.md](data/README.md)).

## Development

```bash
uv sync            # install, including the dev dependency group
make hooks         # one-time: uv run pre-commit install
make lint          # flake8 + mypy
make format        # black
make test          # pytest (in the container: make test-backend from the root) — 1,023 passing,
                   # 1 known failure (test_the_worked_example_at_00_46_prints_three_equal_corcheas)
```

`pyproject.toml` sets `pythonpath = ["src", "."]`. The `"."` was needed by
`tests/test_migration.py`, which imported `scripts.migrate_to_time_matrix`; implementation 02,
Phase 3 deleted both. Every test has its own temporary `.database/` (`tests/conftest.py`), so the
tests never touch the real one.

Pre-commit config lives at the repo root (`../.pre-commit-config.yaml`) and runs
black, flake8 and mypy over `aitu-backend/`. Each phase of implementation 02 is built on its own
`feat/phase-N` branch and merged into `master` after the user's check; the hooks are the only
automatic gate, so install them before your first commit.

### Progress convention

Anything expected to run longer than ~10 s (transcription, long recomputes) takes a
`ProgressReporter` from `aitu_backend.progress` and reports through it. `TqdmProgress`
renders a terminal bar, `CallbackProgress` feeds the SSE stream, `MultiProgress` does
both, `NullProgress` is the silent default. Never call `tqdm` directly in feature code.
