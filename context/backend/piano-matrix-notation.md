# The piano matrix notation: the stored form, the wire form, the adapters

The piano matrix notation is the project's own way of writing a piece: 88 rows (MIDI 21 to 108, one
per key), one column per `frameMs` of time, and a cell that is an **onset** (`1`, the key is
struck), a **sustain** (`-1`, the key is still sounding) or silence (`0`). This page says how that
notation is stored, how it travels to the browser, and how it converts to every other format. The
code is one package, `aitu-backend/src/aitu_backend/pmn/`, written in implementation 08, Phase 2
([plan section 6](../implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-plan.md)).

## 1. Why a sparse form

A row of the matrix is a sequence of runs: silence, an onset followed by some sustain, silence
again. One run is one **rectangle** of the piano roll visualization. Storing each rectangle as
`(key, onset time, length)` instead of every cell loses nothing, because the full matrix at any
`frameMs` is rebuilt from the rectangles in one pass. It is also much smaller: a 3.5-minute piece is
about 2,000 rectangles and about 28,000 active cells at 40 ms.

The rectangles keep **milliseconds**, not columns. The same notes are then viewed at 10 ms on the
piano roll visualization and at 40 ms on the piano sheet, which is what D-03 (the times are the
source of truth) and rule 4 (`frameMs` is a view) ask for.

The milliseconds are those of the **piece**: the original audio with the parts the user cut out
removed (plan section 9.2, Q-1). A cut is a range of 10 ms time frames of the original audio, stored
in `metadata.json`; the original audio file never changes. Once cuts are saved, the backend writes
the edited audio beside it (`piece-r<N>.flac`), which every player plays, so the playhead and the
notes share one time. For a piece with no cut, the time of the piece is the time of the original
audio. The table from one to the other is
`aitu_backend/audio/frames.py` (`FrameTable`), served by `GET /audio/{uuid}/cuts`.

## 2. The sparse form (`pmn/notes.py`)

`Notes` holds one NumPy array per field; index `i` of every array is one note.

| Field | Type | Meaning |
|---|---|---|
| `id` | int64 | Stable identity. Given by the backend, kept across edits and saves, never reused in a piece |
| `key` | int16, 0 to 87 | Row of the matrix. MIDI is `key + 21` |
| `on_ms` | float64 | The onset, in ms of the piece (section 1) |
| `len_ms` | float64, > 0 | Onset plus sustain. The release is `on_ms + len_ms` |
| `hand` | int8 | 0 no hand yet, 1 right hand, 2 left hand |
| `velocity` | uint8 | 64 when the engine has no loudness (MuScriptor has none) |
| `removed` | bool | A reader said the note was never played. Kept so it can be put back; every view leaves it out |
| `hand_guessed` | bool | The hand came from the quick rule for an added note, not from the hand split or a person |

**Why float and not whole milliseconds.** MuScriptor times are whole milliseconds (a 10 ms grid,
then a per-piece lag correction in whole ms). The pieces transcribed by ByteDance store 0.1 ms, and
a column is chosen by rounding. Rounding a stored time to a whole millisecond could move an onset
to the next column and detach the reader's marks keyed on that column (`sheet.json`). So the
arrays keep what the file holds, and only the wire form (section 4) uses whole milliseconds.

## 3. On disk: `notes.pmn` (`pmn/notes_file.py`, `pmn/events_file.py`)

Since implementation 02, Phase 3, the stored notes of a part (rule 1) are `parts/<partId>/notes.pmn`
in the project bundle ([../07-database.md](../07-database.md)): the portable file of section 6,
**version 2** (plan P-5). It is the file of an export too, so nothing is converted on the way out:

```json
{"format": "aimpromptu-pmn", "version": 2, "lowestMidi": 21, "keys": 88, "frameMs": 10,
 "timeUnit": "ms", "durationMs": 257060, "title": "Come on Eileen",
 "notesRevision": 2, "handsRevision": 6, "handsNotesRevision": 0, "audioRevision": 1,
 "engine": "muscriptor-large", "lagCorrectionMs": -21.0, "nextId": 2219,
 "id": [0, 1], "key": [39, 43], "onMs": [3070, 3363], "lenMs": [1220, 587],
 "hand": "rl", "velocity": [64, 64], "removed": [], "handGuessed": []}
```

