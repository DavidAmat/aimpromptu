# Services overview

Two deployable services in the monorepo (`aitu-backend/`, `aitu-frontend/`) and one library in a
sibling checkout. Same git root as the docs; not separate repos. The frontend calls the backend over
HTTP on localhost.

## aitu-backend

| Property | Value |
|---|---|
| Stack | Python 3.12, FastAPI, Pydantic 2, uvicorn, numpy, scipy |
| Module | `aitu_backend` under `src/aitu_backend/` |
| Default bind | `127.0.0.1:8765` (`HOST` / `PORT` in the Makefile) |
| Role | Run the model, store the recorded notes, derive the score |

**Packages:**

| Package | Role |
|---|---|
| `api/` | One router per product section; `main.py` is a thin factory |
| `audio/` | Upload, browser recording, YouTube, ffmpeg normalisation, waveforms |
| `transcription/` | Engines, the artifact and leakage filters, events to matrix, background jobs |
| `matrix/` | Frame ↔ ms, gaps, peaks, the figure ladder, passages, figure bands |
| `hands/` | Which hand plays each onset: a beam search with a gated second pass |
| `notation/` | Figures, tresillos, trills |
| `editing/` | The replacement splice, composing, staging, history |
| `storage/` | Every filesystem path in one module; playground, library, playlists |
| `schemas/` | Pydantic contracts, camelCase on the wire, mirrored in TypeScript |

**Endpoints:** `/health`, `/audio`, `/matrix`, `/time`, `/audio/{uuid}/edits`, `/library`,
`/youtube`, plus the text-notation MVP `/scores` and `/sequence`. Table in
[backend/api.md](backend/api.md), detail in
[`documentation/services/backend/endpoints.md`](../documentation/services/backend/endpoints.md).

**Does not:** draw anything, or decide how a page looks. It decides what each note is called and
where in time it sits.

## aitu-frontend

| Property | Value |
|---|---|
| Stack | React 19, TypeScript, Vite 8, MUI 9 |
| Dev server | `http://localhost:5173` (pinned with `--strictPort`) |
| API base | `VITE_AITU_API_URL`, or `http://127.0.0.1:8765` |
| Role | Every screen, and every pixel of the sheet |

**Sections:** YouTube to Audio, Playground (Upload / Input · Piano Roll · Notes Falling · Piano
Sheet), Piano Library, and a read-only performance page.

**Does not:** decide any note's name — the figures arrive from the backend and are passed straight
through to the renderer.

## @aimpromptu/grid-notation

| Property | Value |
|---|---|
| Location | The sibling checkout `../vexflow-v2` |
| Install | `"file:../../vexflow-v2"` — npm makes it a symlink |
| Version | 0.32.0 |
| Role | All engraving: beams, stems, accidentals, clefs, line breaks, pagination |

It exists because VexFlow lays notes out from tick arithmetic inside measures, and a wall-clock
matrix has neither. **Rebuild it after pulling** — npm does not build a linked dependency, and a
stale `dist/` fails silently. See [frontend/rendering.md](frontend/rendering.md).

## How they connect

```
Browser (Vite dev server, :5173)
    │  GET  /matrix/{id}/events     the recording, in seconds  → Piano Roll, Notes Falling
    │  GET  /time/{id}/peaks        the gap distribution       → the peak plot
    │  GET  /time/{id}/score        the drawable payload       → the staff
    │  PUT  /time/{id}/rhythm       the reader's decisions
    ▼
aitu-backend :8765
    │  reads  data/audio/<uuid>/matrices/events.json
    │  writes data/audio/<uuid>/matrices/rhythm.json
    ▼
TimeScorePayload ──▶ TimeScoreView ──▶ @aimpromptu/grid-notation ──▶ SVG
```

Nothing is drawn from a stored grid, because there is no stored grid.

CORS on the backend is open (`allow_origins=["*"]`) for local development.

## Long work

Transcription takes tens of seconds. `POST /matrix/transcribe` answers `202` with a job id, and the
browser follows a Server-Sent Events stream that reports real model-batch progress. Anything that
can exceed about ten seconds follows this pattern.

## Where to look deeper

- Local dev loop: [04-local-development.md](04-local-development.md)
- The model both services obey: [backend/time-model.md](backend/time-model.md)
- Backend: [backend/README.md](backend/README.md) · [backend/api.md](backend/api.md)
- Frontend: [frontend/README.md](frontend/README.md) · [frontend/rendering.md](frontend/rendering.md)
- Endpoint detail: [`../documentation/services/backend/endpoints.md`](../documentation/services/backend/endpoints.md)
- Component detail: [`../documentation/services/frontend/components.md`](../documentation/services/frontend/components.md)
