# 02: The private web app: implementation plan

Read the prompt this plan answers first: [`02-prompt.md`](02-prompt.md), and the app it describes:
[`../../app/01-app-context.md`](../../app/01-app-context.md). The status lookup is
[`02-checklist.md`](02-checklist.md). Phase reports go beside them as `02-implementation-phase-N.md`,
written by the agent that finishes phase N, following
[`../../language/communication-implementation-plans.md`](../../language/communication-implementation-plans.md)
and [`../../language/communication-style.md`](../../language/communication-style.md).

The binding rules of the project still apply: the five rules of
[`../01-mvp/01-epics-master-plan/plan/wall-clock-rewrite.md`](../01-mvp/01-epics-master-plan/plan/wall-clock-rewrite.md),
the frozen decisions D-01 to D-34 of
[`../01-mvp/03-time-based-concept/decisions.md`](../01-mvp/03-time-based-concept/decisions.md), and the
decisions of implementation 08 ([`../01-mvp/08-new-algorithm-notes-detection-muscriptor/08-plan.md`](../01-mvp/08-new-algorithm-notes-detection-muscriptor/08-plan.md)
section 11). Section 4 checks them one by one. Three of them are changed on purpose, and section 4
says why.

Three rules from the user hold for every phase:

- **Every script that clicks or writes in the app works on a temporary copy of a project**, never on a
  real project of a library.
- **The work runs on the Ubuntu machine; the user looks at the app from the Mac.** Any URL given to the
  user comes with the way to open it (section 9.4).
- **Each phase is built on its own branch, `feat/phase-N`**, made from `master`. When the phase is
  done and the user says it is fine, the branch is merged into `master` locally and `master` is pushed
  to `origin`. There are no pull requests.

**A parallel piece of work.** Another agent builds the data of the Public Library,
from the brief [`public-library-build/02-a-public-library-build-prompt.md`](public-library-build/02-a-public-library-build-prompt.md):
it downloads the chart history, songs, artists, albums and lyrics of `musicchartsarchive.com` into
`data/music-library/` next to the repository (not inside it; changed 2026-10-06). The database Phase 12
reads is `library.sqlite` in that folder. The scripts are `scripts/music-library/`, on the branch
`feat/02-a-public-library` until that branch is merged. This plan does not write to those folders.
Phase 12 is where the two meet (section 15.5). The download and `library.sqlite` are ready (2026-10-07).

---

# 1. Context

## 1.1 What the app does today

After the MVP (implementations 01 to 09, now in [`../01-mvp/`](../01-mvp/)), the app takes one audio
file to one piano sheet. The way in is the flow page (**Piece** in the top bar), with five tabs:
Source, Audio, Notes, Hands, Sheet. MuScriptor transcribes on the RTX 4090 and the notes appear live.
The user edits the rectangles, predicts and corrects the hands, and then works on the piano sheet,
which has a large set of tools: key signature, clef and octave brackets per stretch, figures,
fingering, beams, trills, grace notes, cue size, words under the staff, spacing, re-record a passage,
add a passage, print to PDF, play along.

Around it are older pages: **Playground** (Upload / Input, Notes Falling, Piano Sheet), **YouTube to
Audio**, **Video to Notes** (the reader of piano roll videos, with its development pages) and
**Piano Library** (tracks, tags, playlists and a read-only performance page).

What is stored, from the three surveys made for this plan:

- **No database, no users, no login.** Everything is files under `aitu-backend/data/` (1.2 GB).
- **A piece is one audio uuid**: `data/audio/<uuid>/` with one audio, one `events.json` (the piano
  matrix notation in its stored form), one `rhythm.json` (what the reader decided on the piano sheet),
  cuts in `metadata.json`, and `history/vN/`. 39 folders, 37 with notes, 2 with a saved piano sheet.
- **A second, older storage model** (`data/playground/` and `data/library/`, `.npz` matrices, tracks,
  tags, playlists) is still in the code and is empty on disk. The Piano Library page reads it.
- **Jobs live in memory** (`transcription/jobs.py`: "a single-user local app").
- **The app answers only on `127.0.0.1`**, and the Mac reaches it through one SSH tunnel.

## 1.2 What is wrong or missing

1. **The UI is a proof of concept.** Pages are full of explanations, captions, technical words
   (`ms`, `column`, `f101`, engine names) and plots the user does not need. The sheet page alone is
   5,353 lines in one file (`RhythmPage.tsx`), with five sections of cards above the piano sheet. The
   same upload is reachable from three places, and the piano sheet from two. There is no logical
   order between the sections of the top bar.
2. **There is no user, no project and no library in the sense of the app context.** A piece is an
   audio file. Nothing records a song, an artist, a version, an owner, or a request to publish.
3. **A piece has exactly one audio and one piano matrix notation.** The app context needs a project
   with several audio files played one after the other, and an integrated playlist with several
   `.pmn` files.
4. **New features of the app context do not exist yet**: transposition, the new lyrics, copy and
   paste of passages, Recording in Sheet with Current and Proposal, projects made from other projects,
   playlists of two kinds, Play mode, the public library with its ontology, popularity, requests and
   the Admin panel.
5. **The documentation is stale.** The move of the MVP folders into `01-mvp/` broke about 120
   relative links, and about a dozen pages say "no database, no auth, one user", which this work makes
   false.

## 1.3 Where the work runs

Everything runs on the Ubuntu machine (`david-ubuntu`, RTX 4090, described in
[`../../02b-local-setup.md`](../../02b-local-setup.md) section 12): the code, the containers, the
`.database/` folder and the agent. The Mac is a browser. After Phase 4, any device on the home network
is also a browser (decision Q-2).

---

# 2. Terminology

The words of the app context, each with one meaning. New words are explained here once and then used
the same way everywhere.

**From the app context (used exactly as the user wrote them):**

- **Piano Matrix Notation**, **`.pmn`**: the matrix only (88 keys as rows, frames as columns, onset
  `1`, sustain `-1`, silence `0`), usually in its sparse form. Never the audio and never the metadata.
- **Metadata**: everything on the piano sheet that is not the matrix: title, subtitle, artist name on
  the sheet, key signatures, clefs, octave brackets, figures, beams, fingering, lyrics, spacing, the
  owner's user id.
- **Audio**: the audio files of a project, **aligned** in time with the piano matrix notation.
- **Project**: the bundle of audio, `.pmn` and metadata. A project is attached to a song only at the
  end.
- **The artifacts of a project**: the files of a project, as they are exported and imported.
- **Song**, **artist**, **artist name**, **album**: entities of the music library, each with its own
  id. An artist has one or more artist names, and one of them is the default.
- **Version**: a named pointer from a song to a project. **Fixed versions**: Default, Hard, Medium,
  Easy, and a custom name accepted by the master user. **User versions** (`user_versions/`): one
  project per user and version name.
- **Personal Vault** (layer 1), **Private Library** (layer 2), **Public Library** (layer 3): the three
  storage layers.
- **Master user**: the one user who reviews requests and owns the Public Library.
- **Request**: the "pull request" a user opens to publish into the Public Library. Three kinds (section
  16).
- **Admin Panel**: the pages where the master user reviews requests.
- **Integrated Playlist**, **Songs Playlist**: the two kinds of playlist (section 14).
- **Play mode**: the clean view to play from (section 17).
- **Sheet toolbox**: the toolbox for the whole piano sheet (title, key, transposition, lyrics, layout).
- **Recording in Sheet**, **Current**, **Proposal**: re-recording a passage (section 13).
- **Passage**: a range of frames of a piano sheet.

**From the earlier work (kept):**

- **A frame**: one column of the piano matrix notation as the piano sheet shows it, `frameMs` long
  (40 ms by default). It is what the user calls a frame (`f101` is frame 101). Every mark on the piano
  sheet is keyed by frame.
- **The 10 ms grid**: the axis that the audio and the notes share since implementation 08. A cut, an
  audio segment and a passage of audio are ranges on this grid. A frame of the piano sheet is a whole
  number of 10 ms steps.
- **A cut**: a range removed from the audio of a project.
- **Revision**: a number that goes up by one when the thing it counts changes; **stale**: a step made
  from an older revision (implementation 08, section 8).

**New in this plan:**

- **A part**: one `.pmn` of a project, with its own metadata and its own audio timeline. A normal
  project has one part. An integrated playlist has one part per sub-song separated by a subheader
  (section 8.4).
- **The audio timeline**: the list of audio segments that a part plays one after the other. A segment
  is an audio file and a range of it. A cut, a re-recorded passage and a pasted passage are all changes
  of the timeline (section 8.5).
- **The project bundle**: the folder of a project, with the same layout in the three layers and in an
  export file (section 8.3).
- **`.database/`**: the one folder that holds every record and every file of the app (section 8).
- **Lab**: a section only the master user sees, for the development tools of the video reader.

**Where the user's words and the code's words differ.** The code says *piece* where the app context
says *project*, and `rhythm.json` where the app context says *metadata*. The code changes its words
where a phase rewrites the module anyway (the project bundle, the new routes). It keeps
`/pieces/...` and `/time/...` routes, whose names are not visible to the user (section 8.8).

---

# 3. Decisions

## 3.1 Answered before the plan was written

The user answered four questions on 2026-10-05, each with the recommended option.

**Q-1. What holds the records inside `.database/`?** **Answered: SQLite plus files.** One SQLite file
for the records (users, music library, projects, requests, playlists), and folders beside it for the
audio and the project bundles. The folder is moved by compressing it and decompressing it on another
machine. In the cloud, the folder becomes the volume attached to the instance, or the tables move to
Postgres (section 8).

**Q-2. How do people reach the app?** **Answered: on the home network, with a password login.** The
app answers on the Ubuntu address (`192.168.0.112`), so any device at home opens it with no tunnel.
Each user has a username and a password, the session is a cookie, and the master user is created from
`.env` on the first start (section 9).

**Q-3. Can a re-recorded passage change the length of a song, and is the original audio kept after
cuts?** **Answered: the length may change, and the cut audio is written on save.** A total promotion
of a Proposal may make the song longer or shorter: everything after the passage moves, notes and marks
in the same write, as **Insert** already does when composing. In the Personal Vault, cuts stay as
ranges so they can be undone. When the project is saved to the Private Library, the audio is written
again with only the parts in use, and the original is deleted (sections 4 and 8.5).

**Q-4. What happens to the pages that have no place in the new app?** **Answered: fold them in, and
remove what is dead.** The video becomes a source of **New project → From source**. Notes Falling
becomes a view of Play mode. The development pages of the video reader (Examples, Detection, the score
board) move to **Lab**. The Playground, the old `.npz` library tree and the text-notation MVP
(`/scores`, `/sequence`) are deleted; git history keeps them.

## 3.2 Decided in this plan, without a question

These follow from the answers above or from the code. Each can be changed by the user at any phase.

