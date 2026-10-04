# 08 Phase 3: Containers, the GPU in the backend, and the tunnel

The plan is [`08-plan.md`](08-plan.md) sections 9.1, 10.3 to 10.5 and section 12, Phase 3. The status
lookup is [`08-checklist.md`](08-checklist.md). This report is for the agents of later phases: what
was built, the choices made inside the phase, the measurements, and what Phases 4 to 9 must know.

# 1. What was done

| Task | Result |
|---|---|
| 3.1.1 variables | `aitu_backend/config.py`: `AITU_DATA_DIR`, `AITU_DEVICE` (`cpu` default, `cuda`, `auto`), `AITU_HOST`, `AITU_PORT`, read on every call. `paths.data_dir()` honours `AITU_DATA_DIR`; the three engines take `device=None` and ask `config.device()`; `main.run()` and both Makefiles read host and port |
| 3.1.2 `.env.example` | Repository root. Every name, no value, the default written beside each. `/.env` added to the root `.gitignore` (only `aitu-backend/.env` and `aitu-frontend/.env` were ignored before) |
| 3.1.3 lock | No change needed for `torchaudio` (section 2.1). The lock gained the `muscriptor` extra and `[tool.uv] environments` (section 2.2) |
| 3.2.1 backend image | `aitu-backend/Dockerfile`, `aimpromptu-backend:dev`, 10.4 GB |
| 3.2.2 frontend image | `aitu-frontend/Dockerfile`, `aimpromptu-frontend:dev`, 1.0 GB, `vexflow-v2` through the named context `vexflow` |
| 3.2.3 compose | `compose.yaml` at the root, project name `aimpromptu` |
| 3.2.4 Makefile | Root `Makefile`: `up`, `down`, `logs`, `ps`, `build`, `test-backend`, `shell-backend`. The native `logs` is renamed `logs-native` |
| 3.3.1 GPU | From the container: RTX 4090, driver 595.58.03, torch 2.13.0+cu130, `cuda.is_available()` true, `AITU_DEVICE` resolves to `cuda`, data folder is the host's (36 pieces) |
| 3.3.2 baseline | Section 3 |
| 3.3.3 tests | `make test-backend`: 951 passed, 1 failed (`test_the_worked_example_at_00_46_prints_three_equal_corcheas`, known since Phase 0). Same as natively |
| 3.4.1 proxy | `vite.config.ts` proxies `/api` to `AITU_API_PROXY` (default `http://127.0.0.1:8765`); `API_BASE` defaults to `/api` |
| 3.4.2 tunnel | `scripts/tunnel-from-mac.sh [host] [port]` |
| 3.4.3 Playwright | `playwright` 1.63 as a frontend dev dependency, `npm run screenshot` (`aitu-frontend/scripts/screenshot.mjs`), Chromium headless shell installed in `~/.cache/ms-playwright` |

Checks: backend `pytest` 951 passed, 1 known failure, natively and in the container (945 before,
6 new in `tests/test_config.py`). `black` and `flake8` clean on the changed files. `mypy` on them
reports only the two `unused-ignore` lines in `engine.py` that existed before this phase. Frontend
`lint`, `build`, `check:render` (60 passed), `check:history` pass.

Docs touched: root `README.md` (the container commands and the tunnel), `aitu-frontend/README.md`
(the `/api` base, the screenshot script), `documentation/services/backend/paths-and-data.md`
(`AITU_DATA_DIR`). The full documentation pass is Phase 9.

# 2. Choices made inside the phase

## 2.1 `torchaudio` stays at 2.11

The plan's section 10.5 listed "`torchaudio 2.11` beside `torch 2.13`" as a mismatch to align. There
is nothing to align it to: 2.11.0 is the newest `torchaudio` on PyPI. Since 2.9 `torchaudio` has no
`torch` pin and ships `abi3` libraries built on PyTorch's stable interface, so it is meant to run
beside newer `torch`. Checked: `_IS_TORCHAUDIO_EXT_AVAILABLE` is true, and
`torchaudio.functional.melscale_fbanks` (the only function Transkun calls) runs on `cuda:0`. The
Transkun tests pass.

## 2.2 The `muscriptor` extra, and the lock for two platforms

The Dockerfile needs MuScriptor installed, so the `muscriptor` extra (`muscriptor>=0.3.0`, from
PyPI) is added here, not in Phase 4. Phase 4 still adds `MuScriptorEngine` and its
`engine_installed()` entry.

