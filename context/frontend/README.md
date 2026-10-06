# aitu-frontend

React 19 + TypeScript + Vite app. It brings a recording in, shows how it was actually played, and
draws the sheet with `@aimpromptu/grid-notation`, a renderer built for this project because nothing
off the shelf lays music out on a wall clock.

It owns **all** drawing. The backend decides what each note is called; this app decides how the page
looks and what the reader can do to it.

## Signing in

Every page needs a signed-in user (implementation 02, Phase 4). A reader who is not signed in is sent
to `/login`: the logo, **Username**, **Password** and **Sign in**, nothing else. After signing in the
page returns to the address the reader asked for (`?next=`). When any request answers `401` (the
session ended, the password was reset, or 30 days passed), the page opens the sign-in page again.
There is no sign-up: the master user makes the users in **Admin → Users**. The rules (who can open
what) are in [`../08-security.md`](../08-security.md); the guards are in [pages.md](pages.md).

## The shell

A left sidebar and the page on its right, no top bar (implementation 02, plan section 6.2). The
sidebar has the logo, **Search** (`⌘K`), the sections, and the user menu at the bottom. It is
260 px wide with words, or 64 px with icons only; it is open on the list pages and closed inside a
project. A section appears only once it is built:

| Section | What it is for |
|---|---|
| **Projects** | The user's own projects; each one goes from its audio to its piano sheet, one step at a time |
| **Users** (under Admin, master user only) | Every user: **New user**, **Reset password**, **Disable** / **Enable** |
| **Lab** (under Admin, master user only) | The video reader's pages: the video, its calibration, the detection, its notes, the examples |

Another user sees no Admin group, and an Admin address shows them "Page not found". The libraries,
Requests and Admin's other pages appear in the phases that build them. `/` goes to `/projects`.

The user menu at the bottom shows the username and the role (Master user or User), then
**Change password** (a dialog: the current password and a new one of at least 8 characters), the
theme (**Light**, **Dark** or **System**, the device's own setting), **Keyboard shortcuts** and
**Sign out**.

A page has a title on the left and its one primary action on the right, and no subtitle. The look
is black, white and grey, with colour spent only on the music, in a light and a dark scheme; the
piano sheet stays white paper in both: see [`../colors/color-palette.md`](../colors/color-palette.md).

## The steps of a project

Implementation 08 built one page that walks a piece through five steps in order: **Source** (bring
the audio in), **Audio** (choose the selected region with cuts), **Notes** (watch the live
transcription, then edit the rectangles of the piano roll visualization), **Hands** (the hand split,
then reassign notes to the right hand or the left hand) and **Sheet** (the piano sheet).
Implementation 02 made it the page of a project (`/projects/:id/:step`). A step opens only when the
step before it is ready, and a step whose input changed is marked stale. Nothing on the Audio, Notes
and Hands steps is written before **Save**. A project of another user, or one that does not exist,
shows "There is no project of yours at this address." with **Open Projects**.

Detail: [projects.md](projects.md).

**Removed in implementation 02, Phase 1** (decision Q-4): the Playground (Upload / Input, Notes
Falling, Piano Sheet as tabs), the YouTube to Audio page, and the old Piano Library with its
read-only performance page. A YouTube download is the Source step, Notes Falling opens from a
project's `⋯` menu, and the old paths redirect.

## What a reader does on the sheet

Read the sheet drawn on arrival · change the main figure · title the sheet · say the piece changes speed · rename one
note or a whole passage · choose the key · correct which hand plays a note · fingering · break or
join a beam · octave brackets · take a note off the page · accept a suggested trill · words under
the staff · print a stretch small · a grace note leaning on a note · re-record a passage · add a
passage to a piece being composed · save the reading · print to PDF · play it and follow along.

Detail: [annotations.md](annotations.md).

## Data flow

```
POST  /auth/login               ◀──  Sign in; GET /auth/me when the page opens
GET   /audio/                   ──▶  Projects and Search: the user's own pieces, with when each last changed
GET   /pieces/{id}/status       ──▶  a project: which steps are ready, stale or missing
GET   /audio/{id}/frames/peaks  ──▶  the Audio tab's waveform
PUT   /audio/{id}/cuts          ◀──  the selected region
POST  /matrix/transcribe        ◀──  Transcribe; the progress stream feeds the live Notes tab
PATCH /pieces/{id}/notes        ◀──  the edits of the Notes and Hands tabs, as operations
GET   /matrix/{id}/events       ──▶  Notes Falling          (seconds, as recorded)
GET   /time/{id}/default-reading ─▶ the figure ladder      (the highest pile of gaps is a negra)
GET   /time/{id}/score          ──▶  TimeScoreView ──▶ @aimpromptu/grid-notation
PUT   /time/{id}/rhythm         ◀──  the reader's decisions on the sheet
```

Nothing is drawn from a stored grid, because there is no stored grid. Every view is derived from the
recorded notes.

## Run

The usual way is the containers, from the repository root:

```bash
make up      # the backend (with the GPU) and the frontend; the app is at http://ubuntu:5173 from the Mac
```

Sign in as the master user with `AITU_MASTER_PASSWORD` of `.env`.

Natively: `cd aitu-frontend && npm install && npm run dev`, with the backend at
`http://127.0.0.1:8765`, or `make serve` from the repository root for both. The page calls `/api`,
and the Vite server passes it to the backend. See
[04-local-development.md](../04-local-development.md) and
[aitu-frontend/README.md](../../aitu-frontend/README.md) for every npm script.

## Where to look deeper

- [projects.md](projects.md): Projects and the steps of a project
- [pages.md](pages.md): the routes, the shell, the shared working artifact
- [../colors/color-palette.md](../colors/color-palette.md): the tokens and the colours of the music
- [rendering.md](rendering.md): how the sheet is drawn, and what the app does *not* decide
- [annotations.md](annotations.md): the Sheet step (the page, the defaults, undo, saving), with
  [annotations-notes.md](annotations-notes.md), [annotations-stretches.md](annotations-stretches.md)
  and [annotations-sheet.md](annotations-sheet.md) for its three toolboxes
- [printing.md](printing.md): the PDF, re-wrapped to the paper, never scaled
- [timestamps.md](timestamps.md): the `mm:ss.cc` rule
- [documentation/services/frontend/](../../documentation/services/frontend/): the component tree,
  the renderer seam, the PDF writer
