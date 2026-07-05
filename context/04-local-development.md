# Local development

Run backend and frontend in separate terminals. Both services must be up for the full UI.

## Prerequisites

- **Backend:** Python 3.12.13, [`uv`](https://docs.astral.sh/uv/) installed
- **Frontend:** Node.js (compatible with Vite 8 / npm lockfile)

## Backend

```bash
cd aitu-backend
uv sync
make serve
```

- Starts uvicorn at `http://127.0.0.1:8765` with `--reload`
- Uses `uv run python -m uvicorn aitu_backend.main:app` (avoids shebang truncation on long paths)
- Override host/port: `make serve HOST=0.0.0.0 PORT=9000`

**Verify:**

```bash
curl http://127.0.0.1:8765/health
# {"status":"ok"}

open http://127.0.0.1:8765/docs   # OpenAPI UI
```

**Sample data:** `GET /scores` reads `data/example-scores.json` next to `pyproject.toml`. Working
directory must be `aitu-backend/` (Makefile assumes this).

## Frontend

```bash
cd aitu-frontend
npm install
npm run dev
```

- Vite dev server (default `http://localhost:5173`)
- Expects backend at `http://127.0.0.1:8765` unless overridden

**Override API URL:**

```bash
VITE_AITU_API_URL=http://127.0.0.1:8765 npm run dev
```

No `.env` file is required today; the fallback in `App.tsx` matches the backend default.

## Full dev loop

1. Terminal 1: `cd aitu-backend && uv sync && make serve`
2. Terminal 2: `cd aitu-frontend && npm install && npm run dev`
3. Open the Vite URL in a browser — scores load from `GET /scores`
4. Use SequenceComposer to `POST /sequence` and preview new notation

## Build / lint (frontend)

```bash
cd aitu-frontend
npm run build    # tsc -b && vite build
npm run lint     # eslint .
npm run preview  # preview production build
```

## Notebooks (backend, optional)

Exploratory Jupyter notebooks live under `notebooks/<theme>/`. Not required for the web app. One
thematic subfolder per POC is the standing convention.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Frontend "failed to load scores" | Backend running? `curl /health`. CORS is open locally. |
| Wrong API host | Set `VITE_AITU_API_URL` (no trailing slash). |
| Backend import error | `uv sync` from `aitu-backend/`; module is `aitu_backend`. |
| Empty `/scores` | `data/example-scores.json` exists under `aitu-backend/`. |

## Where to look deeper

- Tech versions: [02-tech-stack.md](02-tech-stack.md)
- Services and ports: [03-services-overview.md](03-services-overview.md)
- Endpoint detail: [../documentation/services/backend/endpoints.md](../documentation/services/backend/endpoints.md)
- Sample data path: [07-database.md](07-database.md)