`uv lock` refused the extra: MuScriptor pins NumPy below 2 on Intel Macs, and the base pins
`numpy>=2.4.5`. A marker on the requirement does not help, because uv still resolves every
platform. `[tool.uv] environments` now limits the lock to `sys_platform == 'linux'` and to Apple
Silicon Macs, the two machines of the project. The lock lost the Windows-only packages (`colorama`,
`pywinpty`) and moved `fastapi` 0.136.1 to 0.141.1 and `uvicorn` 0.47.0 to 0.54.0, because
MuScriptor asks for newer ones. Every test passes on the new versions.

## 2.3 The images hold packages, compose mounts the repository

The plan said "the data folder mounted from the host". The whole repository is mounted instead, at
`/work/aimpromptu`, with the same layout as on the host:

- The code is the host's, so uvicorn (`--reload --reload-dir src`) and Vite reload on every edit.
  Checked: a change in `src/aitu_backend/config.py` restarts the backend; a change in
  `src/layout/BackendStatus.tsx` is a Vite hot update in a connected browser.
- The tests read `pocs/` and `context/` at the repository root (`test_matrix_peaks.py`,
  `bench_device.py`), so they need the repository, not only `aitu-backend/`.
- `AITU_DATA_DIR` in `.env` chooses the host folder mounted over `aitu-backend/data`; inside the
  container the variable is empty, so `paths.data_dir()` is the default path.

The Python environment is at `/opt/venv` (`UV_PROJECT_ENVIRONMENT`), outside the mount, so the host's
`.venv` and the image's never mix. The package comes from `PYTHONPATH=/work/aimpromptu/aitu-backend/src`,
not from an install. Only `pyproject.toml` and `uv.lock` enter the build (`aitu-backend/.dockerignore`
ignores everything else, which keeps the 1.1 GB of audio out of the build context). The frontend's
`node_modules` lives in the image and is kept in front of the host's by an anonymous volume; `make up`
passes `--renew-anon-volumes` so a rebuilt image is not hidden by the old volume.

Both containers run as the host user (`UID` and `GID` from the Makefile), so every file they write
into the repository or the data belongs to `david`, not to root.

## 2.4 The base image and the tools

`python:3.12-slim-bookworm` (Python 3.12.14; the project needs 3.12.13 or newer), not a CUDA image:
the PyPI torch wheel brings its CUDA 13.0 libraries as `nvidia-*` packages, and the NVIDIA Container
Toolkit adds the driver. `uv` 0.11.3 (the host's version) and `deno` 2.9.7 are copied from their
images. `deno` is there because yt-dlp now needs a JavaScript runtime to read YouTube's player; the
YouTube download itself was not tried in the container (it becomes a job in Phase 6).

## 2.5 The caches

- **Hugging Face**: the host's own cache `/mnt/ssd2/hf/data/hub` is bind-mounted at `/hf/hub`
  (`HF_HUB_CACHE`), so Phase 1's weights are reused. `HF_TOKEN` comes from the shell (exported in
  `~/.zshrc`) or from `.env`; checked present in the container.
- **The backend's home folder** is `/mnt/ssd2/aimpromptu/home` (`AITU_CACHE_DIR`). The ByteDance
  checkpoint (172 MB, `~/piano_transcription_inference_data/`) was downloaded there by the first CPU
  run; it was not on the Ubuntu host before. `make up` creates the folder first, because Docker would
  create a missing one as root.

## 2.6 The proxy, and one behaviour change

The page calls `/api/...`; Vite removes the prefix and sends the request to the backend. Checked
through port 5173: `GET /api/health`; `GET /api/time/{uuid}/score` arrives with
`Content-Encoding: gzip` (45 KB instead of 612 KB); `GET /api/audio/{uuid}/file` with a `Range`
header answers 206 with the asked bytes; `GET /api/matrix/progress/{jobId}` streams message by
message.

A stopped backend used to be a network error in the browser, which the client turned into "Could
not reach the backend". Through the proxy it is a **502** from Vite, with a plain-text body. The
client (`api/client.ts`, `fetchOrExplain`) now treats a 502 the same way; the backend never sends
502 itself.

## 2.7 Ports

Both published ports bind to `127.0.0.1` only (5173 and 8765): the Mac goes through SSH, and nothing
is opened to the LAN. `make up` runs `make stop` first, because the native servers use the same
ports; `make serve` while the containers run fails on the busy port, as `--strictPort` intends.

# 3. Measurements (task 3.3.2)

