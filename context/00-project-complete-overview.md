# AImpromptu (aitu) — complete project overview

One-shot orientation. Paste this alone to get the whole project.

## What it is

**Play the piano, get readable sheet music.** You bring in a recording — upload it, record from the
browser, or pull it off YouTube — a model transcribes it, and the app writes it out as a staff you
can read, edit, print and play along with.

Two services in one monorepo, plus a rendering library in a sibling checkout. **POC, local only**:
no cloud, no deploy pipeline, no database, no auth.

| | |
|---|---|
| `aitu-backend` | Python 3.12 / FastAPI. Runs the model, stores the recorded notes, derives everything else |
| `aitu-frontend` | React 19 + TypeScript + Vite. Every screen, every pixel of the sheet |
| `../vexflow-v2` | `@aimpromptu/grid-notation` — the notation renderer, installed from disk |

## The one idea everything follows from

A matrix column used to do two jobs: it was **where a note sits on the page** and it was **the
rhythmic value of that note**. Because it was both, its width came from a tempo somebody typed in,
and a grid that cannot express the playing produces the same wrong figure every time — a run of
equal notes printed as a mix of sixteenths and dotted eighths, every time.

The two jobs are now separate numbers.

- **Position is measured wall-clock time.** A column is a fixed slice of real time, 40 ms by
  default. The column of an onset is `round(onset_ms / frameMs)`. Nothing is fitted to anything.
- **The figure is a name the reader chooses.** You look at a picture of how the piece was actually
  played — the distribution of gaps between one note and the next — click the gap that keeps
  repeating, and say what it is called. Every other note takes its name from that one choice.
- **There is no BPM anywhere in the product.** Not in the transcription, not in the drawing, not in
  any file format.

Renaming a note moves nothing. Changing your mind costs one click and no re-timing.

Full reasoning: [backend/time-model.md](backend/time-model.md). The frozen decisions behind it are
[`decisions.md`](implementations/03-time-based-concept/decisions.md), D-01 … D-34.

## One stored file

```
data/audio/<uuid>/matrices/events.json      the engine's notes, in seconds — KEPT FOREVER
data/audio/<uuid>/matrices/rhythm.json      what the reader decided
```

Everything else about the music is derived on every request: the matrix, the gap distribution, the
figure of each note, the sheet. That is what makes the column length a query parameter rather than a
migration — reading the same piece at 20 ms is another request, not another stored artifact, and
there is no state on disk that can disagree with the screen.

`rhythm.json` holds the only things that are *not* derivable, because a person chose them: which
pile is the beat and what it is called, the key, where the piece changes speed, renamed figures,
beam breaks, notes taken off the page, fingering, trills, grace notes, words under the staff and
cue-size stretches.

## The flow

```
audio in ──▶ engine ──▶ events.json (seconds)
                          │
                          ├─▶ filters, chord grouping on raw times, snap to columns, split hands
                          ├─▶ gaps → peaks → the plot the reader clicks
                          ├─▶ a ladder the reader names → the figure of every note
                          └─▶ TimeScorePayload ──▶ @aimpromptu/grid-notation ──▶ the staff
```

Step by step, with the reason for each ordering:
[`documentation/services/backend/events-to-sheet.md`](../documentation/services/backend/events-to-sheet.md).

## The screens

**Playground** — four tabs, in the order of the work:

| Tab | What you do |
|---|---|
| Upload / Input | Bring a piece in: upload, record, the audio library, or **Compose** an empty one |
| Piano Roll | The recording against a keyboard, left to right, in seconds |
| Notes Falling | The same notes arriving at the keys |
| **Piano Sheet** | The product: the peak plot, naming, the staff, the player, every editing control |

**YouTube to Audio** pulls audio off a video. **Piano Library** is what a performer plays from:
browse, tag, playlists, and a read-only performance page with overlay toggles.

## What a reader can do to a sheet

