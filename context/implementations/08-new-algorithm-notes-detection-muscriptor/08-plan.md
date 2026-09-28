# 08: MuScriptor, the live piano roll, and the move to Ubuntu: implementation plan

Read the prompt this plan answers first: [`08-prompt.md`](08-prompt.md). The status lookup is
[`08-checklist.md`](08-checklist.md). Phase reports go beside them as `08-implementation-phase-N.md`,
written by the agent that finishes phase N, following
[`../../language/communication-implementation-plans.md`](../../language/communication-implementation-plans.md)
and [`../../language/communication-style.md`](../../language/communication-style.md).

The binding rules of the project still apply: the five rules of
[`../01-epics-master-plan/plan/wall-clock-rewrite.md`](../01-epics-master-plan/plan/wall-clock-rewrite.md),
the frozen decisions D-01 to D-34 of
[`../03-time-based-concept/decisions.md`](../03-time-based-concept/decisions.md), and the storage rules
of [`../03-time-based-concept/contract.md`](../03-time-based-concept/contract.md) section 8. Section 4
of this plan checks them one by one. One decision, D-31, is changed on purpose, and section 4 says why.

---

# 1. Context

## 1.1 What the app does today

A user gives the app an audio file (an upload, a recording, a file from the audio library, or a
YouTube download made on a separate page). The backend transcribes it with ByteDance (the default) or
Transkun (the prompt calls it "Tranksum"; the code calls it `transkun`). The engine output is a list of
notes in seconds, stored as `data/audio/<uuid>/matrices/events.json`. Everything else is derived from
that file on each request: the piano matrix notation (88 rows, one per key, and one column per
`frameMs` of time, 40 ms by default), the hand split into a right hand matrix and a left hand matrix,
and finally the piano sheet drawn by `@aimpromptu/grid-notation` (the sibling repository
`../vexflow-v2`).

The user sees this as four Playground tabs: **Input**, **Piano Roll**, **Notes Falling** and
**Piano Sheet** (the `RhythmPage`). When a transcription ends, the app jumps directly to the piano
sheet.

## 1.2 What is wrong with it

The prompt names the problem directly: "currently we have a very crappy way of creating the piano
matrix notation." The exploration of the code confirmed six concrete problems:

1. **The transcription quality.** MuScriptor is a newer model, and the user has already tested it on
   Superestrella with good results.
2. **Nothing is visible while the transcription runs.** The progress bar reports a stage and a
   percentage. The notes arrive only at the end, through a second request.
3. **The piano roll visualization cannot be edited in a useful way.** It can select notes and delete
   them, and nothing else. There is no endpoint to change the start or the end of a note.
4. **The hand split is invisible until the piano sheet.** It is computed again on every request,
   applied silently, and the user sees the result only in the pentagrams. The user cannot check the
   split on the piano roll visualization.
5. **Trimming copies the audio.** "Create segment" writes a new audio file with a new uuid.
6. **There is no flow.** No screen knows which step a piece has reached, nothing stops the user from
   opening the piano sheet of a piece whose notes changed, and nothing marks a piano sheet as out of
   date.

## 1.3 Where the work runs

The Mac mini is too small for a 1.4 billion parameter model, and it has no NVIDIA GPU. The Ubuntu
machine (`david-ubuntu`, RTX 4090, 64 GB of RAM, described in
[`../../02b-local-setup.md`](../../02b-local-setup.md)) is where MuScriptor, the backend and the
frontend will run. The Mac stays as the browser, reached through one SSH tunnel.

---

# 2. Terminology

The words of the prompt, each with one meaning. New words are explained here once and then used the
same way everywhere.

- **MuScriptor**: the new transcription model (Kyutai and Mirelo, 2026). It is the only engine the
  user can use after this work. **ByteDance** and **Transkun** stay in the code and are not deleted.
- **stream mode**: MuScriptor's way of producing notes. It cuts the audio into 5-second chunks and
  sends the notes of each chunk as soon as that chunk is done.
- **a chunk**: one of those 5-second pieces of audio.
- **the piano matrix notation**: 88 rows (MIDI 21 to 108), one column per `frameMs` of time. A cell is
  an **onset** (1, the key is struck), a **sustain** (-1, the key is still sounding) or silence (0).
  The **release** is the column where a run of sustain stops. This is the user's format and it does
  not change.
- **a rectangle**: one note as the piano roll visualization draws it. It starts at an onset and ends at
  the release, or at the next onset of the same key. One rectangle equals one onset followed by its
  run of sustain in one row of the piano matrix notation.
- **the sparse form**: the piano matrix notation stored as a list of rectangles (key, onset time,
  length, hand) instead of as 88 full rows. It holds exactly the same information. Section 6 defines
  it.
- **the piano roll visualization**: the view with the vertical piano keyboard on the left and the
  rectangles on a time axis.
- **the hand split**: the prediction of which notes are played by the **right hand** and which by the
  **left hand**. It turns one piano matrix notation into two: a right hand matrix and a left hand
  matrix.
- **the piano sheet**: the pentagrams drawn by the existing `RhythmPage`. It is not redesigned here.
- **a time frame**: 10 ms of audio. It is 160 samples of the 16 kHz `normalized.wav`, one frame of
  MuScriptor, and one column of the piano matrix notation at `frameMs = 10`. The audio and the piano
  matrix notation share this one axis (section 9.2).
- **the selected region**: the time frames of the original audio that the user keeps. By default it
  is all of the audio. The user can cut parts out of it. The audio file is never copied or changed.
- **a cut**: a range of time frames that the user deleted from the selected region. Because the audio
  and the piano matrix notation share the time frame axis, a cut is also a range of columns.
- **the flow page**: the new page with one tab per step (section 7).
- **a step**: one tab of the flow page. The five steps are Source, Audio, Notes, Hands and Sheet.
- **a revision**: a number that goes up by one each time the thing it counts changes. Section 8 uses
  revisions to know when a later step is out of date.
- **stale**: a step whose result was made from an older revision of an earlier step. A stale step must
  be done again before the user can continue.
- **save**: the explicit button that writes the user's edits to the backend. Nothing is written
  before the user presses it.

---

