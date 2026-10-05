# HTTP API

FastAPI app in `main.py`, thin by design: it builds the app, installs CORS and gzip for JSON answers,
creates the `data/` tree, starts the engine preload, and includes every router from `api/`. Default
`127.0.0.1:8765`, interactive docs at `/docs`. The page calls it as `/api` through the frontend's
server. CORS allows all origins — local, no auth surface.

## The routers

| Prefix | Module | What it is for |
|---|---|---|
| `/audio` | `api/audio.py` | The working store: bring a recording in, trim it, stream it |
| `/matrix` | `api/matrix.py` | Run the model, follow it (the notes arrive live on the stream), read back the notes it heard |
| `/pieces` | `api/pieces.py` | The state of each step, the notes as columns, note operations, predict the hands ([pieces-and-revisions.md](pieces-and-revisions.md)) |
| `/time` | `api/time_score.py` | The score: peaks, the ladder, the drawable payload, the saved reading |
| `/audio/{uuid}/edits` | `api/editing.py` | Staged range editing and composing |
| `/library` | `api/library.py` | Playground versions, promotion, tags, playlists |
| `/youtube` | `api/youtube.py` | Downloads via yt-dlp, also as a job with progress |
| `/video`, `/frame-examples` | `api/video.py`, `api/frame_examples.py` | Reading a Synthesia-style video into a piece (implementations 04 and 05) |

Plus `GET /health`. The original text-notation MVP (`GET /scores`, `POST /sequence`) was deleted in
implementation 02, Phase 1 (Q-4); its pages are in `documentation/deprecated/`.

## The shape of a session

The flow page, from audio to a saved piano sheet:

```
POST /audio/upload            or /youtube/jobs, /audio/recording, /audio/compose
GET  /pieces/{id}/status      which steps are ready; the tabs follow it
PUT  /audio/{id}/cuts         the selected region (optional)
POST /matrix/transcribe       202 + a job id
GET  /matrix/progress/{id}    SSE: chunk messages with the notes, then done
GET  /pieces/{id}/notes       the saved notes, as columns
PATCH /pieces/{id}/notes      the user's edits, as operations
POST /pieces/{id}/hands/predict/job   the hand split, then PATCH with hand operations
GET  /time/{id}/peaks         the picture of the playing
POST /time/{id}/score         draw it
PUT  /time/{id}/rhythm        keep the reading
```

## Nothing on the score path is stored

Every `/time` response is derived from the stored `events.json` on each request. Nothing is written
and nothing is stored, so asking for the same piece at 20 ms instead of 40 is a different query
string rather than a migration. **Nothing on disk can disagree with what the screen shows.**

Since implementation 08 one thing is kept in memory: the hand split, in `transcription/split_cache.py`,
keyed by the piece, the column length and the time `events.json` was last written, so any save makes
it a new entry. A piece whose hands are saved does not need the inference at all: its two hand
matrices are painted from the saved hands in about 20 ms.

## Long work answers immediately

Transcription takes tens of seconds, so `POST /matrix/transcribe` answers `202` with a job id and
the caller follows a Server-Sent Events stream that carries the progress and the notes as they are
found ([muscriptor.md](muscriptor.md)). Transcriptions run one at a time on the GPU. The YouTube
download and **Predict hands** are jobs on the same stream.

## Error conventions

| Status | When |
|---|---|
| 404 | No such audio, session, job, track or playlist |
| 409 | An operation the session's placement does not allow, or a write whose `baseRevision` is old |
| 422 | A body or query the models reject, and conversion failures |
| 503 | `ffmpeg` is missing — the message says so and how to install it |

## Where to look deeper

- [`documentation/services/backend/endpoints.md`](../../documentation/services/backend/endpoints.md)
  — every route, its parameters and what it obeys
- `http://127.0.0.1:8765/docs` — the generated, always-current field reference
- [time-model.md](time-model.md) — why `/time` looks the way it does
- [editing.md](editing.md) — the session flow behind `/audio/{uuid}/edits`
