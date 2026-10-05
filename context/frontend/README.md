# aitu-frontend

React 19 + TypeScript + Vite app. It brings a recording in, shows how it was actually played, and
draws the sheet with `@aimpromptu/grid-notation`, a renderer built for this project because nothing
off the shelf lays music out on a wall clock.

It owns **all** drawing. The backend decides what each note is called; this app decides how the page
looks and what the reader can do to it.

## The shell

A left sidebar and the page on its right, no top bar (implementation 02, plan section 6.2). The
sidebar has the logo, **Search** (`⌘K`), the sections, and the user menu at the bottom. It is
260 px wide with words, or 64 px with icons only; it is open on the list pages and closed inside a
project. A section appears only once it is built:

| Section | What it is for |
|---|---|
| **Projects** | The projects being worked on; each one goes from its audio to its piano sheet, one step at a time |
| **Lab** (under Admin) | The video reader's pages: the video, its calibration, the detection, its notes, the examples |

The libraries, Requests and Admin's other pages appear in the phases that build them. The user menu
is a placeholder until users exist (Phase 4): it holds **Keyboard shortcuts**. `/` goes to
`/projects`.

A page has a title on the left and its one primary action on the right, and no subtitle. The look
is black, white and grey, with colour spent only on the music: see
[`../colors/color-palette.md`](../colors/color-palette.md).

## The steps of a project

Implementation 08 built one page that walks a piece through five steps in order: **Source** (bring
the audio in), **Audio** (choose the selected region with cuts), **Notes** (watch the live
transcription, then edit the rectangles of the piano roll visualization), **Hands** (the hand split,
then reassign notes to the right hand or the left hand) and **Sheet** (the piano sheet).
Implementation 02 made it the page of a project (`/projects/:id/:step`). A step opens only when the
step before it is ready, and a step whose input changed is marked stale. Nothing on the Audio, Notes
and Hands steps is written before **Save**.

Detail: [flow-page.md](flow-page.md).

**Removed in implementation 02, Phase 1** (decision Q-4): the Playground (Upload / Input, Notes
Falling, Piano Sheet as tabs), the YouTube to Audio page, and the old Piano Library with its
read-only performance page. A YouTube download is the Source step, Notes Falling opens from a
project's `⋯` menu, and the old paths redirect.

## What a reader does on the sheet

Name the beat · write the whole piece longer or shorter · say the piece changes speed · rename one
note or a whole passage · choose the key · correct which hand plays a note · fingering · break or
join a beam · octave brackets · take a note off the page · accept a suggested trill · words under
the staff · print a stretch small · a grace note leaning on a note · re-record a passage · add a
passage to a piece being composed · save the reading · print to PDF · play it and follow along.

Detail: [annotations.md](annotations.md).

## Data flow

```
GET   /audio/                   ──▶  Projects and Search: every piece, with when it last changed
GET   /pieces/{id}/status       ──▶  a project: which steps are ready, stale or missing
GET   /audio/{id}/frames/peaks  ──▶  the Audio tab's waveform
PUT   /audio/{id}/cuts          ◀──  the selected region
POST  /matrix/transcribe        ◀──  Transcribe; the progress stream feeds the live Notes tab
PATCH /pieces/{id}/notes        ◀──  the edits of the Notes and Hands tabs, as operations
GET   /matrix/{id}/events       ──▶  Notes Falling          (seconds, as recorded)
GET   /time/{id}/peaks          ──▶  the peak plot          (the picture of the playing)
GET   /time/{id}/score          ──▶  TimeScoreView ──▶ @aimpromptu/grid-notation
PUT   /time/{id}/rhythm         ◀──  the reader's decisions on the sheet
```

Nothing is drawn from a stored grid, because there is no stored grid. Every view is derived from the
recorded notes.

## Run

The usual way is the containers, from the repository root:

```bash
make up      # the backend (with the GPU) and the frontend; the app is at http://localhost:5173
```

Natively: `cd aitu-frontend && npm install && npm run dev`, with the backend at
`http://127.0.0.1:8765`, or `make serve` from the repository root for both. The page calls `/api`,
and the Vite server passes it to the backend. See
[04-local-development.md](../04-local-development.md) and
[aitu-frontend/README.md](../../aitu-frontend/README.md) for every npm script.

## Where to look deeper

- [flow-page.md](flow-page.md): Projects and the steps of a project
- [pages.md](pages.md): the routes, the shell, the shared working artifact
- [../colors/color-palette.md](../colors/color-palette.md): the tokens and the colours of the music
- [rendering.md](rendering.md): how the sheet is drawn, and what the app does *not* decide
- [annotations.md](annotations.md): what a reader can say about a piece, and where it goes
- [printing.md](printing.md): the PDF, re-wrapped to the paper, never scaled
- [timestamps.md](timestamps.md): the `mm:ss.cc` rule
- [documentation/services/frontend/](../../documentation/services/frontend/): the component tree,
  the renderer seam, the PDF writer
