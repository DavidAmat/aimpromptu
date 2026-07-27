# Local development

Run backend and frontend in separate terminals. Both services must be up for the full UI.

## Prerequisites

- **Backend:** Python 3.12.13, [`uv`](https://docs.astral.sh/uv/) installed
- **Frontend:** Node.js (compatible with Vite 8 / npm lockfile)
- **`ffmpeg`** on `PATH` — required by Epic 3 to normalize uploaded and recorded audio, and by
  Epic 3 Story 3.5 for yt-dlp's mp3 extraction. macOS: `brew install ffmpeg`. Without it,
  `/audio/upload` answers `503` with that instruction; the audio tests skip rather than fail.
- **`yt-dlp`** — a normal Python dependency, installed by `uv sync`. It is invoked as
  `python -m yt_dlp` on the backend's own interpreter, so it does **not** need to be on `PATH`.

### Transcription models (optional extra)

The piano-transcription models are **not** part of the base install — torch is a ~200 MB download.

```bash
cd aitu-backend
uv sync --extra transcription     # piano_transcription_inference + torch + librosa
```

> **Basic Pitch is not an extra.** basic-pitch 0.4.0 pins `tensorflow(-macos) <2.15.1`, and cp312
> tensorflow wheels only start at 2.16.1 — so it cannot install on Python 3.12 on any platform.
> And because `uv lock` resolves every extra for every platform, merely declaring it made
> `uv sync --extra transcription` fail too. To benchmark against it, give it its own Python 3.11
> venv: see `aitu-backend/notebooks/transcription-benchmark/README.md`.

Verified July 2026:

- `torch` ships macOS **arm64** wheels for CPython 3.10–3.14, so **Python 3.12 works fine on
  Apple Silicon (M1–M4)** — no version change needed.
- `piano_transcription_inference` does **not** pin torch (it needs matplotlib, mido, librosa,
  torchlibrosa), so there is no dependency conflict to work around.
- On Apple Silicon the model runs on the **CPU**. The package only moves itself to a device when
  the string contains `"cuda"`, so `mps` is accepted and then ignored. A short piano clip still
  transcribes in seconds.
- The **165 MB model checkpoint** is downloaded on first use into
  `~/piano_transcription_inference_data/`. The package would normally fetch it with `wget`, which
  **macOS does not ship** — so the backend downloads it itself, with a progress bar, before
  loading the model. Nothing extra to install.

Without an engine installed, everything still runs: the `silent` engine returns no notes, so the
UI and the pipeline can be exercised end to end. `GET /matrix/engines` reports what is available.

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
