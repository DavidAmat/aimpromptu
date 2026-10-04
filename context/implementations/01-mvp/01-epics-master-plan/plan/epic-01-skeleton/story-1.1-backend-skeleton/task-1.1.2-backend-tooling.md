# Task 1.1.2 — Backend tooling

CI hygiene for a repo where we commit straight to `master`.

## Subtask 1.1.2.1 — Pre-commit

Add `.pre-commit-config.yaml` at repo root running on `aitu-backend/`:

- `black` (default config)
- `flake8` with a config ignoring minor noise (long lines E501, E203, W503)
- `mypy` (pydantic plugin enabled, start permissive: `ignore_missing_imports = true`)

Add the tool configs to `pyproject.toml` where possible. Document `uv run pre-commit install` in the backend README.

## Subtask 1.1.2.2 — Progress convention

Any backend processing expected to take more than ~10 seconds (transcription, matrix recompute of long audios) must report progress:

- wrap loops with `tqdm` for terminal visibility
- expose the same progress via a small `ProgressReporter` interface that Epic 4 will stream to the UI (SSE), so tqdm and UI streaming share one code path

## Subtask 1.1.2.3 — Makefile targets

Add `make lint` (flake8 + mypy), `make format` (black), `make test` (pytest). Keep `make serve` as is.

## Acceptance

Pre-commit runs clean on the restructured codebase; hooks fire on commit.
