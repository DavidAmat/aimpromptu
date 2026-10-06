# AImpromptu (aitu)

**Play the piano, get readable sheet music.** Bring in a recording — upload it, record from the
browser, or pull it off YouTube — and the app transcribes it with MuScriptor on the GPU while you
watch the notes appear, lets you correct the notes and the hands on a piano roll, writes it out as a
staff you can read and correct, and prints it.

The way in is the **Piece** page: five tabs, Source, Audio, Notes, Hands and Sheet, each enabled
once the step before it is ready ([context/frontend/flow-page.md](context/frontend/flow-page.md)).

Local development only: no hosted deploy, and no login yet (every request acts as one master user
until implementation 02, Phase 4). Everything the app stores is in `.database/` at the repository
root: a SQLite database, the projects and the audio files. `make db-backup` copies it while the app
runs ([context/07-database.md](context/07-database.md)).

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
| Backend | `aitu-backend/` | Run MuScriptor on the GPU, store the recorded notes, derive the score |
| Frontend | `aitu-frontend/` | Every screen, and every pixel of the sheet |
| Renderer | `../vexflow-v2` | `@aimpromptu/grid-notation`, installed from disk |

**Monorepo (POC).** One git repository at the workspace root; `aitu-backend/` and `aitu-frontend/`
are service folders, not separate repos. The renderer is a **sibling checkout** on purpose: it knows
nothing about this app's API. On the Ubuntu machine each service runs in its own development
container (`compose.yaml`), with the repository mounted so edits reload.

## Run in containers (the Ubuntu machine, with the GPU)

```bash
make up            # build if needed, start both, wait for both
make logs          # follow both
make test-backend  # the backend tests inside the backend image
make down
```

From the Mac: `scripts/tunnel-from-mac.sh` (one SSH tunnel to port 5173), then open
`http://localhost:5173`. The page calls the backend at `/api`, which Vite passes on, so one port is
enough. `.env.example` lists every setting; only `HF_TOKEN` (the MuScriptor weights) has no default.

## Run locally, without containers

```bash
make serve        # both services; prints where they are
make logs-native  # follow both
make stop
```

App `http://localhost:5173`, API `http://127.0.0.1:8765` (the page reaches it through `/api`), API
docs `/docs`.

Or one at a time:

```bash
cd aitu-backend  && uv sync --extra muscriptor && make serve
cd aitu-frontend && npm install && npm run dev
```

`ffmpeg` must be on `PATH`. The engines are optional extras (`muscriptor`, and the older
`transcription` and `transkun`); natively the backend runs on the CPU unless `AITU_DEVICE=cuda`.
Full setup: [context/04-local-development.md](context/04-local-development.md). The two machines and
the tunnel: [context/02b-local-setup.md](context/02b-local-setup.md).

## Documentation

| Start here | Purpose |
|---|---|
| [context/00-project-complete-overview.md](context/00-project-complete-overview.md) | One-shot orientation — paste this alone to get the whole project |
| [context/00-index.md](context/00-index.md) | Full map of all docs |
| [context/backend/time-model.md](context/backend/time-model.md) | The wall-clock model everything follows from |
| [documentation/README.md](documentation/README.md) | Code-level detail tree |

Subrepo entry points: [aitu-backend/README.md](aitu-backend/README.md) ·
[aitu-frontend/README.md](aitu-frontend/README.md)