# 3. What MuScriptor is, from the paper and the code

These facts come from the paper (`muscriptor_paper.pdf`) and from reading the repository
`github.com/muscriptor/muscriptor` (version 0.3.0). They are documented facts, not measurements. Phase
1 measures the ones marked "to measure".

| Fact | Consequence for us |
|---|---|
| A decoder-only transformer that reads a mel-spectrogram of a 5-second chunk of 16 kHz mono audio and writes MIDI-like tokens | Our `normalized.wav` is already 16 kHz mono, so it can be fed directly |
| Three published sizes: `small` (103M), `medium` (307M, the default), `large` (1.4B) | We use `large`, as the prompt asks. It "really wants a GPU" |
| Weights on Hugging Face, gated: the user must accept the licence once on the model page, then give a token (`HF_TOKEN`) | A human step in Phase 1 |
| Weights licence **CC BY-NC 4.0** (non-commercial). Code licence MIT | Accepted: the app is for personal use only and will not be sold (Q-6) |
| `TranscriptionModel.transcribe()` is a generator. It yields `NoteStartEvent(pitch, start_time, index, instrument)`, then later `NoteEndEvent(end_time, start_event)`, plus `ProgressEvent(completed, total)` once per chunk | This is the stream mode. The notes of chunk N all arrive before any note of chunk N+1 |
| Times have a 10 ms step (a 100 Hz frame rate) | Finer than our 40 ms default column. Nothing is lost when we snap to columns |
| Velocity exists in the tokens but is not in the public events | Our `velocity` field stays at its default (64) unless Phase 1 finds a cheap way to read it |
| One note per key at a time. A new onset of a key ends the open note of that key | This is exactly the prompt's rule for a rectangle |
| "Prelude forcing" (the default) carries the notes that are still sounding from one chunk into the next, so a long note is not cut at each chunk border. It needs `batch_size = 1`, so chunks run one after the other | Quality at chunk borders against speed. To measure |
| Instrument conditioning: `instruments=["acoustic_piano"]` forbids every other instrument | We always pass `acoustic_piano`: the whole project is for the piano (Q-3) |
| The event times can carry a constant lag of up to about 25 ms. MuScriptor removes it using a beat grid (BPM) | Rule 3 forbids storing a BPM. We may apply a fixed lag correction without storing any tempo. To measure |
| The default dtype on CUDA is float32 with float16 autocast | To measure: float16 and bfloat16 speed and memory on the RTX 4090 |
| Their own web UI draws the piano roll visualization on one 2D canvas, reveals each rectangle with a short animation, and smooths the progress bar between chunk anchors (`web/src/pianoroll.ts`, `progress.ts`) | A good model for our live view (section 9.3). We copy the ideas, not the code |

**An assumption to check early.** The prompt hopes that "1 second of processing already processes 20
seconds of the audio". This is not guaranteed. The large model generates tokens one by one, and chunks
run in order when prelude forcing is on. Phase 1 measures the real speed of `large` on the RTX 4090 and
reports it with the options that make it faster (float16 or bfloat16, a larger batch without prelude
forcing, `torch.compile`, or the `medium` model). The live view in section 9.3 works at any speed.

---

# 4. The binding rules, checked one by one

| Rule | How this plan respects it |
|---|---|
| **Rule 1: `events.json` is the piece** | It stays the stored piece. MuScriptor writes it. The edits of the piano roll visualization write it. The hand split is written into it as a hand per note |
| **Rule 2: a column never moves** | The piano roll visualization edits notes, never the length of the piece. A cut changes the length, and after a transcription it therefore starts a new transcription (Q-2), with the old notes kept in history |
| **Rule 3: no BPM, no bar lines, no metre** | MuScriptor's beat grid, its quantized MIDI and its sheet export are not used and not stored. A fixed lag correction in milliseconds is allowed, because it is a timing fix and not a tempo |
| **Rule 4: `frameMs` is a view** | The sparse form stores milliseconds. A piano matrix notation at any `frameMs` is derived from it |
| **Rule 5: the reader's answer beats the rule** | The predicted hand of any note can be changed by the user, and that change is kept |
| **D-03: the float timestamps stay the source of truth** | The sparse form stores milliseconds, not columns |
| **D-29: every player plays the original recorded onset times** | We play only the original audio, never a synthesized MIDI. The rectangles are drawn at the times of the notes, so the playhead and the audio stay aligned |
| **D-30: the sparse matrix stays the portable format, with a header that carries `frameMs`** | Section 6 defines that portable format |
| **D-31: the hand split runs on the snapped time matrix, after conversion, before everything else** | **Changed.** See below |

**D-31 is changed, and this is the reason.** When D-31 was written, the hand split was a hidden
computation that ran again on every request. The prompt now asks for the hand split as a visible step
with its own button, visible on the piano roll visualization, editable note by note, and saved. The
split still runs on the snapped time matrix, with the same `infer_hands` code. What changes is **when**
it runs and **where the result lives**: it runs once, when the user presses **Predict hands**, and the
result is saved as a hand per note in `events.json`. The piano sheet then reads the saved hands
instead of computing them again. Old pieces that have no saved hands keep the old behaviour, so
nothing that exists today breaks. The phase that makes this change (Phase 5) adds a short note under
D-31 in `decisions.md` that explains the sequence.

---

# 5. What already exists and is reused

