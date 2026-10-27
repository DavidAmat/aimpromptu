# HTTP API

FastAPI app in `main.py`, thin by design: it builds the app, installs CORS and gzip for JSON answers,
opens `.database/` (brings the tables to the newest Alembic revision, makes the top folders and the
master user), starts the engine preload, and includes every router from `api/`. Default
`127.0.0.1:8765`, interactive docs at `/docs`. The page calls it as `/api` through the frontend's
server, on the page's own origin, so the browser sends the session cookie by itself. CORS allows all
origins but without credentials, so a page of another origin cannot send that cookie.

## Every route needs a session

Since implementation 02, Phase 4 every route except `GET /health` and `POST /auth/login` needs the
session cookie `aitu_session` that the sign in sets. `main.py` includes the routers in three groups
(`api/__init__.py`), each behind its own check (`auth/dependencies.py`):

| Group | Routers | Check |
|---|---|---|
| Open | `/auth` | none for the sign in |
| User | `/audio`, `/matrix`, `/passages`, `/pieces`, `/sheet`, `/projects`, `/library`, `/playlists`, `/public`, `/requests`, `/shares` and `/shared`, `/youtube`, `/video` | a session, then the rights of the project the route names |
| Master | `/admin`, `/frame-examples` (Lab) | a session of the master user |

The rights check reads the project from the path (`audio_uuid`, the id of a part, or `project_id`)
and applies the rights table of [08-security.md](../08-security.md). A `GET` reads and every other
method writes, except three `POST` routes that read a project and change nothing in it (trim,
duplicate, and the edit copy of a library version: `READ_ROUTES`). Until implementation 03, Phase 10
the list also held the old sheet with the page edits, its ladder preview and the hand prediction. `POST /matrix/transcribe`
names its part in the body and checks it itself.

The code below a route knows the user of the request, so the lists are the user's own (`GET /audio/`
lists only their projects; `GET /video` their videos, and every video for the master user), a new
project belongs to them, and a job records its owner and runs as them. Only the owner of a job and
the master user can follow it.

## The routers

| Prefix | Module | What it is for |
|---|---|---|
| `/auth` | `api/auth.py` | Sign in, sign out, who is signed in, change one's own password |
| `/admin` | `api/admin.py` | The users: list, make, disable, reset a password; **Review**: the requests to decide, and the decision (Phase 14). Master user only |
| `/audio` | `api/audio.py` | The working store: bring a recording in, trim it, stream it |
| `/matrix` | `api/matrix.py` | Run the model, follow it (the notes arrive live on the stream), read back the notes it heard |
| `/pieces` | `api/pieces.py` | The state of each step, the notes as columns, note operations ([pieces-and-revisions.md](pieces-and-revisions.md)) |
| `/sheet` | `api/sheet.py` | The sheet of a part (implementation 03): drawn by the backend as SVG, the AI run, the hands, the reading tools, transpose, add, remove, paste, undo and redo, the pages for print, the song's words (`/sheet/{uuid}/words`) |
| `/passages` | `api/passages.py` | Recording in Sheet (implementation 02, Phase 9): a passage of a part, its takes, the promotion ([editing.md](editing.md)) |
| `/projects` | `api/projects.py` | The Personal Vault: list (with the step of each project), create, rename, delete, duplicate (new ids, the same audio files), export and import a `.aitu` file (implementation 02, Phase 5); **Save to library** and **Edit** (Phase 6) |
| `/library` | `api/library.py` | The Private Library (Phase 6): songs and their versions, artists and their names, the history of a version ([music-library/private-library.md](../music-library/private-library.md)) |
| `/playlists` | `api/playlists.py` | The songs playlists of the Private Library (Phase 10) |
| `/public` | `api/public.py` | The Public Library (Phase 13): songs, artists, playlists, likes, **Add to my library**, the suggestions ([music-library/ontology.md](../music-library/ontology.md)) |
| `/requests` | `api/requests.py` | Requests to the Public Library (Phase 14): send, send again, withdraw, read ([music-library/requests.md](../music-library/requests.md)) |
| `/shares`, `/shared` | `api/shares.py` | A Private Library shared read only (Phase 14): who the user shares with; the libraries shared with the user, **Add to my library** |
| `/youtube` | `api/youtube.py` | Downloads via yt-dlp, also as a job with progress |
| `/video`, `/frame-examples` | `api/video.py`, `api/frame_examples.py` | Reading a Synthesia-style video into a piece (implementations 04 and 05). `/frame-examples` is the master user's (Lab) |