Inside the backend container, Superestrella (`a585f9eb`, 189.2 s), `scripts/bench_device.py`,
raw answer in [`measurements/phase-3-device.json`](measurements/phase-3-device.json). "x real" is
seconds of audio per second of processing. Load times are from the second run (the first CPU load
included the 172 MB checkpoint download: 57 s).

| Engine | Device | Load s | Transcribe s | x real | Notes |
|---|---|---:|---:|---:|---:|
| ByteDance | cpu | 7.2 | 53.6 | 3.5 | 1,343 |
| ByteDance | cuda | 1.2 | 4.6 | 41.4 | 1,340 |
| MuScriptor `large`, float16, batch 1, prelude forcing | cuda | 1.0 | 25.3 | 7.5 | 1,351 |

- **ByteDance on the GPU is 12 times faster** than on the CPU. 1,338 of the 1,343 CPU notes have a
  GPU note of the same key within 1 ms (0.9 ms at most); the other five differ because float
  rounding moves a few peaks across the onset threshold. The stored `events.json` of this piece
  (made on the Mac's CPU) also has 1,343 notes.
- **MuScriptor in the container is the same as natively**: the 1,351 notes match the Phase 1 native
  run (`pocs/poc-muscriptor/out/full/large-float16-b1-prelude/notes.json`) one to one, with 0 ms
  difference. Same speed (7.5 against 7.6 x real), same 3.5 GB GPU peak, first note after 0.18 s.

# 4. Notes for later phases

**Every phase.** Use the containers: `make up`, then the app is `http://localhost:5173` on Ubuntu
(the user opens it through `scripts/tunnel-from-mac.sh`), the backend `http://127.0.0.1:8765`.
`make test-backend ARGS="-k pmn"` runs tests in the image; `docker compose exec backend python ...`
runs a script against the live data. A change to `uv.lock`, `package-lock.json` or `vexflow-v2`
needs `make build` (or `make up`, which builds). Take a screenshot before asking the user to look:
`cd aitu-frontend && npm run screenshot -- /playground/rhythm --piece <uuid> --delay 2500`; the
picture goes to `.run/screenshots/` and the command prints every console error and failed request.

**Phase 4 (the engine).**

- `AITU_DEVICE=cuda` is set by `compose.yaml`; natively the default stays `cpu`. `config.device()`
  returns `cuda` as asked even without a GPU, on purpose (the setup rule: never fall back to the CPU
  silently). `auto` exists for tests and laptops.
- MuScriptor prints its timing lines with `print` to **stdout** as well as stderr (the Phase 1
  report said stderr); `bench_device.py` silences both with `contextlib.redirect_*`. A job thread
  should do the same, or replace `print` in `muscriptor` only for the job's thread.
- uvicorn runs with `--reload`: an edit under `src/` restarts the process, which ends a running
  transcription job and unloads a preloaded model (1.0 s to load `large` again). That is expected in
  development; the preload of Phase 4 should not assume the process lives long.
- `HF_TOKEN` and the cache are in place in the container; no human step is needed.

**Phase 6 (YouTube as a job).** yt-dlp is 2026.8.19 in the image, with `deno` on `PATH` and ffmpeg.
The download was not tried in the container; try it first there.

**Phase 7 (the live view).** The progress stream already passes the Vite proxy without buffering.

**Phase 9 (documentation).** `context/02b-local-setup.md` does not yet mention the containers, the
tunnel, `/mnt/ssd2/aimpromptu/home` or `~/.cache/ms-playwright` (1.3 GB with earlier Playwright
browsers).

# 5. Files

New: `compose.yaml`, `.env.example`, `aitu-backend/Dockerfile`, `aitu-backend/.dockerignore`,
`aitu-frontend/Dockerfile`, `aitu-frontend/.dockerignore`, `aitu-backend/src/aitu_backend/config.py`,
`aitu-backend/tests/conftest.py`, `aitu-backend/tests/test_config.py`,
`aitu-backend/scripts/bench_device.py`, `aitu-frontend/scripts/screenshot.mjs`,
`scripts/tunnel-from-mac.sh`, `measurements/phase-3-device.json`.

Changed: `.gitignore`, `Makefile`, `aitu-backend/Makefile`, `aitu-backend/pyproject.toml` and
`uv.lock`, `storage/paths.py`, `transcription/engine.py`, `main.py`, `aitu-frontend/vite.config.ts`,
`src/api/client.ts`, `src/vite-env.d.ts`, `package.json` and `package-lock.json`, the three
documents of section 1, the plan (sections 10.3, 10.4, 10.5) and the checklist.
