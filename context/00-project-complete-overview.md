# AImpromptu (aitu) — complete project overview

One-shot orientation. Paste this alone to get the whole project.

## What it is

**Play the piano, get readable sheet music.** You bring in a recording — upload it, record from the
browser, or pull it off YouTube — a model transcribes it while you watch the notes appear, you
correct the notes and the hands on a piano roll, and the app writes it out as a staff you can read,
edit, print and play along with.

Two services in one monorepo, plus a rendering library in a sibling checkout. **Local only**: no
cloud, no deploy pipeline, no database, no auth. Both services run in containers on an Ubuntu machine
with an RTX 4090, and the browser on a Mac reaches them through one SSH tunnel
([02b-local-setup.md](02b-local-setup.md) section 12).

| | |
|---|---|
| `aitu-backend` | Python 3.12 / FastAPI. Runs MuScriptor on the GPU, stores the recorded notes, derives everything else |
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
[`decisions.md`](implementations/01-mvp/03-time-based-concept/decisions.md), D-01 … D-34.

## One stored file

```
data/audio/<uuid>/metadata.json             the audio, its cuts and their revision
data/audio/<uuid>/matrices/events.json      the notes, in seconds, with ids, hands and revisions
data/audio/<uuid>/matrices/rhythm.json      what the reader decided on the piano sheet
```

`events.json` is the piano matrix notation in its stored form
([backend/piano-matrix-notation.md](backend/piano-matrix-notation.md)). Since implementation 08 it
also holds the hand of each note once the user saves the hand split, and revision numbers that tell
the app which later step is out of date ([backend/pieces-and-revisions.md](backend/pieces-and-revisions.md)).

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
audio in ──▶ cuts ──▶ MuScriptor (GPU, live) ──▶ events.json (seconds) ◀── edits, saved hands
                          │
                          ├─▶ filters, chord grouping on raw times, snap to columns, split hands
                          ├─▶ gaps → peaks → the plot the reader clicks
                          ├─▶ a ladder the reader names → the figure of every note
                          └─▶ TimeScorePayload ──▶ @aimpromptu/grid-notation ──▶ the staff
```

Step by step, with the reason for each ordering:
[`documentation/services/backend/events-to-sheet.md`](../documentation/services/backend/events-to-sheet.md).

## The screens

**Piece** — the flow page, the way in since implementation 08. Five tabs in the order of the work; a
tab opens only when the step before it is ready ([frontend/flow-page.md](frontend/flow-page.md)):

| Tab | What you do |
|---|---|
| Source | Pick a piece from the library, paste a YouTube URL, or upload a file |
| Audio | See the waveform, play it, cut parts out of the selected region, **Transcribe** |
| Notes | Watch the rectangles appear live, then edit them on a canvas piano roll and play the original audio |
| Hands | **Predict hands**, check the colours along the song, move notes between the hands, **Save** |
| **Sheet** | The product: the peak plot, naming, the staff, the player, every editing control |

**Playground** — Upload / Input (also **Record** and **Compose**), Notes Falling, and the same Piano
Sheet page. **YouTube to Audio** pulls audio off a video. **Video to Notes** reads a Synthesia-style
video into a piece. **Piano Library** is what a performer plays from: browse, tag, playlists, and a
read-only performance page with overlay toggles.

## What a reader can do to a sheet

Name the beat · write the whole piece one step longer or shorter · say the piece changes speed ·
rename one note or a whole passage · choose the key, for the piece or a stretch · correct which hand
plays a note · fingering 1–5 · break or join a beam · octave brackets · take a note off the page ·
accept a suggested trill · words under the staff · print a stretch cue-sized · a grace note leaning
on a note · re-record a marked passage at any speed · add a passage to a piece being composed ·
save the reading with the piece · export a vector PDF · play the recording and follow the line.

Detail: [frontend/annotations.md](frontend/annotations.md). Click by click:
[`user-reviews.md`](implementations/01-mvp/03-time-based-concept/user-reviews.md).

## The API

`127.0.0.1:8765` on the Ubuntu machine (`/api` from the page), docs at `/docs`. The main routers:

| Prefix | For |
|---|---|
| `/audio` | The working store: bring a recording in, its cuts, its waveform, stream it |
| `/matrix` | Run the model, follow it (with the notes, live), read back the notes it heard |
| `/pieces` | Which steps of a piece are ready; the notes as columns and their edits; predict the hands |
| `/time` | The score: peaks, the ladder, the payload, the saved reading |
| `/audio/{uuid}/edits` | Staged re-recording and composing |
| `/library` | Playground versions, promotion, tags, playlists |
| `/youtube` | Downloads, as jobs |
| `/video`, `/frame-examples` | Reading a Synthesia-style video into a piece (implementations 04 and 05) |

Plus `GET /health`, and `GET /scores` / `POST /sequence` — the project's original text-notation MVP,
which still runs but which no screen calls.

## Run locally

On the Ubuntu machine, from the repository root:

```bash
make up           # both containers (the backend on the GPU), waits until they answer
make logs         # follow both
make down
```

On the Mac: `ssh -N -L 5173:localhost:5173 ubuntu`, then open `http://localhost:5173`. Running
natively without containers (`make serve`) still works. See
[04-local-development.md](04-local-development.md).

## Code map

**Backend** `src/aitu_backend/`: `api/` (one router per section), `audio/` (also the cuts and the
frame table), `transcription/` (engines, the GPU queue, the live stream, the lag correction, filters,
events to matrix, jobs, saved hands), `pieces/` (step states and note operations), `pmn/` (the piano
matrix notation and its adapters), `matrix/` (frame ↔ ms, gaps, peaks, the ladder,
passages, figure bands), `hands/` (a beam search with a gated second pass), `notation/` (figures,
tresillos, trills), `editing/` (splice, compose, staging, history), `storage/` (every path in one
module), `schemas/` (Pydantic, camelCase on the wire), `main.py` (a thin factory).

**Frontend** `src/`: `api/` (one module per router), `layout/` (shell and `routes.ts`), `pages/`
(`piece/` is the flow page), `components/{piece,time,notes,audio,input,editing,library,common}/`,
`notes/` (the canvas piano roll's arrays, live feed and edits), `audio/` (cuts, the cut player),
`piano/`, `playback/`, `print/`, `state/`, `ui/`, `music/`.

## What is deliberately gone

Stated so nobody rediscovers it. There is **no** BPM input, **no** granularity choice, **no** Matrix
tab, **no** editing a matrix cell by hand, **no** matrix JSON import or export, **no** bar lines,
time signatures or measures, and **no** text notation as a way to create a piece.

Five Playground tabs were deleted with the tempo model. **Piano Roll** and **Notes Falling** came
back on the wall clock; **Matrix**, **Notes Falling (raw)** and **Music Notation** stay retired —
the first two were views of a grid that no longer exists, and the third is the Piano Sheet tab now.
**Piano Roll** left again in implementation 08: the Notes and Hands tabs of the flow page are the
piano roll visualization now, with an editor. There is also **no** engine choice: MuScriptor is the
only engine the user can run (ByteDance and Transkun stay in the code).

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
