# Services overview

Two deployable services in the monorepo (`aitu-backend/`, `aitu-frontend/`). Same git root as docs;
not separate repos. The frontend calls the backend over HTTP on localhost.

## aitu-backend

| Property | Value |
|----------|-------|
| Stack | Python 3.12, FastAPI, Pydantic 2, uvicorn |
| Module | `aitu_backend` under `src/aitu_backend/` |
| Default bind | `127.0.0.1:8765` (`HOST` / `PORT` in Makefile) |
| Role | Parse custom text notation → sparse-COO JSON score |

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness (`{"status":"ok"}`) |
| GET | `/scores` | List scores from `data/example-scores.json` |
| POST | `/sequence` | Parse request body → one `MatrixScore` |
| — | `/docs` | OpenAPI (FastAPI auto) |

**Key modules:** `sequence.py` (notation logic), `schemas.py` (models), `main.py` (app), `paths.py`
(resolves `data/example-scores.json` relative to the `aitu-backend/` service root).

**Does not:** render staff notation, talk to VexFlow, or persist user submissions (returns JSON only).

## aitu-frontend

| Property | Value |
|----------|-------|
| Stack | React 19, TypeScript, Vite 8, VexFlow 5 |
| Dev server | Vite default (typically `http://localhost:5173`) |
| API base | `VITE_AITU_API_URL` or fallback `http://127.0.0.1:8765` |

**Role:** Fetch scores (`GET /scores`), optionally compose new ones (`POST /sequence`), decode sparse
matrices, render sheet music with VexFlow.

**UI areas:**

| Component | Responsibility |
|-----------|----------------|
| `App.tsx` | Load scores, global layout state (spacing, lyrics size) |
| `ScoreStack` | List loaded scores |
| `LayoutControls` | Spacing / lyrics inputs |
| `SequenceComposer` | Text input → POST /sequence |
| `PianoSheet` | VexFlow rendering |
| `src/music/*` | Types, 88-key map, matrix→notation pipeline |

**Does not:** parse raw text notation (backend only) or define the wire schema (consumes backend JSON).

## How they connect

```
Browser (Vite dev server)
    │  fetch GET /scores, POST /sequence
    ▼
aitu-backend :8765
    │  reads/writes data/example-scores.json (GET only from file; POST returns inline)
    ▼
JSON MatrixScore → aitu-frontend matrixToNotation → PianoSheet (VexFlow canvas/SVG)
```

CORS on the backend is open (`allow_origins=["*"]`) for local development.

## Score shapes

- **One hand:** `matrix` field (treble clef).
- **Two hands:** `r_matrix` (treble) + `l_matrix` (bass); equal `shape[1]` (frame count). Mutually
  exclusive with `matrix`.

Full contract: [shared/notation-spec.md](shared/notation-spec.md).

## Where to look deeper

- Local dev loop: [04-local-development.md](04-local-development.md)
- Backend overview: [backend/README.md](backend/README.md), [backend/api.md](backend/api.md)
- Frontend overview: [frontend/README.md](frontend/README.md)
- Endpoint detail: [../documentation/services/backend/endpoints.md](../documentation/services/backend/endpoints.md)
- Component detail: [../documentation/services/frontend/components.md](../documentation/services/frontend/components.md)