| # | Choice | Why |
|---|---|---|
| P-1 | Keep React, MUI and the current build; replace the theme and the shared components | The sheet editor, the canvas piano roll and the toolboxes are all MUI. A new library would rewrite them for no gain to the user. The look comes from the tokens of section 7, not from the library |
| P-2 | SQLAlchemy 2 and Alembic for the tables | The same code works on SQLite now and on Postgres later (Q-1). Alembic gives numbered migrations |
| P-3 | Audio files are stored once, named by the hash of their content | A copy and paste of a passage, a duplicated project and a pull from the Public Library then copy no audio bytes, which is what the app context asks ("the clipboard does not keep the audio binary") |
| P-4 | `.database/` is gitignored. On this machine it is not inside the repository: `AITU_DATABASE_DIR` in `.env` is `/mnt/ssd2/aimpromptu/.database` | The bytes stay on the large SSD. A link named `.database` inside the repository makes the editor follow it and watch every file (changed 2026-10-06). `AITU_DATABASE_DIR` can point anywhere |
| P-5 | The stored form of the notes becomes `notes.pmn`: the portable `.pmn.json` of implementation 08, with the header of `events.json` | The file in the bundle is the file in the export: no conversion, so an imported project reads exactly as it was saved (section 8.3) |
| P-6 | The migrated pieces keep their uuid as the id of their part | The routes keyed by uuid keep working while the storage changes under them (section 8.8) |
| P-7 | Users are created by the master user; there is no public sign-up | A home network app. A sign-up page is production work |
| P-8 | A light theme first, with tokens for a dark theme; the piano sheet stays white in both | The 09 guidelines ask to respect the system setting; a piano sheet is a page of paper |

## 3.3 To decide on the go

These cannot be answered well before some work is done. The phase named in each row raises it in
its walkthrough under DECISIONS.

| # | Question | Raised in |
|---|---|---|
| Q-5 | The worldwide source is chosen: `musicchartsarchive.com`, downloaded by the parallel work (section 15.5). Still open: the sources for the `spain` and `catalan` regions, and anything that source does not give (genres, tags) | Phase 12, after the reconciliation |
| Q-6 | The popularity formula: the weights of section 15.6, tuned on the downloaded chart history and on a list of songs the user ranks by hand | Phase 12 |
| Q-7 | "Download offline" per project (like Netflix). On one home server the Private Library is already on the same disk as the app, so true offline needs the browser to keep files (a PWA). Build it now, or leave it for the production version? | Phase 6 (recommendation: leave it for production) |
| Q-8 | Can the video reader stream its notes live, like MuScriptor? | Phase 5, after a measurement. *Measured in Phase 5:* **Read notes** takes about a third of the video's length (61 s for 3:09); only the last 22 s (the stitched roll) could send notes as they come, after about 39 s that read the whole video (frames, background, speed). Raised with the options in the Phase 5 report |

---

# 4. The binding rules, checked one by one

| Rule | How this plan respects it |
|---|---|
| **Rule 1: `events.json` is the piece** | Kept in meaning, renamed in form: the stored notes of a part are `notes.pmn` (P-5). They are still the only stored music; the matrix at any `frameMs`, the gaps, the figures and the sheet are still derived on each request |
| **Rule 2: a column never moves** | **Changed (Q-3).** See below |
| **Rule 3: no BPM, no bar lines, no metre** | Unchanged. Figures transposition renames figures; the speed of a Proposal is a time scale (×0.5, ×2), not a tempo. Neither is stored as a BPM |
| **Rule 4: `frameMs` is a view** | Unchanged. Times are stored in ms. Marks are keyed by frame together with the `frameMs` they were made at, as `rhythm.json` already does |
| **Rule 5: the reader's answer beats the rule** | Every new automatic choice has a manual override: the default figure (D-09 below), the default key signature, the automatic clef and octave brackets |
| **D-09: the app never chooses the ladder** | **Changed.** See below |
| **D-29: every player plays the original recorded onset times** | Unchanged. The audio timeline plays recorded audio, never a synthesized sound |
| **D-30: the sparse matrix is the portable format, with `frameMs` in its header** | `.pmn` is that format |
| **08 Q-1: a cut is a range of frames; the original audio never changes** | **Changed (Q-3).** See below |

**Rule 2 is changed, and this is the reason.** Rule 2 exists so that every mark after an edit stays on
its frame. The app context now asks for three edits that change the length on purpose: a total
promotion of a Proposal, a pasted passage, and a passage added to a project from other projects. The
code already has the answer for one of them: **Insert** of Compose moves every note and every mark
after the insertion point by a whole number of frames in the same write
([`../../backend/editing.md`](../../backend/editing.md)). This plan uses that one operation for the
three edits. Edits that do not ask for a new length (a fixed-window promotion, a re-record that keeps
the original audio) still keep every frame where it is. The phase that makes the change (Phase 8) adds
a note under rule 2 in `wall-clock-rewrite.md`.

**D-09 is changed, and this is the reason.** D-09 said the user always names the figure by clicking a
peak of the plot of gaps. The app context asks to remove that plot: the highest peak is a **negra**
by default, and the user changes the figures with **Figures transposition**, which is the figure
shift of D-18 with the figure icons. The ladder is still the user's to change in one action; only
the first choice is now automatic. Phase 2 adds the note under D-09.

**08 Q-1 is changed, and this is the reason.** In the Personal Vault nothing changes: a cut is a
range, and the original audio stays so that the cut can be undone. When a project is saved to the
Private Library, the audio is written again with only the ranges in use, and the original is deleted
when no other project uses it (section 8.5). The app context asks for this to save disk.

---

# 5. What already exists and is reused

| Thing | Where | Reused for |
|---|---|---|
| The flow page and its five steps | `aitu-frontend/src/pages/piece/` | The From source flow of a project (section 10.2) |
| The canvas piano roll and its editor | `components/notes/PianoRollCanvas.tsx`, `pages/piece/NotesEditor.tsx`, `notes/` | Notes and Hands steps; the Proposal view of Recording in Sheet |
| Revisions and staleness | `pieces/status.py`, `context/backend/pieces-and-revisions.md` | Unchanged, per part |
| The `pmn` package and its adapters | `aitu-backend/src/aitu_backend/pmn/` | `notes.pmn`, the export, the clipboard slice |
| Cuts and the table of frames | `audio/frames.py`, `audio/piece_audio.py` | Generalised into the audio timeline (section 8.5) |
| Staged edit sessions, splice, compose, audio splice | `editing/` (`session.py`, `splice.py`, `compose.py`, `audio_splice.py`) | Recording in Sheet, paste, From other projects |
| Undo and redo | `hooks/useEditHistory.ts` | Every new edit. Its limit is 100 steps, above the 20 the app context asks for |
| The two selections and their toolboxes | `RhythmPage.tsx`, `components/common/ToolboxDialog.tsx` | Kept, restyled, split into modules (Phase 2) |
| Key signature suggestion, octave bracket suggestion | `@aimpromptu/grid-notation` (`suggestKeySignature`, `suggestOttavas`) | The default key; the automatic octave brackets; a new automatic clef rule (Phase 7) |
| The figure shift | `SHIFT_LADDER` in RhythmPage, D-18 | Figures transposition |
| The figure icons | `components/time/FigureGlyph.tsx` | Figures transposition, the note toolbox |
| The words under the staff | `Lyric` in `schemas/rhythm.py`, the Lyrics tab | The new lyrics (section 11.5) |
| Recording, metronome, slowed playing | `audio/useRecorder.ts`, `components/editing/useClickTrack.ts` | Recording in Sheet, From scratch |
| The PDF writer | `src/print/` | Unchanged |
| The read-only performance page | `pages/PerformancePage.tsx`, deleted in Phase 1 with the old Piano Library it read; its loader `library/loadPerformanceScore.ts` is kept | The base of Play mode (git history keeps the page) |
| Notes Falling | `pages/piece/NotesFallingPage.tsx` (moved in Phase 1) | A view of Play mode (Q-4) |
| The video reader | `aitu-backend/src/aitu_backend/video/`, `pages/video/` | A source of From source (Q-4); its development pages in Lab |
| Jobs and progress streams | `transcription/jobs.py`, `hooks/useProgress.ts` | Unchanged, with an owner per job (section 18) |
| The seed list of 31 songs | `scripts/seed/youtube-library/library.json`, `seed-state.json` beside it (it maps each uuid to a title and an artist) | The artist and song of the migrated pieces (Phase 3) |
| Playwright on Ubuntu | `scripts/check-flow.mjs`, `screenshot.mjs` | Screenshots at the end of every UI phase |

---

# 6. The structure of the app

## 6.1 Who is on it and what they do

| Person | Comes to |
|---|---|
| A user | Make a piano sheet from a song (a project), keep it in their library, play from it, publish it |
| The master user | The same, and review requests, manage users, use Lab |
| A first-time user | Find a song in the Public Library and play it |

The parent and child relations follow the app context: **a project is the work, a song is the
catalogue entry, a version joins them.** Work in progress lives in Projects; finished work lives in a
library, under a song, as a version.

```
Projects (Personal Vault)                 work in progress, not yet a song
  └─ Project ─ Source · Audio · Notes · Hands · Sheet
                 └─ Passage (Recording in Sheet)

My library (Private Library)              finished work, yours
  ├─ Songs ─ Song ─ Versions ─ Project ─ Play | Edit (opens a copy in Projects)
  ├─ Artists ─ Artist ─ Songs
  ├─ Playlists ─ Playlist ─ Play
  └─ Shared with me

Public library                            everyone's
  ├─ Songs ─ Song ─ Default · Hard · Medium · Easy · custom · Other versions (by user)
  ├─ Artists ─ Artist ─ Songs
  └─ Playlists

Requests                                  what you asked to publish
Admin (master user only) ─ Review · Users · Lab
```

## 6.2 The shell

A left sidebar, the content on the right, no top bar. This is the layout the prompt asks for, and the
one OpenAI uses.

```
┌──────────────────┬──────────────────────────────────────────────────────────┐
│ ◼ AImpromptu   ⇤ │  Projects                                  [ New project ]│
│                  │                                                          │
│  ⌕ Search        │  Superestrella               Sheet     2 h ago       ⋯   │
│                  │  Untitled project            Notes     yesterday     ⋯   │
│  ▢ Projects      │  Mr Blue Sky (edit)          Hands     3 Oct         ⋯   │
│                  │                                                          │
│  My library      │                                                          │
│    Songs         │                                                          │
│    Artists       │                                                          │
│    Playlists     │                                                          │
│    Shared        │                                                          │
│                  │                                                          │
│  Public library  │                                                          │
│    Songs         │                                                          │
│    Artists       │                                                          │
│    Playlists     │                                                          │
│                  │                                                          │
│  Requests     2  │                                                          │
│  Admin        5  │                                                          │
│                  │                                                          │
│ ─────────────────│                                                          │
│  ● david      ⋯  │                                                          │
└──────────────────┴──────────────────────────────────────────────────────────┘
```

- **Sidebar**: 260 px, can be closed to 64 px (icons only), and closed by default inside a project
  and in Play mode, where the piano sheet needs the width. The number beside Requests and Admin is
  the count of requests that wait for this user. The user menu at the bottom holds the theme, the
  password and **Sign out**.
- **Search** (also `⌘K`) looks for songs, artists, playlists and projects in the libraries the user
  can read.
- **A page** has a title on the left and its one primary action on the right of the title. No
  subtitle, no paragraph. Secondary actions are in the `⋯` menu of a row, or on hover.
- **A section appears only when it is built.** Phase 1 shows Projects and Lab; each later phase adds
  its section. A user who is not the master user never sees Admin.

## 6.3 The routes

`src/layout/routes.ts` stays the one place where a path is written.

