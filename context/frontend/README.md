# aitu-frontend

React 19 + TypeScript + Vite app. It brings a recording in, shows how it was actually played, and
draws the sheet — with `@aimpromptu/grid-notation`, a renderer built for this project because
nothing off the shelf lays music out on a wall clock.

It owns **all** drawing. The backend decides what each note is called; this app decides how the page
looks and what the reader can do to it.

## The sections

| Section | What it is for |
|---|---|
| **YouTube to Audio** | Pull audio off a video into the store |
| **Playground** | Where a piece is worked on — four tabs, in the order of the work |
| **Piano Library** | What a performer plays from: browse, tag, playlists, a read-only page |

The Playground tabs:

| Tab | What you do there |
|---|---|
| Upload / Input | Bring a piece in — upload, record, the audio library, or **Compose** an empty one |
| Piano Roll | The recording against a keyboard, left to right |
| Notes Falling | The same notes arriving at the keys |
| **Piano Sheet** | The product: read the playing, name one pile, get the sheet, edit it, print it |

The two visual views sit between input and the sheet because that is when they are useful: they are
how you check a transcription before committing to reading it.

## What a reader does on the sheet

Name the beat · write the whole piece longer or shorter · say the piece changes speed · rename one
note or a whole passage · choose the key · correct which hand plays a note · fingering · break or
join a beam · octave brackets · take a note off the page · accept a suggested trill · words under
the staff · print a stretch small · a grace note leaning on a note · re-record a passage · add a
passage to a piece being composed · save the reading · print to PDF · play it and follow along.

Detail: [annotations.md](annotations.md).

## Data flow

```
GET /matrix/{id}/events  ──▶  Piano Roll, Notes Falling      (seconds, as recorded)
GET /time/{id}/peaks     ──▶  the peak plot                  (the picture of the playing)
GET /time/{id}/score     ──▶  TimeScoreView ──▶ @aimpromptu/grid-notation
PUT /time/{id}/rhythm    ◀──  the reader's decisions
```

Nothing is drawn from a stored grid, because there is no stored grid. Every view is derived from the
recorded notes.

## Run

```bash
cd aitu-frontend && npm install && npm run dev
```

Backend expected at `http://127.0.0.1:8765`; override with `VITE_AITU_API_URL`. Or run both from the
repository root with `make serve`. See [04-local-development.md](../04-local-development.md).

## Where to look deeper

- [pages.md](pages.md) — the routes, the shell, the shared working artifact
- [rendering.md](rendering.md) — how the sheet is drawn, and what the app does *not* decide
- [annotations.md](annotations.md) — what a reader can say about a piece, and where it goes
- [printing.md](printing.md) — the PDF: re-wrap to the paper, never scale
- [timestamps.md](timestamps.md) — the `mm:ss.cc` rule
- [documentation/services/frontend/](../../documentation/services/frontend/) — the component tree,
  the renderer seam, the PDF writer
