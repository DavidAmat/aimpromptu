# Task 3.1.1 — Audio store · progress report

Status: **done**. Date: 2026-07-27.

## Summary

`audio/store.py` — the uuid-keyed working area, plus the CRUD half of `api/audio.py`.

```text
data/audio/<uuid>/
  metadata.json      alias, source, format, duration, sample rate, created_at
  original.<ext>     the file exactly as it arrived
  normalized.wav     mono WAV (Task 3.2.1)
  waveform.json      cached peaks (Task 3.2.1)
```

| Store function | Role |
|----------------|------|
| `create(alias, source, extension, …)` | make the folder + metadata |
| `save_original(uuid, stream, ext)` | write bytes in 1 MB chunks |
| `get` / `read_metadata` / `exists` / `list_all` | reading |
| `update(uuid, **changes)` / `rename(uuid, alias)` | patching |
| `delete(uuid)` | remove the folder |
| `read_waveform` / `write_waveform` | the peak cache |

`StoredAudio` bundles the metadata with `original_path`, `normalized_path`, `waveform_path` and
`has_normalized()`, so callers never build a path themselves.

### Endpoints

| Route | Behaviour |
|-------|-----------|
| `GET /audio/` | every entry, **newest first** — powers "load from library" |
| `GET /audio/{uuid}` | metadata, `404` if absent |
| `PATCH /audio/{uuid}` | rename (`{"alias": "..."}`) |
| `DELETE /audio/{uuid}` | remove the folder |
| `GET /audio/{uuid}/file` | the original for playback; `?normalized=true` for the mono WAV |

The frontend's `src/api/audio.ts` was rewritten to match exactly, including `AudioItem` as a true
mirror of `AudioMetadata` and `SUPPORTED_AUDIO_SUFFIXES`.

### The MinIO seam (subtask 3.1.1.3)

**Every filesystem access for audio goes through `store.py`.** No other module opens, writes or
deletes anything under `data/audio/`. Swapping to MinIO later means reimplementing the ten
functions in that one file. Not building MinIO now, as instructed.

## Errors found and how they were solved

1. **A circular import that had been latent since Epic 2.** `schemas/__init__` -> `schemas.matrix`
   -> `matrix.keys` runs the `matrix/__init__` package body, which (as of Task 2.4.2) eagerly
   imported `matrix.model` — which imports `schemas.matrix`, still half-initialized.
   It only surfaced now because `audio/store.py` is the first module to import
   `aitu_backend.schemas` *before* anything has touched `matrix.model`. The whole test suite had
   been passing on import order alone.
   **Fix:** `matrix/__init__.py` re-exports **nothing** now — it is documentation only, and says
   why. Every caller already imported submodules directly, so nothing else changed.
   *Lesson for later epics: keep package `__init__` files free of eager imports in this codebase.*
2. **`shutil.copyfileobj` and mypy.** Starlette's `UploadFile.file` is a `BinaryIO` that mypy
   cannot reconcile with `copyfileobj`'s `AnyStr` typevar. Replaced with an explicit chunked read
   loop — same behaviour, no ignore comment, and the chunk size is now visible.
3. **A stale smoke test.** `test_placeholder_endpoints_answer_501` listed `/audio/`, which is now
   implemented. Removed from the list with a comment saying why, rather than deleting the test.

## Deviations from the task file

- The task named `GET /audio/{uuid}/file`; the Task 1.2.1 client had guessed `/stream`. Kept the
  task file's name and fixed the client.
- `PATCH` accepts only `alias` today (the one editable field); `store.update()` takes any known
  metadata field, so widening the endpoint later is a schema change, not a rewrite.
- Added `?normalized=true` to the file endpoint — the piano roll will want the exact samples the
  engine read.
- Metadata field is `alias`, not `fileName` as the task file writes it. `AudioMetadata` was fixed
  in Task 1.3.2 and is already used by the frontend types; renaming it now would churn both sides
  for no gain. Flagging it as a wording difference, not a behavioural one.

## Verification

```
pytest tests/test_audio_store.py   # 40 passed (with ffmpeg available)
pytest                             # 344 passed overall
mypy, flake8, black                # clean
npx tsc -b, npm run lint           # clean
```

The acceptance criterion — a CRUD round trip over a temp data dir — is
`test_crud_round_trip`, plus an end-to-end HTTP round trip
(`test_upload_endpoint_round_trip`): upload -> list -> get -> rename -> waveform -> stream ->
delete -> 404.

Also covered: newest-first ordering, a **half-written folder not breaking the listing**, empty
aliases, the uuid being immutable, unknown metadata fields, and `404`s on every route.

## Manual trial for the supervisor

```bash
cd aitu-backend && uv sync && make serve
# in another terminal, with any mp3 to hand:
curl -F "file=@/path/to/take.mp3" -F "alias=Do Re Mi" 127.0.0.1:8765/audio/upload
curl -s 127.0.0.1:8765/audio/ | python3 -m json.tool
open http://127.0.0.1:8765/audio/<uuid>/file      # should play in the browser
```

Then check `aitu-backend/data/audio/<uuid>/` on disk: `metadata.json`, `original.mp3`,
`normalized.wav`. `git status` must stay clean — that tree is gitignored.

**ffmpeg is now a documented prerequisite** (`context/04-local-development.md`). If it is missing,
`/audio/upload` answers `503` telling you to `brew install ffmpeg`, and the audio tests skip
instead of failing.

## For the next worker

- **Story 3.3 (recording)**: `POST /audio/recording` already exists and shares the upload path;
  the browser must send a file with a supported suffix (`.wav` is easiest from MediaRecorder).
- **Story 3.5 (YouTube)**: `ingest.ingest_path(path, "youtube", source_url=url)` is the whole
  backend integration — download with yt-dlp to a temp file, then hand it over.
- **Epic 4**: read `StoredAudio.normalized_path`, never the original. It is already mono at
  `formats.TRANSCRIPTION_SAMPLE_RATE`.
- Never touch `data/audio/` outside `store.py`.