| Path | Page | Phase |
|---|---|---|
| `/login` | Sign in | 4 |
| `/` | Goes to `/projects` | 1 |
| `/projects` | The Personal Vault: the list of projects | 1 (on pieces), 5 |
| `/projects/new` | Choose: From source, From scratch, From other projects | 5 |
| `/projects/:id/:step` | The flow: `source`, `audio`, `notes`, `hands`, `sheet` | 1, 5 |
| `/projects/:id/notes-falling` | Notes Falling of a project, until Play mode | 1 (removed in 11) |
| `/projects/:id/passages/:passageId` | Recording in Sheet | 9 |
| `/projects/:id/compose` | From other projects | 10 |
| `/library/songs`, `/library/songs/:id` | My songs, one song with its versions | 6 |
| `/library/artists`, `/library/artists/:id` | My artists | 6 |
| `/library/playlists`, `/library/playlists/:id` | My playlists | 10 |
| `/library/shared` | Libraries shared with me | 14 |
| `/public/songs`, `/public/songs/:id` | Public songs, one public song | 13 |
| `/public/artists`, `/public/artists/:id` | Public artists | 13 |
| `/public/playlists`, `/public/playlists/:id` | Public playlists | 13 |
| `/play/:projectId` | Play mode for one project | 11 |
| `/play/playlist/:id` | Play mode for a Songs Playlist | 11 |
| `/requests`, `/requests/:id` | My requests | 14 |
| `/admin/requests`, `/admin/requests/:id` | Review | 14 |
| `/admin/users` | Users | 4 |
| `/admin/lab/...` | The video reader's pages: `video`, `calibration`, `detection`, `notes`, `examples` | 1 |
| `/dev/ui`, `/dev/roll-bench` | Development builds only: every shared component on one page; the Notes step's measurements | 1 |

Every old path (`/piece/...`, `/playground/...`, `/youtube`, `/video/...`, `/library/play/...`)
redirects to its new home for one implementation, then is removed in Phase 15.

---

# 7. The design system

## 7.1 The direction

The prompt asks for the white, black and grey of OpenAI: a clean, minimal UI where colour appears only
for small things. The 09 guidelines ([`../01-mvp/09-minimal-ui/09-minimal-ui-guidelines.md`](../01-mvp/09-minimal-ui/09-minimal-ui-guidelines.md))
are the rules for every screen, and their pass of 13 checks (section 13 of the guidelines) is run on
every page a phase touches. Every phase that changes a page uses the `frontend-design` skill.

**The one place colour is spent is the music itself**: the two hands (blue for the right hand, as
today; the left hand colour as today) and the selection. Everything around the music is black, white
and grey, so the sheet and the piano roll are the most colourful things on any screen.

## 7.2 Tokens

Defined once in `src/ui/tokens.ts`, given to the MUI theme, and used everywhere. `palette.ts` keeps
only the colours of the music (hands, selection, piano roll).

| Token | Light | Dark | Used for |
|---|---|---|---|
| `bg` | `#FFFFFF` | `#212121` | Page |
| `bgSidebar` | `#F9F9F9` | `#171717` | Sidebar |
| `bgHover` | `#ECECEC` | `#2F2F2F` | Hover of rows and icon buttons, selected row |
| `line` | `#E5E5E5` | `#3A3A3A` | Borders, dividers |
| `text` | `#0D0D0D` | `#ECECEC` | Text |
| `text2` | `#5D5D5D` | `#B4B4B4` | Secondary text, icons |
| `text3` | `#8F8F8F` | `#8F8F8F` | Disabled, placeholders |
| `primary` | `#000000` on `#FFFFFF` | `#FFFFFF` on `#000000` | The one primary button of a screen |
| `danger` | `#D92D20` | `#F97066` | Only inside a confirmation of a destructive action |
| `paper` | `#FFFFFF` | `#FFFFFF` | The piano sheet (P-8) |

## 7.3 Type, shape, motion

- **Type**: Geist Sans (open licence), self-hosted in `public/fonts/` like Montserrat today. Sizes 13
  (meta), 14 (body, controls), 16 (inputs), 20 (page title, weight 600), 28 (Play mode title). Weights
  400, 500, 600. Sentence case everywhere. Bravura stays for the music.
- **Buttons**: fully rounded (pill), 36 px high (32 in toolboxes). The primary button is black with
  white text; secondary buttons are white with a grey border; icon buttons have no border and a grey
  hover. **Every icon button has a tooltip** that says in a few words what it does (the app context
  asks for this many times).
- **Inputs**: 12 px radius, grey border, black focus ring.
- **Floating things** (toolboxes, floating bars, menus, dialogs): 16 px radius, one soft shadow. Nothing
  else has a shadow; lists and tables are flat with a hover colour.
- **Icons**: the outlined set of `@mui/icons-material`, 20 px.
- **Motion**: only in answer to an action (a panel opens, a row is added). No animation on load.

## 7.4 The shared components

Built in Phase 1 in `src/ui/`, and the only way pages draw these things:

`AppShell`, `Sidebar`, `PageHeader` (title + primary action), `IconAction` (icon button + tooltip),
`PillButton`, `Segmented` (2 to 4 options), `ListRow` (title, meta, status, `⋯` menu), `DataTable`
(sticky header, sortable, rows per page), `EmptyState` (one line + the action that creates the first
one), `ConfirmDialog` (the button repeats the action: "Delete 3 projects"), `Toolbox` (the restyled
`ToolboxDialog`), `FloatingBar` (restyled), `MiniPiano` (a small keyboard to pick one key, for
transposition and grace notes), `FigurePicker` (the figure icons as a segmented control), `StepTabs`
(the steps of a project, restyled).

`PageContainer` and `SectionCard` (title plus description) are deleted: the description is the thing
the guidelines remove. Phase 1 added two more: `Section` (a group with an optional small title and
no description, in place of `SectionCard`) and `RowMenu` (the `⋯` menu of a row or a page).
`/dev/ui` shows every shared component on one page in a development build.

## 7.5 What happens to the words

The deleted explanations go where section 16 of the guidelines says: how a feature works goes to the
documentation; what a control does goes to its tooltip, in one line; a rare warning appears only when
it applies. Technical words leave the screen: no `ms`, no engine name, no `column`, no `API online`.
Frame numbers (`f101`) stay only where the user asked for them: the optional frame numbers of the
piano sheet and the lyrics placement.

---

# 8. Storage: the `.database/` folder

## 8.1 The rule

**Everything the app knows is in `.database/`, and nothing else is needed to run it.** A person who
clones the repository, decompresses a `.database/` archive at its root and runs `make up` has every
user, song, project and audio file. The code never writes data anywhere else.

The parallel work's music library (section 15.5) is a separate folder and is not part of
`.database/`. On this machine it is `/home/david/Documents/projects/music/data/music-library`
(`data/music-library` next to the repository). Phase 12 reads `library.sqlite` in that folder.
`raw/` is the saved HTML, and `manifest.sqlite` is the download log. The import of Phase 13 copies
the public rows into `.database/`, so the running app never reads that folder.

`AITU_DATABASE_DIR` names the folder (default `./.database`). On this machine `.env` sets it to
`/mnt/ssd2/aimpromptu/.database` (P-4). There is no `.database` link inside the repository. Compose
mounts the path from `.env`.

## 8.2 The layout

```
.database/
  aitu.sqlite                 every record (section 8.6), WAL mode
  VERSION                     the layout version, checked at start
  audio/<sha256>.<ext>        every audio file, once, named by its content (P-3)
  users/<userId>/
    vault/<projectId>/        layer 1: Personal Vault, work in progress
    library/<projectId>/      layer 2: Private Library
  public/<projectId>/         layer 3: Public Library
  tmp/<userId>/<itemId>/      temporary files: a YouTube video, its frames, an upload not yet cut
  jobs/                       nothing in Phase 3; reserved for job records if jobs must survive a restart
  lab/frame-examples/         the video reader's example data (Lab)
  history/<projectId>/vN/     earlier states of a project in a library, before a save replaced it
```

The users' Private Libraries never mix: a project is under its owner's folder, and every query is
scoped by owner (section 9.3).

*As built in Phase 3:* the video of a part is `tmp/<userId>/<partId>/video/`; the history of a part
(a splice, a new transcription) is `history/<projectId>/parts/<partId>/vN/`, which leaves
`history/<projectId>/vN/` for the library saves of Phase 6; `lab/frame-examples/` starts as a copy
of the records committed in `aitu-backend/data/frame-examples/`.

## 8.3 The project bundle

The same layout in the Personal Vault, the Private Library, the Public Library and the export file:

```
<projectId>/
  project.json                the project's own metadata (below)
  parts/<partId>/
    notes.pmn                 the piano matrix notation of the part (P-5)
    sheet.json                the metadata of the part's piano sheet (today's rhythm.json)
    timeline.json             the audio timeline of the part (section 8.5)
  staging/<sessionId>/        disposable edit sessions (as today)
  cache/                      derived files, safe to delete: the joined audio, waveforms
```

**`project.json`** holds: `id`, `kind` (`song` or `integratedPlaylist`), `title`, `subtitle`,
`artistText` (the name printed on the sheet, free text), `ownerId`, `frameMs`, the ordered list of
parts with the subheader of each, `origin` (the project or passages it was made from), `basedOn`
(the library project that a vault project edits), `createdAt`, `updatedAt`, `revision`. The links to
a song, an artist and a version are **not** in the bundle; they are records of a library (section
8.6), because the same bundle can sit in two libraries under two different songs.

**`notes.pmn`** is the portable form of [`../../backend/piano-matrix-notation.md`](../../backend/piano-matrix-notation.md)
section 6 (`format: "aimpromptu-pmn"`, header with `frameMs`, `durationMs`, the columns `id`, `key`,
`onMs`, `lenMs`, `hand`, `velocity`), version 2, which adds the header of `events.json`
(`nextId`, `notesRevision`, `handsRevision`, `handsNotesRevision`, `audioRevision`, `engine`,
`lagCorrectionMs`) and the ids of removed notes. It is JSON, like today; the name `.pmn` is the one
the user gave the format. Every writer still goes through one function (`pipeline.save_edit` today).

**`sheet.json`** is `rhythm.json` with three additions: the lyrics pool (section 11.5), the figure the
next figures transposition starts from, and the sheet title block (title, subtitle, artist text).

*As built in Phase 3:* the cache is one folder per part, `cache/<partId>/` (`normalized.wav`,
`waveform.json`, `piece-r<N>.flac/.wav`, scratch clips), and `normalized.wav` is written again from
the stored file when it is missing. `notes.pmn` keeps milliseconds with up to three decimals, not
one: the two hand-made demo pieces have microseconds, and the migration checks every note equal. A
project made by this app has the id of its first part.

**The export** is the bundle plus the audio files it uses, in one zip named `<title>.aitu`. The
import makes a new project in the importer's Personal Vault, with new ids. A test checks that export,
import and export again give the same `notes.pmn`, `sheet.json` and audio.

*As built in Phase 5* (`storage/exchange.py`): the zip also holds `export.json` (the format, its
version, when and from which project); the part files are copied byte for byte; nothing derived,
temporary or historical is exported. The import checks each part file reads as what it is and each
audio file's SHA-256 against its name, reads members only by the names it expects, and leaves
nothing behind when it refuses a file. `origin` of the new project is `{"importedFrom": id}`.

## 8.4 Parts

