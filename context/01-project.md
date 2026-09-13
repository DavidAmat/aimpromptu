# Project

## Name

**AImpromptu** (short: **aitu**). A local app that turns a piano recording into readable sheet
music.

## What it does

You play the piano. The app transcribes the recording, writes it out as a staff, and lets you
correct the reading rather than the recording — name what the beat is, rename a figure, fix which
hand played a note, add fingering and words, and print it.

The distinctive part is how it decides *where* a note goes and *what it is called*: those are two
separate numbers. Position is measured wall-clock time; the figure is a name the reader chooses from
a picture of their own playing. There is no tempo anywhere in the product.

See [backend/time-model.md](backend/time-model.md).

## Who uses it

One musician, on one machine, on their own recordings. It is a local development POC, not a hosted
product: no accounts, no auth, no multi-user anything.

## Problem domain

Standard notation tools expect MIDI, MusicXML or staff entry, and the transcription tools that do
take audio hand you a grid you then have to fight. This project explores a different answer to one
specific failure.

**The failure.** A run of notes played evenly prints as a ragged mix of sixteenths and dotted
eighths, every time. Not because the model heard wrong, and not because of a bug — because a grid
built from a typed tempo cannot express human playing, and every onset has to land on a whole
column of it. A run of notes 106.7 ms apart on a grid of 84.27 ms columns is 1.27 columns per note;
twelve gaps then have to be written as nine short notes and three long ones, and nobody chose the
long ones.

**The answer.** Stop deriving position from rhythmic value. Measure position in real time, and let
the reader name the rhythm. A wrong name then changes one glyph instead of shifting every note
after it.

Three consequences shape everything else:

1. **A column never moves.** Anything addressed by column — a fingering, a lyric, a beam break, a
   passage boundary — survives every edit that does not change the piece's wall-clock length.
2. **Nothing is stored that can be derived.** The engine's notes in seconds are kept; the grid, the
   figures and the sheet are rebuilt per request. There is no stale state.
3. **The reader's answer beats the rule.** Every automatic choice has a manual override applied
   last.

## Repository layout

**Monorepo (POC).** Single git root at `aimpromptu/`. Deployable services live as folders; they are
not nested git repos.

| Path | Role |
|---|---|
| `aitu-backend/` | Python / FastAPI service |
| `aitu-frontend/` | React / TypeScript / Vite app |
| `context/` + `documentation/` | Platform and code-level docs |
| `poc-onset-duration-distribution/` | A measurement POC kept for its data |

The notation renderer, `@aimpromptu/grid-notation`, lives in a **sibling checkout** at
`../vexflow-v2` and is installed from disk. It is a separate repository on purpose: it knows nothing
about this app's API, and this app reaches it through exactly one file.

**Future direction:** package both services as Docker containers. Planned, not built.

Historical folder names: `piano-matrix-generation`, `piano-matrix-notation`, workspace
`music-rendering` (now `aimpromptu`). Phase 0 renamed the services to `aitu-*`.

## How it was built

Two closed implementation plans and one open one, all under
[implementations/](implementations/README.md):

| | |
|---|---|
| **01 — Epics master plan** | Fourteen epics: skeleton, matrix engine, audio, transcription, storage, the Playground, notation, library, range editing, annotations, composing, documentation |
| **02 — VexFlow migration** | Why the project built its own renderer instead of drawing with VexFlow. Closed |
| **03 — Time-based concept** | The wall-clock refactor. Spanned two repositories; closed 2026-08-10 |

The third one replaced the model the first eight epics were built on, which is why several epic
task files were rewritten mid-plan. [`wall-clock-rewrite.md`](implementations/01-epics-master-plan/plan/wall-clock-rewrite.md)
is the bridge between them.

## POC boundaries (out of scope)

- Cloud hosting, CI/CD, Docker images, orchestration
- A database — persistence is the local filesystem
- Authentication, secrets management, network hardening

See [05-deployment.md](05-deployment.md) (stub) and the skipped platform files noted in
[00-index.md](00-index.md).

## Where to look deeper

- Complete orientation: [00-project-complete-overview.md](00-project-complete-overview.md)
- The model: [backend/time-model.md](backend/time-model.md)
- Services and ports: [03-services-overview.md](03-services-overview.md)
- Backend: [backend/README.md](backend/README.md) · Frontend: [frontend/README.md](frontend/README.md)
