> Context: [context/backend/api.md](../../../context/backend/api.md) ·
> [context/backend/time-model.md](../../../context/backend/time-model.md)

# Endpoints

FastAPI app: `aitu-backend/src/aitu_backend/main.py`, title "AImpromptu Backend API". One router per
product section, all of them listed in `api/__init__.py` as `ALL_ROUTERS`.

**The live authority on every field is `http://127.0.0.1:8765/docs`.** The generated OpenAPI page is
built from the same Pydantic models the handlers use, so it cannot drift. This file says what each
route is *for*, which decisions it obeys, and where the model lives — the things a schema dump does
not tell you.

Every request and response body is camelCase, produced by Pydantic aliases. CORS allows all origins
(`allow_origins=["*"]`, `allow_credentials=False`); this is a local POC with no auth surface.

---

## 1. The whole surface in one table

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness: `{"status": "ok"}`. |
| **Audio** | `api/audio.py` | |
| GET | `/audio/` | Every ingested audio. |
| POST | `/audio/upload` | Upload a file; ffmpeg normalises it. |
| POST | `/audio/recording` | Store a browser recording. |
| POST | `/audio/compose` | Start a piece with **nothing in it** (Epic 13). |
| GET | `/audio/{uuid}` | One entry. |
| PATCH | `/audio/{uuid}` | Rename. |
| DELETE | `/audio/{uuid}` | Delete the uuid folder. |
| POST | `/audio/{uuid}/trim` | Persist a range as a new child audio, with lineage. |
| GET | `/audio/{uuid}/file` | Stream the audio. |
| GET | `/audio/{uuid}/range` | Stream one range of it. |
| GET | `/audio/{uuid}/waveform` | Min/max peaks for the waveform view. |
| **Transcription** | `api/matrix.py` | |
| GET | `/matrix/engines` | Which engines can actually run here. |
| POST | `/matrix/transcribe` | Start the model; returns `202` and a job id. |
| GET | `/matrix/progress/{jobId}` | SSE progress stream. |
| GET | `/matrix/jobs/{jobId}` | The same state, for pollers. |
| GET | `/matrix/{uuid}/events` | Every note the model reported, in seconds. |
| PUT | `/matrix/{uuid}/events/removed` | Take notes off the recording, by pitch and second. |
| **The score** | `api/time_score.py` | |
| GET | `/time/{uuid}/peaks` | Where the gaps between attacks pile up. |
| POST | `/time/{uuid}/ladder-preview` | Name one peak, see what every other becomes. |
| GET | `/time/{uuid}/score` | The drawable score payload. |
| POST | `/time/{uuid}/score` | The same, with the reader's page edits folded in. |
| GET | `/time/{uuid}/trills` | Alternating runs, offered as suggestions. |
| PUT | `/time/{uuid}/hands` | Correct which hand plays a note. |
| PUT | `/time/{uuid}/removed` | Take notes off the page, by column and row. |
| PUT | `/time/{uuid}/notes` | Put notes into the recording, by column and row. |
| GET PUT DELETE | `/time/{uuid}/rhythm` | The saved reading. |
| **Editing and composing** | `api/editing.py` | |
| POST | `/audio/{uuid}/edits` | Open a disposable session. |
| GET PATCH DELETE | `/audio/{uuid}/edits/{session}` | Read, adjust, throw away. |
| POST | `/audio/{uuid}/edits/{session}/take` | Upload the take. |
| GET | `/audio/{uuid}/edits/{session}/take` | The take, as played or scaled. |
| GET | `/audio/{uuid}/edits/{session}/waveform` | Peaks of the untrimmed take. |
| GET | `/audio/{uuid}/edits/{session}/window` | The original window, optionally slowed. |
| POST | `/audio/{uuid}/edits/{session}/transcribe` | Transcribe the take as played. |
| POST | `/audio/{uuid}/edits/{session}/preview` | Scale it into the window and draw that stretch. |
| GET | `/audio/{uuid}/edits/{session}/confirmation` | What accepting would change. |
| POST | `/audio/{uuid}/edits/{session}/accept` | Write it into the piece. |
| **Library** | `api/library.py` | |
| GET POST | `/library/playground` | List playground tracks; save a version. |
| GET PATCH | `/library/playground/{artist}/{track}` | One track; rename it. |
| GET DELETE | `/library/playground/{artist}/{track}/{folder}` | One version. |
| GET | `/library/promotion-suggestion/{artist}/{track}` | A suggested promotion name. |
| POST | `/library/promote` | Promote a version into the library. |
| POST | `/library/rollback` | Return to an earlier promotion. |
| GET | `/library/tracks` | Promoted tracks. |
| GET | `/library/tracks/{artist}/{track}` | One promoted track. |
| GET POST | `/library/tags` | Every tag; set a track's tags. |
| GET POST | `/library/playlists` | List and create. |
| GET PATCH DELETE | `/library/playlists/{slug}` | One playlist. |
| **YouTube** | `api/youtube.py` | |
| POST | `/youtube/probe` | Title and length, without downloading. |
| POST | `/youtube/download` | Download the audio as mp3. |
| POST | `/youtube/batch` | Queue several. |
| **Text-notation MVP** | `api/scores.py` | |
| GET | `/scores` | Seed scores from `data/example-scores.json`. |
| POST | `/sequence` | Text notation to a sparse score. |