A normal project has one part. **From other projects** (section 10.4) makes one part per group of
passages joined **sequentially**, and starts a new part at each **subheader**, as the app context
suggests. The order and the subheaders are in `project.json`. The piano sheet of an integrated
playlist draws its parts one after the other, with the subheader as a title between them, and the
user can reorder the parts.

Each part has its own revisions, its own steps and its own staleness, exactly as a piece has today.
That is what lets every route of today work on a part (section 8.8).

## 8.5 The audio timeline

The app context's example is the model:

```json
{"audioRevision": 4, "segments": [
  {"audio": "9f3c…", "fromMs": 0,     "toMs": 83000},
  {"audio": "b71a…", "fromMs": 0,     "toMs": 9000},
  {"audio": "9f3c…", "fromMs": 92000, "toMs": 214000}
]}
```

A part plays its segments one after the other. The time of the notes is the time of this joined
audio. All of the following are one change of the segment list, saved with `baseRevision`:

| Action | Change of the timeline |
|---|---|
| A cut (Audio step) | One segment becomes two, without the cut range |
| Restore a cut | The two segments join again |
| Add another audio file (Audio step) | A segment appended at the end |
| Re-record, keeping the new audio (section 13) | The segments under the passage are replaced by one segment of the take |
| Paste a passage (section 12) | The segments of the copied range are inserted |
| From other projects (section 10.4) | The segments of each chosen passage, in order |

The 08 cuts (`[[startFrame, endFrame)]` over one file) are a special case: one audio, several
segments. `audio/frames.py` (`FrameTable`) becomes the table from the time of the part to a segment
and a time inside its file. Every range is on the 10 ms grid, and a join gets the 5 ms fade of
implementation 08.

**The joined audio** that the browser plays is written to `cache/<partId>/piece-r<audioRevision>.flac`
(as built), and written again when it is missing.

*As built in Phase 3:* `timeline.json` also lists the files it uses with their extension and their
length in 10 ms frames (`"audio": {"<hash>": {"format": "mp3", "frames": 26351}}`), so it reads
without the database and a cut that reaches the end of the file is still a cut; `toMs` is `null`
for a file not measured yet. A splice or a passage put in stores the new recording as a new file
(`store.replace_original`).

*As built in Phase 5* (**add audio**): `timeline.json` gains `sources`, the files of the Audio step
laid end to end in order, and each segment the place of its file in that list (`source`), because
the same file may come twice. The Audio step shows that axis and a cut is a range of it, so the cuts
of implementation 08 and every route that reads `normalized.wav` work unchanged: for a part of
several files, `normalized.wav` is the files' 16 kHz copies joined on whole frames, and a joined
FLAC stands in for the original (`audio/sources.py`). Adding a file raises `audioRevision`. The
general timeline of Phases 8 and 9 (a pasted passage in the middle) is not this list of files end to
end; those phases extend the axis to ranges of files.

**Writing the audio on save (Q-3).** When a project is saved to the Private Library, each audio file
that the timeline uses only in part is written again with only the ranges in use, and the segments are
renumbered to point into the new file. A file that no project uses any more is deleted. A temporary
file of the project (a video, its frames, an upload before its cuts) is deleted. In the Personal Vault
nothing is deleted, so every cut can still be undone.

**Deleting audio.** A file in `audio/` is deleted only when no project in any layer uses it. The table
`audio_refs` (section 8.6) counts the uses; `make db-check` compares it with the bundles.

## 8.6 The tables

SQLite, through SQLAlchemy 2 and Alembic migrations in `aitu-backend/src/aitu_backend/db/` (P-2).
The bundles hold the music; the tables hold who owns what, the music library and the requests. A
script, `make db-reindex`, rebuilds the project rows from the bundles if they ever disagree.

| Group | Tables |
|---|---|
| Users | `users` (numeric `id`, `username`, `password_hash`, `role`: `master` or `user`, `disabled`), `sessions` (hash of the token, user, expiry) |
| Projects | `projects` (`id`, `owner_id`, `layer`: `vault`, `private` or `public`, `kind`, `title`, `based_on`, `public_source_id`, `updated_at`, the step reached), `audio_files` (`hash`, format, duration, size), `audio_refs` (project, hash) |
| Music library, both scopes | `artists`, `artist_names` (several per artist, one default), `albums`, `songs`, `song_artists` (a song points to an **artist name**, which points to its artist, as the app context asks), `song_albums`. Each row has `scope` (`public` or `private`), `owner_id` (empty for public) and, for a private row pulled from the public library, `public_id` |
| Versions | `song_versions` (public: `song_id`, `name` among Default, Hard, Medium, Easy or an accepted custom name, `project_id`; Default points to Hard unless the master user changes it), `user_versions` (public: `song_id`, `user_id`, `version_name`, `project_id`, unique per song, user and name), `private_versions` (private song, version name, project) |
| Song metadata (public) | `genres` (fixed list, at most two per song), `tag_categories` (fixed: films, video_games, tv_shows, adverts), `tag_values` (a value inside a category, such as "Shrek"), `song_tags`, `regions` (`worldwide` by default, `spain`, `catalan`, more by request), `song_regions`, `chart_sources`, `chart_entries` (song, chart, week, rank), `songs.year`, `songs.popularity` (the decade is computed from the year, not stored) |
| Playlists | `playlists` (`owner_id`, `scope`, title), `playlist_items` (position, song, project, optional range). An integrated playlist is a project, not a row here |
| Social | `likes` (user, project), `library_shares` (owner, the user it is shared with) |
| Requests | `requests` (`kind`, author, status, timestamps), `request_items` (one proposed change each, with its own decision and comment), `request_comments` |

*As built in Phase 3* (revision `0001`): every table above, plus `parts` (a part finds its project,
P-6) and `song_genres` (the link of a song to its one or two genres), plus `external_key` on the
public artists, albums and songs for the import of Phase 12, and `songs.default_version`. The fixed
lists are written by the revision: 13 genres, 4 tag categories, the region `worldwide`.
`projects.step` is filled by the migration and `db-reindex`; Phase 5 keeps it current. *As built in
Phase 5:* a write of a part's notes, sheet or timeline clears it, and the list of projects works it
out again for the cleared rows only (working it out reads every part: 0.9 s for 39 projects).

## 8.7 Moving, backing up, the cloud

- `make db-backup` writes `.database-YYYYMMDD.tar.zst`. It uses SQLite's own backup command first, so a
  running app gives a consistent copy.
- `make db-restore FILE=...` restores into an empty `.database/`.
- `make db-check` checks the layout version, the tables against the bundles, and the audio counts.
- In the cloud, `.database/` is the attached volume. Nothing in the code assumes a local disk beyond
  that one folder.

## 8.8 The routes after the storage change

The uuid in today's routes (`/audio/{uuid}`, `/pieces/{uuid}`, `/time/{uuid}`, `/matrix/...`) becomes
**the id of a part** (P-6). A migrated piece becomes a project with one part whose id is the old
uuid, so every route and every check script keeps working while the storage changes under them. Each
route first resolves the part to its project and checks that the user may read it, or write it
(section 9.3).

New routers: `/auth`, `/projects` (list, create, rename, delete, export, import, duplicate, the parts
of a project), `/library` (the Private Library: songs, artists, versions, playlists, save, pull),
`/public` (the Public Library), `/requests`, `/admin`. The old `/library` router (playground, `.npz`,
promotions) is deleted, with its storage modules (`storage/repository.py`, `promotion.py`,
`browse.py`, `playlists.py`, `matrix_store.py`), and so are `/scores` and `/sequence` (Q-4).

## 8.9 The migration of the current data

`scripts/migrate/to_database.py`, run once in Phase 3, safe to run twice:

1. Creates the master user (from `.env`).
2. For each `aitu-backend/data/audio/<uuid>/` with notes: a project with one part (id = uuid);
   `events.json` → `notes.pmn`, `rhythm.json` → `sheet.json`, `metadata.json` cuts → timeline, audio
   files → `audio/<hash>`, `history/` → `.database/history/`.
3. A piece found in `scripts/seed/youtube-library/seed-state.json` (it maps the uuid to a title and an artist) goes to the
   master user's Private Library, under a private song and a private artist, version name "original".
   Every other piece goes to the master user's Personal Vault.
4. A piece with a video: the video folder goes to `tmp/<masterId>/` and stays there.
5. `frame-examples/` goes to `lab/`.
6. A report: counts, sizes, and every piece it could not move, with the reason.

`aitu-backend/data/` is not deleted. The user deletes it after checking the app (a human step at the
end of Phase 3), and Phase 15 removes the code that reads it.

