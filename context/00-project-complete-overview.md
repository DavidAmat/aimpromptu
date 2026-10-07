# AImpromptu (aitu) — complete project overview

One-shot orientation. Paste this alone to get the whole project.

## What it is

**Play the piano, get readable sheet music.** You bring in a recording — upload it, record from the
browser, or pull it off YouTube — a model transcribes it while you watch the notes appear, you
correct the notes and the hands on a piano roll, and the app writes it out as a staff you can read,
edit, print and play along with.

Two services in one monorepo, plus a rendering library in a sibling checkout. **Local only**: no
cloud and no deploy pipeline. Everything is stored in one folder, `.database/` (SQLite and files,
implementation 02, Phase 3). Both services run in containers on an Ubuntu machine with an RTX 4090,
and the browser of any device of the home network opens the page at `http://ubuntu:5173`
([02b-local-setup.md](02b-local-setup.md) section 12; the SSH tunnel still works).

**Users** (implementation 02, Phase 4). Every page asks to sign in, and every route of the backend
needs a session. The master user is made on the first start from `.env` and makes the other users
in **Admin → Users**; there is no sign-up. Each user sees and changes only their own projects, and
the master user has no right over another user's private projects. The users, the session cookie,
the rights table and what this setup does not protect: [08-security.md](08-security.md).

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
.database/users/<user>/<layer>/<projectId>/project.json            the project: title, owner, parts
.database/users/<user>/<layer>/<projectId>/parts/<partId>/notes.pmn      the notes, with ids, hands and revisions
.database/users/<user>/<layer>/<projectId>/parts/<partId>/sheet.json     what the reader decided on the piano sheet
.database/users/<user>/<layer>/<projectId>/parts/<partId>/timeline.json  the audio files it plays, and the cuts
.database/audio/<sha256>.<ext>                                     every audio file, once
```

A piece is a **part** of a **project**; the uuid of the routes is the id of the part
([07-database.md](07-database.md)). `notes.pmn` is the piano matrix notation in its stored form
([backend/piano-matrix-notation.md](backend/piano-matrix-notation.md)). Since implementation 08 it
also holds the hand of each note once the user saves the hand split, and revision numbers that tell
the app which later step is out of date ([backend/pieces-and-revisions.md](backend/pieces-and-revisions.md)).

Everything else about the music is derived on every request: the matrix, the gap distribution, the
figure of each note, the sheet. That is what makes the column length a query parameter rather than a
migration — reading the same piece at 20 ms is another request, not another stored artifact, and
there is no state on disk that can disagree with the screen.

`sheet.json` holds the only things that are *not* derivable, because a person chose them: which
pile is the beat and what it is called, the key, where the piece changes speed, renamed figures,
beam breaks, notes taken off the page, fingering, trills, grace notes, words under the staff and
cue-size stretches.

## The flow

```
audio in ──▶ cuts ──▶ MuScriptor (GPU, live) ──▶ notes.pmn (ms) ◀── edits, saved hands
                          │
                          ├─▶ filters, chord grouping on raw times, snap to columns, split hands
                          ├─▶ gaps → peaks → the plot the reader clicks
                          ├─▶ a ladder the reader names → the figure of every note
                          └─▶ TimeScorePayload ──▶ @aimpromptu/grid-notation ──▶ the staff
