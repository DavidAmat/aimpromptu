# aitu-backend

Python 3.12 / FastAPI service. It runs the piano transcription model, stores the one file that
cannot be recreated, and derives everything else from it on demand: the wall-clock matrix, the
distribution of gaps, the figure of every note, and the score payload the browser draws.

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
| HTTP | `api/` | One router per product section; `main.py` is a thin factory |
| Audio | `audio/` | Upload, browser recording, YouTube, ffmpeg normalisation, waveforms |
| Transcription | `transcription/` | Engines, the artifact and leakage filters, events to matrix, jobs |
| The grid and its measurement | `matrix/` | Frame ↔ ms, gaps, peaks, the ladder, passages, figure bands |
| Hands | `hands/` | Which hand plays each onset: a beam search with a gated second pass |
| Naming notes | `notation/` | Figures, tresillos, trills |
| Contracts | `schemas/` | Pydantic models, camelCase on the wire, mirrored in TypeScript |
| Editing | `editing/` | The replacement splice, composing, staging, history |
| Persistence | `storage/` | Every path in one module; playground versions, library, playlists |

## The one stored file

`data/audio/<uuid>/matrices/events.json` — the engine's note events in seconds, before any grid was
involved. Everything else about the music is a function of it, so re-reading a piece at 20 ms
instead of 40 is a different query string rather than a migration.

The one thing stored beside it is `rhythm.json`: what the reader decided, which is the only thing
about a piece that nothing can derive.

## API

`127.0.0.1:8765`, interactive docs at `/docs`. Overview: [api.md](api.md).

## Notebooks

Interactive POC demos live under `notebooks/<theme>/` — one thematic subfolder per POC. Do not
deep-read them; they import `aitu_backend` to stay in sync with the package.

## Run

```bash
cd aitu-backend && uv sync && make serve
```

Or both services from the repository root with `make serve`. See
[04-local-development.md](../04-local-development.md).

## Where to look deeper

- [time-model.md](time-model.md) — the wall-clock model and the decisions behind it
- [editing.md](editing.md) — re-recording a passage, and composing a piece from nothing
- [api.md](api.md) — the HTTP surface
- [notation-and-parsing.md](notation-and-parsing.md) — the text-notation MVP path
- [documentation/services/backend/](../../documentation/services/backend/) — every endpoint, field,
  path and parameter
