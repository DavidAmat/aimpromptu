# aitu-backend

Python/FastAPI service that parses custom text piano notation into a compact sparse-COO
JSON score. Notation-agnostic — emits no VexFlow; the frontend owns all rendering.

## Responsibilities

| Area | Module | Role |
|------|--------|------|
| Notation logic | `sequence.py` | Text parsing, onset normalization, sparse-COO builder (single source of truth). |
| API models | `schemas.py` | Pydantic: `SparseMatrix`, `MatrixScore`, `SequenceRequest` (camelCase JSON). |
| HTTP | `main.py` | `GET /health`, `GET /scores`, `POST /sequence`. |
| Data path | `paths.py` | Resolves `data/example-scores.json`. |

## Notation

The full contract lives in [shared/notation-spec.md](../shared/notation-spec.md).
Backend-specific parsing overview: [notation-and-parsing.md](notation-and-parsing.md).

## API

Three endpoints on `127.0.0.1:8765`. Overview: [api.md](api.md).

## Notebooks

Interactive POC demos live under `notebooks/<theme>/` — one thematic subfolder per POC
(e.g. `notebooks/dummy-matrix/`, `notebooks/88-keys-matrix/`). Do not deep-read them;
they import `aitu_backend` to stay in sync with the package.

## Run

```bash
cd aitu-backend && uv sync && make serve
```

See [04-local-development.md](../04-local-development.md).

## Where to look deeper

- [notation-and-parsing.md](notation-and-parsing.md) — text → sparse-COO overview
- [api.md](api.md) — HTTP surface
- [documentation/services/backend/](../../documentation/services/backend/) — endpoints,
  schemas, sequence logic, paths and data
- [shared/notation-spec.md](../shared/notation-spec.md) — the notation contract