Version 2 keeps **every note in the order of the part**, the removed ones too (they can be put
back): `removed` and `handGuessed` list note ids. Times are milliseconds with up to three decimals:
the 0.1 ms of the ByteDance pieces and the microseconds of the two hand-made demo pieces convert
with every number equal (the migration checked all 71,290 notes). `outside` would hold a note
outside the 88 keys; none exists.

The code still works in the shape the file had before, `events.json` (one object per note with
`midiNote`, `start` and `end` in seconds, `velocity`, and `hand` / `handGuessed` / `removed` when
set), and converts at the file boundary (`events_file.read_payload`, `write_payload`). The header is
the one of schema `1.1` of `events.json`:

| Key | Where | Default for an old file |
|---|---|---|
| `id` | every note | `0, 1, 2 ...` in file order, given on read and stored at the next save |
| `nextId` | top level | the note count: the first id no note has used |
| `notesRevision` | top level | 1 |
| `handsRevision` | top level | 0 (nothing edited since the file was written) |
| `handsNotesRevision` | top level | 0 (the hands of these notes were never saved as a step) |
| `audioRevision` | top level | 0 |
| `engine` | top level | `null`; a new transcription records the engine's name |
| `lagCorrectionMs` | top level | 0 |

Reading never writes: an old file gives the same ids on every read, because nothing changes on disk
until the next save. A writer that only changes notes keeps the header already on disk. A new
note gets `nextId`, so the id of a deleted note is never given again, not even by a new
transcription of the same piece. What makes the revisions go up is plan section 8:

- A new transcription writes `notesRevision` (1, or one more than before), `audioRevision` (the one
  of `timeline.json` it was made from; a later cut makes the notes stale), `engine` and
  `lagCorrectionMs`, raises `handsRevision` and sets `handsNotesRevision` to 0. The notes it
  replaces are copied to the part's history first.
- Every other writer goes through `pipeline.save_edit`: a notes edit raises `notesRevision`; any
  edit raises `handsRevision`; saving hands that leave every live note with a hand sets
  `handsNotesRevision` to the current `notesRevision`.
- `sheet.json` records the `handsRevision` the piano sheet was saved for. A different value in
  `notes.pmn` makes the Sheet tab stale.

**The saved hands** (D-31, changed in Phase 5). When every live note has a `hand`, the two hand
matrices are painted from those hands and no inference runs
(`transcription/saved_hands.py`); otherwise the inference runs and the hands that are set are laid
on top, as before. `handGuessed` marks a hand given by the quick rule to a note added after the
hands were saved (plan section 8.3).

## 4. To the browser: the columns (`pmn/columns.py`)

One list per field, not one object per note, so the frontend copies each list once into a typed
array:

```json
{"revision": 7, "handsRevision": 3, "durationMs": 189160,
 "id": [0, 1, 2], "key": [39, 43, 46], "onMs": [3070, 3363, 3364],
 "lenMs": [1220, 587, 137], "hand": "llr"}
```

Only live notes, sorted by onset then key. Times are whole milliseconds: `lenMs` is the rounded
release minus the rounded onset, at least 1. `hand` has one character per note: `r`, `l`, or `-`
for no hand yet. `guessed` lists the ids of the notes whose hand came from the quick rule. Measured
on the 34 pieces of the library: 38 KB median (83 KB at most), 14 KB compressed, against 634 KB
(1.5 MB at most) for the piano sheet payload.

`GET /pieces/{uuid}/notes` sends this form, with `stale`. Edits come back as a list of operations
(`PATCH /pieces/{uuid}/notes`, plan section 6.4), never as the whole piece.

## 5. The dense matrix (`pmn/dense.py`)

`to_dense(notes, frame_ms, duration_ms, hand=...)` gives the 88 x N `int8` matrix, whole or for one
hand; `to_hand_grids` gives the right hand matrix and the left hand matrix together. The onset
column is the onset rounded to the nearest column, halves up (D-02); the release column is rounded
the same way; a note always owns its onset column. Two rules keep one rectangle equal to one run:

- **One key sounds one note at a time**: a note ends at its release or at the next onset of the same
  key, whichever is first.
