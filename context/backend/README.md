# aitu-backend

Python 3.12 / FastAPI service. It runs the piano transcription model (MuScriptor, on the GPU of the
Ubuntu machine), stores the notes (the one file that cannot be recreated), derives the wall-clock
matrix and the hand split from them on demand, and writes and draws the piano sheet: the AI or the
algorithm writes `sheet.f1`, and the backend draws it as SVG (implementation 03). The AI also writes a
stretch again, or the song at a level (implementations 04 and 04-3): [../ai/README.md](../ai/README.md). It
keeps the music library and reads Synthesia-style videos. Since implementation 08 it also keeps a revision
for each step of a piece, so the flow page knows which step is out of date.

Until implementation 03, Phase 10 (2026-10-27) the backend did no drawing: it derived the gaps, the
figure of every note and a score payload that the browser drew with `@aimpromptu/grid-notation`
(vexflow-v2). That sheet and its code were removed in that phase.

## The idea in one paragraph

A matrix column used to do two jobs: it was where a note sits on the page **and** it was the
rhythmic value of that note. Because it was both, its width came from a tempo somebody typed in,
and a grid that cannot express the playing produces the same wrong figure every time. The two jobs
are now separate. **Position is measured wall-clock time**: one column is a fixed number of
milliseconds, 40 by default. **The figure is a name given by one reference figure**: the AI or the
algorithm chooses how long a negra lasts, every other note takes its name from that one choice, and
**Transpose figures** is the reader's override. (Until implementation 03 the reader chose it, by
clicking the gap that repeats in their playing.) There is no BPM, no compás and no tempo anywhere
in the product.

Full reasoning: [time-model.md](time-model.md).

## Responsibilities

| Area | Package | Role |
|---|---|---|
| HTTP | `api/` | One router per product section, `/auth` and `/admin` among them; `main.py` is a thin factory that puts every router behind the session and rights check |
| Users and rights | `auth/` | The session cookie, Argon2id passwords, the slow-down after wrong passwords, the rights table, the check every route runs before anything else ([08-security.md](../08-security.md)) |
| Audio | `audio/` | Upload, browser recording, YouTube, ffmpeg normalisation, waveforms, the cuts and the frame table, the edited audio |
| Transcription | `transcription/` | Engines ([MuScriptor](muscriptor.md), ByteDance, Transkun), the model registry and the GPU queue, the live stream, the lag correction, the filters, events to matrix, the split cache, the saved hands |
| Steps of a piece | `pieces/` | Which steps are ready or stale, and the note operations ([pieces-and-revisions.md](pieces-and-revisions.md)) |
| The grid | `matrix/` | Frame ↔ ms, the matrix model, the keys, the hand split's entry point (`hands.py`). The gaps, peaks, ladder, passages and figure bands were removed in implementation 03, Phase 10 |
| Hands | `hands/` | Which hand plays each onset: a beam search with a gated second pass; the starting hands of the sheet |
| The new sheet's core | `sheet/` | The chain of implementation 03, copied from the research core in its Phase 1 and grown since: the F1 text (`sheet/sheet/`), the algorithm (`proposal`, `proposal/frames.py` for the new sheet), the AI step (`llm`: `frames.py` writes a sheet window by window, frames prompt version 7; `levels.py` and `catalog/` write a level with its patterns, implementation 04-3), the music analysis of the levels (`levels/`: the grid, the harmony, the hands; no AI), and the engine (`engrave/frames.py`: `render_frames`). The research's bars path stays for the scripts and the golden tests. The core imports no AI library: the clients are in `sheet_llm.py` (`OpenAIComplete`, and `ClaudeComplete` with `ANTHROPIC_API_KEY`); every run uses GPT-6.1 Terra at medium unless the user chooses another model (`part_sheet/job.py`, `MODEL`). The scripts of `aitu-backend/scripts/` draw, write and check sheets and build the galleries of the phases (`draw_frames.py`, `write_sheet.py`, `llm_sheet.py`, `levels_gallery.py`, `level_run_page.py` and others). Contracts, and a map of which page tells each part: `src/aitu_backend/sheet/README.md` |
| The sheet in the app | `part_sheet/` | The stored `sheet.f1`, the sheet of a part at any moment (`build`), the AI's jobs (`job`: the whole run, a stretch, a level, a batch written again), the history of AI runs (`runs`), the edits and their log, the reading tools, a change of length, the old sheet's marks (`legacy`) |
| The music library | `library/` | The Private and the Public Library: songs, artists, versions, playlists, requests, shares, the folders and the metadata, popularity and genres ([music-library/](../music-library/README.md)) |
| The video reader | `video/` | A Synthesia-style video read into notes: the piano overlay, the falling rectangles, the examples of the Lab |
| Contracts | `schemas/` | Pydantic models, camelCase on the wire. `schemas/time_matrix.py` keeps only the frame length, the figure names and two marks of the old `sheet.json` since implementation 03, Phase 10 |
| Editing | `editing/` | Paste, Recording in Sheet, the parts of a project, the marks of an old `sheet.json`, history |
| Persistence | `storage/` | Every path in one module (`paths.py`); the project bundle, the audio store, finding the project of a part |
| Database | `db/` | The SQLite tables (SQLAlchemy 2 models, times stored and returned in UTC), the Alembic migrations, the users and the sessions, the backup, check and reindex tools |
| The format | `pmn/` | The piano matrix notation: the sparse form and every adapter |

