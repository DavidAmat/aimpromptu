> Context: [context/backend/api.md](../../../context/backend/api.md) ·
> [context/backend/time-model.md](../../../context/backend/time-model.md) ·
> [context/backend/piano-matrix-notation.md](../../../context/backend/piano-matrix-notation.md)

# Endpoints

FastAPI app: `aitu-backend/src/aitu_backend/main.py`, title "AImpromptu Backend API". One router per
product section, all of them listed in `api/__init__.py` as `ALL_ROUTERS`.

**The live authority on every field is `http://127.0.0.1:8765/docs`.** The generated OpenAPI page is
built from the same Pydantic models the handlers use, so it cannot drift. This file says what each
route is *for*, which decisions it obeys, and where the model lives. A schema dump does not say
those things.

Every request and response body is camelCase, produced by Pydantic aliases. CORS allows all origins
(`allow_origins=["*"]`, `allow_credentials=False`); this is a local POC with no auth surface.

**JSON answers are compressed.** `JsonGZipMiddleware` (`aitu_backend/compression.py`, implementation
08, Phase 2) compresses a JSON answer of 1 KB or more with gzip at level 5 when the client sends
`Accept-Encoding: gzip`. Audio files and the SSE progress stream are never compressed. The piano
sheet answer is about 11 times smaller this way (634 KB median, 56 KB sent). A `curl` without
`--compressed` receives plain JSON.

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
| POST | `/audio/{uuid}/trim` | Persist a range as a new child audio, with lineage. Refused on a piece with cuts. |
| GET | `/audio/{uuid}/file` | Stream the audio of the piece (the edited audio once cuts are saved). |
| GET | `/audio/{uuid}/range` | Stream one range of `normalized.wav`. |
| GET | `/audio/{uuid}/waveform` | Min/max peaks for the waveform view, of the edited audio when there are cuts. |
| GET | `/audio/{uuid}/frames/peaks` | One min/max pair per 10 ms time frame of the original (implementation 08). |
| GET PUT | `/audio/{uuid}/cuts` | The selected region: the cuts and the frame table (implementation 08). |
| **Transcription** | `api/matrix.py` | |
| GET | `/matrix/engines` | The engines the page may offer. Only `muscriptor` now. |
| GET | `/matrix/engine` | The one engine: installed, device, loaded, waiting jobs, load error (implementation 08). |
| POST | `/matrix/transcribe` | Start MuScriptor; returns `202` and a job id. |
| GET | `/matrix/{uuid}/job` | The waiting or running transcription of a piece (implementation 08). |
| GET | `/matrix/progress/{jobId}` | SSE stream of any job: progress, live notes, `done`. |
| GET | `/matrix/jobs/{jobId}` | The same state, for pollers. |
| GET | `/matrix/{uuid}/events` | Every note the model reported, in seconds. Notes Falling draws it. |
| PUT | `/matrix/{uuid}/events/removed` | Mark notes as removed, by pitch and second. Notes Falling uses it. |
| **The flow page** | `api/pieces.py` | |
| GET | `/pieces/{uuid}/status` | Every step of the piece, its state, and the step it opens on (implementation 08). |
| GET | `/pieces/{uuid}/notes` | The live notes as columns, with the revisions (implementation 08). |
| PATCH | `/pieces/{uuid}/notes` | A list of operations on notes named by id (implementation 08). |
| POST | `/pieces/{uuid}/hands/predict` | The hand split as one hand per note. Writes nothing (implementation 08). |
| POST | `/pieces/{uuid}/hands/predict/job` | The same, as a job with progress (implementation 08). |
| **The score** | `api/time_score.py` | |
| GET | `/time/{uuid}/peaks` | Where the gaps between attacks gather into piles. |
| POST | `/time/{uuid}/ladder-preview` | Name one peak, see what every other becomes. |
| GET | `/time/{uuid}/score` | The drawable score payload. |
| POST | `/time/{uuid}/score` | The same, with the reader's page edits applied. |
| GET | `/time/{uuid}/trills` | Alternating runs, offered as suggestions. |
| PUT | `/time/{uuid}/hands` | Correct which hand plays a note. Written by note id since implementation 08. |
| PUT | `/time/{uuid}/removed` | Mark notes as removed from the page, by column and row. |
| PUT | `/time/{uuid}/notes` | Add notes to the recording, by column and row. |
| GET PUT DELETE | `/time/{uuid}/rhythm` | The saved reading. |
| **Editing and composing** | `api/editing.py` | |
| POST | `/audio/{uuid}/edits` | Open a disposable session. |
| GET PATCH DELETE | `/audio/{uuid}/edits/{session}` | Read, adjust, discard. |
| POST | `/audio/{uuid}/edits/{session}/take` | Upload the take. |
| GET | `/audio/{uuid}/edits/{session}/take` | The take, as played or scaled. |
| GET | `/audio/{uuid}/edits/{session}/waveform` | Peaks of the untrimmed take. |
| GET | `/audio/{uuid}/edits/{session}/window` | The original window, optionally slowed. |
| POST | `/audio/{uuid}/edits/{session}/transcribe` | Transcribe the take as played (GPU queue). |
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
| POST | `/youtube/download` | Download the audio as mp3, in the request. |
| POST | `/youtube/jobs` | The same download as a job; returns `202` and a job id (implementation 08). |
| POST | `/youtube/batch` | Queue several. |
| **Text-notation MVP** | `api/scores.py` | |
| GET | `/scores` | Seed scores from `data/example-scores.json`. |
| POST | `/sequence` | Text notation to a sparse score. |