| Thing | Where | What it gives |
|---|---|---|
| The engine protocol | `aitu-backend/src/aitu_backend/transcription/engine.py` (`TranscriptionEngine`, `ENGINES`, `engine_installed`) | MuScriptor becomes one more engine that returns `list[NoteEvent]` |
| Jobs and progress over Server-Sent Events | `transcription/jobs.py`, `progress.py`, `GET /matrix/progress/{jobId}` | The job thread and the event stream. Server-Sent Events (SSE) is a one-way stream of messages from the backend to the browser over one HTTP request. We add note messages to it |
| The hand split | `hands/infer.py` (`infer_hands`, method `refine`), `matrix/hands.py` | Unchanged. About 0.5 s for a 3.5-minute piece |
| Events to the piano matrix notation | `transcription/events_to_matrix.py` (`ONSET = 1`, `SUSTAIN = -1`) | The dense form. Section 6 adds the adapters around it |
| History folders | `editing/history.py` (`history/vN/`) | A copy of `events.json` before it is replaced, so nothing is lost |
| The vertical piano keyboard | `aitu-frontend/src/piano/Piano.tsx`, `keyPositions.ts` | The "piano SVG" of the prompt, with per-key colours already possible |
| Undo and redo | `aitu-frontend/src/hooks/useEditHistory.ts` (implementation 06) | A generic history that groups one gesture into one step. Reused by the new editor |
| Selection | `hooks/useNoteSelection.ts` | Click, Command-click, and a band drawn over empty space |
| Toolboxes and bars | `components/common/ToolboxDialog.tsx`, `FloatingBar.tsx` | The floating panels the piano sheet uses. The new editor uses the same ones, so the pages look alike |
| The progress bar and the player | `playback/ProgressBar.tsx`, `components/time/ScorePlayer.tsx` | The slider of the song and the original audio playback |
| The piano sheet | `pages/playground/RhythmPage.tsx`, `components/time/TimeScoreView.tsx` | Used as it is in the last step. Not redesigned |
| The waveform | `components/audio/WaveformView.tsx`, `WaveformRangeSelector.tsx`, `GET /audio/{uuid}/waveform` | The peaks endpoint is reused. The drawing moves to a canvas (section 9.2) |
| The YouTube download | `audio/youtube.py`, `POST /youtube/download` | Reused, moved into a job so the request does not block |

---

# 6. The piano matrix notation: the stored form, the wire form, the adapters

## 6.1 Why the format matters

The prompt asks for a format that is light to send to the frontend and light for the backend
algorithms, and that keeps the user's 88-row piano matrix notation. Today the piece is stored as
`events.json` (light, about 128 KB for a 3.5-minute piece), but the piano sheet request sends
**666 KB** of JSON for the same piece. Most of that is sustain cells sent one by one, as three lists
of numbers per hand. The piano roll visualization also identifies notes by their position in the list,
so an identity changes after any deletion. A move or a resize cannot work on top of that.

## 6.2 The sparse form

A row of the piano matrix notation is a sequence of runs: silence, then an onset followed by some
sustain, then silence again. A rectangle is exactly one of those runs. Storing each run as
**(key, onset time, length)** instead of storing every cell is lossless: the full 88-row matrix at
any `frameMs` can be rebuilt from it in one pass. This is the sparse form, and it is how the piece is
stored, sent and edited.

One rectangle carries five values:

| Field | Type | Meaning |
|---|---|---|
| `id` | integer | Stable identity, given by the backend, never reused in a piece |
| `key` | 0 to 87 | Row of the piano matrix notation (MIDI = key + 21) |
| `onMs` | integer ms | The onset, in milliseconds of the original audio timeline (section 9.2) |
| `lenMs` | integer ms | Onset plus sustain. The release is `onMs + lenMs` |
| `hand` | `r`, `l` or none | The hand, empty until the hand split runs |

Milliseconds and not columns, because of D-03 and rule 4: the same stored piece is viewed at 10 ms on
the piano roll visualization and at 40 ms on the piano sheet.

## 6.3 On disk

`events.json` keeps its current shape, so every existing reader keeps working. Three things are added:

- an `id` on every note (given once, on the first read of an old file, and then kept);
- a header with `notesRevision`, `handsRevision`, `engine` (for example `muscriptor-large`),
  `audioRevision` and `lagCorrectionMs` (section 8);
- a `hand` on every note once the hand split is saved (today `hand` is only a manual pin).

## 6.4 On the wire

The frontend receives the notes as **columns**, one list per field, not as one object per note:

```json
{"revision": 7, "handsRevision": 3, "durationMs": 189160,
 "id": [0, 1, 2], "key": [39, 43, 46], "onMs": [3070, 3363, 3364],
 "lenMs": [1220, 587, 137], "hand": "llr"}
```

This is fast for the frontend, because it copies each list once into a typed array and draws from
those arrays with no conversion. It is also small: an estimate for 2,000 notes is about 40 KB, or
about 12 KB compressed. The backend adds gzip compression to its responses (`GZipMiddleware`). Phase 2
measures the real sizes on all 34 transcribed pieces.

Edits go back to the backend as a **list of operations**, never as the whole piece:

```json
{"baseRevision": 7,
 "ops": [{"op": "move", "id": 12, "onMs": 4410, "lenMs": 300},
         {"op": "delete", "ids": [15, 16]},
         {"op": "add", "tempId": -1, "key": 40, "onMs": 5000, "lenMs": 250},
         {"op": "hand", "ids": [3, 4], "hand": "l"}]}
```

`baseRevision` protects against a lost update. If the stored revision is not 7 any more, the backend
refuses with 409 and the page says so, instead of writing over a newer version.

**The hand split needs no upload.** The prompt suggested sending the piano matrix notation to the
backend for the hand split. The backend already holds the saved notes, so the request only names the
revision: `POST /pieces/{uuid}/hands/predict {"baseRevision": 7}`. The answer is the hand string,
`"rrlrl..."`, in the same order as the ids. Unsaved edits must be saved first, which the save button
already does in one click.

## 6.5 The adapters

The prompt asks for the underlying format to be the one used by any future export. One module,
`aitu_backend/pmn/` ("piano matrix notation"), holds the format and every conversion, with a
round-trip test for each:

| Adapter | Direction | Used by |
|---|---|---|
| `events.json` | both | Storage, and every existing reader |
| Dense 88 x N matrix at a `frameMs` (`int8`, 1 / -1 / 0), whole or per hand | both | The hand split, the piano sheet, the `.npz` exports |
| COO matrix (`SparseCooMatrix`) | out | The existing piano sheet payload, unchanged |
| Columns (section 6.4) | both | The frontend |
| MIDI file | both | Export, and reading a MIDI file in the future |
| MuScriptor events | in | The engine |
| A portable `.pmn.json` file: a header (`format`, `version`, `lowestMidi: 21`, `keys: 88`, `durationMs`, `title`) and the columns | both | The "default format" for any future export (D-30) |

