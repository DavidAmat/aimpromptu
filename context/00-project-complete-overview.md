# AImpromptu (aitu) — complete project overview

One-shot orientation. Paste this alone to get the whole project.

## What it is

**A web app to catalogue songs and make their piano versions** ([app/01-app-context.md](app/01-app-context.md),
in the user's words). You bring in a recording (upload it, record it in the browser, or download it
from YouTube), a model transcribes it while you watch the notes appear, you correct the notes and the
hands on a piano roll, and the app writes it out as a piano sheet you can read, edit, print and play
from. A finished piano sheet becomes a **version** of a **song** in your own library, and can be
published to the **Public Library** that every user shares, after the master user reviews it.

Two services in one monorepo, plus a rendering library in a sibling checkout. **A personal version on
a home network**: no cloud and no deploy pipeline ([05-deployment.md](05-deployment.md)). Both
services run in containers on an Ubuntu machine with an RTX 4090, and the browser of any device at
home opens the page at `http://ubuntu:5173`. Everything the app knows is in one folder,
`.database/` (SQLite and files, [07-database.md](07-database.md)).

| | |
|---|---|
| `aitu-backend` | Python 3.12 / FastAPI. Runs MuScriptor on the GPU, stores the recorded notes, derives everything else, keeps the music library |
| `aitu-frontend` | React 19 + TypeScript + Vite + MUI. Every screen, every pixel of the sheet |
| `../vexflow-v2` | `@aimpromptu/grid-notation` — the notation renderer, installed from disk |

How it was built: the MVP (implementations 01 to 09), then implementation 02, the private web app
(Phases 0 to 15, closed 2026-10-18): [implementations/README.md](implementations/README.md).

## Users

Every page asks to sign in, and every route of the backend needs a session. The **master user** is
made on the first start from `.env`; it makes the other users in **Admin → Users** (there is no
sign-up), reviews the requests to the Public Library and uses Lab. Each user reads and changes only
their own projects and library, unless an owner shares their library; the master user has no extra
right over another user's private work. The cookie, the rights table and what a home network does
not protect: [08-security.md](08-security.md).

## The one idea everything follows from

A matrix column used to do two jobs: it was **where a note sits on the page** and it was **the
rhythmic value of that note**. Because it was both, its width came from a tempo somebody typed in,
and a grid that cannot express the playing produces the same wrong figure every time — a run of
equal notes printed as a mix of sixteenths and dotted eighths, every time.

The two jobs are now separate numbers.

- **Position is measured wall-clock time.** A column (a **frame**) is a fixed slice of real time,
  40 ms by default. The frame of an onset is `round(onset_ms / frameMs)`. Nothing is fitted.
- **The figure is a name.** The gaps between one note and the next pile up around a few lengths; the
  highest pile is a **negra** by default, and every other note takes its name from it. The reader
  changes that choice with **Figures transposition** or note by note.
- **There is no BPM anywhere in the product.** Not in the transcription, not in the drawing, not in
  any file format.

Renaming a note moves nothing. Full reasoning: [backend/time-model.md](backend/time-model.md). The
frozen decisions behind it are [`decisions.md`](implementations/01-mvp/03-time-based-concept/decisions.md),
D-01 … D-34; implementation 02 changed three of them on purpose (its plan, section 4).

## What is stored

```
.database/aitu.sqlite                                             every record: users, projects, the music library, requests
.database/audio/<sha256>.<ext>                                    every audio file, once, never changed
.database/users/<user>/vault/<projectId>/                         the Personal Vault: work in progress
.database/users/<user>/library/<projectId>/                       the Private Library: finished versions
.database/public/<projectId>/                                     the Public Library's versions
.database/requests/<projectId>/                                   the copy a request sent, kept with it
<projectId>/project.json                                          a project: title, kind, owner, its parts in order
<projectId>/parts/<partId>/notes.pmn                              the notes, with ids, hands and revisions
<projectId>/parts/<partId>/sheet.json                             what the reader decided on the piano sheet
<projectId>/parts/<partId>/timeline.json                          the audio files it plays, their ranges, the cuts
```

A project is the work; it has one **part**, or one per sub-song for an integrated playlist. The uuid
of the routes is the id of a part. `notes.pmn` is the piano matrix notation in its stored form
([backend/piano-matrix-notation.md](backend/piano-matrix-notation.md)), with revision numbers that
say which later step is out of date ([backend/pieces-and-revisions.md](backend/pieces-and-revisions.md)).
An audio file is stored once by its content, so a copy, a paste or a pull copies no audio bytes.