## The one stored file

`parts/<partId>/notes.pmn` in the project bundle under `.database/` (until implementation 02, Phase 3,
`data/audio/<uuid>/matrices/events.json`) — the engine's note events, before any grid was
involved, with an id per note, the hand of each note once the hand split is saved, and the revisions
of section 1 of [pieces-and-revisions.md](pieces-and-revisions.md). The matrix and the hand split are a function of it, so
re-reading a piece at 20 ms instead of 40 is a different parameter rather than a migration.

Its format, the sparse form it is read into, and every conversion (the dense matrix, the COO
payload, the wire columns, MIDI, MuScriptor events, `.pmn.json`) are one package, `pmn/`:
[piano-matrix-notation.md](piano-matrix-notation.md).

Beside it is the sheet: since implementation 03, `sheet.f1`, the reading the AI or the algorithm
wrote and the user changed. `sheet.json` (was `rhythm.json`) is the old sheet's reading; nothing
writes a new one since Phase 10, and an existing one is read only for its armadura, a renamed
reference figure and the marks Phase 9 carries (`part_sheet/legacy.py`). Beside them, `timeline.json` says which audio
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
Every way to run and test it, natively too: [04-local-development.md](../04-local-development.md).

## Where to look deeper

- [time-model.md](time-model.md) — the wall-clock model and the decisions behind it
- [muscriptor.md](muscriptor.md) — the transcription engine, the GPU queue and the live stream
- [pieces-and-revisions.md](pieces-and-revisions.md) — the steps of a piece, the revisions, the `/pieces` routes
- [piano-matrix-notation.md](piano-matrix-notation.md) — the stored form, the wire form, the adapters
- [editing.md](editing.md) — paste, and Recording in Sheet (a passage re-recorded and promoted)
- [api.md](api.md) — the HTTP surface
- [08-security.md](../08-security.md): the users, the session, the rights table
- [`aitu-backend/src/aitu_backend/sheet/README.md`](../../aitu-backend/src/aitu_backend/sheet/README.md) — the new sheet, sections 9 to 17, with a map of the pages that tell each part
- [sheet-f1.md](../../documentation/services/backend/sheet-f1.md) — how a sheet is made, from the notes to `sheet.f1`;
  [sheet-drawing.md](../../documentation/services/backend/sheet-drawing.md) — how the backend draws it
- [../ai/README.md](../ai/README.md) — the AI in the app; its code: [ai-runs.md](../../documentation/services/backend/ai-runs.md)
  and [ai-levels.md](../../documentation/services/backend/ai-levels.md)
- [notation-and-parsing.md](../../documentation/deprecated/notation-and-parsing.md) — deprecated: the text-notation MVP, deleted in implementation 02, Phase 1
- [deprecated/time-matrix.md](../../documentation/deprecated/time-matrix.md) — deprecated: the old sheet's score payload, removed in implementation 03, Phase 10
- [documentation/services/backend/](../../documentation/services/backend) — every endpoint, field,
  path and parameter