The last two are the project's original MVP and are **not** part of the wall-clock path. See
[§9](#9-the-text-notation-mvp-routes).

The video reader's routers (`/video` in `api/video.py`, `/frame-examples` in
`api/frame_examples.py`, implementations 04 to 07) are not described on this page. Their reasoning
is in `context/implementations/01-mvp/04-synthesia-to-notes/` and `05-piano-overlay-from-black-keys/`.

---

## 2. `/audio`: the working store

One uuid folder per ingested audio, whatever the source. Upload, browser recording and YouTube all
converge on `audio/ingest.py`, so the rest of the system never asks where a recording came from.

`POST /audio/upload` accepts `.mp3 .aac .m4a .wav .webm .ogg`. Browser recordings arrive as webm or
ogg because Chrome records nothing else, and ffmpeg converts them on the server. **Without `ffmpeg`
on `PATH` this route answers `503`** with that instruction rather than failing obscurely.

`POST /audio/{uuid}/trim` writes a **physical** child audio with absolute lineage back to its root
source, rather than remembering a range. A named segment survives the parent being deleted and can
itself be trimmed again. A piece with cuts is refused with `422`, because the seconds of the range
selector are those of the piece and the file's are not: such a piece is cut on the Audio tab of the
flow page instead.

`POST /audio/compose` is the odd one out: it creates a piece with no audio file at all. It writes an
empty `events.json` (`durationSeconds: 0`) and a `frameMs` on the metadata, and the first accepted
passage is what creates a recording. Body: `{ "name": string, "frameMs": number }`.

`GET /audio/` and `GET /audio/{uuid}` add three computed fields to `metadata.json`: `hasNotes`,
`needsRederivation`, and `originalDurationSeconds`. Once cuts are saved, `durationSeconds` is the
length of the piece (the original minus the cuts) and `originalDurationSeconds` keeps the length of
the untouched file.

### 2.1 GET and PUT /audio/{uuid}/cuts

Before implementation 08, the only way to remove part of a recording was **Create segment**, which
copies the audio. The flow page needed a selected region that a reader can change and restore, and
that maps directly onto the notes. A cut is therefore a range of 10 ms time frames of the original
audio, `[startFrame, endFrame)`, stored in `metadata.json`. The piece is every frame that no cut
deletes. The model is in `audio/frames.py` (`FrameTable`, `normalize_cuts`, `join_kept`).

The answer of both methods (`CutsResponse`):

| Field | Meaning |
|---|---|
| `audioUuid` | |
| `audioRevision` | Rises by one each time the cuts change. Notes made from another revision are stale. |
| `frameMs` | Always `10`: one time frame, 160 samples of the 16 kHz `normalized.wav`. |
| `totalFrames` | Frames of the original audio. |
| `pieceFrames` | Frames of the piece, once the cuts are removed. |
| `cuts` | Sorted `[startFrame, endFrame)` pairs of the original. |
| `kept` | The frame table: one row per kept range, `{pieceStart, originalStart, length}` in frames. |
| `notesStale` | True when the stored notes were transcribed from other cuts. |

`PUT` body: `{ "cuts": [[start, end], ...], "baseRevision": n }`. `baseRevision` is optional.

- The cuts are sorted, clipped to the audio and merged where they overlap or touch.
- `audioRevision` rises only when the cuts really change, so saving the same cuts twice does not make
  the notes stale (`store.set_cuts`).
- `409` when `baseRevision` is not the stored revision, so a page never writes over a newer
  selection. `422` when the cuts would delete the whole audio. `409` from both methods when the audio
  has no `normalized.wav` yet.