Plus `GET /health`. The original text-notation MVP (`GET /scores`, `POST /sequence`) was deleted in
implementation 02, Phase 1 (Q-4); its pages are in `documentation/deprecated/`. The old Piano
Library router (`/library`: playground versions, promotion, tags, playlists) was deleted in Phase 3;
`/library` is the Private Library since Phase 6. The `/time` router (`api/time_score.py`: the old
sheet's peaks, ladder, score payload, saved reading, paste, restore and lyrics) and **Predict hands**
(`/pieces/{uuid}/hands/predict`) were deleted in implementation 03, Phase 10 (2026-10-27) with the
vexflow-v2 sheet; the lyrics moved to `GET/PUT /sheet/{uuid}/words`.

The `{uuid}` of `/audio`, `/matrix`, `/pieces` and `/sheet` is the id of a **part** of a project
(plan P-6). A project made by this app has the id of its first part.

## The shape of a working session

The flow page, from signing in to a saved piano sheet:

```
POST /auth/login              the cookie aitu_session; every request after sends it
POST /audio/upload            or /youtube/jobs, /audio/recording; POST /projects for From scratch
GET  /pieces/{id}/status      which steps are ready; the tabs follow it
PUT  /audio/{id}/cuts         the selected region (optional)
POST /matrix/transcribe       202 + a job id
GET  /matrix/progress/{id}    SSE: chunk messages with the notes, then done
GET  /pieces/{id}/notes       the saved notes, as columns
PATCH /pieces/{id}/notes      the user's edits, as operations
GET  /sheet/{id}?width=N      the sheet, drawn as SVG (the algorithm's until the AI writes one)
POST /sheet/{id}/llm          Enhance with AI: 202 + a job id, followed on /matrix/progress/{id}
POST /sheet/{id}/reading      one edit of the toolboxes; the answer is the sheet drawn again
```

## What is stored, and what is derived

The notes (`notes.pmn`) and the sheet (`sheet.f1`, implementation 03) are stored; the drawing is
derived from `sheet.f1` on each request, and a sheet written for older notes is laid again on the
current ones, so it is never stale for the page. Until implementation 03, Phase 10 the old sheet was
derived whole from the notes on every `/time` request and only the reader's decisions were stored.

Since implementation 08 one thing is kept in memory: the hand split, in `transcription/split_cache.py`,
keyed by the piece, the column length and the time `notes.pmn` was last written, so any save makes
it a new entry. A piece whose hands are saved does not need the inference at all: its two hand
matrices are painted from the saved hands in about 20 ms.

## Long work answers immediately

Transcription takes tens of seconds, so `POST /matrix/transcribe` answers `202` with a job id and
the caller follows a Server-Sent Events stream that carries the progress and the notes as they are
found ([muscriptor.md](muscriptor.md)). Transcriptions run one at a time on the GPU. The YouTube
download, an AI run on a sheet and **Write the proposal** of a take are jobs on the same stream.

## Error conventions

| Status | When |
|---|---|
| 401 | No session, or an ended one: "Sign in first." (the page opens the sign-in page) |
| 403 | A project the user may read but not change ("You can open this project but not change it."), a page of the master user asked by another user, or a wrong current password |
| 404 | No such audio, project, editing session or job, **or one the user may not read**: the answer is the same, so an address tells nothing about another user's work |
| 409 | An operation the editing session's placement does not allow, a write whose `baseRevision` is old, or a username that is taken |
| 422 | A body or query the models reject, and conversion failures |
| 503 | `ffmpeg` is missing — the message says so and how to install it |

## Where to look deeper

- [`documentation/services/backend/endpoints.md`](../../documentation/services/backend/endpoints.md):
  every route, its parameters and what it obeys, with `/auth` and `/admin`
- [08-security.md](../08-security.md): the users, the session cookie, the rights table
- `http://127.0.0.1:8765/docs` — the generated, always-current field reference
- [time-model.md](time-model.md) — the wall-clock model the sheet is built on
- [`aitu-backend/src/aitu_backend/sheet/README.md`](../../aitu-backend/src/aitu_backend/sheet/README.md) — the sheet behind `/sheet`, sections 9 to 17
- [editing.md](editing.md) — paste and Recording in Sheet, behind `/sheet/{uuid}/paste` and `/passages`