Everything else about the music is derived on every request: the matrix, the gap distribution, the
figure of each note, the sheet. Reading the same piece at 20 ms is another request, not another
stored file, and there is no state on disk that can disagree with the screen. `sheet.json` holds
only what a person chose: the key and its stretches, renamed figures, beams, clefs, octave
brackets, fingering, trills, grace notes, lyrics, spacing. `make db-backup`, `db-restore`,
`db-check` and `db-reindex` keep the folder ([07-database.md](07-database.md)).

## The flow of a piano sheet

```
audio in ──▶ cuts ──▶ MuScriptor (GPU, live) ──▶ notes.pmn (ms) ◀── edits, saved hands
                          │
                          ├─▶ filters, chord grouping on raw times, snap to frames, split hands
                          ├─▶ gaps → the highest pile is a negra → the figure of every note
                          └─▶ TimeScorePayload ──▶ @aimpromptu/grid-notation ──▶ the piano sheet
```

Step by step, with the reason for each ordering:
[`documentation/services/backend/events-to-sheet.md`](../documentation/services/backend/events-to-sheet.md).

## The screens

A sign-in page, then a left sidebar in black, white and grey (colour only on the music;
[frontend/README.md](frontend/README.md), [frontend/pages.md](frontend/pages.md)):

| Sidebar | What it is |
|---|---|
| **Search** (`⌘K`) | Songs, artists and projects of every library the user may read |
| **Projects** | The Personal Vault. **New project**: From source, From scratch, From other projects; **Import** a `.aitu` file; per row Duplicate, Export, Rename, Delete |
| **My library**: Songs, Artists, Playlists, Shared | The Private Library: songs with their versions, artists with several names, songs playlists, the libraries others share with you |
| **Public library**: Songs, Artists, Playlists | Every user's catalogue: 9,055 songs imported from a chart history, with popularity, filters, versions and likes |
| **Requests** | What you asked to publish, with a number when a change is asked |
| **Admin** (master user): Review, Users, Lab | The review of requests, the users, the video reader's pages |

**A project** goes through five steps in the order of the work; a step opens only when the step
before it is ready ([frontend/projects.md](frontend/projects.md)):

| Step | What you do |
|---|---|
| Source | Drop an audio or a video file, or paste a YouTube link (as audio, or as a piano roll video) |
| Audio | See the waveform, play it, cut parts out, add another audio at the end, **Transcribe**. For a video: **Video**, fit the piano, **Read notes** |
| Notes | Watch the rectangles appear live, then edit them on a canvas piano roll |
| Hands | **Predict hands**, check the colours, move notes between the hands, **Save** |
| **Sheet** | The piano sheet, drawn on arrival; the floating bar; the sheet toolbox (title, key, transposition, lyrics, layout), the range and note toolboxes |

**From scratch** starts on a blank sheet, to record or paste into. **From other projects** picks
passages of other projects, one after the other or under a subheader, and saves them as a song or as
an **integrated playlist** (one part per sub-song) ([frontend/playlists.md](frontend/playlists.md)).
A marked passage opens **Recording in Sheet**: **Current** and **Proposal**, a recorded take
transcribed in the passage's key, then promoted ([frontend/recording-in-sheet.md](frontend/recording-in-sheet.md)).

**My library** ([music-library/private-library.md](music-library/private-library.md)): **Save to
library** asks the artist, the song and a version name, moves the project there (its audio written
again with only the ranges in use) and opens the song. A version opens read only; **Edit** makes a
copy in Projects, which then replaces the version (its earlier state kept in a history) or becomes a
new one.

**The Public Library** ([music-library/ontology.md](music-library/ontology.md),
[music-library/popularity.md](music-library/popularity.md)): search, chips for decade, region, genre
and tag, sort by popularity (worked out for the decade chosen), year or title; one song with its
chart line, its fixed versions (Hard, Medium, Easy) and Other versions by user; **Add to my library**
for a song, an artist or a playlist.

**Requests and the review** ([music-library/requests.md](music-library/requests.md)): **Publish** a
version or a playlist, **Suggest a change**, **Propose a song**, **Ask for a fixed version**. The
master user reviews a request like a pull request (a Conversation with comments on a stretch of the
sheet, a Sheet tab with Proposed and Now) and decides each item; what is accepted is written in one
transaction, credited to its author. **Share my library** lets other users read your library.

**Play mode** ([frontend/play-mode.md](frontend/play-mode.md)) shows the sheet alone and plays it,
keeping the cursor in the middle of the window: a project, a version, an integrated playlist
nonstop, a songs playlist song by song; lyrics show by their frames; **Notes Falling** is one of its
views.

## What a reader can do to a sheet

Name the figures (Figures transposition) · move every note by an interval (Notes transposition) ·
choose the key, for the piece or a stretch · correct which hand plays a note · fingering 1–5 · break
or join a beam · clefs and octave brackets, automatic for the left hand · take a note off the page ·
accept a suggested trill · lyrics dragged onto their frames · a stretch cue-sized · grace notes ·
re-record a marked passage and promote it · copy and paste a passage, across projects · undo every
step · export a vector PDF · play the recording and follow the line.

