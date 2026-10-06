# Tech stack

Locked versions from lockfiles. Re-read `uv.lock` and `package-lock.json` when upgrading.

## Backend (`aitu-backend/`)

| Item | Version / constraint |
|------|----------------------|
| Python | 3.12.13 (`.python-version`); `requires-python >=3.12.13,<3.13`. The backend image runs 3.12.14 |
| Package manager | `uv` + `uv.lock` |
| Build | hatchling; wheel/sdist package `src/aitu_backend` |
| Web | FastAPI 0.141.1, uvicorn[standard] 0.54.0. JSON answers are compressed with gzip (`compression.py`) |
| Validation | Pydantic 2.13.4 |
| Numerics | numpy 2.4.5, scipy 1.17.1 |
| Progress / uploads | tqdm >=4.67, python-multipart >=0.0.20 |
| YouTube | yt-dlp **>=2026.8.19** — a hard floor, not a preference: every earlier build picks a YouTube player client that now answers `403`, so downloads fail outright |
| MIDI | mido 1.3.3 (base dependency since implementation 08: the MIDI adapter of `pmn/`) |
| Passwords | argon2-cffi 25.1.0 (`>=23.1.0`): Argon2id hashes with its default parameters (`auth/passwords.py`, implementation 02, Phase 4) |
| Sessions | No library: 32 random bytes in the cookie `aitu_session` (`HttpOnly`, `SameSite=Lax`, 30 days, renewed on use), and only their SHA-256 in the `sessions` table (`auth/sessions.py`). See [08-security.md](08-security.md) |
| Optional extras | `muscriptor` (muscriptor 0.3.0, librosa 0.11.0; **the engine in use**), `transcription` (ByteDance's piano_transcription_inference 0.0.6, librosa), `transkun` (Transkun 2.0.1). All three pull torch **2.13.0** (with its own CUDA 13.0 libraries on Linux) and torchaudio 2.11.0. The lock is resolved for Linux and Apple Silicon only. **No `basic-pitch` extra** — it pins tensorflow <2.15.1, which has no cp312 wheels, and a declared-but-unresolvable extra breaks `uv lock` for the whole project |
| Dev group | pytest, httpx, black, flake8, mypy, pre-commit, types-tqdm (`[dependency-groups] dev`) |
| Notebooks | ipykernel 7.2.0, jupyterlab 4.5.7, ipywidgets (dev/exploratory) |

Runtime entry: `uv run python -m uvicorn aitu_backend.main:app` (see `Makefile`), or the backend
container (`compose.yaml`).

## Frontend (`aitu-frontend/`)

| Item | Version / constraint |
|------|----------------------|
| Runtime | React 19.2.6, react-dom 19.2.6 |
| Language | TypeScript 6.0.3 |
| Bundler | Vite 8.1.5, `@vitejs/plugin-react` 6.0.1. The development server proxies `/api` to the backend, and answers only to the host names of `allowedHosts` (`vite.config.ts`) and to IP addresses |
| Notation | `@aimpromptu/grid-notation` **0.42.0**, installed from disk (`file:../../vexflow-v2`); zero runtime dependencies, Bravura inlined. **Rebuild it after pulling** — npm does not build a linked dependency and a stale `dist/` fails silently |
| Routing | react-router-dom 7.x |
| Components | MUI 9.x (`@mui/material`, `@mui/icons-material`, `@mui/x-data-grid`) + emotion 11.x. The theme has a light and a dark colour scheme on CSS variables; MUI keeps the user's choice in the browser (`mui-mode`) |
| Lint | ESLint 10.4.0 flat config: `@eslint/js`, `typescript-eslint` 8.x, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `globals` |
| Browser checks | Playwright 1.63.0 with its headless Chromium (`check:flow`, `time:flow`, `bench:*`, `screenshot`), and tsx for the `check:*` scripts in TypeScript |

Scripts: `npm run dev` (vite), `npm run build` (`tsc -b && vite build`), `npm run lint`, the
`check:*`, `bench:*` and `time:flow` scripts ([04-local-development.md](04-local-development.md)
section 5), `npm run preview`.

## Containers (implementation 08)

| Item | Value |
|------|-------|
| Runtime | Docker with Compose v2 and the NVIDIA Container Toolkit, on the Ubuntu machine |
| Backend image | `python:3.12-slim-bookworm`, `uv` 0.11.3, `ffmpeg`, `deno` (for yt-dlp), the three engine extras; the GPU reserved in `compose.yaml` |
| Frontend image | `node:22-bookworm-slim`, the Vite development server (development mode, decision Q-5), its own build of `../vexflow-v2` |
| Code | Mounted from the host, not copied: edits reload both services |
| GPU | NVIDIA RTX 4090, driver 595.58.03; torch reports `cuda` inside the container |

## Cross-service

| Item | Value |
|------|-------|
| API base in the page | `/api`, passed to the backend by the Vite server (one port, on the home network or through the SSH tunnel), so the browser sends the session cookie by itself |
| Page address | `0.0.0.0:5173` on the Ubuntu machine (`WEB_BIND`); `http://ubuntu:5173` from the Mac |
| Backend address | `127.0.0.1:8765` on the Ubuntu machine, never on the network |
| Frontend override env | `VITE_AITU_API_URL` (no trailing slash) |
| JSON field casing | camelCase on the wire (Pydantic aliases on backend; TS types on frontend) |
| CORS | Backend allows all origins (`*`) without credentials, so no page of another origin can send the session cookie |

## Decisions for the implementation plan

Locked by the organizer for `context/implementations/01-mvp/01-epics-master-plan/plan/`; workers follow these unless the human supervisor agrees to a change.

| Area | Decision |
|------|----------|
| Python style/CI | pre-commit with `black`, `flake8` (ignore long-line/minor errors), `mypy`; commits go straight to `master` |
| Data models | Pydantic everywhere on the backend; camelCase wire format via aliases |
| Progress | `tqdm` for any >10 s processing, mirrored to the UI via a ProgressReporter + SSE |
| API | Plain FastAPI endpoints; functional over best-practice. Containers since implementation 08 |
| Matrix persistence | No matrix is stored: **only `notes.pmn` (the notes, the portable `.pmn` version 2) and `sheet.json` (the reader's decisions) are stored per part**, and every matrix is derived per request. The `.npz` files of the old Piano Library were deleted in implementation 02, Phase 3 |
| Piano transcription | **MuScriptor `large`** since implementation 08: the only engine the user can choose, on the GPU, float16, one chunk at a time, piano only ([backend/muscriptor.md](backend/muscriptor.md)). Before it, `piano_transcription_inference` (ByteDance, onset threshold **0.5**) was the default and **Transkun** a second choice; both stay in the code behind `transcription/engine.py` and are refused by the route. Spotify Basic Pitch cannot install on Python 3.12 |
| Audio tooling | `ffmpeg` (prerequisite) for conversion/normalization, `yt-dlp` (run as `python -m yt_dlp`) for YouTube |
| Accepted audio | `.mp3 .aac .m4a .wav .webm .ogg` — webm/ogg for browser recordings (Chrome records only webm/opus; ffmpeg converts server-side) |
| Frontend components | MUI (+ MUI X) standard across all pages; Aceternity UI only decorative; palette from `context/colors/color-palette.md` as `palette.ts` |
| Notation rendering | `@aimpromptu/grid-notation` in the browser, engraving the matrix directly. Frame columns — not measures, voices or accumulated ticks — are the horizontal source of truth, so the two hands cannot drift apart. The backend chooses every note's printed figure and hands it over with the matrix; it builds no score document and draws nothing |
| Time model | A column is a fixed number of milliseconds (`frameMs`, 40 by default) and carries no rhythmic meaning. No BPM, no granularity, no bar lines. See [backend/time-model.md](backend/time-model.md) |
| Storage | `.database/` (implementation 02, plan section 8): **SQLite** for the records (users, projects, the music library, requests), through **SQLAlchemy 2** models with **Alembic** migrations (`aitu_backend/db/`), and folders beside it for the audio files (stored once, by SHA-256) and the project bundles. On the Ubuntu machine a link to `/mnt/ssd2/aimpromptu/.database`, mounted into the backend container at `/database`. See [07-database.md](07-database.md) |
| GPU | The RTX 4090 of the Ubuntu machine (`AITU_DEVICE=cuda` in the container); natively the default stays `cpu` |

## Not used (POC)

- Cloud provider SDKs
- Database servers (SQLite is a file in `.database/`; the SQLAlchemy models can move to Postgres in the production version)
- HTTPS: the app is plain HTTP on the home network; the production answer is a reverse proxy ([08-security.md](08-security.md))

The sign in (implementation 02, Phase 4) uses one library, argon2-cffi, for the password hashes. The
session is the app's own: a random cookie checked against the `sessions` table, with no OAuth and no
JWT ([08-security.md](08-security.md)).

## Where to look deeper

- Run commands: [04-local-development.md](04-local-development.md)
- Service roles: [03-services-overview.md](03-services-overview.md)
- Coding style: [09-coding-conventions.md](09-coding-conventions.md)
- Locked dependency detail: `aitu-backend/uv.lock`, `aitu-frontend/package-lock.json`
