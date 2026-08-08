# Tech stack

Locked versions from lockfiles. Re-read `uv.lock` and `package-lock.json` when upgrading.

## Backend (`aitu-backend/`)

| Item | Version / constraint |
|------|----------------------|
| Python | 3.12.13 (`.python-version`); `requires-python >=3.12.13,<3.13` |
| Package manager | `uv` + `uv.lock` |
| Build | hatchling; wheel/sdist package `src/aitu_backend` |
| Web | FastAPI 0.136.1, uvicorn[standard] 0.47.0 |
| Validation | Pydantic 2.13.4 |
| Numerics | numpy 2.4.5, scipy 1.17.1 |
| Progress / uploads | tqdm >=4.67, python-multipart >=0.0.20 |
| YouTube | yt-dlp >=2026.7.4 |
| Optional extras | `transcription` (piano_transcription_inference, torch >=2.4, librosa). **No `basic-pitch` extra** — it pins tensorflow <2.15.1, which has no cp312 wheels, and a declared-but-unresolvable extra breaks `uv lock` for the whole project |
| Dev group | pytest, httpx, black, flake8, mypy, pre-commit, types-tqdm (`[dependency-groups] dev`) |
| Notebooks | ipykernel 7.2.0, jupyterlab 4.5.7, ipywidgets (dev/exploratory) |

Runtime entry: `uv run python -m uvicorn aitu_backend.main:app` (see `Makefile`).

## Frontend (`aitu-frontend/`)

| Item | Version / constraint |
|------|----------------------|
| Runtime | React 19.2.6, react-dom 19.2.6 |
| Language | TypeScript 6.0.3 |
| Bundler | Vite 8.0.13, `@vitejs/plugin-react` 6.0.1 |
| Notation | `@aimpromptu/grid-notation` 0.15.x, installed from disk (`file:../../vexflow-v2`); zero runtime dependencies, Bravura inlined |
| Routing | react-router-dom 7.x |
| Components | MUI 9.x (`@mui/material`, `@mui/icons-material`, `@mui/x-data-grid`) + emotion 11.x |
| Lint | ESLint 10.4.0 flat config: `@eslint/js`, `typescript-eslint` 8.x, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `globals` |

Scripts: `npm run dev` (vite), `npm run build` (`tsc -b && vite build`), `npm run lint`, `npm run preview`.

## Cross-service

| Item | Value |
|------|-------|
| API default | `http://127.0.0.1:8765` |
| Frontend override env | `VITE_AITU_API_URL` (no trailing slash) |
| JSON field casing | camelCase on the wire (Pydantic aliases on backend; TS types on frontend) |
| CORS | Backend allows all origins (`*`) for local POC |

## Decisions for the implementation plan

Locked by the organizer for `context/implementations/plan/`; workers follow these unless the human supervisor agrees to a change.

| Area | Decision |
|------|----------|
| Python style/CI | pre-commit with `black`, `flake8` (ignore long-line/minor errors), `mypy`; commits go straight to `master` |
| Data models | Pydantic everywhere on the backend; camelCase wire format via aliases |
| Progress | `tqdm` for any >10 s processing, mirrored to the UI via a ProgressReporter + SSE |
| API | Plain FastAPI endpoints; functional over best-practice, no containerization yet |
| Matrix persistence | `scipy.sparse` COO int8 saved as compressed `.npz` (`save_npz`); dense form only transient for JSON export/import; separate files per hand |
| Piano transcription | `piano_transcription_inference` (ByteDance), behind `transcription/engine.py`, installed via `uv sync --extra transcription`. CPU on Apple Silicon — the package ignores non-CUDA devices. Spotify Basic Pitch remains the intended fallback but is Python ≤3.11 only, so it runs in its own venv (see the benchmark README) |
| Audio tooling | `ffmpeg` (prerequisite) for conversion/normalization, `yt-dlp` (run as `python -m yt_dlp`) for YouTube |
| Accepted audio | `.mp3 .aac .m4a .wav .webm .ogg` — webm/ogg for browser recordings (Chrome records only webm/opus; ffmpeg converts server-side) |
| Frontend components | MUI (+ MUI X) standard across all pages; Aceternity UI only decorative; palette from `context/colors/color-palette.md` as `palette.ts` |
| Notation rendering | `@aimpromptu/grid-notation` in the browser, engraving the matrix directly. Frame columns — not measures, voices or accumulated ticks — are the horizontal source of truth, so the two hands cannot drift apart. The backend hands over the matrix and stores the reader's markup; it builds no score document |
| Storage | Local filesystem under `aitu-backend/data/` (playground/library/audio trees); MinIO only if containerized later |
| GPU | CPU now; keep engine `device` parameterized and matrix ops numpy-vectorized for future CUDA hosts |

## Not used (POC)

- Docker / docker-compose
- Cloud provider SDKs
- SQL/NoSQL database drivers
- Auth libraries (OAuth, JWT, etc.)

## Where to look deeper

- Run commands: [04-local-development.md](04-local-development.md)
- Service roles: [03-services-overview.md](03-services-overview.md)
- Coding style: [09-coding-conventions.md](09-coding-conventions.md)
- Locked dependency detail: `aitu-backend/uv.lock`, `aitu-frontend/package-lock.json`
