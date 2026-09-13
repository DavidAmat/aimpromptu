# HTTP API

FastAPI app in `main.py`, thin by design: it builds the app, installs CORS, creates the `data/` tree
and includes every router from `api/`. Default `127.0.0.1:8765`, interactive docs at `/docs`. CORS
allows all origins — local POC, no auth surface.

## The six routers

| Prefix | Module | What it is for |
|---|---|---|
| `/audio` | `api/audio.py` | The working store: bring a recording in, trim it, stream it |
| `/matrix` | `api/matrix.py` | Run the model, follow it, read back the notes it heard |
| `/time` | `api/time_score.py` | The score: peaks, the ladder, the drawable payload, the saved reading |
| `/audio/{uuid}/edits` | `api/editing.py` | Staged range editing and composing |
| `/library` | `api/library.py` | Playground versions, promotion, tags, playlists |
| `/youtube` | `api/youtube.py` | Downloads via yt-dlp |

Plus `GET /health`, and `GET /scores` / `POST /sequence` — the original text-notation MVP, which
still runs but which no screen calls.

## The shape of a session

```
POST /audio/upload            or /recording, /youtube/download, /audio/compose
POST /matrix/transcribe       202 + a job id
GET  /matrix/progress/{id}    SSE, until done
GET  /time/{id}/peaks         the picture of the playing
POST /time/{id}/ladder-preview  "if I call this peak a negra, what follows?"
GET  /time/{id}/score         draw it
PUT  /time/{id}/rhythm        keep the reading
```

## Nothing on the score path is cached

Every `/time` response is derived from the stored `events.json` on each request. Nothing is written
and nothing is stored, so asking for the same piece at 20 ms instead of 40 is a different query
string rather than a migration.

That costs a second or two on a five-minute piece and buys a system with **no stale state in it** —
nothing on disk can disagree with what the screen shows.

## Long work answers immediately

Transcription takes tens of seconds, so `POST /matrix/transcribe` answers `202` with a job id and
the caller follows a Server-Sent Events stream that reports real model-batch progress. Anything that
can exceed about ten seconds follows this pattern.

## Error conventions

| Status | When |
|---|---|
| 404 | No such audio, session, job, track or playlist |
| 409 | An operation the session's placement does not allow |
| 422 | A body or query the models reject, and conversion failures |
| 503 | `ffmpeg` is missing — the message says so and how to install it |

## Where to look deeper

- [`documentation/services/backend/endpoints.md`](../../documentation/services/backend/endpoints.md)
  — every route, its parameters and what it obeys
- `http://127.0.0.1:8765/docs` — the generated, always-current field reference
- [time-model.md](time-model.md) — why `/time` looks the way it does
- [editing.md](editing.md) — the session flow behind `/audio/{uuid}/edits`