The same module replaces the Python loops that build the COO payload today (`to_coo_payload`, and the
per-cell check in `SparseCooMatrix._check_arrays`) with NumPy array operations. Phase 2 measures the
difference.

---

# 7. The flow page

## 7.1 The tabs

The current Playground has tabs that do not depend on one another. The prompt asks for a flow. The
proposal is one new page, `/piece/:uuid/<step>`, with five tabs in order:

| Step | Tab | What the user does | Ready when |
|---|---|---|---|
| 1 | **Source** (`/piece/new`) | Pick a piece from the library, upload an audio file, or paste a YouTube URL | An audio exists |
| 2 | **Audio** | See the waveform, play it, select a region, delete parts, then press **Transcribe** | Always, once the audio exists |
| 3 | **Notes** | Watch the live transcription, then edit the rectangles and play the original audio against them | A saved transcription exists and is not stale |
| 4 | **Hands** | Press **Predict hands**, check the colours along the song, reassign notes, save | Every note that is not removed has a hand, and the hand split is not stale |
| 5 | **Sheet** | The existing piano sheet, with all its tools | Opens when step 4 is ready |

The uuid is in the address, not only in the browser's session storage, so a reload or a shared link
opens the same piece at the same step.

**Opening a piece from the library** goes to the furthest step that is ready. A piece with a piano
sheet opens on the Sheet tab. A piece that was only transcribed opens on the Notes tab. A tab after the
first step that is not ready is disabled, and its tooltip says what is missing ("Predict hands first").
The user can always go back to an earlier tab.

**Steps 3 and 4 share one editor.** The Hands tab shows the same piano roll visualization with the
rectangles coloured by hand, and it adds the hand tools. Keeping them as two tabs follows the prompt's
order ("the hand split step, the step of the piano roll notation"), and it makes the staleness rule of
section 8 visible: a notes edit can make the Hands tab stale without touching the Notes tab.

## 7.2 What happens to the current Playground

The flow page becomes the entry point of the app (`/` goes to `/piece/new`). The Playground's Input
page keeps working, but its engine choice disappears, because MuScriptor is forced. Piano Roll and
Notes Falling stay reachable for now. Whether they stay after this work is decision Q-4.

## 7.3 Save and leaving a tab

Every edit on the Audio, Notes and Hands tabs is held in the page until the user presses **Save**. A
floating bar shows "N unsaved changes" with **Save** and **Discard**. Moving to the next tab with
unsaved changes asks the user to save or discard first. Leaving the page with unsaved changes shows
the browser's own warning.

---

# 8. Revisions and staleness

## 8.1 The problem

The prompt is explicit: a change of hand, an added note or a deleted note must never let an old piano
sheet be shown as if it were current. Today nothing records what a result was made from.

## 8.2 The revision chain

Each step records the revision of the step before it at the moment it was made:

| Stored | Counter | Goes up when | Records |
|---|---|---|---|
| `metadata.json` | `audioRevision` | The selected region changes and is saved | - |
| `events.json` header | `notesRevision` | A transcription finishes, or a notes edit is saved (move, resize, add, delete) | the `audioRevision` it was transcribed from |
| `events.json` header | `handsRevision` | Anything above changes, or a hand changes | the `notesRevision` the hand split was predicted for |
| `rhythm.json` | - | - | the `handsRevision` the piano sheet was saved for |

One endpoint, `GET /pieces/{uuid}/status`, compares these numbers and answers the state of every step:
`missing`, `running`, `ready` or `stale`. The flow page uses only that answer to enable its tabs.

## 8.3 What each change makes stale

| Saved change | Notes | Hands | Sheet |
|---|---|---|---|
| The selected region | stale: transcribe again (Q-2) | stale | stale |
| A new transcription | new | missing | stale |
| A rectangle moved or resized | - | still valid for the notes that keep their hand | stale |
| A rectangle added | - | incomplete until the new note has a hand | stale |
| A rectangle deleted | - | still valid | stale |
| A hand changed on the Hands tab | - | - | stale |
| A hand changed on the Sheet tab | - | - | stays ready: the sheet that made the change draws it at once |

**A hand changed on the Sheet tab** is a normal edit of the piano sheet, and the user does it often.
It writes the same saved hands as the Hands tab, so the Hands tab shows it too. It does not make the
Sheet tab stale, because the page that made the change is already showing the result. The backend
moves the `handsRevision` recorded in `rhythm.json` forward with the change, but only when
`rhythm.json` was current before it. Section 9.7 says how this change stays fast.

