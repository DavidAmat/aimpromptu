# Services overview

Two deployable services in the monorepo (`aitu-backend/`, `aitu-frontend/`) and one library in a
sibling checkout. Same git root as the docs; not separate repos. Since implementation 08 both
services run in containers on the Ubuntu machine (`compose.yaml`), and the browser on the Mac reaches
them through one SSH tunnel to the frontend's port; the frontend passes `/api` to the backend.

## aitu-backend

| Property | Value |
|---|---|
| Stack | Python 3.12, FastAPI, Pydantic 2, uvicorn, numpy, scipy, PyTorch with CUDA, SQLAlchemy 2 and Alembic over SQLite |
| Module | `aitu_backend` under `src/aitu_backend/` |
| Container | `backend` (`aimpromptu-backend:dev`), the GPU reserved, published on `127.0.0.1:8765` |
| Natively | `127.0.0.1:8765` (`AITU_HOST` / `AITU_PORT`) |
| Data | `.database/` at the repository root (`AITU_DATABASE_DIR`), mounted at `/database` in the container: [07-database.md](07-database.md) |
| Role | Run MuScriptor on the GPU, store the recorded notes, keep the revisions of each step, derive the score |

**Packages:**

| Package | Role |
|---|---|
| `api/` | One router per product section; `main.py` is a thin factory |
| `audio/` | Upload, browser recording, YouTube, ffmpeg normalisation, waveforms, the cuts and the frame table, the edited audio |
| `transcription/` | Engines (MuScriptor, ByteDance, Transkun), the model registry, the GPU queue, the live stream, the lag correction, the filters, events to matrix, the split cache, the saved hands |
| `pieces/` | The state of each step of a piece, and the note operations ([backend/pieces-and-revisions.md](backend/pieces-and-revisions.md)) |
| `pmn/` | The piano matrix notation: the sparse form and every adapter |
| `matrix/` | Frame ↔ ms, gaps, peaks, the figure ladder, passages, figure bands |
| `hands/` | Which hand plays each onset: a beam search with a gated second pass |
| `notation/` | Figures, tresillos, trills |
| `editing/` | The replacement splice, composing, staging, history |
| `storage/` | Every filesystem path in one module; the project bundle, the audio store |
| `db/` | The SQLite tables, the Alembic migrations, the master user, the backup, check and reindex tools |
| `schemas/` | Pydantic contracts, camelCase on the wire, mirrored in TypeScript |

**Endpoints:** `/health`, `/audio`, `/matrix`, `/pieces`, `/time`, `/audio/{uuid}/edits`, `/projects`,
`/youtube`, `/video`, `/frame-examples`. (The text-notation MVP `/scores` and `/sequence` was deleted
in implementation 02, Phase 1, and the old Piano Library router `/library` in Phase 3.) Table in
[backend/api.md](backend/api.md), detail in
[`documentation/services/backend/endpoints.md`](../documentation/services/backend/endpoints.md).

**Does not:** draw anything, or decide how a page looks. It decides what each note is called and
where in time it sits.

## aitu-frontend

| Property | Value |
|---|---|
| Stack | React 19, TypeScript, Vite 8, MUI 9 |
| Container | `frontend` (`aimpromptu-frontend:dev`), the Vite development server, published on `127.0.0.1:5173` |
| Dev server | `http://localhost:5173` (pinned with `--strictPort`); from the Mac through the tunnel |
| API base | `/api`, which the Vite server passes to the backend; `VITE_AITU_API_URL` overrides it |
| Role | Every screen, and every pixel of the sheet |

**Sections** (a left sidebar): **Projects** (each project: Source, Audio, Notes, Hands, Sheet;
[frontend/flow-page.md](frontend/flow-page.md)) and **Lab** (the video reader's pages).

**Does not:** decide any note's name — the figures arrive from the backend and are passed straight
through to the renderer.

## @aimpromptu/grid-notation

| Property | Value |
|---|---|
| Location | The sibling checkout `../vexflow-v2` |
| Install | `"file:../../vexflow-v2"` — npm makes it a symlink |
| Version | 0.42.0 |
| Role | All engraving: beams, stems, accidentals, clefs, line breaks, pagination |

It exists because VexFlow lays notes out from tick arithmetic inside measures, and a wall-clock
matrix has neither. **Rebuild it after pulling** — npm does not build a linked dependency, and a
stale `dist/` fails silently. The frontend image builds its own copy, so `make up` after a change
there. See [frontend/rendering.md](frontend/rendering.md).

## How they connect

```
Browser on the Mac ──ssh -L 5173──▶ frontend container (Vite, :5173)
                                      │  /api/* passed to the backend
    GET  /pieces/{id}/status      which steps are ready     → the step tabs of a project
    PUT  /audio/{id}/cuts         the selected region       → the Audio tab
    POST /matrix/transcribe       + SSE chunk messages      → the live Notes tab
    GET/PATCH /pieces/{id}/notes  the notes, as operations  → the Notes and Hands tabs
    GET  /time/{id}/score         the drawable payload      → the Sheet tab
                                      ▼
                         backend container (:8765, the GPU)
    reads and writes .database/: aitu.sqlite, the project bundles (project.json,
    parts/<id>/notes.pmn, sheet.json, timeline.json) and audio/<sha256>.<ext>
                                      ▼
TimeScorePayload ──▶ TimeScoreView ──▶ @aimpromptu/grid-notation ──▶ SVG
```

Nothing is drawn from a stored grid, because there is no stored grid.

CORS on the backend is open (`allow_origins=["*"]`) for local development; through the proxy the
page and the backend share one origin anyway.

## Long work

Transcription takes 20 to 50 seconds. `POST /matrix/transcribe` answers `202` with a job id, the
job waits for the GPU (one transcription at a time), and the browser follows a Server-Sent Events
stream that carries the notes as MuScriptor finds them ([backend/muscriptor.md](backend/muscriptor.md)).
The YouTube download and **Predict hands** are jobs on the same stream. Anything that can exceed
about a second follows this pattern.

## Where to look deeper

- Local dev loop and containers: [04-local-development.md](04-local-development.md)
- The two machines and the tunnel: [02b-local-setup.md](02b-local-setup.md)
- The model both services obey: [backend/time-model.md](backend/time-model.md)
- Backend: [backend/README.md](backend/README.md) · [backend/api.md](backend/api.md)
- Frontend: [frontend/README.md](frontend/README.md) · [frontend/rendering.md](frontend/rendering.md)
- Endpoint detail: [`../documentation/services/backend/endpoints.md`](../documentation/services/backend/endpoints.md)
- Component detail: [`../documentation/services/frontend/components.md`](../documentation/services/frontend/components.md)
