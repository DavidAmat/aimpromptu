# aitu-frontend

React 19 + TypeScript + Vite app. It brings a recording in, shows how it was actually played, and
draws the sheet with `@aimpromptu/grid-notation`, a renderer built for this project because nothing
off the shelf lays music out on a wall clock.

It owns **all** drawing. The backend decides what each note is called; this app decides how the page
looks and what the reader can do to it.

## The sections

The top bar, in this order:

| Section | What it is for |
|---|---|
| **Piece** | The flow page: one piece, from its audio to its piano sheet, one tab per step. Where a piece starts |
| **YouTube to Audio** | Download the audio of a video into the store |
| **Video to Notes** | Read the falling rectangles of a piano tutorial video |
| **Playground** | The older working tabs, kept beside the flow page |
| **Piano Library** | What a performer plays from: browse, tag, playlists, a read-only page |

The app opens on the flow page (`/` goes to `/piece/new`).

## The flow page

Implementation 08 added one page that walks a piece through five steps in order: **Source** (bring
the audio in), **Audio** (choose the selected region with cuts), **Notes** (watch the live
transcription, then edit the rectangles of the piano roll visualization), **Hands** (the hand split,
then reassign notes to the right hand or the left hand) and **Sheet** (the piano sheet). A tab opens
only when the step before it is ready, and a step whose input changed is marked stale. Nothing on
the Audio, Notes and Hands tabs is written before **Save**.

Detail: [flow-page.md](flow-page.md).

## The Playground

| Tab | What you do there |
|---|---|
| Upload / Input | Bring a piece in: upload, record, the audio library, or **Compose** an empty one |
| Notes Falling | The notes arriving at the keys |
| **Piano Sheet** | The product: read the playing, name one pile, get the sheet, edit it, print it |

The Piano Sheet tab and the flow page's Sheet tab are the same page. The Playground's **Piano Roll**
tab was removed in implementation 08: the Notes and Hands tabs of the flow page are the piano roll
visualization now, and `/playground/piano-roll` opens the flow page.

## What a reader does on the sheet

Name the beat · write the whole piece longer or shorter · say the piece changes speed · rename one
note or a whole passage · choose the key · correct which hand plays a note · fingering · break or
join a beam · octave brackets · take a note off the page · accept a suggested trill · words under
the staff · print a stretch small · a grace note leaning on a note · re-record a passage · add a
passage to a piece being composed · save the reading · print to PDF · play it and follow along.

Detail: [annotations.md](annotations.md).

## Data flow

```
GET   /pieces/{id}/status       ──▶  the flow page: which tabs are ready, stale or missing
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

- [flow-page.md](flow-page.md): the flow page, step by step
- [pages.md](pages.md): the routes, the shell, the shared working artifact
- [rendering.md](rendering.md): how the sheet is drawn, and what the app does *not* decide
- [annotations.md](annotations.md): what a reader can say about a piece, and where it goes
- [printing.md](printing.md): the PDF, re-wrapped to the paper, never scaled
- [timestamps.md](timestamps.md): the `mm:ss.cc` rule
- [documentation/services/frontend/](../../documentation/services/frontend/): the component tree,
  the renderer seam, the PDF writer
