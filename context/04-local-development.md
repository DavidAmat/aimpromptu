# Local development

The app runs on the Ubuntu machine, in two containers (implementation 08), and the user opens it
from the Mac over the home network at `http://ubuntu:5173` and signs in (implementation 02,
Phase 4). The machines and the folders are described in
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
| `frontend` | `aimpromptu-frontend:dev`, 1 GB | `0.0.0.0:5173` (`WEB_BIND`), every address of the machine | Node 22 and the Vite development server |

**Run `make up` again after a change of `uv.lock` or `package-lock.json`.** The images hold the
packages. (Until implementation 03, Phase 10 the frontend image also built `../vexflow-v2`, the old
sheet's renderer, so a change there needed `make build` too; the app no longer uses it.)
`make up` builds with `--build` and renews the frontend's `node_modules` volume, so a new image is
used at once.

**Variables.** Compose reads `.env` beside `compose.yaml` (copy `.env.example`, which lists every
variable with its default). Nothing is required on Ubuntu: `HF_TOKEN` is exported in the shell,
`.database/` is `AITU_DATABASE_DIR` in `.env` (mounted at `/database` in the backend), the
master user is `master` unless `AITU_MASTER_USERNAME` says otherwise, and the Hugging Face cache is
`/mnt/ssd2/hf/data/hub`. Three names of `.env` came with the users and the home network
(implementation 02, Phase 4):

| Name | What it does |
|---|---|
| `AITU_MASTER_PASSWORD` | The master user's first password, read only while the master user has none. Without it the master user cannot sign in. On this machine `.env` holds a generated one |
| `WEB_BIND` | Where the page listens. Default `0.0.0.0`, every address, so the devices of the home network reach it; `127.0.0.1` keeps it to this machine and the SSH tunnel |
| `AITU_ALLOWED_HOSTS` | More host names the page answers to, separated by commas. Vite already answers to `localhost`, `ubuntu`, `david-ubuntu`, `david-ubuntu.local` and to any IP address, and refuses every other name |

**`.database/`**, where every record and every file of the app is ([07-database.md](07-database.md)).
On a new machine, make the folder before the first `make up` (Docker would make a missing one as
root; `make up` makes a plain folder when nothing is there):

```bash
mkdir -p /mnt/ssd2/aimpromptu/.database
```

Set `AITU_DATABASE_DIR=/mnt/ssd2/aimpromptu/.database` in `.env`. Do not put a link to that folder inside the repository: the editor follows the link and watches every file.

| Command (on the host, from the repository root) | Does |
|---|---|
| `make db-backup` | `.database-YYYYMMDD-HHMMSS.tar.zst` beside `.database/`; safe while the app runs |
| `make db-restore FILE=.database-….tar.zst` | Into an empty `.database/`; then `make up` |
| `make db-check` | The tables against the bundles and the audio store (`HASHES=1` hashes every file) |
| `make db-reindex` | The rows of the projects and the audio again, from the bundles on disk |

They run with the local environment (`uv run --no-sync`), because they need `tar` with zstd, which
the image does not have. The tables reach the newest Alembic revision by themselves when the backend
starts.

## 2. Open the app from the Mac

Open `http://ubuntu:5173` (the Mac's `/etc/hosts` maps `ubuntu`) or `http://192.168.0.112:5173`.
`make up` prints this address when it ends. The page calls the backend at `/api`, which the Vite
server passes to the backend container; the audio files and the progress stream go the same way. The
backend itself stays on `127.0.0.1:8765` of Ubuntu.

Every page first asks to sign in: **Username** `master` (or `AITU_MASTER_USERNAME`) and the
**Password** of `AITU_MASTER_PASSWORD` in `.env`. The other users are made in **Admin → Users**.
After signing in the page opens on **Projects**; a project goes through Source, Audio, Notes,
Sheet ([frontend/projects.md](frontend/projects.md)). The users, the session and what each user
can open are in [08-security.md](08-security.md).

The SSH tunnel still works, as the fallback (away from home, or with `WEB_BIND=127.0.0.1`):

```bash
ssh -N -L 5173:localhost:5173 ubuntu      # or scripts/tunnel-from-mac.sh
```

Then open `http://localhost:5173` and sign in the same way.

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
to `http://127.0.0.1:8765`. Natively the page listens on `localhost` only, so the Mac reaches it
through the tunnel. `VITE_AITU_API_URL` overrides the base if a page must call another
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

**Backend.** `make test-backend` (in the container). The one known failure of earlier phases,
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas`, was
removed with the old sheet's payload in implementation 03, Phase 10. Two GPU tests run only when a GPU and the weights are present. Every
test acts as the master user unless it is marked `real_login`, in which case it signs in through
`/auth`; `test_auth.py` and `test_rights.py` check the sign in and the rights table.

**Frontend**, from `aitu-frontend/` on the host (the scripts that open a browser need `make up` and
Playwright's Chromium, installed once with `npx playwright install chromium`):

| Command | What it checks |
|---|---|
| `npm run build`, `npm run lint` | Types, the production build, ESLint |
| `npm run check:history`, `check:geometry` | Undo and redo; the video piano overlay against the backend's fixture |
| `npm run check:cuts`, `check:notes` | The Audio tab's cuts; the Notes tab's arrays, edits and operations |
| `npm run check:flow` | A project walked in a headless Chromium on a temporary upload (about 2 minutes with the transcription) |
| `npm run check:projects`, `check:library` | The Projects page, New project, export and import; Save to library, a version, Edit, Replace, history |
| `npm run check:paste` | Copy and paste of a passage on the new sheet (the sheet toolbox's Transpose and Lyrics: `check:frames-toolbox`) |
| `npm run check:passage` | Recording in Sheet: Current and Proposal, a take written and promoted (it transcribes; `-- --played` sends the takes' keys instead and needs no GPU) |
| `npm run check:compose`, `check:play` | From other projects, the parts, songs playlists; Play mode |
| `npm run check:public`, `check:requests` | The Public Library and Add to my library; requests, the review and sharing, with a temporary second user |
| `npm run check:frames-sheet`, `check:frames-edit`, `check:frames-tools`, `check:frames-toolbox` | The sheet on a copy of a library version: drawn and played; picking notes, the hand, undo and redo; the note and range toolboxes; the sheet toolbox, lyrics and Print to PDF (`--live` spends a few cents of the AI) |
| `npm run check:frames-page` | The sheet page on a copy of a library version: the AI symbol, the header and its buttons, the floating bar hidden and shown, ⌘ and the wheel (and a pinch) zoom, the cursor dragged across lines (implementation 04, Phase 1) |
| `npm run check:journey` | **The whole journey**, timed: a YouTube link to a piano sheet, saved, published, reviewed and accepted, then pulled, played and composed by a second user (two temporary users; it transcribes) |
| `npm run time:flow` | The whole flow, timed, on three temporary pieces (an upload, a copied library piece, a new YouTube download) |
| `npm run bench:roll` | The Notes tab's frame rate |
| `npm run screenshot -- <path> [--piece <uuid>] [--theme dark] [--signed-out]` | One screenshot of the app, in the light or the dark scheme, signed in or on the sign-in page |

Run the browser checks one at a time, and not while the backend tests run on the CPU: under load a
check can time out while the page is right. When another project holds the GPU, skip the checks
that transcribe (`check:flow` without `--no-transcribe`, `check:passage`, `check:journey`,
`time:flow`).

**The scripts that open the app sign in** as the master user (`scripts/session.mjs`), with
`AITU_MASTER_USERNAME` and `AITU_MASTER_PASSWORD` of `.env`, or with `AITU_CHECK_USERNAME` and
`AITU_CHECK_PASSWORD` when these are set: every `check:*` that opens a browser,
`time:flow` and `screenshot`. Without a password they stop at once and say so.

**Every script that clicks or writes in the app works on temporary copies** (of a project, or a
temporary user it makes), never on a project of a library, and removes what it made at the end.

## 6. The notation renderer

The piano sheet is laid out and drawn by the backend (`aitu_backend/sheet/`, an SVG answered by
`GET /sheet/{uuid}`), so there is no renderer to build on the frontend side. `npm run check:render`
and `npm run check:note-names`, which checked the old renderer `@aimpromptu/grid-notation` (the
sibling checkout `../vexflow-v2`), were removed with it in implementation 03, Phase 10, and
`make build` no longer needs `../vexflow-v2`. See [frontend/rendering.md](frontend/rendering.md).

## 7. Troubleshooting

| Symptom | Check |
|---|---|
| "Could not reach the backend" | `make ps`; the page's server answers 502 when the backend is down. `make logs` shows why |
| A transcription ends at once with no notes | `curl localhost:8765/matrix/engine`. "No CUDA GPUs are available" means the container lost its GPU: `docker compose up -d --force-recreate backend` |
| The model does not load | `GET /matrix/engine` `error`: a missing `HF_TOKEN`, or a licence not accepted on Hugging Face |
| The Mac cannot open `ubuntu:5173` | `make ps`; `WEB_BIND` in `.env` must not be `127.0.0.1`. A page saying the host is not allowed means a name Vite does not know: add it to `AITU_ALLOWED_HOSTS` |
| The Mac cannot open `localhost:5173` | The tunnel closed (the Mac slept). Run it again |
| The page keeps asking to sign in | The session ended (a password changed, the user was disabled, or 30 days passed), or the password is wrong. The master user's first password is `AITU_MASTER_PASSWORD` of `.env` |
| Upload answers `503` | `ffmpeg` is not on `PATH` (natively) |
| Port 5173 or 8765 already in use | `make stop` (native servers) or `make down` |

## Where to look deeper

- The machines, the folders and the tunnel: [02b-local-setup.md](02b-local-setup.md)
- Tech versions: [02-tech-stack.md](02-tech-stack.md)
- Services and ports: [03-services-overview.md](03-services-overview.md)
- Endpoint detail: [../documentation/services/backend/endpoints.md](../documentation/services/backend/endpoints.md)
- Where files land: [07-database.md](07-database.md) and
  [../documentation/services/backend/paths-and-data.md](../documentation/services/backend/paths-and-data.md)