- A change writes the edited audio, `piece-r<N>.flac` and `piece-r<N>.wav`
  ([`paths-and-data.md`](paths-and-data.md#22-the-edited-audio-piece-rnflac-and-piece-rnwav)), and
  deletes the cached `waveform.json`. `500` when ffmpeg cannot write the edited audio.
- The route does **not** start a transcription. It makes the stored notes stale. The next
  `POST /matrix/transcribe` then transcribes again without `force`, and the old notes are copied to
  `history/vN/` first.

### 2.2 GET /audio/{uuid}/file

The audio of the piece, for every player. Two query flags, both `false` by default:

| Piece | No flag | `normalized=true` | `original=true` |
|---|---|---|---|
| No cuts | The file the user gave (`original.<ext>`) | `normalized.wav` | `original.<ext>` |
| With cuts | `piece-r<N>.flac` | `piece-r<N>.wav` | `original.<ext>` |

Until Phase 6 every player played the untouched original, so on a cut piece the audio ran ahead of
the notes by the length of the cuts before the playhead. The user's rule (2026-09-29) is that once
the cuts are saved, the edited audio is the audio of the piece. Only the Audio tab asks for
`original=true`, because it draws the cuts on the original so a reader can restore one. A missing
edited file is written on the first request (`audio/piece_audio.py`, `ensure`).

Every answer of this route carries `Cache-Control: no-cache`, because the same address serves other
bytes after the cuts change. `GET /audio/{uuid}/range` and the range edit still read
`normalized.wav` in the time of the original.

### 2.3 GET /audio/{uuid}/frames/peaks

The waveform of the Audio tab. A cut snaps to one 10 ms frame, so the tab needs the waveform at that
step for every zoom level. One pair of values per frame for the whole audio is only 2 bytes per
frame, so the route sends all of it at once and the page draws every zoom from memory.

| Field | Meaning |
|---|---|
| `audioUuid` | |
| `frameMs` | `10` |
| `totalFrames` | Frames of the original audio: the same count as `GET /audio/{uuid}/cuts`. |
| `peak` | The loudest sample of the audio, 0 to 1. The values below are scaled so that it is 127. |
| `min`, `max` | Base64 of one signed byte per frame: the lowest and the highest sample of that frame. |

It reads `normalized.wav` (the original, not the piece), so frame `f` here is frame `f` of a cut.
`409` when there is no `normalized.wav` or when it is not 16 kHz. There is no cache. On Superestrella
(18,917 frames) the answer is 50.6 KB of JSON, 35 KB sent, in 8 to 30 ms.

---

<a id="3-matrix--running-the-model"></a>

## 3. `/matrix`: running the model

Before implementation 08, these routes let the reader choose ByteDance or Transkun, ran one job per
request with a new model each time, and reported progress only. Now there is one engine, MuScriptor,
loaded once, with one transcription at a time on the GPU, and the progress stream also carries the
notes as they are heard. The engine itself is described in
[`transcription-pipeline.md`](transcription-pipeline.md#engines).

**Nothing here returns a grid.** A grid is a view of the recorded notes at a chosen frame length, so
it is built while the request is answered and served from `/time` instead.

### 3.1 GET /matrix/engines and GET /matrix/engine

`GET /matrix/engines` returns `{engine: bool}` for the engines the page may offer. It now lists only
`{"muscriptor": true}`; `false` means the `muscriptor` extra is not installed. With one entry the
Input page shows no engine choice.

`GET /matrix/engine` is the startup check of the one engine:

```json
{"name": "muscriptor", "installed": true, "device": "cuda",
 "loaded": ["muscriptor-large (cuda, float16)"], "waiting": 0, "error": null}
```

`device` is `AITU_DEVICE`. `loaded` is what the model registry (`transcription/models.py`) holds.
`waiting` counts the transcriptions queued behind the running one. `error` says, in plain words, why
the preload failed (a missing Hugging Face token or licence, for example). When a transcription ends
at once with no notes, check this route first: a container can lose its GPU after the host's service
manager reloads (Phase 7 report, 6.3).

### 3.2 POST /matrix/transcribe

```json
{ "audioUuid": "…", "frameMs": 40, "startSeconds": null,
  "endSeconds": null, "engine": "muscriptor", "force": false }
```

There is one number in that body and it is a length of time. It does not decide what any note is
called: the figures are chosen afterwards, from a ladder the reader names (D-01, D-09). Here
`frameMs` only says which hand split to prepare in the cache after the save.

- **The engine is forced.** `engine` is kept for older clients and defaults to `muscriptor`. Any
  other value answers `422`: "Unknown transcription engine" for a name that does not exist, and a
  message saying the engine is kept in the code but cannot be chosen for `bytedance`, `transkun`,
  `basic-pitch` and `silent`. A missing audio answers `404` before that check.
- **When the model runs.** It runs when `force` is true, when a range is given, or when the piece
  has no current notes (no `events.json`, or notes made from another `audioRevision`). Otherwise the
  job reads the stored notes, prepares the split and ends: `force` is needed only to replace current
  notes.
- **The GPU queue.** A job that runs the model goes into the GPU queue of `transcription/jobs.py`:
  one worker thread, in order of arrival. While another transcription runs, the job's status is
  `waiting` and its stream sends a `waiting` stage ("Waiting for 1 other transcription to finish").
  The range-edit take (`POST /audio/{uuid}/edits/{session}/transcribe`) uses the same queue.
- **One job per piece.** The job carries the key `transcribe:<uuid>`. While a job with that key is
  waiting or running, this route returns that job instead of starting a second one, so a double
  click or a second browser tab cannot transcribe the same piece twice.
- **A range** (`startSeconds` and `endSeconds`) is the older path: the WAV is sliced first and the
  cuts are not applied.

Answers `202` with `{ "jobId", "status" }`, where `status` is usually `running` or `waiting`. A full
transcription of Superestrella (189 s) takes about 25 s on the RTX 4090.

### 3.3 GET /matrix/{uuid}/job

`{ "jobId", "status" }` of the transcription of this piece that is waiting or running, or `404` when
there is none. A page that is opened or reloaded during a transcription uses it to find the stream
again, then reads every frame from the start.

### 3.4 GET /matrix/progress/{jobId}

A Server-Sent Events stream (`text/event-stream`, `Cache-Control: no-cache`,
`X-Accel-Buffering: no`) of **any** job of `transcription/jobs.py`: a transcription, a YouTube job
(`POST /youtube/jobs`) or a hand prediction (`POST /pieces/{uuid}/hands/predict/job`). It has three
kinds of frame.

**Progress frames** have no event name:
`{stage, current, total, fraction, message, timestamp}`. A MuScriptor transcription reports the
stages `waiting` (only when queued), `transcribe` (one step per 5-second chunk, message
`chunk n/total`) and `timing` (the lag measurement, message `lag correction +15 ms`).

**`event: chunk` frames** carry the live notes of a MuScriptor transcription (`transcription/live.py`):

```json
{"type": "chunk", "done": 3, "total": 38, "upToMs": 15000, "durationMs": 189160,
 "open":   {"id": [41, 42], "key": [40, 52], "onMs": [14210, 14800]},
 "closed": {"id": [30, 31], "key": [39, 44], "onMs": [9900, 11000], "lenMs": [1200, 800]}}
```

- One frame is sent when a chunk ends (`done` counts whole chunks), at most every 0.25 s inside a
  chunk when a note started or ended, and once more at the end for the notes MuScriptor closes after
  its last chunk.
- `closed` holds only the rectangles that ended since the previous frame. `open` holds every
  rectangle still sounding, which the page draws up to `upToMs`.
- The ids are the ids of the saved notes. The times are whole milliseconds of the piece, **before**
  the lag correction, which is known only at the end. The page reads the saved notes after `done`.
- An `EventSource` that listens only to unnamed frames never receives these, because a named event
  goes only to a listener of that name.

**The final frame** is `event: done`: `{type: "done", status, error, ...}` with `status` `done` or
`error`. Each kind of job adds its own fields:

| Job | Extra fields of `done` |
|---|---|
| Transcription | `audioUuid`, `revision` (the new `notesRevision`), `lagCorrectionMs`, `noteCount` |
| YouTube download | `audioUuid`, `alias`, `durationSeconds` |
| Hand prediction | every field of the `POST /pieces/{uuid}/hands/predict` answer |

**Reconnection.** Every frame except the final `done` carries an SSE `id:`, which is its index in the
job's list of frames. A reader that connects late first receives every frame already sent, in order,
then the new ones; each reader keeps its own position, so two tabs never take frames from each
other. A reconnecting `EventSource` sends `Last-Event-ID` and resumes after that frame. A comment
line (`: keep-alive`) is sent after 15 s with no frame. An unknown job id answers one `event: error`
frame and a `done` frame with `status: "error"`.

Jobs live in memory: the last 50 finished jobs are remembered, and a restart of the backend (also
any `--reload`) loses them. The notes themselves are on disk.

### 3.5 GET /matrix/jobs/{jobId}

`{jobId, status, error, stage, fraction}` from the last progress frame, for clients that cannot hold
an SSE connection. `status` is `waiting`, `running`, `done` or `error`. `404` for an unknown job.

### 3.6 GET /matrix/{uuid}/events

Every note the model reported, in seconds, with the discards **marked rather than removed**. The
artifact filter is applied here only as a label, because the point of the route is to show what the
rest of the system chose not to use: a filter that can be checked instead of taken on trust. On a
`muscriptor-*` piece no filter runs in the hand split, so no note is labelled (`artifactCount: 0`).

Each event carries:

- `id`, the stable note id of `events.json`, which `PATCH /pieces/{uuid}/notes` names it by;
- `hand`: the saved hand when there is one, otherwise the hand of the standard split at `frameMs`,
  read from the shared split cache. It is a label and nothing else: the times are untouched, and a
  split that fails leaves the notes uncoloured rather than failing the request;
- `removed`, `artifact`, `octaveBelow`.

The answer also carries `revision` and `handsRevision`, which a page needs to send a `PATCH`.
`409` when the piece has no `events.json`.

**Notes Falling** draws this. The Playground's Piano Roll page, which also drew it, was removed in
Phase 9: the Notes and Hands tabs of the flow page replace it, and they read
`GET /pieces/{uuid}/notes` instead.

### 3.7 PUT /matrix/{uuid}/events/removed

Marks notes as removed from the recording, addressed by pitch and start second (`midiNote`, `start`,
matched to 4 decimals). `removed: false` restores them. `removed` is a flag on the note event, so
nothing is deleted and restoring a note returns it exactly as it was. Answers `{changed, unmatched}`.

There are **two** routes that write this flag, and that is deliberate: the two screens genuinely
hold different things. Notes Falling knows raw seconds; a reader on the sheet has clicked a notehead
and knows a column and a row, which is `PUT /time/{uuid}/removed`. Same field, same consequences.

Removing a note is not a filter on one screen. A note's printed length is the gap to the next onset
in the same hand (D-14), so removing one **renames its neighbour**. That is why it is written onto
the recording rather than drawn over.

Since implementation 08 the write goes through `pipeline.save_edit`: `notesRevision` and
`handsRevision` rise by one, and a saved piano sheet becomes stale, because this page is not the
sheet.

---

<a id="4-time--the-wall-clock-score"></a>

## 4. `/time`: the wall-clock score

Everything here is derived from the stored `events.json`, so reading a piece at 20 ms instead of 40
is a different query string rather than a migration. One thing is kept in memory: the hand split of
each piece, in the shared split cache (`transcription/split_cache.py`), keyed by the uuid, `frameMs`
and the modification time of `events.json` in nanoseconds. Any save of `events.json` is a new key, so
an old split is never served. When every placed note has a saved hand, the split is painted from
those hands in a few milliseconds instead of running the inference (D-31, changed in implementation
08, Phase 5).

### GET /time/{uuid}/peaks

| Query | Default | Meaning |
|---|---|---|
| `hand` | `right` | `right`, `left` or `both`. |
| `frameMs` | 40 | |
| `startSeconds` | 0 | Measure a stretch rather than the piece. |
| `endSeconds` | none | |

Returns the piles of gaps between attacks, each with its centre, median, mean, count, share and
edges, plus `attackCount`, `gapCount` and an optional plain-language `warning`.

Measured on the **raw recorded times, never on the columns** (D-07). Snapping first splits every
pile in two: a real 337 ms gap becomes 8 or 9 frames depending on phase, so one clean spike holding
half the data becomes two half-height spikes and the reader is asked to name a peak nobody played.

Each hand is measured on its own, because the gap between a right-hand run and a held left-hand
chord is not a rhythm and would hide the peak that matters.

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
| `boundaryMs` | `""` | One anchor per passage: **one more value than boundaries**. |

Returns a `TimeScorePayload`: the two hand matrices, the passages, every printed note with its
figure already chosen, and the layout hints. Field detail in
[`time-matrix.md`](time-matrix.md#29-timescorepayload).

A mismatched count of boundaries and anchors is a `422` that says both numbers.

Both score routes encode the payload once (`_json`, a `Response` with `model_dump_json`) instead of
letting FastAPI validate every cell a second time. `response_model` stays on the decorators for the
documentation (Phase 2).

### POST /time/{uuid}/score

The same answer, with the reader's page edits applied **before any figure is named**. Body adds
`hiddenNotes` and `trills` to the query parameters above, and `dropDecorative`.

The edits have to be applied on this side rather than in the browser for one reason: hiding a note
changes the gap to its neighbour, and therefore that neighbour's printed figure. An overlay drawn
after the figures were chosen would show the right noteheads with the wrong names.

Each pass works on `_editable_copy`, which copies only the two hand grids and shares everything else
with the cached split. A deep copy of the whole split used to be about two thirds of a request with
decorative notes removed, which copies once per pass (Phase 8).

### GET /time/{uuid}/trills

`frameMs`, and `minPairRepeats` (2–20, default 3). Returns stretches where two notes a whole tone or
less apart trade places at least three times, evenly, under 300 ms, measured on the raw attack times
per hand.

**A suggestion and nothing more.** Nothing is written and the sheet does not change until the reader
accepts one: a missed trill costs a reader nothing, and a wrong one hides notes that were really
played, so the reader has the last word.

### PUT /time/{uuid}/hands

Which hand plays a note is a fact about the *playing*, not about the page: it survives a change of
column length and it decides the printed length of its neighbours. So it is written onto the note
event rather than stored as an annotation, and everything downstream follows without coordinating.

Body: `{ "frameMs": 40, "notes": [{ "startFrame", "row", "hand": "right" | "left" }] }`. Answers
`{assigned, unmatched}`.

Since implementation 08, Phase 5, the route is light, because a reader moves hands often:

1. The cell (`startFrame`, `row`) is resolved to a **note id** in the cached split the page already
   shows (`build.event_ids`). No hand split runs because of the request.
2. When the piece has no saved hands yet, the first change first saves the hand of every live note
   as that split draws it, then applies the change. The page looks the same, and from then on the
   sheet is painted from the saved hands.
3. The hand is written onto the note by id, and `hand_guessed` is cleared.
4. `pipeline.save_edit` raises `handsRevision`. The page that made the change already draws it, so a
   saved reading that was current moves forward with it and stays current (`sheet_follows`).

Measured on Superestrella: 8 to 12 ms for the `PUT` and 33 to 36 ms for the sheet request after it,
where it used to cost a new hand split (1.1 to 1.5 s).

### PUT /time/{uuid}/removed and PUT /time/{uuid}/notes

`PUT /time/{uuid}/removed` addresses notes by column and row. Restoring one cannot be resolved
against the current matrix (the note is not in it, which is what removed means), so a restore builds
its lookup from a split with every removal undone, which is the numbering the columns were recorded
with. One extra split, paid only on an undo.

`PUT /time/{uuid}/notes` is its opposite, and writes to the same place for the same reason. A reader
looking at the keyboard panel can see a note missing from a chord. Drawing an extra notehead beside
the score would be the wrong fix twice. First, the printed length of a note is the gap to the next
onset in the same hand, so a note that appears from nowhere renames its neighbour. Second, Notes
Falling and playback would continue to disagree with the page.

The times are the column's own: a note added at f120 starts 120 column-lengths into the piece. That
is only ever a few milliseconds from where a played note would have landed, and the whole page is
drawn on that grid anyway. The hand travels with it, pinned the way a corrected hand is. A key
already struck in that column is **refused and counted** rather than merged, because the matrix
rejects a frame where both hands hold one key and merging would lose a note.

`PUT /time/{uuid}/notes` answers `{"added": n, "duplicate": n}`; `PUT /time/{uuid}/removed` answers
`{changed, unmatched}`. Both go through `pipeline.save_edit` with `sheet_follows`, like the hand
route.

### GET / PUT / DELETE /time/{uuid}/rhythm

The reader's saved reading: the anchor, the key, clef changes, speed changes, renamed figures, beam
breaks and beam joins, hidden notes, fingering, trills, grace notes, lyrics, cue-size stretches and
how far apart the notes and the lines stand. One per piece: a second reading replaces the first. See
[`rhythm-and-annotations.md`](rhythm-and-annotations.md).

`PUT` stamps `handsRevision` with the current value from `events.json`; the client's value is
ignored. A later edit of the notes or the hands outside the Sheet tab makes the reading stale, and
the Sheet tab asks the reader to press **Write the sheet** again. `409` when the piece has no notes.

`DELETE` answers `204` and is what **Remove all** calls.

---

<a id="5-audiouuidedits--staged-editing-and-composing"></a>

## 5. `/audio/{uuid}/edits`: staged editing and composing

A disposable session holds the take. Cancel deletes the folder and nothing else; nothing reaches the
piece until accept.

Accept does one of two things, and which one is the session's `placement`:

- **`replace`** (Epic 11) splices the take into exactly the window it replaces. The piece keeps its
  length, which is what lets every mark after the window keep its address.
- **`append`** and **`insert`** (Epic 13) put a new passage in and make the piece longer. This is the
  one place in the product where that is allowed, because a piece being composed has nothing after
  the insertion point to protect.

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

Transcribing the take as played rather than after stretching is essential: a time-stretched
recording is a different sound, and the model would be reading an artefact instead of the playing.
The take is transcribed by MuScriptor through the GPU queue, like a whole piece.

`GET …/confirmation` reports dropped marks (`figureOverrides`, `beamBreaks`, `hiddenNotes`,
`fingerings`) for a replace, and moved marks with the column shift for an insert. A fingering that
has silently moved looks exactly like a fingering that has silently stayed, so the count is shown
before the button is pressed.

Errors: `404` for a missing session or audio, `409` for an operation the session's placement does
not allow (asking to fit a composed passage to a window, for instance), `503` when ffmpeg is
missing, `422` when a conversion fails.

Detail in [`editing-and-compose.md`](editing-and-compose.md).

---

## 6. `/pieces`: the flow page

The flow page (`/piece/:uuid` in the frontend) has five tabs: Source, Audio, Notes, Hands, Sheet.
Before implementation 08 nothing on the backend could say which of these steps a piece had
completed, and the notes could only be edited through the sheet's columns and rows. The `/pieces`
router (`api/pieces.py`, Phase 5) gives the page one status answer to enable its tabs from, the notes
in the compact columns form, and edits by note id with a revision check. The model is in
`aitu_backend/pieces/` (`status.py`, `edits.py`) and `transcription/saved_hands.py`. The revision
chain is described in
[`context/backend/piano-matrix-notation.md`](../../../context/backend/piano-matrix-notation.md#3-on-disk-eventsjson-pmnevents_filepy).

### 6.1 GET /pieces/{uuid}/status

```json
{"audioUuid": "…",
 "steps": [{"step": "notes", "state": "ready", "enabled": true, "reason": null,
            "details": {"noteCount": 1351, "engine": "muscriptor-large"}}, …],
 "resume": "sheet",
 "revisions": {"audio": 0, "notes": 1, "notesAudio": 0, "hands": 2,
               "handsNotes": 1, "sheetHands": 2}}
```

- `steps` holds `source`, `audio`, `notes`, `hands`, `sheet`, in that order.
- `state` is `missing` (never made), `running` (a transcription is working on it), `stale` (made
  from an older revision of an earlier step) or `ready`.
- `enabled` is true when every step before it is ready. A stale Sheet tab stays enabled, because it
  opens with a banner that asks the reader to write the sheet again.
- `reason` is a sentence the page shows as it is, as the tab's tooltip or a banner.
- `details`: `audio` gives `audioRevision` and `cuts` (a count); `notes` gives `noteCount` and
  `engine`, plus `jobId` and `jobStatus` while running; `hands` gives `withoutHand`, `unplaced`,
  `guessed` and `saved`.
- `resume` is the furthest enabled step that is ready or running (or a stale Sheet): the tab a piece
  opens on.
- `revisions` are the numbers the states are computed from: `audio` (`metadata.json`), `notes`,
  `notesAudio`, `hands`, `handsNotes` (`events.json`), and `sheetHands` (`rhythm.json`).

The Notes step is `stale` when `notesAudio` differs from `audio` (a cut was saved after the
transcription). The Hands step is `ready` when every live note the piano sheet places at 40 ms has a
hand. A note the sheet cannot place (shorter than one column, or sharing its column with another
note of its key) stays without a hand, is counted in `unplaced`, and does not keep the step from
being ready. A piece transcribed before Phase 5 that already has a saved sheet reads its Hands step
as `ready` with `saved: false`. The Sheet step is `stale` when `sheetHands` differs from `hands`.

`404` for an unknown uuid. The answer takes 5 to 24 ms.

### 6.2 GET /pieces/{uuid}/notes

The live notes in the columns form of the piano matrix notation (`pmn/columns.py`): one list per
field, sorted by onset then key, whole milliseconds of the piece.

```json
{"revision": 7, "handsRevision": 3, "durationMs": 189160, "stale": false,
 "id": [0, 1, 2], "key": [39, 43, 46], "onMs": [3070, 3363, 3364],
 "lenMs": [1220, 587, 137], "hand": "llr", "guessed": []}
```

`hand` has one character per note: `r`, `l`, or `-` for no hand. `guessed` lists the ids whose hand
came from the quick rule. `stale` is true when the selected region changed after the transcription.
`409` when the piece has not been transcribed. About 4 ms and 10 KB sent for Superestrella.

### 6.3 PATCH /pieces/{uuid}/notes

The page never sends the whole piece. It sends a list of operations on notes named by their id, and
the backend applies them in order (`pieces/edits.py`).

```json
{"baseRevision": 7, "baseHandsRevision": 3,
 "ops": [{"op": "move", "id": 12, "onMs": 3050, "lenMs": 400},
         {"op": "add", "tempId": -1, "key": 40, "onMs": 5000, "lenMs": 250, "hand": "l"},
         {"op": "hand", "ids": [3, 4, 5], "hand": "r"}]}
```

| `op` | Fields | Changes |
|---|---|---|
| `move` | `id`, `onMs`, `lenMs`, optional `key` (0 to 87) | the notes: move or resize, and change key when `key` is given |
| `delete` | `ids` | the notes: marked removed (the id is kept) |
| `restore` | `ids` | the notes: a removed note returns with its id and hand |
| `add` | `tempId` (negative), `key`, `onMs`, `lenMs`, optional `hand` (`r` or `l`) | the notes |
| `hand` | `ids`, `hand` (`r` or `l`) | the hands |

`ops` holds 1 to 50,000 operations. Times are milliseconds of the piece.

**The rules.**

- **One key sounds one note at a time.** After the operations, on every key an operation touched, a
  note that runs into the next onset of its key is shortened to that onset. Only pairs where one
  note was placed or moved by an operation are changed, so overlaps already in old ByteDance files
  stay as they were. Two notes of one key that start less than 0.5 ms apart are refused.
- A note may not end more than 1 ms after the end of the piece.
- A `move` on a removed note is refused ("Restore it first").
- A request that changes nothing answers `saved: false` and writes nothing.

**The answer** (`NotesPatchResult`):

| Field | Meaning |
|---|---|
| `revision`, `handsRevision` | The new revisions, to send as the base of the next `PATCH`. |
| `saved` | False when nothing changed. |
| `added` | `[{tempId, id}]`: the id the backend chose for each added note. |
| `changed` | Columns (`id`, `key`, `onMs`, `lenMs`, `hand`, `guessed`) of every note the backend changed beyond the request: added notes, notes the same-key rule shortened, notes the quick rule gave a hand. The page replaces its copy of each. |
| `sheetStale` | True when a saved piano sheet was current before this edit and is stale now. |

**The revisions** (`pipeline.save_edit`): a notes operation raises `notesRevision`; any operation
raises `handsRevision`; a hand edit that leaves every placed live note with a hand sets
`handsNotesRevision` to the new `notesRevision`. When the hands were already saved as a whole, a
live note with no hand (an added note, a restored note) receives the hand of its neighbours by the
quick rule and is marked `guessed`.

**Errors.** Nothing is written when a request is refused.

- `404`: unknown uuid.
- `409`: `baseRevision` is not the stored `notesRevision`, or `baseHandsRevision` (when given) is
  not the stored `handsRevision`; the notes are stale because the selected region changed ("Transcribe
  again"); the piece has not been transcribed.
- `422`: an operation cannot be applied (an unknown id, a reused `tempId`, a note past the end, two
  onsets of one key at the same time), with a message naming the operation, or a body that does not
  match the schema.

The route holds `pipeline.piece_lock(uuid)` from its read to its write, so a revision check and its
write cannot interleave with another request.

### 6.4 POST /pieces/{uuid}/hands/predict

**Predict hands** on the Hands tab. The same hand split the piano sheet has always run (the inference
on the snapped time matrix, D-31), read back as one hand per note id. **Nothing is written**: the page
shows the answer as unsaved changes, and **Save** sends it as two `hand` operations of a `PATCH`.

Body: `{ "baseRevision": n, "frameMs": 40, "replace": false }`. With `replace: false` the saved hands
the user set are kept and only the notes without a hand, or with a guessed hand, are predicted.
`replace: true` predicts every note again.

| Field | Meaning |
|---|---|
| `revision`, `handsRevision`, `frameMs` | What the prediction was made from. |
| `id` | The live notes, in the order of `GET /pieces/{uuid}/notes`. |
| `hand` | One character per note of `id`: `r`, `l`, or `-` for a note the split could not place. |
| `changed` | How many notes would change hand if this is saved (a note with no hand counts). |
| `unplaced` | How many notes are `-`. They are drawn red for the user to delete or assign. |
| `elapsedMs` | |

`409` when `baseRevision` is old or the piece has not been transcribed. The inferred split is cached:
the first prediction on Superestrella takes about 1.2 s, a second one about 9 ms.

### 6.5 POST /pieces/{uuid}/hands/predict/job

The same prediction as a job, so the page can show real progress. Same body; answers `202` with
`{jobId, status}`. The checks (`404`, `409`) run before the job starts.

The page follows `GET /matrix/progress/{jobId}`. The stages are `events` (building the matrix) and
`two-hands` (the inference, in hundredths: the beam search reports 0 to 60, the refine rounds 60 to
100). The `done` frame carries every field of the direct answer. The job key is
`hands:<uuid>:<notesRevision>:<frameMs>:<replace>`, so a second request with the same options while
the first runs returns the same job. When the split is already cached, the job ends at once. It does
not use the GPU queue.

---

## 7. `/library`: playground versions and promotion

Two trees, and the difference between them is the point. The **playground** holds work in progress,
versioned per track as `v<N>_f<frameMs>` folders. The **library** holds what a performer plays from:
named promotions, rollback, tags and playlists.

`POST /library/promote` takes an editable promotion name, and either replaces the current promotion
or adds another alongside it. `GET /library/promotion-suggestion/{artist}/{track}` proposes one
before the dialog opens.

Storage layout in [`paths-and-data.md`](paths-and-data.md).

---

## 8. `/youtube`

`yt-dlp` is a normal Python dependency and is invoked as `python -m yt_dlp` on the backend's own
interpreter, so it never depends on `PATH`. In the container `deno` is installed beside it, because
yt-dlp needs a JavaScript runtime to read YouTube's player.

The body of the three single-video routes is `{ "url": string, "fileName": string | null }`;
`fileName` is the display name and defaults to the video title. Errors keep yt-dlp's own words:
`422` for a link that is not a YouTube URL, `503` when yt-dlp is missing, `502` when the download
fails.

- `POST /youtube/probe` reads a video's title, length and uploader without downloading anything.
- `POST /youtube/download` extracts mp3 and ingests it like any upload, inside the request.
- `POST /youtube/batch` downloads several in order; one failure does not stop the rest.

### 8.1 POST /youtube/jobs

The Source tab of the flow page needed a download that shows its progress and does not hold a
request open for the whole download. This route runs the same download as a background job and
answers `202` with `{jobId, status}` at once.

- The URL and the presence of yt-dlp are checked before the job exists, so a wrong link is `422` at
  once.
- The page follows `GET /matrix/progress/{jobId}`: a `download` stage in percent, then a `store`
  stage while the audio is converted, then `event: done` with `audioUuid`, `alias` and
  `durationSeconds`, or with `status: "error"` and yt-dlp's message.
- The job key is `youtube:<url>`: a second request for the same URL while the first runs returns
  the first job.
- It does not use the GPU queue. A 19 s video reached the Audio tab in 2.5 s.

---

## 9. The text-notation MVP routes

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

## 10. What used to be here and is not

Stated plainly so nobody searches for it. These routes belonged to the tempo-based model and were
deleted in P4.2 with the Playground tabs that called them:

- reading one processing step of a stored matrix (`raw`, `collapsed`, `clean`)
- switching granularity, and any BPM parameter
- editing a matrix cell
- transposition
- matrix JSON import and export

If one of these should return on the wall-clock path, it is a new feature request with its own
reasoning, not unfinished work.

Implementation 08 deleted no route. It removed two choices and one page:

- **The engine choice.** `POST /matrix/transcribe` refuses every engine except `muscriptor` with
  `422`, and `GET /matrix/engines` no longer lists ByteDance or Transkun. Both engines stay in the
  code with their tests, and pieces they transcribed keep their filters.
- **A new model per job.** The model is loaded once per process (`transcription/models.py`), and
  only one transcription runs on the GPU at a time.
- **The Playground's Piano Roll page**, removed in Phase 9. `/playground/piano-roll` now redirects
  to the flow page. `GET /matrix/{uuid}/events` and `PUT /matrix/{uuid}/events/removed` stay, because
  Notes Falling uses them.

---

## 11. Where to look deeper

- [`context/backend/piano-matrix-notation.md`](../../../context/backend/piano-matrix-notation.md):
  `events.json` schema 1.1, the columns form, the revisions
- [`time-matrix.md`](time-matrix.md): every schema 2.0 field
- [`events-to-sheet.md`](events-to-sheet.md): how a response is derived
- [`editing-and-compose.md`](editing-and-compose.md): the splice and the insertion
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md): `rhythm.json`
- [`transcription-pipeline.md`](transcription-pipeline.md): what happens before any of this
- [`paths-and-data.md`](paths-and-data.md): where each file of these routes lives
- `http://127.0.0.1:8765/docs`: the generated, always-current field reference
