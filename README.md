# AImpromptu (aitu)

**Play the piano, get readable sheet music.** Bring in a recording — upload it, record from the
browser, or pull it off YouTube — and the app transcribes it, writes it out as a staff you can read
and correct, and prints it.

Local development only: no hosted deploy, no accounts, no database.

## What makes it different

A note's **position** and a note's **name** are two separate numbers.

Position is measured wall-clock time: a column is a fixed slice of real time, 40 ms by default.
The rhythmic figure is a name you choose — you look at a picture of how the piece was actually
played, click the gap that keeps repeating, and say what it is called. Every other note takes its
name from that one choice.

There is no BPM anywhere in the product. Renaming a note moves nothing.

Why: [context/backend/time-model.md](context/backend/time-model.md).

## Who it's for

- **Musicians** who want a readable page out of their own playing, and want to correct the reading
  rather than fight a grid.
- **Developers** extending the transcription pipeline, the wall-clock matrix, or the notation
  renderer.

## Services

| Service | Folder | Role |
|---|---|---|
| Backend | `aitu-backend/` | Run the model, store the recorded notes, derive the score |
| Frontend | `aitu-frontend/` | Every screen, and every pixel of the sheet |
| Renderer | `../vexflow-v2` | `@aimpromptu/grid-notation`, installed from disk |

**Monorepo (POC).** One git repository at the workspace root; `aitu-backend/` and `aitu-frontend/`
are service folders, not separate repos. The renderer is a **sibling checkout** on purpose: it knows
nothing about this app's API. Later we plan to package each service as its own Docker container —
not implemented yet.

## Run locally

```bash
make serve     # both services; prints where they are
make logs      # follow both
make stop
```

App `http://localhost:5173`, API `http://127.0.0.1:8765`, API docs `/docs`.

Or one at a time:

```bash
cd aitu-backend  && uv sync && make serve
cd aitu-frontend && npm install && npm run dev
```

`ffmpeg` must be on `PATH`. The transcription models are an optional extra
(`uv sync --extra transcription`); without one, every screen still works against the `silent`
engine. Full setup: [context/04-local-development.md](context/04-local-development.md).

## Documentation

| Start here | Purpose |
|---|---|
| [context/00-project-complete-overview.md](context/00-project-complete-overview.md) | One-shot orientation — paste this alone to get the whole project |
| [context/00-index.md](context/00-index.md) | Full map of all docs |
| [context/backend/time-model.md](context/backend/time-model.md) | The wall-clock model everything follows from |
| [documentation/README.md](documentation/README.md) | Code-level detail tree |

Subrepo entry points: [aitu-backend/README.md](aitu-backend/README.md) ·
[aitu-frontend/README.md](aitu-frontend/README.md)
