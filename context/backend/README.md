# aitu-backend

Python 3.12 / FastAPI service. It runs the piano transcription model (MuScriptor, on the GPU of the
Ubuntu machine), stores the one file that cannot be recreated, and derives everything else from it on
demand: the wall-clock matrix, the distribution of gaps, the figure of every note, and the score
payload the browser draws. Since implementation 08 it also keeps a revision for each step of a piece,
so the flow page knows which step is out of date.

It does **no drawing**. The frontend owns every pixel; this service decides what each note is
called and where in time it sits.

## The idea in one paragraph

A matrix column used to do two jobs: it was where a note sits on the page **and** it was the
rhythmic value of that note. Because it was both, its width came from a tempo somebody typed in,
and a grid that cannot express the playing produces the same wrong figure every time. The two jobs
are now separate. **Position is measured wall-clock time** — one column is a fixed number of
milliseconds, 40 by default. **The figure is a name the reader chooses** — you click the gap that
repeats in your own playing, say what it is called, and every other note takes its name from that
one choice. There is no BPM anywhere in the product.

Full reasoning: [time-model.md](time-model.md).

## Responsibilities

| Area | Package | Role |
|---|---|---|
| HTTP | `api/` | One router per product section, `/auth` and `/admin` among them; `main.py` is a thin factory that puts every router behind the session and rights check |
| Users and rights | `auth/` | The session cookie, Argon2id passwords, the slow-down after wrong passwords, the rights table, the check every route runs before anything else ([08-security.md](../08-security.md)) |
| Audio | `audio/` | Upload, browser recording, YouTube, ffmpeg normalisation, waveforms, the cuts and the frame table, the edited audio |
| Transcription | `transcription/` | Engines ([MuScriptor](muscriptor.md), ByteDance, Transkun), the model registry and the GPU queue, the live stream, the lag correction, the filters, events to matrix, the split cache, the saved hands |
| Steps of a piece | `pieces/` | Which steps are ready or stale, and the note operations ([pieces-and-revisions.md](pieces-and-revisions.md)) |
| The grid and its measurement | `matrix/` | Frame ↔ ms, gaps, peaks, the ladder, passages, figure bands |
| Hands | `hands/` | Which hand plays each onset: a beam search with a gated second pass |
| Naming notes | `notation/` | Figures, tresillos, trills |
| Contracts | `schemas/` | Pydantic models, camelCase on the wire, mirrored in TypeScript |
| Editing | `editing/` | The replacement splice, composing, staging, history |
| Persistence | `storage/` | Every path in one module (`paths.py`); the project bundle, the audio store, finding the project of a part |
| Database | `db/` | The SQLite tables (SQLAlchemy 2 models, times stored and returned in UTC), the Alembic migrations, the users and the sessions, the backup, check and reindex tools |
| The format | `pmn/` | The piano matrix notation: the sparse form and every adapter |

## The one stored file

`parts/<partId>/notes.pmn` in the project bundle under `.database/` (until implementation 02, Phase 3,
`data/audio/<uuid>/matrices/events.json`) — the engine's note events, before any grid was
involved, with an id per note, the hand of each note once the hand split is saved, and the revisions
of section 1 of [pieces-and-revisions.md](pieces-and-revisions.md). Everything else about the music is a function of it, so re-reading a piece at 20 ms
instead of 40 is a different query string rather than a migration.

Its format, the sparse form it is read into, and every conversion (the dense matrix, the COO
payload, the wire columns, MIDI, MuScriptor events, `.pmn.json`) are one package, `pmn/`:
[piano-matrix-notation.md](piano-matrix-notation.md).

The one thing stored beside it is `sheet.json` (was `rhythm.json`): what the reader decided, which is
the only thing about a piece that nothing can derive. Beside them, `timeline.json` says which audio
the part plays. Where all of this lives, and the tables of the database: [07-database.md](../07-database.md).

## API

`127.0.0.1:8765`, interactive docs at `/docs`. The page reaches it as `/api` through the frontend's
server. Every route needs a session except `GET /health` and `POST /auth/login`, and checks the
rights of the project it names: a project the user may not read answers `404`, one they may read but
not change answers `403`. Overview: [api.md](api.md); the users, the session and the rights table:
[08-security.md](../08-security.md).

## Notebooks

Interactive POC demos live under `notebooks/<theme>/` — one thematic subfolder per POC. Do not
deep-read them; they import `aitu_backend` to stay in sync with the package.

## Run

In the container, from the repository root: `make up` (and `make test-backend` for the tests).
Natively:

```bash
cd aitu-backend && uv sync --extra muscriptor && make serve
```

See [04-local-development.md](../04-local-development.md).

## Where to look deeper

- [time-model.md](time-model.md) — the wall-clock model and the decisions behind it
- [muscriptor.md](muscriptor.md) — the transcription engine, the GPU queue and the live stream
- [pieces-and-revisions.md](pieces-and-revisions.md) — the steps of a piece, the revisions, the `/pieces` routes
- [piano-matrix-notation.md](piano-matrix-notation.md) — the stored form, the wire form, the adapters
- [editing.md](editing.md) — re-recording a passage, and composing a piece from nothing
- [api.md](api.md) — the HTTP surface
- [08-security.md](../08-security.md): the users, the session, the rights table
- [notation-and-parsing.md](../../documentation/deprecated/notation-and-parsing.md) — deprecated: the text-notation MVP, deleted in implementation 02, Phase 1
- [documentation/services/backend/](../../documentation/services/backend) — every endpoint, field,
  path and parameter