Name the beat · write the whole piece one step longer or shorter · say the piece changes speed ·
rename one note or a whole passage · choose the key, for the piece or a stretch · correct which hand
plays a note · fingering 1–5 · break or join a beam · octave brackets · take a note off the page ·
accept a suggested trill · words under the staff · print a stretch cue-sized · a grace note leaning
on a note · re-record a marked passage at any speed · add a passage to a piece being composed ·
save the reading with the piece · export a vector PDF · play the recording and follow the line.

Detail: [frontend/annotations.md](frontend/annotations.md). Click by click:
[`user-reviews.md`](implementations/03-time-based-concept/user-reviews.md).

## The API

`127.0.0.1:8765`, docs at `/docs`. Six routers:

| Prefix | For |
|---|---|
| `/audio` | The working store: bring a recording in, trim it, stream it |
| `/matrix` | Run the model, follow it, read back the notes it heard |
| `/time` | The score: peaks, the ladder, the payload, the saved reading |
| `/audio/{uuid}/edits` | Staged re-recording and composing |
| `/library` | Playground versions, promotion, tags, playlists |
| `/youtube` | Downloads |

Plus `GET /health`, and `GET /scores` / `POST /sequence` — the project's original text-notation MVP,
which still runs but which no screen calls.

## Run locally

```bash
make serve        # both services, from the repository root
make logs         # follow both
make stop
```

Backend `http://127.0.0.1:8765`, app `http://localhost:5173`. Or one at a time:

```bash
cd aitu-backend  && uv sync && make serve
cd aitu-frontend && npm install && npm run dev
```

`ffmpeg` must be on `PATH`. The transcription models are an optional extra
(`uv sync --extra transcription`, a ~200 MB torch download); without one the `silent` engine still
lets every screen be exercised end to end. See [04-local-development.md](04-local-development.md).

## Code map

**Backend** `src/aitu_backend/`: `api/` (one router per section), `audio/`, `transcription/`
(engines, filters, events to matrix, jobs), `matrix/` (frame ↔ ms, gaps, peaks, the ladder,
passages, figure bands), `hands/` (a beam search with a gated second pass), `notation/` (figures,
tresillos, trills), `editing/` (splice, compose, staging, history), `storage/` (every path in one
module), `schemas/` (Pydantic, camelCase on the wire), `main.py` (a thin factory).

**Frontend** `src/`: `api/` (one module per router), `layout/` (shell and `routes.ts`), `pages/`,
`components/{time,notes,audio,input,editing,library,common}/`, `piano/`, `playback/`, `print/`,
`state/`, `ui/`, `music/`.

## What is deliberately gone

Stated so nobody rediscovers it. There is **no** BPM input, **no** granularity choice, **no** Matrix
tab, **no** editing a matrix cell by hand, **no** matrix JSON import or export, **no** bar lines,
time signatures or measures, and **no** text notation as a way to create a piece.

Five Playground tabs were deleted with the tempo model. **Piano Roll** and **Notes Falling** came
back on the wall clock; **Matrix**, **Notes Falling (raw)** and **Music Notation** stay retired —
the first two were views of a grid that no longer exists, and the third is the Piano Sheet tab now.

If one of these should return, it is a new feature request with its own reasoning, not unfinished
work.

## Where to look next

- Platform: [01-project.md](01-project.md) · [02-tech-stack.md](02-tech-stack.md) ·
  [03-services-overview.md](03-services-overview.md) · [04-local-development.md](04-local-development.md)
- The model: [backend/time-model.md](backend/time-model.md)
- Backend: [backend/README.md](backend/README.md) ·
  detail [../documentation/services/backend/](../documentation/services/backend/)
- Frontend: [frontend/README.md](frontend/README.md) ·
  detail [../documentation/services/frontend/](../documentation/services/frontend/)
- How it got here: [implementations/README.md](implementations/README.md)
- Full index: [00-index.md](00-index.md)
