# Local development

## Both services at once

From the repository root:

```bash
make serve     # starts both in the background and prints where they are
make status    # what is running
make logs      # follow both
make stop      # shut both down
```

`serve` returns your terminal, so closing it does not kill the servers — `make stop` does. Logs go
to `.run/`. The frontend port is pinned with `--strictPort` on purpose: Vite's default is to hop to
the next free port when 5173 is taken, which is friendly right up until you have two copies of the
app running and are reading the wrong one. Use `make serve WEB_PORT=5174` if you want a second.

The rest of this page is the same thing one service at a time, which is what you want when you are
working on one of them.

## Prerequisites

- **Backend:** Python 3.12.13, [`uv`](https://docs.astral.sh/uv/) installed
- **Frontend:** Node.js (compatible with Vite 8 / npm lockfile)
- **`ffmpeg`** on `PATH` — normalises uploaded and recorded audio, extracts mp3 for yt-dlp, and
  does the pitch-preserving stretch that range editing and composing need. macOS:
  `brew install ffmpeg`. Without it, `/audio/upload` answers `503` with that instruction; the audio
  tests skip rather than fail.
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

A second engine, **Transkun**, is a separate extra: `uv sync --extra transkun`. It ships its own
weights inside the wheel, so there is no download step. It is **not** an upgrade — on the same
audio it finds two notes ByteDance misses and loses four it gets, so it is offered beside ByteDance
rather than instead of it. `uv sync` installs only the extras you name, so for both:
`uv sync --extra transcription --extra transkun`.

Without any engine installed, everything still runs: the `silent` engine returns no notes, so the
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

**Demo pieces.** Two pieces written by hand rather than recorded, so the right answer is known
before you open anything:

```bash
cd aitu-backend && uv run python scripts/make_demo_pieces.py
```

They appear under **Playground → Upload / Input → the audio library** as `even-and-swung` and
`classical-mix`. The click-by-click walk through them is
[`user-reviews.md`](implementations/03-time-based-concept/user-reviews.md).

**Backend tests:**

```bash
cd aitu-backend && make test
```

769 passing in about 15 seconds. One failure,
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas`, is
pre-existing on a clean checkout and unrelated to anything recent.

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

No `.env` file is required today; the fallback in `api/client.ts` (`API_BASE`) matches the
backend default.

## Full dev loop

1. `make serve` from the repository root, or the two services in two terminals.
2. Open `http://localhost:5173` → **Playground → Upload / Input**.
3. Pick a piece from the audio library, or upload one, and press **Run transcription**. There are
   two settings: the engine, and the time resolution. There is no tempo to type in.
4. Go to **Piano Sheet**, click a bar in the plot, name it, and press **Write the sheet**.

## The notation renderer

The sheet is drawn by `@aimpromptu/grid-notation`, installed from the sibling `../vexflow-v2`
checkout as a symlink. **npm does not build a linked dependency for you**, so after any change
there:

```bash
cd ../vexflow-v2 && npm run build
```

A stale `dist/` fails silently — the app keeps engraving with the old code and nothing warns. If a
documented feature seems missing, check the build before checking the docs.

## Build / lint (frontend)

```bash
cd aitu-frontend
npm run build         # tsc -b && vite build
npm run lint          # eslint .
npm run check:render  # draw a real score headlessly in jsdom
npm run preview       # preview production build
```

`check:render` exists because a notation renderer fails loudly at draw time and **silently at
layout time**: a score that draws no noteheads, loses a hand or stops beaming renders a
blank-looking page with no error, and neither typecheck nor lint can see it.

26 checks, all passing. It draws a real schema 2.0 envelope and hands the renderer each note's
printed figure, exactly as `TimeScoreView` does, so it guards the path the app actually uses.

## Notebooks (backend, optional)

Exploratory Jupyter notebooks live under `notebooks/<theme>/`. Not required for the web app. One
thematic subfolder per POC is the standing convention.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| The app cannot reach the backend | Backend running? `curl http://127.0.0.1:8765/health`. CORS is open locally. |
| Wrong API host | Set `VITE_AITU_API_URL` (no trailing slash). |
| Backend import error | `uv sync` from `aitu-backend/`; module is `aitu_backend`. |
| A test fails that you did not touch | `test_the_worked_example_at_00_46…` is a known pre-existing failure. |
| Upload answers `503` | `ffmpeg` is not on `PATH`. |
| A sheet feature seems missing | Rebuild `../vexflow-v2`; `dist/` is probably stale. |
| Transcription never finishes | `GET /matrix/engines` — is an engine installed? |
| Port 5173 already in use | `make stop`, or `make serve WEB_PORT=5174`. |

## Where to look deeper

- Tech versions: [02-tech-stack.md](02-tech-stack.md)
- Services and ports: [03-services-overview.md](03-services-overview.md)
- Endpoint detail: [../documentation/services/backend/endpoints.md](../documentation/services/backend/endpoints.md)
- Where files land: [07-database.md](07-database.md) and
  [../documentation/services/backend/paths-and-data.md](../documentation/services/backend/paths-and-data.md)
- What to click, in order: [`user-reviews.md`](implementations/03-time-based-concept/user-reviews.md)
