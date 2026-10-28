# aitu-frontend

React 19 + TypeScript + Vite app. It brings a recording in, shows how it was actually played, and
shows the piano sheet the backend draws (`GET /sheet/{uuid}` answers an SVG; implementation 03).

The backend decides what each note is called and lays the sheet out; this app draws the SVG, what
moves over it (the cursor, the picked notes, the marked stretch), and what the reader can do to it.
The old sheet, drawn in the browser by `@aimpromptu/grid-notation` (the sibling repository
vexflow-v2), was removed in implementation 03, Phase 10 (2026-10-27).

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
| **Songs**, **Artists** (under My library) | The user's Private Library: songs with their versions, artists with their names ([music-library/private-library.md](../music-library/private-library.md)) |
| **Users** (under Admin, master user only) | Every user: **New user**, **Reset password**, **Disable** / **Enable** |
| **Lab** (under Admin, master user only) | The video reader's pages: the video, its calibration, the detection, its notes, the examples |

Another user sees no Admin group, and an Admin address shows them "Page not found". Playlists,
Shared, the Public Library, Requests and Admin's other pages appear in the phases that build them. `/` goes to `/projects`.

The user menu at the bottom shows the username and the role (Master user or User), then
**Change password** (a dialog: the current password and a new one of at least 8 characters), the
theme (**Light**, **Dark** or **System**, the device's own setting), **Keyboard shortcuts** and
**Sign out**.

A page has a title on the left and its one primary action on the right, and no subtitle. The look
is black, white and grey, with colour spent only on the music, in a light and a dark scheme; the
piano sheet stays white paper in both: see [`../colors/color-palette.md`](../colors/color-palette.md).

## The steps of a project

Implementation 08 built one page that walks a piece through its steps in order; there are four today: **Source** (bring
the audio in), **Audio** (choose the selected region with cuts), **Notes** (watch the live
transcription, then edit the rectangles of the piano roll visualization) and **Sheet** (the piano sheet: the
sheet at once, and the AI writing the hands and the reading in the background). The **Hands** step left
the flow in implementation 03, Phase 5, and its code was removed in Phase 10.
Implementation 02 made it the page of a project (`/projects/:id/:step`). A step opens only when the
step before it is ready, and a step whose input changed is marked stale. Nothing on the Audio and Notes
steps is written before **Save**. A project of another user, or one that does not exist,
shows "There is no project of yours at this address." with **Open Projects**.

Detail: [projects.md](projects.md).

**Removed in implementation 02, Phase 1** (decision Q-4): the Playground (Upload / Input, Notes
Falling, Piano Sheet as tabs), the YouTube to Audio page, and the old Piano Library with its
read-only performance page. A YouTube download is the Source step, Notes Falling is a view of
Play mode (Phase 11, [play-mode.md](play-mode.md)). The old paths redirected until Phase 15.

## What a reader does on the sheet

Read the sheet drawn on arrival · **Enhance with AI** (the whole sheet, **Simplify** one hand or both, or one
stretch of both hands or one with the reader's own words) · change the main figure (**Transpose figures**) · title the sheet · set a note's figure by hand · choose
the key of the piece or of a stretch · correct which hand plays a note · fingering · cut or join a beam · clefs
and octave lines · take a note off the page or add one on the keyboard · trills, mordents, turns, a rolled chord,
a fermata · words under the staff · a grace note leaning on a note · re-record a passage on its own page and
promote it · copy and paste a passage · print to PDF · play it and follow along. Every change is written at once
as one step of undo.

Detail: [annotations.md](annotations.md).

## Data flow

```
POST  /auth/login               ◀──  Sign in; GET /auth/me when the page opens
GET   /audio/                   ──▶  Projects and Search: the user's own pieces, with when each last changed
GET   /pieces/{id}/status       ──▶  a project: which steps are ready, stale or missing
GET   /audio/{id}/frames/peaks  ──▶  the Audio tab's waveform
PUT   /audio/{id}/cuts          ◀──  the selected region
POST  /matrix/transcribe        ◀──  Transcribe; the progress stream feeds the live Notes tab
PATCH /pieces/{id}/notes        ◀──  the edits of the Notes tab, as operations
GET   /matrix/{id}/events       ──▶  Notes Falling of Play mode (seconds, as recorded)
GET   /sheet/{id}?width=N       ──▶  the sheet as an SVG and its cursor map ──▶ FramesSheetView
POST  /sheet/{id}/llm           ◀──  Enhance with AI; the progress stream says when to read the sheet again
POST  /sheet/{id}/llm/simplify  ◀──  Simplify one hand or both (GET /sheet/{id}/llm/costs: the dialog's costs)
POST  /sheet/{id}/...           ◀──  each edit of the sheet, one step of undo kept by the backend
```

Nothing is drawn from a stored grid, because there is no stored grid. Every view is derived from the
recorded notes.

## Run

`make up` from the repository root, then `http://ubuntu:5173` from any device at home. Every way to
run, open and check the app: [04-local-development.md](../04-local-development.md); every npm
script: [aitu-frontend/README.md](../../aitu-frontend/README.md).

## Where to look deeper

- [projects.md](projects.md): Projects and the steps of a project
- [pages.md](pages.md): the routes, the shell, the shared working artifact
- [../colors/color-palette.md](../colors/color-palette.md): the tokens and the colours of the music
- [rendering.md](rendering.md): how the sheet is drawn (by the backend)
- [annotations.md](annotations.md): the Sheet step (the page, the defaults, undo, saving), with
  [annotations-notes.md](annotations-notes.md), [annotations-stretches.md](annotations-stretches.md)
  and [annotations-sheet.md](annotations-sheet.md) for its three toolboxes
- [printing.md](printing.md): the PDF, re-wrapped to the paper, never scaled
- [timestamps.md](timestamps.md): the `mm:ss.cc` rule
- [documentation/services/frontend/](../../documentation/services/frontend/): the component tree and
  the PDF writer