**What "stale" means on the Sheet tab.** The piano sheet is always drawn from the current
`events.json` (contract section 8), so the notes on it are never old. What can be old is the reader's
work saved in `rhythm.json`: the named figure, the overrides, the beam breaks, the fingering. When the
Sheet tab is stale, it opens with a banner ("The notes or the hands changed since this sheet was
saved") and asks the user to press **Write the sheet** again before anything else. Marks that point to
notes that no longer exist are dropped by the logic that already does this (`live`). The page itself is
not otherwise changed.

**An added rectangle** gets a hand from a quick rule (the hand of the nearest note in time, or by
pitch when there is no neighbour) and is shown with a dashed border until the user confirms it or
predicts again. This keeps the Hands tab usable after a small edit without running the full hand split
again.

**A new transcription** copies the previous `events.json` and `rhythm.json` into `history/vN/`
before it replaces them. Today a new transcription deletes `rhythm.json` with no copy.

---

# 9. The design, step by step

## 9.1 Backend: MuScriptor as an engine

- `MuScriptorEngine` in `transcription/engine.py`, installed through a new `muscriptor` extra in
  `pyproject.toml`. It gets its own entry in `engine_installed()`.
- **Forced.** `DEFAULT_ENGINE = "muscriptor"`, MuScriptor first in `ENGINES`, and `/matrix/engines`
  reports only MuScriptor as selectable. The pipeline's special case for ByteDance
  (`options = {"reporter": ...} if engine == "bytedance"`) becomes a check for any engine that
  supports progress. ByteDance and Transkun stay importable and tested.
- **Loaded once.** A model registry keeps one loaded model per `(engine, size, device, dtype)` for the
  life of the process. It loads at startup when `AITU_PRELOAD_ENGINE=muscriptor-large` is set. Today a
  new model is built for every job.
- **Configured, not hard-coded.** `AITU_DEVICE` (`cuda`, `cpu` or `auto`), `AITU_MUSCRIPTOR_MODEL`
  (`large`), `AITU_MUSCRIPTOR_DTYPE`, `AITU_DATA_DIR`, `HF_TOKEN`, `HF_HOME`. Today the device is fixed
  to `cpu` and the data folder cannot be moved.
- **One transcription at a time on the GPU.** A single worker queue. A second request waits and its
  progress bar says "waiting". Today two jobs can load two models and write the same `events.json`.
- **The filters.** `artifacts.py` and `leakage.py` were tuned for ByteDance. Phase 1 measures whether
  they help or harm MuScriptor, and the engine turns them on or off from that result.

## 9.2 Backend and frontend: the selected region, as ranges of time frames

The user answered Q-1 with a rule: the audio is first sampled in time frames, deleting an audio region
deletes a range of time frames, and any range of time frames maps to a range of columns of the piano
matrix notation. A change of the audio therefore has a direct and cheap consequence on the piano matrix
notation and on everything that depends on it.

**One axis.** A time frame is 10 ms: 160 samples of the 16 kHz `normalized.wav`, one MuScriptor frame,
and one column of the piano matrix notation at `frameMs = 10`. Frame `f` of the audio and column `f`
of the piano matrix notation are the same 10 ms. At a coarser view, such as the 40 ms of the piano
sheet, column `c` holds the frames `4c` to `4c + 3`, so the conversion is one integer division.

**Stored as cuts.** The audio file on disk is never changed. `metadata.json` gains `cuts`, a sorted
list of frame ranges `[startFrame, endFrame)` of the original audio, empty by default. The selected
region is every frame that is not in a cut. Cut borders are whole frames, so they always fall on a
column border.

**The piece is shorter.** The kept frames are joined end to end, and they are the time frames of the
piece. A piece with a 10-second cut in the middle is 1,000 frames shorter. The notes, the piano matrix
notation, the hand split and the piano sheet all work in the frames of the piece and need no change.
The link between a frame of the piece and a frame of the original audio is a small table with one row
per kept range (the first frame of the piece, the first frame of the original, the length). Any frame
or any range converts in one lookup in that table, whatever the length of the piece.

**Playback.** The player plays the original audio file. When the playhead of the piece reaches the
end of a kept range, the player jumps the original audio to the start of the next kept range. The
waveform of the Audio tab and the piano roll visualization use the same table, so the three views stay
aligned.

**The input of MuScriptor.** The kept frames are joined in memory and given to MuScriptor as one
audio signal. No audio file is written. At each join, a fade of 5 ms out and 5 ms in avoids a click
that could be read as a note, without changing the number of frames.

**A cut after a transcription** starts a new transcription (Q-2), and the old notes and the old
piano sheet go into history. Because the axis is shared, removing the same columns from the notes
directly would also be possible, in milliseconds and keeping the edits. It is not planned, because
the user chose a new transcription, but it is the simple option to use if that changes.

Old "segments" made with **Create segment** stay as they are.

## 9.3 Backend: the live stream of notes

The transcription job sends one SSE message per chunk:

```json
{"type": "chunk", "done": 3, "total": 38, "upToMs": 15000,
 "open":   {"id": [41, 42], "key": [40, 52], "onMs": [14210, 14800]},
 "closed": {"id": [30, 31, 40], "key": [39, 44, 46], "onMs": [9900, 11000, 13050], "lenMs": [1200, 800, 950]}}
```

`closed` holds the rectangles that ended in this chunk. `open` holds the ones that started and are
still sounding, which the frontend draws up to `upToMs` and extends when their end arrives. The last
message, `{"type": "done", "revision": 1}`, arrives after the lag correction, the filters and the save.
The frontend then asks for the saved notes once (section 6.4). This replaces what it drew, which
differs from the streamed notes only by those corrections.

The stream carries the messages of a running job to any page that connects, including a page that
reconnects after a reload. Their order is the order of the chunks.

## 9.4 Frontend: the Audio tab

A canvas waveform with zoom (Command and the mouse wheel, like the piano sheet), a playhead, and a
selection made by dragging. The keyboard and the buttons:

- **Space**: play or pause. **Play selection** plays only the selected part. **Play all** plays the
  selected region and jumps over the cuts.
- **Delete** (or Backspace) turns the selected part into a cut. The selection snaps to whole time
  frames (10 ms), so a cut always falls on a column border of the piano matrix notation. Cuts are drawn shaded and crossed.
  Clicking a cut and pressing **Restore** removes it.
- Undo and redo (Command-Z and Shift-Command-Z) with `useEditHistory`.
- **Save** writes the cuts, as frame ranges. **Transcribe** saves and starts the transcription, then opens the
  Notes tab.

The waveform peaks come from `GET /audio/{uuid}/waveform?points=N`. When the user zooms far in, the
page asks for more points in the visible range. It does not draw one SVG element per bar, which is
what makes the current waveform slow.

## 9.5 Frontend: the Notes tab, live

The view follows the MuScriptor examples in
[`examples/`](examples/): a dark panel, the vertical piano keyboard on the left, rectangles on
horizontal key lanes, a thin progress bar below with "1:50 / 3:09", and the time taken.

**How it stays fast.** The rectangles are drawn on a **canvas**, which is one drawing surface that
JavaScript paints directly. They are not React elements. Today's piano roll visualization is SVG with
one element per note, and it rebuilds every note about 33 times per second during playback. The canvas
editor keeps the notes in typed arrays (one list per field), keeps an index per key for fast hit tests,
and repaints only on the browser's animation frame:

- Stream messages go into a queue. Each animation frame takes everything in the queue, adds it to the
  arrays and paints. If the backend sends 50 chunks in one second, the page paints 60 frames and not 50
  React updates.
- Each new rectangle grows from left to right over about 250 ms, like the MuScriptor examples.
- The playhead is on a second canvas above the notes, so moving it repaints one line and not every
  rectangle.
- Only the visible time range is painted.

The target is 60 frames per second with 10,000 rectangles, and no frame dropped while a stream of 100
chunks per second arrives. Phase 7 measures both.

**While it transcribes**, the progress bar advances with the chunks. It is smoothed between chunks,
like MuScriptor's own `ProgressEstimator`. The view follows the progress. No audio plays, as the prompt
says.

**After it finishes**, the user can play the original audio. The playhead moves with
`audio.currentTime`. A rectangle starts at the exact time of its onset, so the moment the playhead
touches it is the moment the note sounds. The scrub bar, double-click to seek, and "Follow playhead"
behave like on the piano sheet.

**The edit tools** (the same gestures as the piano sheet, and a toolbox built from the same
`ToolboxDialog`):

| Gesture | Result |
|---|---|
| Click | Select one rectangle |
| Command-click | Add or remove a rectangle from the selection |
| Drag on empty space | Select all rectangles in the band |
| Drag a selected rectangle left or right | Move its onset earlier or later (with Shift held: also change the key) |
| Drag the left or the right edge | Make it start later or earlier, or end earlier or later |
| Delete or Backspace | Delete the selection |
| Double-click on empty space | Add a rectangle of 250 ms on that key |
| Command-Z, Shift-Command-Z | Undo, redo |

Moves snap to 10 ms by default, which is MuScriptor's own step. A move that would overlap another
rectangle on the same key shortens the earlier one, because one key cannot sound twice at the same
time.

## 9.6 Frontend: the Hands tab

The same editor. The rectangles are coloured by hand with the existing `handColors()`, and the keys of
the piano keyboard light up in the hand colour during playback.

- **Predict hands** runs the hand split and colours every rectangle. With the GPU and a warm backend
  this takes about half a second for a 3.5-minute piece.
- **To right hand**, **To left hand**, and the keys `R` and `L`, move the selected rectangles to that
  hand. The whole rectangle moves (onset and sustain), which moves those cells from one hand matrix to
  the other. The rectangle takes the other colour.
- A filter shows both hands, only the right hand, or only the left hand.
- **Save**, then **Continue to the sheet**.

## 9.7 The Sheet tab

`RhythmPage` inside the flow page, with the stale banner of section 8.3. The page's look and its
controls do not change.

**Moving a note to the other hand on the piano sheet must stay light.** The user does it freely and
often. Today one move costs about 0.5 s of hand split computed again on the backend, and then the
whole piano sheet payload (666 KB) is built and sent again. After this work:

1. The page keeps calling `PUT /time/{uuid}/hands`, so `RhythmPage` and its undo do not change. The
   backend finds the notes by their id and changes only their `hand` in the saved hands. The request
   and the write are a few bytes and a few milliseconds.
2. The piano sheet is built from the saved hands, so the hand split is **not** computed again. The
   right hand matrix and the left hand matrix are two masks of the same sparse form (section 6), which
   is one NumPy operation.
3. The payload is built with the NumPy adapters of Phase 2 and sent with gzip.

The target is under 300 ms from the click to the redrawn piano sheet for a 3.5-minute piece, measured
in Phase 8 with the time of each part (request, build, transfer, drawing). If the drawing itself is
the largest part, the report says so and proposes the next step. It does not change the drawing
package in this implementation.

Two other small performance fixes are possible and are **not** part of the plan unless they leave the
page's look and behaviour exactly the same: the page re-renders itself on every animation frame during
playback, and `GET /matrix/{uuid}/events` computes the hand split again on every call with no cache
(the second one is fixed in Phase 4 anyway).

---

# 10. The move to Ubuntu, the containers, the tunnel

## 10.1 What must move

| What | Size | How |
|---|---|---|
| The `aimpromptu` repository | - | `git push` from the Mac, `git clone` on Ubuntu |
| The `vexflow-v2` repository (`@aimpromptu/grid-notation`), branch `plan-resume` | - | Same. It must sit **beside** `aimpromptu`, because the frontend depends on `file:../../vexflow-v2` |
| `aitu-backend/data/audio/` (37 pieces, gitignored) | 1.1 GB | `rsync` from the Mac to Ubuntu over SSH |
| `aitu-backend/data/frame-examples/cache/` (gitignored) | 2 MB | `rsync`. Found in Phase 0 |
| `pocs/poc-synthesia-frames` video and frame outputs (gitignored) | about 270 MB | `rsync` |
| `context/implementations/04-synthesia-to-notes/examples/` (gitignored) | 74 MB | `rsync` |
| The ByteDance checkpoint `~/piano_transcription_inference_data/` | 164 MB | Not copied. It downloads itself on first use |
| `_to_delete/` | 384 MB | Not copied, unless the user asks |

**Before the commit, two problems found in the repository must be fixed:**

- The POC folders were moved into `pocs/`, but the `.gitignore` rules for their large files still
  named the old root path. A plain `git add` would have committed about **286 MB** of video and frame
  files. **Done on 2026-09-28, while writing this plan:** the rules now start with `pocs/`, and a new
  block ignores model weights, audio, video and `__pycache__` in every folder under `pocs/`. What
  `pocs/` adds to git is now 167 files and about 13 MB. Five `__pycache__` files that were committed by
  mistake before the move are no longer added. Phase 0 still checks the size of the whole commit before
  the push.
- The move broke one backend test (`tests/test_matrix_peaks.py` line 266 reads
  `poc-onset-duration-distribution/data` at the root) and some commands in the POC README files. They
  are fixed in the same commit.

## 10.2 The machines

The Ubuntu code goes under `/home/david/Documents/projects/music/` (the setup document's rule for
code) unless the user chooses another path. The MuScriptor repository is cloned beside it, as the
prompt asks. The Hugging Face cache and the Docker data go on `/mnt/ssd2`.

The Mac reaches Ubuntu already (`ssh ubuntu`). The prompt also asks for Ubuntu to reach the Mac, so a
later agent on Ubuntu can fetch a file it needs. This requires **Remote Login** on the Mac and the
Ubuntu key in the Mac's `authorized_keys`. It is a human step in Phase 0.

## 10.3 The containers

The repository has no container today. Phase 3 adds:

- `aitu-backend/Dockerfile`: Python 3.12, `uv`, `ffmpeg`, PyTorch with CUDA, and the `muscriptor`,
  `transcription` and `transkun` extras.
- `aitu-frontend/Dockerfile`: Node, and the Vite development server with hot reload. The build uses
  the sibling `vexflow-v2` through a Compose `additional_contexts` entry, and builds its `dist/`.
- `compose.yaml` at the repository root: the backend with the GPU reserved (`deploy.resources.
  reservations.devices`, driver `nvidia`), the data folder mounted from the host, the Hugging Face
  cache as a volume on `/mnt/ssd2`, `.env` for `HF_TOKEN`; the frontend with the source folders mounted
  so edits reload.
- `.env.example` with every variable name and no values.
- `Makefile` targets `up`, `down`, `logs`, `test-backend`, `shell-backend`.

The frontend runs in development mode, with hot reload, because agents keep editing the code on Ubuntu
(Q-5). A production image comes later, when the app is ready to package.

The host needs the NVIDIA Container Toolkit so a container can use the GPU. Phase 3 checks it with
`docker run --rm --gpus all nvidia/cuda:<version>-base nvidia-smi` and asks the user to install it if
it is missing.

## 10.4 The tunnel

Today the browser calls the backend directly on port 8765, and the frontend on port 5173. That would
need two forwarded ports. Instead, the Vite server forwards `/api` to the backend (a proxy, one server
passing requests to another), and the frontend calls `/api` relatively. The audio files and the SSE
stream go through the same path. On the Mac, one command then opens the app:

```bash
ssh -N -L 5173:localhost:5173 ubuntu
```

and the browser uses `http://localhost:5173`. A script `scripts/tunnel-from-mac.sh` holds this command
and says what to open.

## 10.5 Low-effort performance fixes found during the exploration

The prompt allows clear, low-effort fixes. These were found, and each has an owner phase:

| Problem | Today | Fix | Phase |
|---|---|---|---|
| A new model for every transcription | torch import and weights loaded per job | The model registry of section 9.1 | 4 |
| The device is fixed to CPU | `DEFAULT_DEVICE = "cpu"` | `AITU_DEVICE` | 3 |
| The transcription job computes the hand split and throws it away | The first sheet request pays it again | Put the result in the split cache | 4 |
| `GET /matrix/{uuid}/events` runs the hand split on every call | about 0.5 s each | Use the split cache | 4 |
| The piano sheet payload is 666 KB, built with Python loops | about 0.5 s to build | NumPy adapters and gzip | 2 |
| The YouTube download blocks the HTTP request | yt-dlp and ffmpeg inside the request | A job with progress | 6 |
| The piano roll visualization rebuilds every note 33 times per second | SVG, one element per note | The canvas editor | 7 |
| `torchaudio 2.11` locked beside `torch 2.13` | a version mismatch | Align the versions in the lock file | 3 |

---

# 11. Decisions

The first version of this plan listed six open questions. The user answered all six on 2026-09-28.
They are kept here with the answer, so a later reader knows what was asked and why the plan reads as
it does.

**Q-1. After a cut in the middle of the audio, is the piece shorter, or does it keep a silent gap?**
**Answered: shorter, on a shared axis of time frames.** In the user's words, the audio is first
sampled in time frames, deleting an audio region deletes a range of time frames, and any range of time
frames maps to a range of columns of the piano matrix notation. Section 9.2 is written from that rule.

**Q-2. When the selected region changes after a transcription, what happens to the edited notes?**
**Answered: transcribe again.** The old notes and the old piano sheet go into history.

**Q-3. Transcribe only piano, or every instrument shown as piano?** **Answered: piano only.** The
whole project is for the piano, so every transcription is conditioned on `acoustic_piano`.

**Q-4. Do Piano Roll and Notes Falling stay in the Playground after this work?** **Answered: as
recommended.** Notes Falling stays. The old Piano Roll is removed in Phase 9, because the Notes tab
replaces it.

**Q-5. Frontend container in development mode or production mode?** **Answered: development mode.**
There is no production image until everything is ready to package.

**Q-6. The MuScriptor weights are licensed for non-commercial use only (CC BY-NC 4.0).**
**Answered: acceptable.** The app is for the user's personal use and will not be sold.

**Also confirmed by the user:** `vexflow-v2` is cloned in the same folder as `aimpromptu`; Phase 1
measures the real speed of MuScriptor before anything depends on it; and moving a note to the other
hand on the piano sheet must stay light and fast (section 9.7).

---

# 12. The phases

Each phase is sized for one agent session. Every phase ends with its report,
`08-implementation-phase-N.md`, and the walkthrough message of the communication guide.

## Phase 0: Commit and push from the Mac, and move to Ubuntu (on the Mac)

Confirm the `.gitignore` rules for `pocs/` (already fixed), fix the paths the move broke, check the size of the commit,
commit everything on `master` and push. Confirm that `vexflow-v2` is pushed. Write a data manifest
(every gitignored file to copy, with its size) and the script `scripts/migrate/push-data-to-ubuntu.sh`,
which copies the data with `rsync` to a path given as an argument. The walkthrough then gives the user
the commands to open Cursor on Ubuntu, clone both repositories side by side, and run the copy script
from the Mac. The optional Ubuntu-to-Mac access is also listed there.

## Phase 1: MuScriptor on Ubuntu, and what it outputs (on Ubuntu)

Check the machine: GPU driver, CUDA, Docker, NVIDIA Container Toolkit, `uv`, Node, `ffmpeg`. Check that
the copied data matches the manifest. Install the backend natively, run its tests, build `vexflow-v2`
and the frontend. Clone MuScriptor beside the project, install it, authenticate to Hugging Face (a
human step for the licence and the token), and run its own command-line tool and its own web UI
through the tunnel.

Then the POC, `pocs/poc-muscriptor/`, in the layout of the other POCs (`README.md`, `RESULTS.md`,
`scripts/`, `data/`, `out/`):

1. The first 20 seconds of Superestrella (`a585f9eb-...`) on CPU and on GPU: the raw events, saved as
   they come, to document the output format with real examples.
2. Speed and memory for `small`, `medium` and `large`; float32, float16 and bfloat16; batch size 1
   against larger batches without prelude forcing; with and without `torch.compile`. Reported as
   "seconds of audio per second of processing" and GPU memory in GB.
3. The lag: MuScriptor's own `onset_delay` against the beats, compared with a direct onset detection
   on the audio. This decides `lagCorrectionMs`.
4. Every run is conditioned on `acoustic_piano` (Q-3). One short check without conditioning is kept
   only to confirm that the conditioning removes the other instruments and no piano notes.
5. The whole song with `large` on the GPU, compared with the ByteDance `events.json` of the same song:
   note counts, onsets that agree within 50 ms, and a picture of both piano roll visualizations.
6. Whether the `artifacts.py` and `leakage.py` filters help or harm MuScriptor notes.

## Phase 2: The piano matrix notation format

The `pmn` module of section 6: the sparse form, every adapter, the portable `.pmn.json`, the stable
ids, the header fields of `events.json` (read from old files without a change on disk until the next
save). Round-trip tests for every adapter. The NumPy rewrite of the COO payload and gzip. A table of
sizes and build times on all 34 transcribed pieces, before and after. A specification page,
`context/backend/piano-matrix-notation.md`.

## Phase 3: Containers, the GPU in the backend, and the tunnel

The configuration variables of section 9.1 (`AITU_DATA_DIR`, `AITU_DEVICE`, host and port). The two
Dockerfiles, `compose.yaml`, `.env.example`, the Makefile targets. The GPU checked from inside the
backend container, first with ByteDance on CUDA (already supported, a useful baseline) and then with
MuScriptor. The Vite proxy, the relative `/api` base, and `scripts/tunnel-from-mac.sh`. All backend
tests pass inside the container. A headless browser (Playwright) on Ubuntu, so later agents can take
screenshots of the UI themselves.

## Phase 4: MuScriptor in the backend, and the live stream

`MuScriptorEngine`, forced as the default. The model registry and the preload. The single GPU worker
queue. The cuts in `metadata.json` as frame ranges, the table from the frames of the piece to the
frames of the original audio, and the joined audio in memory (section 9.2). The chunk
messages of section 9.3 on the progress stream. The lag correction and the filter choice from Phase 1.
The history copy before a new transcription. The two split cache fixes. Tests with a fake MuScriptor
model, so the tests do not need the GPU, plus one GPU test that runs only when a GPU is present.

## Phase 5: The piece API, revisions and the hand split as a step

`GET /pieces/{uuid}/status`. `GET /pieces/{uuid}/notes` (columns). `PATCH /pieces/{uuid}/notes`
(operations with `baseRevision`). `POST /pieces/{uuid}/hands/predict`. The revision chain of section 8,
the handsRevision recorded in `rhythm.json`, and the piano sheet reading the saved hands (the D-31
change, with its note in `decisions.md`). The quick hand rule for an added note. Tests for every
staleness case of the table in section 8.3. `PUT /time/{uuid}/hands` (used by the piano sheet) writes
the saved hands by note id, without computing the hand split again.

## Phase 6: The flow page, the Source tab and the Audio tab

The route `/piece/:uuid/<step>`, the five tabs, their enabling from the status endpoint, the redirect
to the furthest ready step. The Source tab (library, upload, YouTube as a job). The Audio tab of
section 9.4. The save bar and the warning for unsaved changes. The Playground Input page loses its
engine choice.

## Phase 7: The Notes tab: the live piano roll visualization and the editor

The canvas editor of section 9.5, the live stream, the progress bar, playback of the original audio
with the playhead, every edit gesture, undo and redo, save. The two performance targets measured and
written in the report.

## Phase 8: The Hands tab and the Sheet tab

Section 9.6 and section 9.7: **Predict hands**, the colours, the reassignment, the filter, save; the
Sheet tab with the stale banner and the rule that forces **Write the sheet** again. The time from a
hand move on the piano sheet to the redrawn piano sheet, measured part by part, against the target of
300 ms.

## Phase 9: The checks, the documentation, and closing

The old Piano Roll tab removed and Notes Falling kept (Q-4). The whole flow in the browser on three pieces (Superestrella, a piece from the library, and a new
YouTube URL), with timings: download, transcription, hand split, first piano sheet. The documentation
pages in `context/` and `documentation/` for the new engine, the format, the flow page, the containers
and the tunnel. `context/02b-local-setup.md` updated for the new way of working. Q-4 applied. The
folder README marked complete.

---

# 13. What could go wrong

| Risk | What is done about it |
|---|---|
| `large` is slower than hoped on the RTX 4090 | Phase 1 measures it first. The live view works at any speed. The faster options (float16, batching, `medium`) are measured and ready |
| The Hugging Face licence or token is missing when a job starts | The backend checks the token at startup and the page says what to do, instead of failing in the middle of a job |
| A commit of 286 MB of POC files | The `.gitignore` fix and the size check come before the commit |
| The frontend cannot build on Ubuntu because `vexflow-v2` is missing or its `dist/` is old | Cloned side by side in Phase 0, built in Phase 1, built inside the image in Phase 3 |
| Two users (or two tabs) edit the same piece | `baseRevision` on every write. A refused write says so and offers to reload |
| The hand split saved in `events.json` breaks the old pieces | Old pieces without saved hands keep the old behaviour. Tests pin both cases |
| The browser drops frames during a fast stream | The queue and the animation frame of section 9.5, and the target measured in Phase 7 |
| An old piano sheet is shown after a change | The revision chain of section 8, and a test for each row of its table |
| The joined audio makes a false note at a cut | A 5 ms fade out and in at each join, with no change in the number of frames, and a check in Phase 4 on a piece with a cut |

---

# 14. How it is checked

- `aitu-backend`: `make test`, inside the container from Phase 3 on. New tests for the adapters, the
  engine with a fake model, the stream messages, the operations, the revisions and staleness.
- `aitu-frontend`: `npm run lint`, `npm run build`, `npm run check:render`, `npm run check:history`,
  plus a check script for the editor's typed arrays and operations.
- `vexflow-v2`: `npm test` if anything there changes (nothing is planned).
- In the browser, through the tunnel, by the user, at the end of Phases 6, 7, 8 and 9. From Phase 3
  on, the agent also takes its own screenshots with Playwright before it asks the user.
