# Task 1.1.1 — Backend restructure · progress report

Status: **done**. Date: 2026-07-26.

## Summary

`aitu-backend/src/aitu_backend/` now has the package layout every later epic writes into,
and `main.py` is a thin app factory.

**Packages created** (each with a docstring naming the epic that fills it):
`api/`, `matrix/`, `audio/`, `transcription/`, `storage/`, `notation/`, `schemas/`.

**Migrations** (done with `git mv`, so history follows):

| Before | After |
|--------|-------|
| `sequence.py` | `matrix/text_notation.py` |
| `schemas.py` | `schemas/score.py` |
| `paths.py` | `storage/paths.py` |
| `/scores`, `/sequence` inline in `main.py` | `api/scores.py` router |

`schemas/__init__.py` re-exports `MatrixScore`, `SequenceRequest`, `SparseMatrix`, so
`from aitu_backend.schemas import MatrixScore` keeps working.

**Routers** — one `APIRouter` per section, all included by `create_app()`:

| Prefix | File | Endpoints |
|--------|------|-----------|
| *(none)* | `api/scores.py` | `GET /scores`, `POST /sequence` — real, unchanged behaviour |
| `/audio` | `api/audio.py` | list/get/delete, upload, recording, waveform, stream |
| `/matrix` | `api/matrix.py` | transcribe, progress (SSE), recompute, get, export, import, transpose |
| `/notation` | `api/notation.py` | score document, annotations, range preview |
| `/library` | `api/library.py` | playground list/save, promote, tracks, playlists |
| `/youtube` | `api/youtube.py` | download, queue |

Every not-yet-implemented endpoint raises `501` via `api/_placeholders.py:not_implemented()`,
with a detail string naming the epic that owns it (e.g. *"Not implemented yet — the
transcription pipeline is delivered by Epic 4 (Transcription)."*). The frontend shell can be
wired against final URLs today.

`main.py` also gained a `lifespan` that calls `storage.paths.ensure_data_tree()` on startup.

## Errors found and how they were solved

1. **`python-multipart` missing.** The `/audio/upload` placeholder declares an `UploadFile`
   parameter; FastAPI refuses to build such a route without `python-multipart`, so app import
   failed at test collection. Added `python-multipart>=0.0.20` to `[project].dependencies`
   (Epic 3 needs it anyway).
2. **`storage/paths.py` depth.** Moving the module one level deeper broke `repo_root()`.
   Renamed it `backend_root()` and switched to `Path(__file__).resolve().parents[3]`, and split
   out `data_dir()` so no other module ever writes `"data"` as a literal.
3. **Stale `sequence` import in a notebook.** `notebooks/88-keys-matrix/02-88-keys-matrix.ipynb`
   imported `aitu_backend.sequence`; rewritten to `aitu_backend.matrix.text_notation`.

## Deviations from the task file

- The task listed `api/` files as "audio, matrix, notation, library, youtube" but the MVP
  `/scores` and `/sequence` endpoints had no home. Added a sixth file, `api/scores.py`, with
  **no prefix** so the existing frontend page keeps working at the same URLs. Its docstring
  records that Epic 10 absorbs `/scores` and Epic 6 reuses `/sequence`.
- `ensure_data_tree()` is a stub creating only `data/`; Task 1.4.1 grows it into the full tree.
- Added `api/_placeholders.py` (not in the task file) so the `501` message shape is written once.

## Verification

```
uv run pytest        # tests/test_api_smoke.py — 6 tests
```

- `/health` returns `{"status": "ok"}`
- `/scores` parses `data/example-scores.json` into `MatrixScore` models
- `/sequence` round-trip: `["*Do-4", "*Re-4", "Re-4", "*Mi-4"]` -> rows `[39, 41, 41, 43]`,
  onset `[39, 41, -1, 43]` (the sustain is the `-1`)
- mismatched hand lengths and unknown notes -> `422`
- five placeholder routes -> `501`

Run in the sandbox against a Python **3.10** venv (no 3.12 build available offline); all code
avoids 3.11+/3.12-only syntax, so this is a valid proxy. Re-run on the Mac with `make test`.

## Manual trial for the supervisor

```bash
cd aitu-backend && uv sync && make serve
curl -s 127.0.0.1:8765/health          # {"status":"ok"}
curl -s 127.0.0.1:8765/audio/ | head   # 501 with the Epic 3 message
open http://127.0.0.1:8765/docs        # six tag groups: scores, audio, matrix, notation, library, youtube
```

Then `cd aitu-frontend && npm run dev` — the existing page must still list the example scores
and render a composed sequence. (Task 1.2.1 replaces that page; until then it is the regression check.)

## For the next worker

- `uv.lock` is **not** regenerated: the sandbox has no Python 3.12 to resolve against. The first
  `uv sync` on the Mac updates it (new deps: `tqdm`, `python-multipart`, plus the `dev` group).
- Put new endpoints in the matching `api/` file, never in `main.py`.
- `context/09-coding-conventions.md` still says notation logic lives in `sequence.py` and paths in
  `paths.py`; both are stale. Updated at the end of Epic 1 in one pass.
