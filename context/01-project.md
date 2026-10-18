# Project

## Name

**AImpromptu** (short: **aitu**). A web app to catalogue existing songs and make their piano
versions.

## What it does

The full product, in the user's own words, is [app/01-app-context.md](app/01-app-context.md): its
glossary is the vocabulary of every page here. In short:

- **A project** turns a recording into a piano sheet. It starts from a source (an audio or a video
  file, or a YouTube link), from scratch (record or paste), or from passages of other projects. The
  app transcribes the audio live, predicts the hands and writes the piano sheet, which the user
  edits: figures, keys, clefs, lyrics, transposition, re-recorded passages.
- **Three storage layers.** Work in progress is in the user's **Personal Vault** (Projects). A
  finished piano sheet is saved to the user's **Private Library** as a **version** of a **song** of
  an **artist**. The **Public Library** is everyone's: a catalogue of songs imported from a chart
  history, with popularity, and the versions users publish to it.
- **Requests.** A user publishes to the Public Library by a request, like a pull request, which the
  **master user** reviews in the Admin panel and accepts in whole or in part.
- **Play mode** shows the piano sheet alone and plays the recording with it, for one song or a
  playlist.

The distinctive part is how the app decides *where* a note goes and *what it is called*: those are
two separate numbers. Position is measured wall-clock time; the figure is a name derived from the
gaps of the playing, which the reader can change. There is no tempo anywhere in the product. See
[backend/time-model.md](backend/time-model.md).

## Who uses it

One musician and the people of their home, on one machine, on their own recordings. It is a
personal app on the home network, not a hosted product: each person signs in with a username and a
password made by the master user ([08-security.md](08-security.md)). A production version (a cloud
host, HTTPS, sign-up, no YouTube download) is later work ([05-deployment.md](05-deployment.md)).

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

**The answer.** Stop deriving position from rhythmic value. Measure position in real time, and name
the rhythm from the playing itself. A wrong name then changes one glyph instead of shifting every
note after it.

Three consequences shape everything else:

1. **A frame keeps its place.** Anything addressed by frame (a fingering, a lyric, a beam break, a
   passage boundary) survives every edit that does not change the length. The edits that change the
   length on purpose (a paste, a promoted recording, a passage added) move everything after them in
   the same write (implementation 02, plan section 4).
2. **Nothing is stored that can be derived.** The engine's notes in milliseconds are kept; the grid,
   the figures and the sheet are rebuilt per request. There is no stale state.
3. **The reader's answer beats the rule.** Every automatic choice has a manual override applied
   last.

## Repository layout

**Monorepo.** Single git root at `aimpromptu/`. The services live as folders; they are not nested
git repositories.

| Path | Role |
|---|---|
| `aitu-backend/` | Python / FastAPI service |
| `aitu-frontend/` | React / TypeScript / Vite app |
| `context/` + `documentation/` | Platform and code-level docs ([00-documentation-instructions.md](00-documentation-instructions.md)) |
| `scripts/` | The link checker of the docs, the seed list of 31 songs, the tunnel from the Mac |
| `pocs/` | Measurement proofs of concept, kept for their data |

The notation renderer, `@aimpromptu/grid-notation`, lives in a **sibling checkout** at
`../vexflow-v2` and is installed from disk. It is a separate repository on purpose: it knows nothing
about this app's API, and this app reaches it through exactly one file.

The data is outside git: `.database/` ([07-database.md](07-database.md)), on this machine at
`/mnt/ssd2/aimpromptu/.database`. The downloaded chart history the Public Library was imported from
is `data/music-library/`, next to the repository ([music-library/reconciliation.md](music-library/reconciliation.md)).

**Containers.** Both services run as Docker containers on the Ubuntu machine, the backend with the
GPU, and a browser at home opens the page at `http://ubuntu:5173`
([04-local-development.md](04-local-development.md)). They are development images; there is no
production image yet.

Historical folder names: `piano-matrix-generation`, `piano-matrix-notation`, workspace
`music-rendering` (now `aimpromptu`).

## How it was built

The implementations, all under [implementations/](implementations/README.md):

| | |
|---|---|
| **01-mvp** (01 to 09) | One audio file to one piano sheet, for one person: the epics master plan, the own renderer, the wall-clock refactor, the video reader, MuScriptor and the move to the Ubuntu machine, the minimal UI guidelines. All closed |
| **02-private-web-app** | The app of the app context: the design system and the sidebar, `.database/`, users on the home network, projects, the Private and Public Libraries, the sheet toolbox, copy and paste, Recording in Sheet, playlists, Play mode, requests and the review, sharing. Phases 0 to 15 complete 2026-10-18; Phases 16 and 17 (the `spain` and `catalan` regions, a popularity inferred from YouTube views) added the same day |

The wall-clock refactor (01-mvp/03) replaced the model the first epics were built on;
[`wall-clock-rewrite.md`](implementations/01-mvp/01-epics-master-plan/plan/wall-clock-rewrite.md)
is the bridge, and its five rules still bind new work.

## Out of scope for this version

- Cloud hosting, CI/CD, production images, HTTPS ([05-deployment.md](05-deployment.md))
- Public sign-up, email, password recovery
- Offline downloads per project (decision Q-7: left for the production version)
- A synthesized sound from the notes: only recorded audio plays

## Where to look deeper

- Complete orientation: [00-project-complete-overview.md](00-project-complete-overview.md)
- The app, in the user's words: [app/01-app-context.md](app/01-app-context.md)
- The model: [backend/time-model.md](backend/time-model.md)
- Services and ports: [03-services-overview.md](03-services-overview.md)
- Running it: [04-local-development.md](04-local-development.md)
- Backend: [backend/README.md](backend/README.md) · Frontend: [frontend/README.md](frontend/README.md)
  · The music library: [music-library/README.md](music-library/README.md)