*As built in Phase 3:* the two pieces with audio and no notes were moved too (one has a calibrated
video), so nothing is left behind; every note is checked against the old file; the new files keep
the times of the old ones. `POST /projects/{id}/duplicate` (Phase 5's route) was made early, because
the scripts that work on copies (`bench:sheet`, `time:flow`) could no longer copy a folder by hand.

---

# 9. Users, login and access on the home network

## 9.1 Users

- **The master user** is created on the first start from `AITU_MASTER_USERNAME` and
  `AITU_MASTER_PASSWORD` in `.env`, and is the owner of the Public Library.
- **Other users** are created by the master user in **Admin → Users** (P-7): a username and a first
  password, which the user changes from the user menu. The master user can disable a user and reset a
  password.
- A user has a numeric id and a username. Only the username is ever shown to other users.

## 9.2 The login

- `POST /auth/login` checks the password (Argon2 hash) and sets a session cookie (`HttpOnly`,
  `SameSite=Lax`, 30 days, renewed on use). `POST /auth/logout`, `GET /auth/me`,
  `PUT /auth/password`.
- Five wrong passwords in a minute for one username slow the next tries.
- Every route except `/auth/login` and `/health` needs a session; the frontend sends the cookie on
  every request, on the audio files and on the progress streams (all on the same origin through the
  Vite proxy, so the browser sends it by itself).
- The login page: the logo, **Username**, **Password**, **Sign in**. Nothing else.

## 9.3 Who can read and write what

| Thing | Read | Write |
|---|---|---|
| A project in a Personal Vault | Its owner | Its owner |
| A project in a Private Library | Its owner; users it is shared with (section 15.4) | Its owner, through a copy in the vault (section 10.6) |
| The Public Library | Every user | The master user, by accepting requests |
| A request | Its author and the master user | Its author (until reviewed); the master user (the decision) |
| Users, Lab | The master user | The master user |

One function per route checks this before anything else, and tests check each row of this table
with two users.

*As built in Phase 4* (`auth/dependencies.py`, `auth/rights.py`, `context/08-security.md`): one
router-level check reads the session, then applies the table to the project the route names by its
path parameter. A project the user may not read answers 404, like a project that does not exist; one
they may read but not write answers 403. The master user has no right over another user's private
projects. **One change for now:** the owner writes a Private Library project in place, as before;
the copy in the vault of section 10.6 arrives in Phase 6, which changes that one line.

## 9.4 Access on the home network

- The frontend container publishes 5173 on all addresses of the Ubuntu machine (`WEB_BIND=0.0.0.0`),
  and Vite answers to the names `ubuntu`, `192.168.0.112` and `localhost`.
- The backend stays on `127.0.0.1`: the browser reaches it only through the frontend's `/api`.
- From the Mac: `http://ubuntu:5173` (the Mac's `/etc/hosts` already maps `ubuntu`) or
  `http://192.168.0.112:5173`. The tunnel still works and stays documented.
- *As built in Phase 4:* Vite also answers to `david-ubuntu` (the machine's own name) and to the
  names in `AITU_ALLOWED_HOSTS`; `WEB_BIND=127.0.0.1` in `.env` keeps the page to the machine. The
  browser scripts sign in as the master user with the password of `.env`
  (`aitu-frontend/scripts/session.mjs`). The **Video** choice of the Source step is shown to the
  master user only until Phase 5, because a video project still opens in Lab.
- **What this does not protect**: the traffic is plain HTTP on the home network, so a password crosses
  the Wi-Fi unencrypted. This is acceptable at home and is written in a new `context/08-security.md`,
  with the production answer (HTTPS behind a reverse proxy). The Docker port 2375 of the machine,
  which is already open on the network with no authentication, is named there too.

---

# 10. Projects

## 10.1 The Projects page

The Personal Vault. One row per project: title ("Untitled project" until it has one), the step it
reached, when it changed, and a `⋯` menu (Open, Duplicate, Export, Delete). **New project** opens a
small menu with three choices: **From source**, **From scratch**, **From other projects**. An
**Import** item in the same menu takes a `.aitu` file. A project being edited from a library shows
"Editing" and the song it belongs to.

Empty state: "No projects yet" and the **New project** button.

*As built in Phase 5:* the menu shows **From scratch** and **From other projects** disabled ("Not
available yet") until Phases 8 and 10. The row menu also has **Rename** and **Notes Falling**. Until
Phase 6 gives the Private Library its pages, its projects are listed on this page too, in a group
**In my library** under the vault, so the 30 migrated songs stay one click away.

## 10.2 From source

The user is never asked for a name, a song or an artist before the piano sheet is ready (app context).
The steps keep the order of implementation 08, restyled:

```
← Untitled project        Source  Audio  Notes  Hands  Sheet          [ Save to library ]
─────────────────────────────────────────────────────────────────────────────────────────
```

The step tabs are text with a small dot for the state (ready, running, stale, missing); a step that is
not ready is grey with its reason in a tooltip. **Save to library** appears only when the Sheet step
is ready.

1. **Source.** One drop zone ("Drop an audio or video file") with **Choose file**, and one field
   **Paste a YouTube link** with a `Segmented` choice **Audio / Video**. Nothing else. A YouTube link
   downloads as a job with a thin progress bar. A video source goes to the video steps below.
2. **Audio.** The waveform, full width. A floating bar of icon actions with tooltips: play, play
   selection, cut, restore, zoom, undo, redo, **add audio** (another file appended to the timeline).
   The primary action is **Transcribe**.
   **Video.** For a video source the same step shows the video with the detected rectangles and the
   piano overlay, and the calibration controls of the current video pages, as icon actions. The
   primary action is **Read notes**. The video and its frames are temporary files (section 8.5).
3. **Notes.** The live piano roll, as today, with the progress as a thin bar under the step tabs, and
   the editor's floating toolbar. Whether the video reader can also stream its notes is Q-8.
4. **Hands.** The same editor, coloured by hand, with a **floating toolbox**: **Predict hands**, **To
   right** (R), **To left** (L), the hand filter, and the counter of notes with no hand. Explanations
   only in tooltips.
5. **Sheet.** Section 11.

*As built in Phase 5:* the drop zone takes an audio or a video file (`.mp4 .mov .m4v .mkv`; a
video file becomes a project like a downloaded video, `POST /video/upload`), and the **Video** choice
is shown to every user. The Video step (the Audio tab is named **Video**) prepares the frames on
opening, fits the piano on one frame with the calibration editor (**Save the piano**), and plays the
video with the piano on it; **Read notes** is one job that measures the roll once per fitting, reads
and writes the notes (`POST /video/{id}/read`), then opens the Notes step. The detection, the
measurements and single-note corrections stay in Lab. The video stays a temporary file of the part
until Phase 6 deletes it on save.

**Save to library** asks three things in one dialog: **Artist** and **Song** (each a searchable select
over the user's Private Library, with "Create …" when the name is not there, and suggestions from the
Public Library), and **Version name** (free text, for example "easy", "acoustic"). Saving moves the
project to the Private Library (section 8.5 says what happens to the audio) and opens the song.

## 10.3 From scratch

An empty project: an empty `notes.pmn`, an empty timeline, the default `frameMs`, and the Sheet step
open on a blank piano sheet. Two ways to fill it, both in the sheet's floating bar:

- **Record** opens Recording in Sheet (section 13) with an empty Current, so the take becomes the
  first passage.
- **Paste** inserts a passage copied from any project the user can read (section 12).

The steps Source, Audio, Notes and Hands are hidden for a project made from scratch until it has
audio; then they work as usual.

## 10.4 From other projects

The page `/projects/:id/compose`, in three moves (the app context's list):

```
┌──────────────────────────┬─────────────────────────────────────────────────────┐
│ Passages             [+] │  Clocks — Coldplay (my version)        [ Add passage ]│
│                          │                                                     │
│ 1 Clocks  0:12–1:05   ⋯  │   ┌───────────── piano sheet, read only ──────────┐ │
│   ── sequential ──       │   │  the user selects a range, or nothing for all │ │
│ 2 Fix You 2:01–2:40   ⋯  │   └────────────────────────────────────────────────┘ │
│   ── subheader ──        │                                                     │
│ 3 Yellow  whole       ⋯  │                                                     │
│                          │                                                     │
│ [ Save as song ] [ Save as integrated playlist ]                                │
└──────────────────────────┴─────────────────────────────────────────────────────┘
```

1. **[+]** opens a picker over every project the user can read (Personal Vault, Private Library,
   Public Library).
2. The chosen project's piano sheet opens read only. The user selects a range, or keeps nothing
   selected for the whole sheet, and presses **Add passage**.
3. From the second passage on, a `Segmented` choice asks **Sequential** or **Subheader** for the join
   with the passage before it. Passages can be dragged to a new order.

**Save as song** writes one project; **Save as integrated playlist** writes a project of kind
`integratedPlaylist` (section 14.1). Either way the passages are **copies**, never references: the
notes and the metadata of each range are copied, and the audio segments are added to the timeline
(no audio bytes are copied, P-3). The new project opens on its Sheet step in the Personal Vault.

Taking a whole project is the same as **Duplicate**, which also exists as a row action everywhere a
project is listed.

## 10.5 Steps and revisions

Unchanged from implementation 08, per part: `GET /pieces/{partId}/status` answers the state of each
step. A project's step reached (shown in the list) is the lowest step reached by its parts.

## 10.6 Edit a project of the Private Library

**Edit** on a version of a song copies its bundle into the Personal Vault (no audio bytes copied),
with `basedOn` pointing at the library project. The library copy does not change. In the vault,
**Save to library** then offers **Replace the version** (the library project gets the new content; its
previous content goes to `history/`) or **Save as a new version**. **Discard** deletes the vault copy.
A song whose version is being edited shows "Editing" beside that version.

---

# 11. The sheet

## 11.1 What is removed

The five cards above the piano sheet go: "Add a passage" (it becomes **Paste** and **Record** in the
floating bar), "How this piece was played" (the plot of gaps), "Name it" (the figure is chosen
automatically, D-09 changed), "Does the piece change speed?" (it moves to the range toolbox, as one
more tab, with no caption), and the explanatory captions of every slider and select. The footer text
goes. The page is the piano sheet, a floating bar, and the toolboxes.

## 11.2 The page

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ ← Superestrella       Source  Audio  Notes  Hands  Sheet       [ Save to library ]│
│                                                                               │
│      Superestrella                                                            │
│      Aitana                                                                   │
│   ┌──────────────── piano sheet (paper) ────────────────────────────────────┐ │
│   │ ...                                                                     │ │
│   └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│            ( ▶  ↶  ↷  │  ✎ Sheet toolbox  │  ● Record  ⎘ Paste  │  ⎙  ⋯ )      │
└───────────────────────────────────────────────────────────────────────────────┘
```

**The floating bar** (draggable, as today): play or pause, undo, redo, the sheet toolbox, Record,
Paste, Print, and a `⋯` with Save, Remove all and the frame numbers on or off. **Save** stays explicit
(nothing is written before it), and the bar shows a small dot when there are unsaved changes.

*As built in Phase 2:* **Save** is a visible button on the bar, with the dot on it, not an item of
the `⋯` (a save hidden in a menu is the "hidden action" of the 09 guidelines). The `⋯` holds *Show
the keyboard*, *Find trills*, *Bring back N notes taken off* and *Remove all* (with a confirmation).
The frame numbers are in the **Layout** tab. **Paste** joins the bar in Phase 8. **Record** opens
today's compose panel (play a passage and put it in) until Phase 9. A thin scrub bar stays above the
sheet.

**Line wrapping.** The prompt says the line wrap of `vexflow-v2` may have stopped working. The survey
found the renderer wraps to the container width on each draw. Phase 2 checks it on three widths and on
a window resize, finds where it fails if it does, and fixes it (in the frontend, or in `vexflow-v2`).

## 11.3 Defaults that replace recommendations

| Before | Now |
|---|---|
| The user clicks a peak of the plot and names it | The highest peak is a **negra** (D-09 changed). The backend chooses it when `sheet.json` has no figure yet |
| "Try X (n fewer accidentals)" | The key signature with the fewest accidentals is applied when the sheet is first written. The user can change it in the sheet toolbox |
| "Group high notes under 8va (n)" chip | Applied when the sheet is first written, with the new clef rule (section 11.7) |

Each default is applied once, when the sheet is first written, and is an ordinary edit after that:
the user can change it and undo it.

## 11.4 The sheet toolbox

A side panel that opens from the floating bar, with `Segmented` tabs. Every action in it is one undo
step.

| Tab | Content |
|---|---|
| **Title** | Title, subtitle, artist name printed on the sheet (Phase 2: stored in `rhythm.json` as `title`, `subtitle`, `artist`) |
| **Key** | The key signature of the piece. Key changes of passages are in the range toolbox |
| **Transpose** | Two tabs, **Notes** and **Figures** (below). Phase 2 has a simpler **Figures** tab in its place: one `FigurePicker` for the main figure (what the highest pile is called), one undo step; Phase 7 replaces it |
| **Lyrics** | The pasted lyrics and their pieces (section 11.5) |
| **Layout** | Space between notes, space between lines, size of marks, zoom, frame numbers on or off |

**Notes transposition.** Two `MiniPiano`s: **From** and **To**. The user clicks a key on each (the
names in tooltips are Spanish, `Do 3`, as everywhere). The interval between them is applied to every
note: every key of `notes.pmn` moves by that many semitones, and the key signature moves with it.
Notes that would leave the 88 keys are counted. **Preview** draws the piano sheet with the change in a
dialog; **Transpose** applies it, **Cancel** closes. It is a notes edit (the notes revision goes up;
the hands stay), and undo puts every key back.

**Figures transposition.** Two `FigurePicker`s (the figure icons, no names): **From**, pressed on
**negra** the first time, and **To**. The change is the figure shift of D-18 by the number of steps
between them. It renames figures and moves nothing in time. Beams that can no longer exist (a beam
on notes that become negras) and figure overrides that no longer make sense are removed, and the
preview dialog shows how many. Undo restores the beams and the overrides exactly. The next time the
tab opens, **From** is pressed on the last **To** (stored in `sheet.json`).

Both transpositions use one dialog: a preview of the result, the counts of what is removed, and the
buttons **Transpose** and **Cancel**.

## 11.5 Lyrics

**In the Lyrics tab**: one text box. The user pastes the lyrics of the song. Each line becomes one
**lyrics piece** (a rounded block with the text). The pieces that are not placed yet wait in the
**lyrics pool**, a column on the right of the piano sheet while the Lyrics tab is open.

**Placing a piece**: drag it from the pool and drop it on the piano sheet. Its start snaps to the
frame under its left edge (`fromFrame`, for example `f101`). Its right edge can be dragged, and it
snaps to a frame too (`toFrame`), so a piece always starts and ends on a frame. Play mode shows a piece
from the time of `fromFrame` to the time of `toFrame`.

**Each piece also has**: a vertical offset (drag it up or down, above high notes or octave brackets),
a font size, a width, and line breaks inside it.

**Lyrics edit mode** shows a small toolbar of icon actions, each with a tooltip:

| Action | What it does |
|---|---|
| Select | Click, `⌘`-click to add, or drag a box over several pieces |
| Merge | Joins the selected pieces into one, in order |
| Split | Puts a cursor in the piece; Enter splits it at the cursor |
| Line break | A new line inside the piece |
| Font size − / + | For the selected pieces |
| Back to pool | Takes the selected pieces off the sheet |
| Delete | Deletes the selected pieces |

Stored in `sheet.json`: the pool (ordered text pieces), and each placed piece as `id`, `text`,
`fromFrame`, `toFrame`, `offsetY`, `fontSize`, `width`, `lines`. Today's `Lyric` (`fromColumn`,
`toColumn`, `offsetX/Y`, `width`, `fontSize`) is read as a placed piece, so the saved sheets keep their
words.

## 11.6 Selections

Unchanged in what they can do, which already matches the app context: a range of frames with **Both /
R / L**, or a set of notes; since Phase 2 the range toolbox also has a **Speed** tab (the old card
*Does the piece change speed?*), shown as a percentage of the speed of the piece and stored as
before; each toolbox hands its selection to the other; notes move to the right or
the left hand. Restyled as icon actions with tooltips, and with one addition per toolbox:

- **The range toolbox** gains **Key for this passage**: it runs the fewest-accidentals rule on the
  selected frames only and shows the key it finds on the button ("Use Re major here"); one press
  applies it as a key change of the passage. It also gains **Copy** (section 12) and **Record this
  passage** (section 13).
- **The note toolbox** gains **Copy** of the frames those notes cover.

## 11.7 Clefs and octave brackets for the left hand

A new rule in `@aimpromptu/grid-notation` (`suggestClefChanges`, beside `suggestOttavas`), applied
when the sheet is first written and offered again in the range toolbox:

1. A run of the left hand that is written high enough for its stems to reach the right hand, and that
   lasts **at least four figures**, prints in the treble clef for that run.
2. A shorter high run does not change clef (a clef change for one note is worse to read); if it is far
   above the staff it gets an `8va` or `15ma` bracket, by the existing rule.
3. A very low run of the left hand gets an `8vb` bracket.

The numbers (how high, how many figures) are constants in one place, set by Phase 7 on the pieces of
the library and shown to the user in screenshots.

## 11.8 Undo

Every action of this section and of sections 12 to 14 is undoable with `⌘Z` / `Ctrl+Z`, and redoable,
with at least 20 steps kept (the hook keeps 100). An action that writes to `notes.pmn` or to the
timeline (a transposition of notes, a paste, a promotion) carries its own undo call to the backend,
as the hand swap does today. The two exceptions of today (an accepted re-record and an inserted
passage could not be undone) end: the previous state is kept in the session until the next save, so
undo restores it.

---

# 12. Copy and paste

**Copy** (range toolbox, note toolbox, `⌘C`) puts a **passage reference** in the app's clipboard and
in the system clipboard (as JSON text under a type of its own):

```json
{"type": "aimpromptu/passage", "project": "…", "part": "…", "layer": "private",
 "fromMs": 12000, "toMs": 31000}
```

The clipboard carries no notes and no audio: the backend reads them when the user pastes, so a
copied passage can be big. **Paste** (floating bar, `⌘V`) inserts the passage at the playhead, or
replaces the selected range.

What a paste writes, in one save:

- **Notes**: the notes of the source part inside the range, moved to the insertion point, with new ids.
- **Metadata**: the marks of the source inside the range (fingering, figure overrides, beams, octave
  brackets, clef changes, lyrics pieces, cue size), moved to their new frames. The key signature in
  force at the start of the copied range becomes a key change at the insertion point, so the passage
  reads as it did in its song.
- **Audio**: the segments of the source timeline inside the range, inserted in the target timeline. No
  audio bytes are copied (P-3).
- **Everything after the insertion point** moves later by the passage's length, notes and marks in the
  same write: the Insert rule of Compose, generalised (rule 2 changed, Q-3).

The source can be any project the user can read: their vault, their library, a library shared with
them, the Public Library. The backend checks the read right on paste.

---

# 13. Recording in Sheet

**Record this passage** (range toolbox) opens `/projects/:id/passages/:passageId`. The passage is a
copy of the selected frames: its notes, its metadata, its audio segments, the key signature in force,
the figure of the sheet.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ ← Superestrella · passage f420–f498                         [ Promote ▾ ]      │
│ Current                                                                ▶      │
│  ┌────────── piano sheet of the passage ──────────────────────────────────┐   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│ Proposal                                          take 2 ▾   ×1.0   ▶         │
│  ┌────────── piano sheet of the take, same key ───────────────────────────┐   │
│  │        [══════ window, same length as Current ══════]                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                   ( ● Record   ✂ Range   ⇔ Window   ↶ ↷   ✎ Sheet toolbox )    │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Recording.** **Record** records from the browser (with the metronome and the slowed original of
today's re-record, if the user wants them). Several takes can be recorded; the selector picks one.

**The condensed steps.** For a take, the user only selects the range of the take to keep (the same
waveform selection as the Audio step). Then the rest is automatic: MuScriptor, the hand split, and the
piano sheet, written **with the passage's key signature and figure**, so Current and Proposal can be
compared. The sheet toolbox works on the Proposal (figures, key, everything), with undo.

**Promote** offers two ways, as the app context asks:

1. **Fit to the window.** A window as long as Current lies over the Proposal and can be dragged. The
   **speed** control (×0.25 to ×4) scales the take in time, so the user finds the speed where the
   played notes fill the window. Then the user chooses the audio:
   - **Keep the original audio**: only the notes inside the window replace the notes of the passage,
     scaled into it. The length of the song does not change.
   - **Use my recording**: the notes and the take (scaled with pitch kept, as today's splice) replace
     the passage. The length does not change.
2. **Replace the whole passage.** The whole selected take replaces the passage, at speed ×1 or the
   chosen speed. If its length differs, the song gets longer or shorter: everything after the passage
   moves (Q-3). This always uses the recording as the audio, because the original audio of the passage
   cannot match notes of another length. A confirmation says by how much the song changes ("The song
   gets 3.2 s longer").

The promotion is one write: notes, metadata and timeline together. Marks inside the replaced passage
are dropped and counted before the button is pressed, as today. Back on the whole piano sheet, nothing
shows that a passage was re-recorded (app context). Undo works on the whole sheet after a promotion
(section 11.8).

This reuses the staged session of `editing/` (`/audio/{id}/edits`), generalised from one window of one
audio to a passage of a part, and its two panels (`RangeRerecordPanel`, `ComposePassagePanel`) become
this page.

---

# 14. Playlists

## 14.1 Integrated playlist

A project of kind `integratedPlaylist` (section 10.4). It opens on its Sheet step like any project,
with:

- the parts drawn one after the other, each subheader as a title between them, and a mark at the end
  of each sub-song when there is no subheader;
- a panel listing the sub-songs, where they can be reordered, renamed, and joined or separated
  (join two parts into one sequential part, or split one part at a frame with a new subheader);
- every editing tool, Recording in Sheet included, on any passage, because each part is an ordinary
  part.

## 14.2 Songs playlist

A row in `playlists` with ordered items. Each item is a song, the version chosen for it (a project),
and optionally a range. Nothing in a songs playlist can be edited, only chosen.

- Created from **My library → Playlists → New playlist**, or by selecting several songs in a search
  and **Make a playlist** (the app context's dynamic playlist).
- The playlist page lists its songs with the version and the range; rows can be reordered.
- **Play** opens Play mode on the first song (section 17).

Public playlists exist in the Public Library and follow the requests of section 16 like a song.

---

# 15. The music library

## 15.1 Private and public

The same entities in two scopes, in the same tables (section 8.6):

- **Private**: created by the user with any names ("every user can create its own ontology"). A
  private song has a title, one or more artists, and the user's own optional fields (year, genre,
  free tags). Its versions point to projects of the user's Private Library.
- **Public**: created only by an accepted request, or by the import of section 15.5. Full metadata
  (section 15.3).

**Pull from the Public Library**: **Add to my library** on a public song, on an artist ("all songs"),
or on a playlist copies the entities into private rows (with `public_id` kept) and copies the chosen
version projects into the user's Private Library (no audio bytes copied). After that there is no sync:
the private metadata is the user's own.

## 15.2 Versions

As the app context lists them:

```
Song: Heaven (Bryan Adams)
  Default  → Hard
  Hard     → project 81f2…  by anna
  Medium   → project 0c9e…  by david
  Easy     → (none)
  acoustic → project 77ab…  by joan      (a custom fixed version of this song only)
  Other versions
    anna   easy       → project 12de…
    joan   acoustic   → project 77ab…
```

- **Other versions** is the `user_versions/` tree of the app context: one project per user and version
  name. The page shows it as that tree, grouped by username; the files stay under the project's id, so
  a rename never moves a file.
- A public version name must be a simple name: lowercase letters, digits and hyphens, at most 24
  characters. A private version name is free text, renamable at any time; when the user opens a
  request, the dialog proposes the simple form of it, and the master user can suggest another.
- Each project can be liked once per user. Other versions are sorted by likes, then by date.

## 15.3 Metadata of a public song

| Field | Rule |
|---|---|
| Year | A number. The **decade** (50s, 60s … 20s, 30s) is computed from it |
| Genre | One or two, from a small fixed list: pop, rock, hip hop, r&b and soul, electronic and dance, latin, indie, folk and singer-songwriter, country, jazz and blues, classical, soundtrack, metal. No sub-genres |
| Tags | Fixed categories (films, video_games, tv_shows, adverts), each with free values ("Shrek"), added by request |
| Region | `worldwide` by default; `spain`, `catalan` and others are added by request. A region says where the song was popular, not where the artist is from |
| Rankings | The chart weeks and positions of the song, per chart (section 15.6) |
| Popularity | 0 to 100, computed from the rankings (section 15.6) |
| Artists | Through artist names, so "The Jackson 5" and "Jackson Five" are two names of one artist |
| Album | Optional |

## 15.4 Sharing a private library

The owner shares their whole Private Library with another user (read only) from the user menu. The
other user sees it under **My library → Shared**, can play from it, copy passages from it, and add
its songs to their own library (the same pull as from the Public Library).

## 15.5 Filling the Public Library

**The data is built by a parallel piece of work**, not by this plan: the brief
[`public-library-build/02-a-public-library-build-prompt.md`](public-library-build/02-a-public-library-build-prompt.md),
with its own plan and phase reports in the same folder. There is no response file. The download
finished on 2026-10-07. What it produced:

- the source: `musicchartsarchive.com`, the singles charts and the album charts;
- the raw HTML in `data/music-library/raw/` (next to the repository, not inside it), in folders that follow the site;
- the database Phase 12 reads: `library.sqlite` in that same folder. On this machine the full path is `/home/david/Documents/projects/music/data/music-library/library.sqlite`. It holds songs, artists (only those with an artist page; several artists per song), albums (optional per song, with their track list), the chart history of each song and each album, the lyrics, and the all-weeks popularity. The region is `worldwide`. Nothing is invented for fields the site does not give (no genre, no tags). The chart dates are one table of dates, referenced by id;
- `manifest.sqlite` in the same folder is the download log. Phase 12 does not import it.

**Phase 12 reconciles that database with this app.** It reads `library.sqlite`, the parallel plan, and
the phase reports `02-a-implementation-phase-1.md` through `02-a-implementation-phase-5.md`. It does
not change the parallel work:

1. **The mapping** from its tables to the tables of section 8.6: songs, artists, artist names, albums,
   song and album relations, chart sources and entries, regions. Each field of the parallel model is
   either mapped to a field of ours, or listed as not kept, with the reason.
2. **The gaps in both directions.** Fields we have and it does not give (genre, tags, `spain` and
   `catalan` regions, years where the site has none). Fields it gives and section 8.6 has no place for
   yet: the **lyrics of a song** (useful as the text the sheet toolbox's Lyrics tab starts from,
   section 11.5) and the **chart history and popularity of an album**. Where they go is decided then,
   not now.
3. **Identity.** How a song and an artist of the download become one public row each, and stay the
   same row when the download runs again (its ids, or the site's URL slugs, kept as an external key).
   Artist names that the site writes in several ways become artist names of one artist.
4. **The import script** that the Phase 13 import starts from: it reads the parallel work's database
   and writes public rows owned by the master user, and can run again to add songs without creating
   duplicates. The 31 songs of the seed list are checked to be present.

The import writes public rows owned by the master user, and can run again to add songs without
creating duplicates.

## 15.6 Popularity

A first formula, to be tuned in Phase 12 on a list of songs the user ranks by hand (Q-6). Only
positions inside the top `N` of a chart count (the top 100, or the size of the chart), so a song at
place 2,000 adds nothing, which is what the app context asks.

For each chart week where the song is at position `r` in a chart of size `N`:

```
points(r) = ((N + 1 − r) / N) ^ 2        place 1 → 1.00, place 10 → 0.83, place 30 → 0.50, place 100 → 0.0001
```

```
S        = sum of points over all weeks and charts (each chart with a weight; worldwide charts 1.0)
peak     = ((N + 1 − bestRank) / N) ^ 3
P        = 100 × ( 0.6 × (1 − e^(−S / 10)) + 0.4 × peak )
```

What it gives, as a first check against the app context's examples:

| Song | P |
|---|---|
| Number 1 for 30 weeks | 97 |
| Number 1 for 10 weeks | 78 |
| Between places 10 and 30 (place 20) for 20 weeks | 65 |
| Number 1 for 1 week | 46 |
| Place 5 for 1 week | 41 |
| Place 80 for 3 weeks | 1 |

The app context says a song held at places 10 to 30 for many weeks should be close to a song in the
top 10 for one week. With these weights it is above it, so the weights (0.6 and 0.4, the 10 of the
saturation, the squares) are exactly what Phase 12 tunes. A popularity is computed per region from
that region's charts; the one shown by default is `worldwide`.

---

# 16. Requests and the Admin panel

## 16.1 The three kinds

As the app context separates them:

| Kind | What it proposes | Needs before |
|---|---|---|
| **Metadata** | A change of a public song or artist: name, artist names, year, genre, tags, region. Also a new song or a new artist | - |
| **User version** | A project into `user_versions/<user>/<version name>/` of a public song, new or replacing the user's own | The public song exists, or the same request proposes it |
| **Fixed version** | The user's accepted user version becomes Hard, Medium, Easy or a new named version of the song | That user version was accepted |

A request is made of **items**, one per proposed change (a new artist, a new song, a metadata change,
the project, the version pointer). This is what makes a **partial acceptance** possible: the master
user can accept the new artist and the new song, and refuse the project.

## 16.2 Opening a request

From a song of the Private Library: **Publish** opens one dialog:

1. **Public song**: search the Public Library. If it is not there, **Propose this song** (and, the same
   way, **Propose this artist**), with the fields of section 15.3. No private id is ever sent; the
   public ids are made on acceptance.
2. **Version**: the version name, in its simple form.
3. **Send**. The request appears in **Requests**, with its status: open, changes asked, accepted,
   partly accepted, refused, withdrawn.

The project is copied when the request is sent, so later edits in the user's library do not change
what the master user reviews. A request with changes asked can be updated by the author and sent
again.

## 16.3 The Admin panel

- **Review**: the list of open requests, oldest first, with their kind and author.
- **A request**: its items, each with **Accept**, **Refuse** and **Ask for a change** (with a comment,
  for example a better version name). For a project item, a **side by side** view: the current public
  version on the left (or nothing for a new one) and the proposed project on the right, both as read
  only piano sheets that play. For a new song or artist, its full metadata.
- **Accepting** writes in one transaction: the public rows (with new ids), the project copied to
  `public/`, the version pointer, and the author's username in the song's metadata as the creator of
  that version.
- **Users**: create, disable, reset a password (Phase 4).
- **Lab**: the video reader's development pages (Phase 1).

---

# 17. Play mode

A white page with the piano sheet and nothing else:

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                  ⏭   ✕       │
│                                                                               │
│                         piano sheet, wide, scrollable                         │
│                                                                               │
│                                   ▶                                           │
└───────────────────────────────────────────────────────────────────────────────┘
```

- **Close** (top right) leaves Play mode; **Next** (beside it) appears only in a songs playlist.
- **Play / Pause** plays the audio with the cursor. While it plays, the page scrolls by itself and
  keeps the cursor near the **middle of the screen**, so the line before and the line after are both
  visible.
- Lyrics show and hide with their frames.
- `Space` plays or pauses, the arrow keys scroll, `Escape` closes.
- A small toggle (in a menu that appears when the pointer moves, and fades after) switches to **Notes
  Falling**, the view kept from the Playground (Q-4).
- **In a songs playlist**: when a song ends, the next one opens. With Play mode closed, the playlist
  page shows the songs on the left to choose one or reorder them, and a **Continuous** option draws all
  the songs on one page, one after the other, so scrolling goes from one song to the next.

Play mode opens from any version of a song in any library (**Song → version → Play**), from a project,
and from a playlist.

---

# 18. Background jobs with several users

- One GPU queue for everyone, first in first out, as today. A job records its owner; the page shows
  "Waiting, 2 before you" while a job waits.
- A user sees and follows only their own jobs; the master user sees all of them in Admin.
- Jobs stay in memory (a restart loses a running job, as today). A job lost by a restart is shown as
  "Stopped, start again", because the part's status already says what is missing.

---

# 19. The documentation

The prompt asks that the documentation stop being stale, following
[`../../00-documentation-instructions.md`](../../00-documentation-instructions.md): `context/` says what
something is and how it flows, `documentation/` gives exact paths and fields, and every page links to
the other. Each phase updates the pages it makes false, in the same phase. The list below says which
phase owns which page.

| Page | What changes | Phase |
|---|---|---|
| `context/implementations/README.md`, `context/00-index.md` | The `01-mvp/` paths (about 60 broken links), rows for 07, 09 and 02, the numbering scheme `NN-group/NN-implementation` | 0 |
| The 14 live pages with one or two broken links, and the ~50 inside `01-mvp/` | Paths only | 0 |
| `TODO.md`, `project-features.md`, `project-implementation-organization.md`, `context/research/piano-transcription/...` | Moved to `context/archive/` (they describe the old model) | 0 |
| `library/` at the root | Moved to `scripts/seed/youtube-library/`, so "library" means one thing | 0 |
| `context/00-documentation-instructions.md` | The implementation folders, the end of the docs-migration rules, `08-security` no longer skipped | 0 |
| `context/colors/color-palette.md` | The tokens of section 7 and the colours of the music | 1 |
| `context/frontend/README.md`, `pages.md`, `documentation/services/frontend/components.md`, `aitu-frontend/README.md` | The shell, the sidebar, the routes, the shared components | 1, then each UI phase |
| `context/frontend/flow-page.md` | Becomes `projects.md`: the three ways in and the steps | 1, 5 |
| `context/frontend/annotations.md` | The sheet toolbox, the defaults, transposition, lyrics; split, because it is over the 200-line limit | 2, 7 |
| `context/07-database.md`, `documentation/services/backend/paths-and-data.md` | Full rewrite: `.database/`, the tables, the bundle, the timeline | 3 |
| `context/backend/piano-matrix-notation.md` | `notes.pmn` version 2, the export | 3 |
| `context/backend/pieces-and-revisions.md` | Parts, the id of a part, owners | 3, 5 |
| `context/backend/README.md`, `backend/api.md`, `documentation/services/backend/endpoints.md`, `aitu-backend/README.md` | New packages and routers, 401 and 403 | 3, 4, then each phase |
| `context/08-security.md` (new) | The login, the cookie, the rights table, what home network access does not protect | 4 |
| `context/02b-local-setup.md` section 12, `context/04-local-development.md`, `README.md` | Opening the app on the home network, `.env`, backup and restore, the first master user | 3, 4 |
| `context/02-tech-stack.md`, `03-services-overview.md`, `09-coding-conventions.md` | SQLite, SQLAlchemy, Alembic, Argon2; user scoping rules; old leftovers | 3, 4 |
| `context/backend/editing.md` | Paste, Recording in Sheet, length changes (rule 2) | 8, 9 |
| `context/music-library/` (new): `reconciliation.md`, `ontology.md`, `popularity.md`, `requests.md` | The music library, and how the parallel work's data maps onto it | 12, 13, 14 |
| `context/frontend/play-mode.md` (new), `playlists` in `projects.md` | Play mode, playlists | 10, 11 |
| `context/00-project-complete-overview.md`, `01-project.md`, `05-deployment.md` | Rewritten for the new app; `01-project.md` becomes the product page and points at `app/01-app-context.md` | 15 |
| Run instructions in five places | One home (`04-local-development.md`), the others link to it | 15 |
| `backend/notation-and-parsing.md`, `documentation/.../schemas.md`, `sequence-logic.md` | To `documentation/deprecated/` with the text-notation MVP; the COO part of `02-notation-spec.md` stays | 1 |

---

# 20. The phases

Each phase is sized for one agent session, ends with its report `02-implementation-phase-N.md` and the
walkthrough message of the communication guide, and updates the documentation it makes false (section
19). Each UI phase ends with Playwright screenshots taken by the agent, the 13-check pass of the 09
guidelines on every page it touched, and a human check through the browser.

## Phase 0: The documentation repaired, and a baseline (markdown and file moves only)

Fix every relative link broken by the move into `01-mvp/`, with a script that checks every link of
`context/` and `documentation/` and fails on a broken one (`scripts/docs/check-links.py`, kept for
every later phase). Rewrite `context/implementations/README.md` (the two groups, 01-mvp and 02, the
numbering) and the implementation part of `00-index.md`; add `app/01-app-context.md`, the language
guides and this folder. Archive the four old root and research files. Move `library/` to
`scripts/seed/youtube-library/` and fix the paths in `seed_library.py`. Update
`00-documentation-instructions.md`. Then the baseline: screenshots of every current page (kept in the
report for the before and after), the backend test count, the frontend checks.

## Phase 1: The design system and the app shell

The tokens, the Geist font, the MUI theme, the light and dark themes (P-8). The shared components of
section 7.4. The sidebar shell, with Projects (listing today's pieces), the user menu (a placeholder
until Phase 4) and Lab. The flow page moves to `/projects/:id/:step` and its steps Source, Audio,
Notes and Hands are restyled to section 10.2 (the Source step with the YouTube audio and video choice;
the video steps still open the current video pages until Phase 5). The Playground, the YouTube page,
the old Piano Library page and its `/library` playground API calls are removed from the UI (Q-4); old
paths redirect. The video development pages move under `/admin/lab/`. Notes Falling stays reachable
from a project's `⋯` menu until Play mode exists. The text-notation MVP routes and their docs are
removed (Q-4). Every page touched passes the 13 checks. No backend storage change.

## Phase 2: The sheet page

`RhythmPage.tsx` split into modules (the page, the floating bar, the range toolbox, the note toolbox,
the sheet toolbox, the edits model), with no change of behaviour first, checked by the existing
checks and by screenshots. Then section 11.1 to 11.3: the cards removed, the default negra from the
highest peak (backend, with its test, and the note under D-09), the default key and octave brackets
on first write, the floating bar, the sheet toolbox with its Title, Key and Layout tabs (Transpose and
Lyrics in Phase 7), the toolboxes as icon actions with tooltips, the line wrap checked and fixed
(section 11.2). Timings of the first piano sheet and of a hand move kept within 10% of the
implementation 08 numbers.

## Phase 3: The `.database/` folder, the tables, the project bundle, the migration

`AITU_DATABASE_DIR`, the folder on `/mnt/ssd2` (a link at first; `.env` since 2026-10-06), `.gitignore`, the Compose mount. SQLAlchemy and Alembic,
the tables of section 8.6 (all of them, so later phases add no migration they can avoid). The bundle
(section 8.3) with `notes.pmn` version 2 and `sheet.json`; the audio store by hash; the audio timeline
of section 8.5 (one audio per part for now, cuts as segments); the cached joined audio. Every module
that wrote under `data/audio/<uuid>/` now writes the bundle of the part, through `storage/paths.py`
only. The routes keyed by uuid work on parts (P-6, section 8.8). The old `/library` router and its
storage modules deleted. The migration script of section 8.9, run on a copy first, then for real; its
report. `make db-backup`, `db-restore`, `db-check`, `db-reindex`. All backend tests pass on a
temporary `.database/` per test. The human step: the user opens the migrated pieces and then decides
when to delete `aitu-backend/data/`.

## Phase 4: Users, login and the home network

The `users` and `sessions` tables in use, Argon2, the auth routes, the session check on every route,
the rights table of section 9.3 with a test per row and two users. The master user from `.env`. The
login page, the user menu (change password, theme, sign out), **Admin → Users**. The jobs record their
owner (section 18). `WEB_BIND` and Vite's allowed hosts; the app opened from the Mac at
`http://ubuntu:5173`. `context/08-security.md`.

## Phase 5: Projects and the Personal Vault

The `/projects` routes (list, create, rename, delete, duplicate, export, import) and the Projects page
(section 10.1). **New project** with its three choices (From scratch and From other projects open
their pages, built in Phases 8 and 10). From source on projects: the Source step, the Audio step with
**add audio** (several files in one timeline), the video as a step of the project (section 10.2)
with its temporary files, the Notes and Hands steps. Q-8 measured (can the video reader send notes
while it reads?) and raised. The `.aitu` export and import with their round-trip test.

## Phase 6: The Private Library

**Save to library** (artist, song, version name), with the audio written on save (section 8.5,
Q-3) and the temporary files deleted. My library: Songs, one song with its versions, Artists (with
their artist names), the Edit flow through a vault copy, Replace the version or Save as a new version,
history. Duplicate and Export from any version. Q-7 raised (offline downloads).

## Phase 7: The sheet toolbox: transposition, lyrics, keys and clefs of passages

Notes transposition and Figures transposition with their preview dialog, counts and undo (section
11.4); the `MiniPiano` and `FigurePicker`. The lyrics of section 11.5: the pool, drag and drop, frame
snapping, offset, size, width, line breaks, the edit toolbar (select, merge, split, back to pool,
delete), and the old saved words read as placed pieces. **Key for this passage** in the range toolbox.
The automatic clef rule in `vexflow-v2` (section 11.7) with its constants set on the library and shown
in screenshots; `npm test` in `vexflow-v2`.

## Phase 8: Copy and paste, and From scratch

Copy and paste of section 12 (the clipboard reference, the backend paste with notes, metadata and audio
segments, the insert that moves everything after it, and undo), across projects and layers with the
read check. Rule 2 changed, with its note in `wall-clock-rewrite.md`. From scratch (section 10.3).
Playback of a timeline of several audio files checked at every join.

## Phase 9: Recording in Sheet

The passage page of section 13: Current and Proposal, recording and takes, the condensed steps (range
of the take, then transcription, hands and piano sheet with the passage's key and figure), the window
and the speed, the two promotions with the audio choice, the confirmation of a length change, undo
after promotion. The staged session generalised to a passage of a part; the two old panels removed.

## Phase 10: From other projects, and the playlists

The compose page of section 10.4 (picker, read-only sheet, passages, sequential or subheader, reorder),
**Save as song** and **Save as integrated playlist** with parts. The integrated playlist on the Sheet
step (section 14.1: subheaders, the sub-song panel, reorder, join and split parts). Songs playlists
(section 14.2): the tables in use, My library → Playlists, **Make a playlist** from a selection.

## Phase 11: Play mode

Section 17: the clean page, Close and Next, Play and Pause with the scroll that keeps the cursor in
the middle, the lyrics shown by their frames, the keys, Notes Falling as a view, songs playlists (next
song, the list when closed, the continuous page). Entry points from every place a version or a
playlist is shown. (The old `PerformancePage` was already removed in Phase 1, with the old library
it read; `library/loadPerformanceScore.ts` is kept for this phase.)

## Phase 12: The music library data reconciled (any time after Phase 3; the parallel data is ready)

Read `library.sqlite` at the path in section 15.5, the parallel plan, and its phase reports. There is
no response file. Write `context/music-library/reconciliation.md`: the mapping of its tables to
section 8.6, the gaps in both directions, the identity rule, and the decisions they need. Add to
section 8.6 (and its Alembic migration) only what the reconciliation shows is missing. Run the
popularity formula of section 15.6 on the downloaded chart history of songs (and of albums, if Q-6
keeps them), and tune it on a list the user ranks by hand. Q-5 (the regions not covered) and Q-6
raised with a recommendation each. This phase writes nothing into `data/music-library/` or into the
parallel work's scripts. Those scripts are on `feat/02-a-public-library` until that branch is merged.
The database is already in the folder next to the repository, so this phase can read it from here.

## Phase 13: The Public Library

The import of the reconciled data of Phase 12 into public rows, safe to run again. The Public Library pages:
search, the filter chips (decade, genre, region, tag category and value), sort by popularity, year or
title; one song with its metadata, fixed versions and Other versions by user; artists with their
names; public playlists. Likes. **Add to my library** for a song, an artist or a playlist (section
15.1). The seed list's songs present.

## Phase 14: Requests, the Admin panel and sharing

The three kinds of request with their items (section 16), the Publish dialog, My requests, the review
pages with side by side, partial acceptance, changes asked and resent, the transaction that publishes,
the creator's username on the version. Library sharing (section 15.4) and **Shared**. The counts in the
sidebar.

## Phase 15: The checks, the documentation, and closing

The whole journey in the browser, on temporary copies, with two users: a project from a YouTube link
to a piano sheet, saved to the library, published, reviewed and accepted, pulled by the second user,
played in Play mode, copied into a project from other projects. Timings. The documentation of section
19 that is still open, the old redirects removed, the code that read `aitu-backend/data/` removed. The
folder README marked complete.

---

# 21. What could go wrong

| Risk | What is done about it |
|---|---|
| The storage change breaks the 39 real pieces | The migration runs on a copy first, writes a report, and `aitu-backend/data/` stays until the user deletes it. `make db-check` compares the result |
| The split of the 5,353-line sheet page changes behaviour | Phase 2 splits first with no change, checked by the existing checks and screenshots, before any redesign |
| A user reads another user's private project | One rights check per route, a test per row of section 9.3 with two users, and tests that every list query is scoped by owner |
| A password crosses the home Wi-Fi in plain text | Accepted for a home network; written in `08-security.md` with the production answer |
| Two people write the same project | `baseRevision` on every write, as today; a refused write offers to reload |
| An audio file is deleted while a project still uses it | `audio_refs` counts uses; a file is deleted only at zero; `make db-check` compares the counts with the bundles |
| A length change detaches marks from their notes | The one Insert operation, already tested, moves notes and marks in the same write; tests for paste, promotion and composing |
| A source of the Public Library forbids reuse, or blocks downloads | Phase 12 checks terms and pace before any import; Q-5 is the user's decision |
| The popularity formula does not match the user's sense | Tuned on a list the user ranks by hand (Q-6) |
| A large `.database/` is slow to back up | `zstd`, and the audio files never change once written, so a later version can copy only new files |
| A GPU job of one user blocks the others | One queue, first in first out, with the waiting position shown |

---

# 22. How it is checked

- `aitu-backend`: `make test-backend` (inside the container), with a temporary `.database/` per test.
  When another project holds the GPU, the tests run on the CPU instead (the command is in the Phase 0
  report, section 4.2); the baseline is 1,040 tests.
  New tests: the bundle and `notes.pmn` version 2, the timeline, the migration on a fixture tree, the
  export and import round trip, the rights table, the login, copy and paste, the promotions, the
  requests and partial acceptance, the popularity formula.
- `aitu-frontend`: `npm run lint`, `npm run build`, the existing `check:*` scripts, and new ones:
  `check:shell` (every route renders for a master user and for a plain user), `check:transpose`,
  `check:lyrics`, `check:paste`. `check-flow.mjs` follows the routes of the projects.
- `vexflow-v2`: `npm test` for the clef rule (Phase 7) and any line wrap fix (Phase 2).
- `scripts/docs/check-links.py` passes at the end of every phase.
- In the browser, by the user, at the end of every UI phase, at `http://ubuntu:5173` (from Phase 4) or
  through the tunnel (before it). The agent takes its own screenshots first.

---

# 23. Not in this implementation

| Thing | Why |
|---|---|
| A production build, HTTPS, a cloud deployment | The app context says this is the later, production-based version. `.database/` is ready to be its volume |
| Public sign-up, email, password recovery by email | Production work (P-7) |
| Offline downloads in the browser | Q-7; on one home server the libraries are already on the same disk |
| Removing the YouTube download and the video source | They stay in this personal, local version; the app context says they leave in the production version |
| Synthesized sound from the `.pmn` | The app context excludes it: only recorded audio plays |