- **Two notes of one key in one column are one note**: the longer is kept (`DenseReport.merged`).

`from_dense` reads the runs back; a sustain with nothing before it is read as an onset. Dense to
sparse to dense gives the same cells for any valid matrix. Sparse to dense to sparse gives the same
notes whenever the times are whole columns, which is every MuScriptor note at 10 ms.

This is the plain conversion. The piano sheet is still built by `events_to_time_matrix`, which also
groups near-simultaneous onsets (D-04) and drops notes shorter than one column (D-05).

## 6. Every adapter

| Module | Direction | What | Used by |
|---|---|---|---|
| `events_file` | both | The shape of `events.json`, and the pipeline's `NoteEvent` list; the file boundary | Storage |
| `notes_file` | both | `notes.pmn`, the `.pmn` version 2, from and to that shape | Storage |
| `dense` | both | 88 x N `int8`, whole or per hand | The hand split |
| `coo` | out (and back) | The COO payload of the piano sheet, with NumPy | `PianoMatrix.to_coo_payload` |
| `columns` | both | The wire form of section 4 | `GET /pieces/{uuid}/notes` and the answer of its `PATCH` |
| `midi` | both | A Standard MIDI File | Export, and reading MIDI later |
| `muscriptor` | in | MuScriptor's events, one at a time (`MuScriptorAssembler`) | The engine and the live stream (Phase 4) |
| `portable` | both | `.pmn.json` version 1, the live notes; it reads version 2 as an export | Any export (D-30) |

The COO payload itself is the unchanged contract of
[`02-notation-spec.md`](../music/notation-logic/02-notation-spec.md).

**MIDI.** No BPM is stored (rule 3), so the file uses one timing unit: 500 ticks per beat at
500,000 microseconds per beat, which makes one tick one millisecond. No time signature is written.
Each hand is a track (`right hand`, `left hand`, `no hand`), so the hand survives the round trip. A
file from elsewhere is read with its own tempo map.

**MuScriptor.** A note's id is given when its start arrives, so the id the browser sees during the
live stream is the id of the saved note. Open and closed notes can be asked for at any moment. The
per-piece lag correction is subtracted from every onset and release only when the notes are taken,
because it is known only at the end.

The live stream (Phase 4, `transcription/live.py`) sends those open and closed notes to the browser
as `event: chunk` frames of `GET /matrix/progress/{jobId}`, in the same column layout as section 4
(`id`, `key`, `onMs`, `lenMs`), with the engine's own times before the lag correction. The notes
the page reads after the `done` frame carry the correction.

**`.pmn.json`.** A header (`format: "aimpromptu-pmn"`, `version`, `lowestMidi: 21`, `keys: 88`,
`frameMs: 10`, `timeUnit: "ms"`, `durationMs`, `title`) and the columns with `velocity`. `frameMs` is
the time frame of the shared axis of the audio and the notes (plan section 9.2). Version 1 keeps one
decimal and only the live notes; version 2 is the stored `notes.pmn` of section 3.

## 7. What the piano sheet request gained

The piano sheet answer (`POST /time/{uuid}/score`) keeps its shape and its content: the answers of
the old and the new code are identical on all 34 pieces. What changed is how it is built and sent:

- The COO lists are built with NumPy, and the per-cell check is one array operation.
- The route sends the payload it built instead of letting FastAPI dump it, check it again and
  encode it, and it no longer reads the notes file on every request only to see that it exists.
- JSON answers are compressed with gzip at level 5 (`aitu_backend/compression.py`); audio and the
  progress stream are not. The piano sheet answer is about 12 times smaller (56 KB median).

Measured in implementation 08, Phase 2, over the 34 pieces: a warm request went from 24 ms to
19 ms median; the table per piece is in the
[Phase 2 report](../implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-implementation-phase-2.md).

## Where to look deeper

- The format decision and the flow around it:
  [08-plan.md](../implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-plan.md) sections 6
  and 8.
- The wall-clock model this format serves: [time-model.md](time-model.md).
- The tests, one round trip per adapter: `aitu-backend/tests/test_pmn.py`; `notes.pmn`:
  `aitu-backend/tests/test_notes_file.py`.
- The measurement script: `aitu-backend/scripts/bench_payloads.py`.