```

Step by step, with the reason for each ordering:
[`documentation/services/backend/events-to-sheet.md`](../documentation/services/backend/events-to-sheet.md).

## The screens

A sign-in page first (**Username**, **Password**, **Sign in**). Then a left sidebar with **Search**
(`⌘K`), **Projects**, **My library** (**Songs**, **Artists**), and for the master user an **Admin**
group with **Users** and **Lab**, in black,
white and grey with colour only on the music (implementation 02, Phase 1;
[frontend/README.md](frontend/README.md)). The user menu at the bottom changes the password, chooses
the theme (**Light**, **Dark** or **System**; the piano sheet stays white paper) and signs out.

**Projects** — the way in: the Personal Vault, with **New project** (From source; From scratch and
From other projects later), **Import** of a `.aitu` file, and per row Duplicate, Export, Rename and
Delete. A project goes through five steps in the order of the
work; a step opens only when the step before it is ready ([frontend/projects.md](frontend/projects.md)):

| Step | What you do |
|---|---|
| Source | Drop an audio or a video file, or paste a YouTube link (as audio, or as a piano roll video) |
| Audio | See the waveform, play it, cut parts out, add another audio at the end, **Transcribe**. For a video project this step is **Video**: fit the piano on the video, **Read notes** |
| Notes | Watch the rectangles appear live, then edit them on a canvas piano roll and play the original audio |
| Hands | **Predict hands**, check the colours along the song, move notes between the hands, **Save** |
| **Sheet** | The product: the staff drawn on arrival (the highest pile of gaps is a negra), the floating bar, the sheet, note and range toolboxes |

**My library** — finished work (implementation 02, Phase 6;
[music-library/private-library.md](music-library/private-library.md)). **Save to library** on a
project with its sheet saved asks the artist, the song and a version name, moves it there (its audio
written again with only the ranges in use, its temporary files deleted), and opens the song. A
version opens read only; **Edit** makes a copy in Projects, which then **replaces the version** (its
earlier state kept in a history that can be restored) or becomes a new version. Artists have
several names and can be merged.

**Notes Falling** opens from a project's `⋯` menu. **Lab** (master user only) holds the video
reader's pages: it reads a Synthesia-style video into a piece. **Users** (master user only) makes
users, disables them and resets a password. The Playground, YouTube to Audio and the old Piano Library were
removed in implementation 02, Phase 1 (decision Q-4).

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
| `/projects` | The Personal Vault: list, create, rename, delete, duplicate, export and import a project |
| `/youtube` | Downloads, as jobs |
| `/auth`, `/admin` | Sign in, sign out, change one's password; the users (master user only) |
| `/video`, `/frame-examples` | Reading a Synthesia-style video into a piece (implementations 04 and 05) |

Plus `GET /health`. Every route except `/health` and `POST /auth/login` needs a session. The
project's original text-notation MVP (`GET /scores`, `POST /sequence`) was deleted in
implementation 02, Phase 1, and the old `/library` router in Phase 3.

## Run locally

On the Ubuntu machine, from the repository root:

```bash
make up           # both containers (the backend on the GPU), waits until they answer
make logs         # follow both
make down
```

On the Mac: open `http://ubuntu:5173` and sign in (the master user's first password is
`AITU_MASTER_PASSWORD` of `.env`). The SSH tunnel (`ssh -N -L 5173:localhost:5173 ubuntu`, then
`http://localhost:5173`) is the fallback. Running natively without containers (`make serve`) still works. See
[04-local-development.md](04-local-development.md).

## Code map

**Backend** `src/aitu_backend/`: `api/` (one router per section), `auth/` (the session, the
passwords, the rights check), `audio/` (also the cuts and the
frame table), `transcription/` (engines, the GPU queue, the live stream, the lag correction, filters,
events to matrix, jobs, saved hands), `pieces/` (step states and note operations), `pmn/` (the piano
matrix notation and its adapters), `matrix/` (frame ↔ ms, gaps, peaks, the ladder,
passages, figure bands), `hands/` (a beam search with a gated second pass), `notation/` (figures,
tresillos, trills), `editing/` (splice, compose, staging, history), `storage/` (every path in one
module, the project bundle, the audio store), `db/` (the SQLAlchemy tables, the Alembic revisions,
the users, the backup and check tools), `schemas/` (Pydantic, camelCase on the wire),
`main.py` (a thin factory).

**Frontend** `src/`: `api/` (one module per router), `layout/` (shell, `routes.ts`, the guards
`RequireUser` and `RequireMaster`), `pages/` (`LoginPage`, `ProjectsPage`, `admin/UsersPage`, and
`piece/`: the steps of a project), `components/{piece,time,notes,audio,editing,video}/`,
`notes/` (the canvas piano roll's arrays, live feed and edits), `audio/` (cuts, the cut player),
`piano/`, `playback/`, `print/`, `state/` (also the signed-in user), `ui/` (the tokens, the light and dark theme and the shared components), `music/`.

## What is deliberately gone

Stated so nobody rediscovers it. There is **no** BPM input, **no** granularity choice, **no** Matrix
tab, **no** editing a matrix cell by hand, **no** matrix JSON import or export, **no** bar lines,
time signatures or measures, and **no** text notation as a way to create a piece.

Five Playground tabs were deleted with the tempo model. **Piano Roll** and **Notes Falling** came
back on the wall clock; **Matrix**, **Notes Falling (raw)** and **Music Notation** stay retired —
the first two were views of a grid that no longer exists, and the third is the Piano Sheet tab now.
**Piano Roll** left again in implementation 08: the Notes and Hands steps are the piano roll
visualization now, with an editor. The whole Playground left in implementation 02, Phase 1. There is also **no** engine choice: MuScriptor is the
only engine the user can run (ByteDance and Transkun stay in the code).

If one of these should return, it is a new feature request with its own reasoning, not unfinished
work.

## Where to look next

- Platform: [01-project.md](01-project.md) · [02-tech-stack.md](02-tech-stack.md) ·
  [03-services-overview.md](03-services-overview.md) · [04-local-development.md](04-local-development.md) ·
  [08-security.md](08-security.md)
- The model: [backend/time-model.md](backend/time-model.md)
- Backend: [backend/README.md](backend/README.md) ·
  detail [../documentation/services/backend/](../documentation/services/backend/)
- Frontend: [frontend/README.md](frontend/README.md) ·
  detail [../documentation/services/frontend/](../documentation/services/frontend/)
- How it got here: [implementations/README.md](implementations/README.md)
- Full index: [00-index.md](00-index.md)