The last two are the project's original MVP and are **not** part of the wall-clock path — see
[§8](#8-the-text-notation-mvp-routes).

---

## 2. `/audio` — the working store

One uuid folder per ingested audio, whatever the source. Upload, browser recording and YouTube all
converge on `audio/ingest.py`, so the rest of the system never asks where a recording came from.

`POST /audio/upload` accepts `.mp3 .aac .m4a .wav .webm .ogg`. Browser recordings arrive as webm or
ogg because Chrome records nothing else, and ffmpeg converts them server-side. **Without `ffmpeg`
on `PATH` this route answers `503`** with that instruction rather than failing obscurely.

`POST /audio/{uuid}/trim` writes a **physical** child audio with absolute lineage back to its root
source, rather than remembering a range. A named segment survives the parent being deleted and can
itself be trimmed again.

`POST /audio/compose` is the odd one out: it creates a piece with no audio file at all. It writes an
empty `events.json` (`durationSeconds: 0`) and a `frameMs` on the metadata, and the first accepted
passage is what creates a recording. Body: `{ "name": string, "frameMs": number }`.

---

## 3. `/matrix` — running the model

Five routes, and between them they are everything the Upload / Input tab needs: which models are
installed, start one, follow it, ask how it went, and read the notes it produced.

**Nothing here returns a grid.** A grid is a view of the recorded notes at a chosen frame length, so
it is built while the request is answered and served from `/time` instead.

### POST /matrix/transcribe

```json
{ "audioUuid": "…", "frameMs": 40, "startSeconds": null,
  "endSeconds": null, "engine": "bytedance", "force": false }
```

There is one number in that body and it is a length of time. It does not decide what any note is
called: the figures are chosen afterwards, from a ladder the reader names (D-01, D-09). `force`
runs the model again on audio that already has its recorded notes.

Answers `202` with `{ "jobId", "status" }` because transcription takes tens of seconds. Follow
`GET /matrix/progress/{jobId}` — a Server-Sent Events stream that reports real model-batch progress
and ends with a named `done` event — or poll `GET /matrix/jobs/{jobId}`.

`GET /matrix/engines` returns `{engine: bool}`; `false` means the package is not installed, so the
UI can grey the option out instead of letting the reader pick something that will fail.

### GET /matrix/{uuid}/events

Every note the model reported, in seconds, with the discards **marked rather than removed**. The
artifact filter is applied here only as a label, because the point of the route is to show what the
rest of the system chose not to use — a filter that can be checked instead of taken on trust.

Each event carries a `hand`, filled from the standard split at `frameMs` so the colours agree with
the sheet. It is a label and nothing else: the times are untouched, a manual hand correction still
wins, and a split that fails leaves the notes uncoloured rather than failing the request.

This is what Piano Roll and Notes Falling draw.

### PUT /matrix/{uuid}/events/removed

Marks notes as taken off the recording, addressed by pitch and start second. `removed` is a flag on
the note event, so nothing is deleted and putting a note back restores it exactly.

There are **two** routes that write this flag, and that is deliberate: the two screens genuinely
hold different things. A reader on Piano Roll knows raw seconds; a reader on the sheet has clicked a
notehead and knows a column and a row, which is `PUT /time/{uuid}/removed`. Same field, same
consequences.

Removing a note is not a filter on one screen. A note's printed length is the gap to the next onset
in the same hand (D-14), so taking one off **renames its neighbour** — which is why it is written
onto the recording rather than drawn over.

---

## 4. `/time` — the wall-clock score

Everything here is derived from the stored `events.json` on every request. Nothing is cached and
nothing is written, so re-reading a piece at 20 ms instead of 40 is a different query string rather
than a migration.

### GET /time/{uuid}/peaks

| Query | Default | Meaning |
|---|---|---|
| `hand` | `right` | `right`, `left` or `both`. |
| `frameMs` | 40 | |
| `startSeconds` | 0 | Measure a stretch rather than the piece. |
| `endSeconds` | — | |

Returns the piles of gaps between attacks, each with its centre, median, mean, count, share and
edges, plus `attackCount`, `gapCount` and an optional plain-language `warning`.

Measured on the **raw recorded times, never on the columns** (D-07). Snapping first splits every
pile in two: a real 337 ms gap becomes 8 or 9 frames depending on phase, so one clean spike holding
half the data becomes two half-height spikes and the reader is asked to name a peak nobody played.

Each hand is measured on its own, because the gap between a right-hand run and a held left-hand
chord is not a rhythm and would bury the peak that matters.

### POST /time/{uuid}/ladder-preview

```json
{ "anchorFigure": "negra", "anchorMs": 480, "hand": "right",
  "frameMs": 40, "startSeconds": 0, "endSeconds": null }
```

Returns the resulting `FigureLadder`, a `headerLabel` such as `negra = 480 ms · ≈125 BPM`, the
equivalent `bpm`, and every detected peak labelled under that ladder with how far off it fits.

This exists because the app never chooses the ladder (D-09) and the reader has to be able to judge
a choice before committing to it (D-10). A pile at a third of the **negra** is named
`corchea de tresillo` rather than a 33 %-wrong corchea (D-32).

### GET /time/{uuid}/score

| Query | Default | Meaning |
|---|---|---|
| `anchorFigure` | `negra` | |
| `anchorMs` | **required** | |
| `frameMs` | 40 | |
| `boundaries` | `""` | Passage boundaries as frame numbers, e.g. `250,900`. |
| `boundaryMs` | `""` | One anchor per passage — **one more value than boundaries**. |

Returns a `TimeScorePayload`: the two hand matrices, the passages, every printed note with its
figure already chosen, and the layout hints. Field detail in
[`time-matrix.md`](time-matrix.md#29-timescorepayload).

A mismatched count of boundaries and anchors is a `422` that says both numbers.

### POST /time/{uuid}/score

The same answer, with the reader's page edits folded in **before any figure is named**. Body adds
`hiddenNotes` and `trills` to the query parameters above.

The edits have to be applied on this side rather than in the browser for one reason: hiding a note
changes the gap to its neighbour, and therefore that neighbour's printed figure. An overlay drawn
after the figures were chosen would show the right noteheads with the wrong names.

### GET /time/{uuid}/trills

`frameMs`, and `minPairRepeats` (2–20, default 3). Returns stretches where two notes a whole tone or
less apart trade places at least three times, evenly, under 300 ms, measured on the raw attack times
per hand.

**A suggestion and nothing more.** Nothing is written and the sheet does not change until the reader
accepts one: a missed trill costs a reader nothing, and a wrong one hides notes that were really
played, so the reader has the last word.

### PUT /time/{uuid}/hands, PUT /time/{uuid}/removed, PUT /time/{uuid}/notes

Which hand plays a note is a fact about the *playing*, not about the page: it survives a change of
column length and it decides the printed length of its neighbours. So it is written onto the note
event rather than stored as an annotation, and everything downstream follows without coordinating.

`PUT /time/{uuid}/removed` addresses notes by column and row. Putting one back cannot be resolved
against the current matrix — the note is not in it, which is what removed means — so a restore
builds its lookup from a split with every removal undone, which is the numbering the columns were
written down at. One extra split, paid only on an undo.

`PUT /time/{uuid}/notes` is its opposite, and writes to the same place for the same reason. A reader
looking at the keyboard panel can see a note missing from a chord; drawing an extra notehead beside
the score would be the wrong fix twice over, because the printed length of a note is the gap to the
next onset in the same hand — so a note appearing out of nowhere renames its neighbour — and because
the roll, the falling view and playback would all go on disagreeing with the page.

The times are the column's own: a note added at f120 starts 120 column-lengths into the piece. That
is only ever a few milliseconds from where a played note would have landed, and the whole page is
drawn on that grid anyway. The hand travels with it, pinned the way a corrected hand is. A key
already struck in that column is **refused and counted** rather than merged, because the matrix
rejects a frame where both hands hold one key and merging would lose a note.

Answers `{"added": n, "duplicate": n}`.

### GET / PUT / DELETE /time/{uuid}/rhythm

The reader's saved reading: the anchor, the key, clef changes, speed changes, renamed figures, beam
breaks and beam joins, hidden notes, fingering, trills, grace notes, lyrics, cue-size stretches and
how far apart the notes and the lines stand. One per piece — a second
reading replaces the first. See [`rhythm-and-annotations.md`](rhythm-and-annotations.md).

`DELETE` answers `204` and is what **Remove all** calls.

---

## 5. `/audio/{uuid}/edits` — staged editing and composing

A disposable session holds the take. Cancel deletes the folder and nothing else; nothing reaches the
piece until accept.

Accept does one of two things, and which one is the session's `placement`:

- **`replace`** (Epic 11) splices the take into exactly the window it replaces. The piece keeps its
  length, which is what lets every mark after the window keep its address.
- **`append`** and **`insert`** (Epic 13) put a new passage in and make the piece longer — the one
  place in the product where that is allowed, because a piece being composed has nothing after the
  insertion point to protect.

`POST /audio/{uuid}/edits` takes the placement plus either a window (`startFrame`/`endFrame` or
`startSeconds`/`endSeconds`), a moment (for `insert`), or nothing but `gapSeconds` (for `append`),
along with `frameMs`, `slowdown` (1, 2 or 4), `spliceAudio` and an optional `clickIntervalMs` for
the metronome.

The flow is fixed and each step is its own route, so a reader can stop at any of them:

```
POST …/take        store the untrimmed recording
POST …/transcribe  run the model on the take AS PLAYED, never on stretched audio
POST …/preview     scale it into the window and draw that stretch alone
GET  …/confirmation  what accepting would change, counted by kind
POST …/accept      splice, snapshot to history/, advance the version
```

Transcribing the take as played rather than after stretching is load-bearing: a time-stretched
recording is a different sound, and the model would be reading an artefact instead of the playing.

`GET …/confirmation` reports dropped marks (`figureOverrides`, `beamBreaks`, `hiddenNotes`,
`fingerings`) for a replace, and moved marks with the column shift for an insert. A fingering that
has silently moved looks exactly like a fingering that has silently stayed, so the count is said out
loud before the button is pressed.

Errors: `404` for a missing session or audio, `409` for an operation the session's placement does
not allow (asking to fit a composed passage to a window, for instance), `503` when ffmpeg is
missing, `422` when a conversion fails.

Detail in [`editing-and-compose.md`](editing-and-compose.md).

---

## 6. `/library` — playground versions and promotion

Two trees, and the difference between them is the point. The **playground** holds work in progress,
versioned per track as `v<N>_f<frameMs>` folders. The **library** holds what a performer plays from:
named promotions, rollback, tags and playlists.

`POST /library/promote` takes an editable promotion name, and either replaces the current promotion
or adds another alongside it. `GET /library/promotion-suggestion/{artist}/{track}` proposes one
before the dialog opens.

Storage layout in [`paths-and-data.md`](paths-and-data.md).

---

## 7. `/youtube`

`yt-dlp` is a normal Python dependency and is invoked as `python -m yt_dlp` on the backend's own
interpreter, so it never depends on `PATH`. `POST /youtube/probe` reads a video's title and length
without downloading anything; `download` extracts mp3 and ingests it like any upload.

---

## 8. The text-notation MVP routes

`GET /scores` and `POST /sequence` are the project's original seed: a line-per-time-frame text
notation converted into a sparse 88-key score. They still run, and `matrix/text_notation.py` is
still their single source of truth.

**They are not part of the wall-clock path and no screen calls them.** Text notation and matrix JSON
were removed from Upload / Input in P4.2 for one reason: a sheet is written from recorded onsets and
neither of those has any. `POST /sequence` still takes `tempoBpm` and `timeStepSeconds`, which is
the clearest sign of which model it belongs to.

Parsing detail in [`sequence-logic.md`](sequence-logic.md), payload shapes in
[`schemas.md`](schemas.md).

`GET /scores` reads `data/example-scores.json` and answers `404` with a hint if it is missing.
`POST /sequence` answers `422` for an unknown note name or for hands with different frame counts.

---

## 9. What used to be here and is not

Stated plainly so nobody looks for it. These routes belonged to the tempo-based model and were
deleted in P4.2 with the Playground tabs that called them:

- reading one processing step of a stored matrix (`raw`, `collapsed`, `clean`)
- switching granularity, and any BPM parameter
- editing a matrix cell
- transposition
- matrix JSON import and export

If one of these should return on the wall-clock path, it is a new feature request with its own
reasoning, not unfinished work.

---

## 10. Where to look deeper

- [`time-matrix.md`](time-matrix.md) — every schema 2.0 field
- [`events-to-sheet.md`](events-to-sheet.md) — how a response is derived
- [`editing-and-compose.md`](editing-and-compose.md) — the splice and the insertion
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md) — `rhythm.json`
- [`transcription-pipeline.md`](transcription-pipeline.md) — what happens before any of this
- `http://127.0.0.1:8765/docs` — the generated, always-current field reference