Detail: [frontend/annotations.md](frontend/annotations.md) and the pages it links.

## The API

`127.0.0.1:8765` on the Ubuntu machine (`/api` from the page), docs at `/docs`. One router per
section ([backend/api.md](backend/api.md), every route in
[`endpoints.md`](../documentation/services/backend/endpoints.md)):

| Prefix | For |
|---|---|
| `/auth`, `/admin` | Sign in, sign out, one's password; the users (master user only) |
| `/projects` | The Personal Vault: list, create, rename, delete, duplicate, export, import, compose, save to library |
| `/audio`, `/youtube` | Bring a recording in, its cuts, its waveform, stream it; downloads as jobs |
| `/matrix`, `/pieces`, `/time` | Run the model and follow it live; the steps and the notes; the piano sheet and its saved reading |
| `/passages` | Recording in Sheet: a passage, its takes, the promotion |
| `/library`, `/playlists` | The Private Library: songs, artists, versions, history; songs playlists |
| `/public` | The Public Library: lists, one song or artist, likes, Add to my library |
| `/requests`, `/admin/requests` | Requests, their conversation, the review |
| `/shares`, `/shared` | Sharing one's library, and reading the ones shared with you |
| `/video`, `/frame-examples` | Reading a Synthesia-style video into a project (implementations 04 and 05) |

Plus `GET /health`. Every route except `/health` and `POST /auth/login` needs a session.

## Run it

On the Ubuntu machine, `make up` from the repository root; then any device at home opens
`http://ubuntu:5173` and signs in. Every command, the first master password, the tunnel, the native
run and the troubleshooting are in one place: [04-local-development.md](04-local-development.md).

## Code map

**Backend** `src/aitu_backend/`: `api/` (one router per section), `auth/` (the session, the
passwords, the rights check), `audio/` (cuts, the frame table, the audio written again on save),
`transcription/` (engines, the GPU queue, the live stream, filters, jobs, saved hands), `pieces/`,
`pmn/` (the piano matrix notation and its adapters), `matrix/` (frame ↔ ms, gaps, peaks, figure
bands), `hands/`, `notation/`, `editing/` (splice, compose, paste, passages, history), `library/`
(the private and public rows, the import, popularity, pull, requests, shares), `storage/` (every
path in one module, the project bundle, the audio store), `db/` (the tables, the Alembic revisions,
the backup and check tools), `schemas/`, `main.py`.

**Frontend** `src/`: `api/` (one module per router), `layout/` (the shell, `routes.ts`, the guards),
`pages/` (`piece/` the steps and the sheet, `compose/`, `library/`, `public/`, `requests/`, `play/`,
`admin/`, `video/`), `components/`, `notes/` (the canvas piano roll), `audio/`, `playback/`,
`print/`, `state/`, `ui/` (the tokens, the light and dark theme, the shared components).

## What is deliberately gone

Stated so nobody rediscovers it. There is **no** BPM input, **no** granularity choice, **no** Matrix
tab, **no** editing a matrix cell by hand, **no** bar lines, time signatures or measures, **no** text
notation as a way to create a piece, and **no** plot of gaps to click (the highest pile is a negra by
default since implementation 02, Phase 2). The Playground, YouTube to Audio and the old Piano Library
left in implementation 02, Phase 1 (decision Q-4); their old addresses redirected until Phase 15.
There is **no** engine choice: MuScriptor is the only engine the user can run (ByteDance and Transkun
stay in the code). **Offline downloads** per project are left for a production version (Q-7).

If one of these should return, it is a new feature request with its own reasoning, not unfinished
work.

## Where to look next

- The app, in the user's words: [app/01-app-context.md](app/01-app-context.md)
- Platform: [01-project.md](01-project.md) · [02-tech-stack.md](02-tech-stack.md) ·
  [03-services-overview.md](03-services-overview.md) · [04-local-development.md](04-local-development.md) ·
  [05-deployment.md](05-deployment.md) · [07-database.md](07-database.md) · [08-security.md](08-security.md)
- The model: [backend/time-model.md](backend/time-model.md)
- The music library: [music-library/README.md](music-library/README.md)
- Backend: [backend/README.md](backend/README.md) ·
  detail [../documentation/services/backend/](../documentation/services/backend/)
- Frontend: [frontend/README.md](frontend/README.md) ·
  detail [../documentation/services/frontend/](../documentation/services/frontend/)
- How it got here: [implementations/README.md](implementations/README.md)
- Full index: [00-index.md](00-index.md)
