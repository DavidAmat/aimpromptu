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
project. Its sections (`layout/AppLayout.tsx`):

| Section | What it is for |
|---|---|
| **Projects** | The user's own projects; each one goes from its audio to its piano sheet, one step at a time |
| **Songs**, **Artists**, **Playlists**, **Shared** (under My library) | The user's Private Library: songs with their versions, artists with their names, the songs playlists, and the libraries other users share with the user ([music-library/private-library.md](../music-library/private-library.md), [playlists.md](playlists.md)) |
| **Songs**, **Artists**, **Playlists** (under Public library) | The Public Library that every user shares ([music-library/ontology.md](../music-library/ontology.md)) |
| **Requests** | The user's requests to the Public Library, with the number of those with changes asked ([music-library/requests.md](../music-library/requests.md)) |
| **Review** (under Admin, master user only) | The requests waiting for a review, with their number |
| **Users** (under Admin, master user only) | Every user: **New user**, **Reset password**, **Disable** / **Enable** |
| **Lab** (under Admin, master user only) | The video reader's pages: the video, its calibration, the detection, its notes, the examples ([lab.md](lab.md)) |

Projects and the songs of My library can be put in folders and carry metadata ([folders-and-metadata.md](folders-and-metadata.md)).
Another user sees no Admin group, and an Admin address shows them "Page not found". `/` goes to `/projects`.
**Play mode** (`/play/...`) is the sheet alone, outside the shell ([play-mode.md](play-mode.md)).

The user menu at the bottom shows the username and the role (Master user or User), then
**Change password** (a dialog: the current password and a new one of at least 8 characters),
**Share my library**, the theme (**Light**, **Dark** or **System**, the device's own setting), **Keyboard shortcuts** and
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

Read the sheet drawn on arrival · **Enhance with AI** (the whole song written again, a level, easy, medium or hard,
of one hand or both with its patterns, or one stretch of both hands or one with the reader's own words; the
history of AI runs: [../ai/README.md](../ai/README.md)) · change the main figure (**Transpose figures**) · title the sheet · set a note's figure by hand · choose
the key of the piece or of a stretch · correct which hand plays a note · fingering · cut or join a beam · clefs
and octave lines · take a note off the page or add one on the keyboard · trills, mordents, turns, a rolled chord,
a fermata · words under the staff · a grace note leaning on a note · re-record a passage on its own page and
promote it · copy and paste a passage · print to PDF · play it and follow along. Every change is written at once
as one step of undo.

Detail: the page itself (the header, the zoom, the floating toolbox, undo) in [sheet-page.md](sheet-page.md);
the toolboxes in [annotations.md](annotations.md).

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
POST  /sheet/{id}/llm/level     ◀──  a level of a stretch; /llm/level-copy the whole song at a level, a new project
GET   /sheet/{id}/llm/batches   ──▶  the batches of a run and the dialog's cost and time (also /llm/costs)
GET   /sheet/{id}/llm/runs      ──▶  the history of AI runs
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
- [folders-and-metadata.md](folders-and-metadata.md): the folders, the pills and the metadata of My projects and My library
- [rendering.md](rendering.md): how the sheet is drawn (by the backend)
- [sheet-page.md](sheet-page.md): the Sheet step's page: the header, the zoom, the floating toolbox, undo and redo
- [annotations.md](annotations.md): the toolboxes of the Sheet step, with
  [annotations-notes.md](annotations-notes.md), [annotations-stretches.md](annotations-stretches.md)
  and [annotations-sheet.md](annotations-sheet.md) for its three toolboxes
- [printing.md](printing.md): the PDF, re-wrapped to the paper, never scaled
- [recording-in-sheet.md](recording-in-sheet.md): a passage re-recorded and promoted
- [playlists.md](playlists.md): From other projects, the parts, the playlists
- [play-mode.md](play-mode.md): Play mode and Notes Falling
- [lab.md](lab.md): the Lab, the video reader's pages
- [../ai/README.md](../ai/README.md): the AI on the sheet: every kind of run
- [timestamps.md](timestamps.md): the `mm:ss.cc` rule
- [documentation/services/frontend/](../../documentation/services/frontend/): the component tree and
  the PDF writer
