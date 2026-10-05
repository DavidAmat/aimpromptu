# Local development

The app runs on the Ubuntu machine, in two containers, and the user opens it from the Mac through
one SSH tunnel (implementation 08). The machines and the folders are described in
[02b-local-setup.md](02b-local-setup.md) section 12. Running the two services natively, without
containers, still works and is described after.

## 1. In containers (the usual way)

From the repository root, on Ubuntu:

```bash
make up              # build the images if needed, start the backend (GPU) and the frontend, wait
make logs            # follow both logs
make ps              # what is running
make down            # stop both
make build           # rebuild both images
make test-backend    # the backend tests inside the backend image (ARGS="-k pmn" to filter)
make shell-backend   # a shell in the running backend container
```

Both images hold only the tools and the packages. The repository itself is mounted at
`/work/aimpromptu`, so an edit on the host reloads the backend (`uvicorn --reload`) and the page
(Vite) at once, and the tests in the container run on the host's files. The frontend runs in
development mode (decision Q-5 of implementation 08).

| Container | Image | Port on Ubuntu | What it holds |
|---|---|---|---|
| `backend` | `aimpromptu-backend:dev`, 10.4 GB | `127.0.0.1:8765` | Python 3.12, `uv`, `ffmpeg`, PyTorch with CUDA, the `muscriptor`, `transcription` and `transkun` extras. Reserves the GPU and loads MuScriptor `large` at start |
| `frontend` | `aimpromptu-frontend:dev`, 1 GB | `127.0.0.1:5173` | Node 22, the Vite development server, and its own build of `../vexflow-v2` |

**Run `make up` again after a change of `uv.lock`, `package-lock.json` or `../vexflow-v2`.** The
images hold the packages, and the frontend image holds its own build of the piano sheet package.
`make up` builds with `--build` and renews the frontend's `node_modules` volume, so a new image is
used at once.

**Variables.** Compose reads `.env` beside `compose.yaml` (copy `.env.example`, which lists every
variable with its default). Nothing is required on Ubuntu: `HF_TOKEN` is exported in the shell, the
data folder defaults to `aitu-backend/data`, and the Hugging Face cache to `/mnt/ssd2/hf/data/hub`.

## 2. Open the app from the Mac

```bash
ssh -N -L 5173:localhost:5173 ubuntu      # or scripts/tunnel-from-mac.sh
```

Then open `http://localhost:5173`. The page calls the backend at `/api`, which the Vite server passes
to the backend container; the audio files and the progress stream go the same way. The page opens on
**Projects**; a project goes through Source, Audio, Notes, Hands, Sheet
([frontend/flow-page.md](frontend/flow-page.md)).

## 3. Natively, without containers

```bash
make serve        # both services in the background, prints where they are
make status       # what is running
make logs-native  # follow both
make stop         # shut both down
```

`make up` stops the native servers first, because both ways use the same two ports. Natively the
backend runs on the CPU unless `AITU_DEVICE=cuda` is set, and it needs the extras:

```bash
cd aitu-backend
uv sync --extra muscriptor --extra transcription --extra transkun
make test
```

The frontend natively: `cd aitu-frontend && npm install && npm run dev`. Its proxy then sends `/api`
to `http://127.0.0.1:8765`. `VITE_AITU_API_URL` overrides the base if a page must call another
backend directly.

`ffmpeg` must be on `PATH` (uploads answer `503` without it). `yt-dlp` is a Python dependency and
needs nothing more.

## 4. The transcription engines

MuScriptor is the only engine the user can choose. ByteDance and Transkun stay in the code and their
tests run, but `POST /matrix/transcribe` refuses them. The MuScriptor weights are gated on Hugging
Face: the account behind `HF_TOKEN` must have accepted the licence of `muscriptor-large` once.
`GET /matrix/engine` says whether the model is loaded, on which device, and any error at start.
Details: [backend/muscriptor.md](backend/muscriptor.md).

## 5. Checks

**Backend.** `make test-backend` (in the container): 1,039 passed and 1 known failure,
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas`, which
fails on a clean checkout too. Two GPU tests run only when a GPU and the weights are present.

**Frontend**, from `aitu-frontend/` on the host (the scripts that open a browser need `make up` and
Playwright's Chromium, installed once with `npx playwright install chromium`):

| Command | What it checks |
|---|---|
| `npm run build`, `npm run lint` | Types, the production build, ESLint |
| `npm run check:render` | A real score drawn headlessly in jsdom (a renderer fails silently at layout time) |
| `npm run check:history`, `check:note-names`, `check:geometry` | Undo and redo, Spanish note names, sheet geometry |
| `npm run check:cuts`, `check:notes` | The Audio tab's cuts; the Notes tab's arrays, edits and operations |
| `npm run check:flow` | A project walked in a headless Chromium on a temporary upload (about 2 minutes with the transcription) |
| `npm run time:flow` | The whole flow, timed, on three temporary pieces (an upload, a copied library piece, a new YouTube download) |
| `npm run bench:roll`, `bench:sheet` | The Notes tab's frame rate; a hand move on the piano sheet, part by part |
| `npm run screenshot -- <file> [--piece <uuid>]` | One screenshot of the app |

**Every script that clicks or writes in the app works on a temporary copy of a piece**, never on a
library piece, and deletes the copy at the end.

## 6. The notation renderer

The piano sheet is drawn by `@aimpromptu/grid-notation`, the sibling checkout `../vexflow-v2`. npm
does not build a linked dependency, and a stale `dist/` fails silently: the app keeps drawing with
the old code. In the containers, `make up` rebuilds it inside the frontend image. Natively:
`cd ../vexflow-v2 && npm run build`.

## 7. Troubleshooting

| Symptom | Check |
|---|---|
| "Could not reach the backend" | `make ps`; the page's server answers 502 when the backend is down. `make logs` shows why |
| A transcription ends at once with no notes | `curl localhost:8765/matrix/engine`. "No CUDA GPUs are available" means the container lost its GPU: `docker compose up -d --force-recreate backend` |
| The model does not load | `GET /matrix/engine` `error`: a missing `HF_TOKEN`, or a licence not accepted on Hugging Face |
| The Mac cannot open `localhost:5173` | The tunnel closed (the Mac slept). Run it again |
| A sheet feature seems missing | `../vexflow-v2` changed: `make up` (or `make build`) |
| A test fails that you did not touch | `test_the_worked_example_at_00_46…` is the known failure |
| Upload answers `503` | `ffmpeg` is not on `PATH` (natively) |
| Port 5173 or 8765 already in use | `make stop` (native servers) or `make down` |

## Where to look deeper

- The machines, the folders and the tunnel: [02b-local-setup.md](02b-local-setup.md)
- Tech versions: [02-tech-stack.md](02-tech-stack.md)
- Services and ports: [03-services-overview.md](03-services-overview.md)
- Endpoint detail: [../documentation/services/backend/endpoints.md](../documentation/services/backend/endpoints.md)
- Where files land: [07-database.md](07-database.md) and
  [../documentation/services/backend/paths-and-data.md](../documentation/services/backend/paths-and-data.md)
