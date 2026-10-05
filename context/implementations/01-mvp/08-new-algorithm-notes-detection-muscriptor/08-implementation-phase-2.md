# 08 Phase 2: The piano matrix notation format

The plan is [`08-plan.md`](08-plan.md) section 6 and section 12, Phase 2. The status lookup is
[`08-checklist.md`](08-checklist.md). The specification page written in this phase is
[`../../../backend/piano-matrix-notation.md`](../../../backend/piano-matrix-notation.md). This report is
for the agents of later phases: what was built, the choices made inside the phase, the
measurements, and what Phases 3 to 8 must know.

# 1. What was done

| Task | Result |
|---|---|
| 2.1.1 sparse form | `aitu_backend/pmn/notes.py`: `Notes`, one NumPy array per field (`id`, `key`, `on_ms`, `len_ms`, `hand`, `velocity`, `removed`), validation, `live()`, `of_hand()`, `sorted()`, `take()`, `copy()`, `equals()` |
| 2.1.2 adapters | `pmn/events_file.py` (events.json and `NoteEvent`), `pmn/dense.py` (whole and per hand), `pmn/coo.py`, `pmn/columns.py`, `pmn/midi.py`, `pmn/muscriptor.py` (`MuScriptorAssembler`), `pmn/portable.py` (`.pmn.json`) |
| 2.1.3 tests | `tests/test_pmn.py`, 33 tests: a round trip per adapter, the matrix at 10 ms and 40 ms, and every `events.json` of the library read and written back (skipped when `data/audio` is absent) |
| 2.2.1 ids | `NoteEvent.id`; `pipeline.save_note_events` keeps ids and gives `nextId` to new notes; an old file gets `0..n-1` in file order on read |
| 2.2.2 header | `notesRevision`, `handsRevision`, `audioRevision`, `engine`, `lagCorrectionMs`, `nextId` at the top level of `events.json`, schema `1.1`; `TranscribedEvents.header`; a new transcription records `engine` |
| 2.3.1 COO | `PianoMatrix.to_coo_payload` is `pmn.coo.coo_from_grid` (NumPy, `model_construct`); `SparseCooMatrix._check_arrays` is vectorised |
| 2.3.2 gzip | `aitu_backend/compression.py`, `JsonGZipMiddleware`: JSON only, level 5, 1 KB minimum; `tests/test_compression.py`, 6 tests |
| 2.3.3 table | Section 3 below; raw files in [`measurements/`](measurements/); script `aitu-backend/scripts/bench_payloads.py` |
| 2.3.4 spec page | `context/backend/piano-matrix-notation.md`, linked from `context/00-index.md`, `context/backend/README.md` and `documentation/services/backend/paths-and-data.md` |

Checks: `pytest` 945 passed, 1 failed (the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas`,
Phase 0 report 2.1); 906 before, 39 new. `flake8`: only the old E402 in `events_to_matrix.py`.
`mypy`: no error in any file of this phase (the 67 old errors elsewhere are unchanged). `black`:
the new files are formatted. The frontend is not changed: the browser decompresses gzip itself.

Two small fixes on the piano sheet route (`api/time_score.py`), found while profiling it:

- `_hands` read and validated all of `events.json` on every request only to see that it exists
  (about 10 ms on a large piece). It now checks the file and reads its `st_mtime_ns` (nanoseconds,
  which also fixes the one-second stamp the old docstring worried about).
- Both score routes return `_json(payload)`, a `Response` with `model_dump_json`. Returning the
  model made FastAPI dump it to a dict, validate the dict against the response model (every COO
  cell again) and then encode it. `response_model` stays on the decorators for the docs.
- `to_time_envelope` uses `TimeMatrixEnvelope.model_construct`: pydantic runs a model's "after"
  validators again on every model instance it receives, so the COO check ran once more per hand.
  The envelope's own frame check still runs when `TimeScorePayload` receives it.

The answers are unchanged: `POST /time/{uuid}/score` (40 ms, `dropDecorative`) and
`GET /time/{uuid}/score` (20 ms) give the same JSON on the old commit and the new code for all 34
pieces (compared with a worktree of `729bd5c`).

`mido>=1.3.3` is now a base dependency (it was already installed through the `transcription`
extra). It was added with `uv add --no-sync`, so the venv keeps its extras.

# 2. Choices made inside the phase

1. **Times are `float64` ms in memory, whole ms on the wire.** The plan's table said "integer ms".
   The ByteDance pieces store 0.1 ms, and `test_transcription_raw_events` already pins that
   0.2501 s and 0.2503 s are two attacks. A column is chosen by rounding (D-02), so rounding the
   stored time to 1 ms can move an onset to the next column and detach `rhythm.json` marks keyed on
   it. MuScriptor times are whole ms, so for every new piece the floats hold integers. The columns
   form rounds; `.pmn.json` keeps one decimal. The plan's section 6.2 is updated.
2. **`velocity` and `removed` are in the sparse form** beside the five fields of the plan, so the
   `events.json` round trip is lossless. Every view (dense, COO, columns, MIDI, `.pmn.json`) takes
   `live()` notes only.
3. **The hand character for "no hand yet" is `-`** in the columns and in `.pmn.json`.
4. **Old files.** Ids `0..n-1` in file order; `nextId = n`; `notesRevision 1`, `handsRevision 0`,
   `audioRevision 0`, `engine null`, `lagCorrectionMs 0`. Reading never writes (tested with bytes
   and mtime). A repeated id keeps its first holder; the copy gets a new id.
5. **The header survives the old writers.** `save_note_events(..., header=None)` reads the header
   already on disk, so `PUT /time/{uuid}/hands`, the splice, compose and the video writer keep the
   revisions without knowing about them. Nothing bumps a revision yet: that is Phase 5.
6. **Notes outside the 88 keys.** The sparse form refuses them; the adapters that read foreign data
   (events.json, MIDI, MuScriptor) leave them out and count them. The `NoteEvent` writer still
   stores them. None of the 66,780 stored notes is outside the keyboard.
7. **The dense rules.** Onset and release columns rounded halves up (same as `frame_of_ms`); a note
   owns at least one column; one key sounds one note at a time; two notes of a key in one column
   become the longer one (`DenseReport.merged`). No D-04 grouping and no D-05 drop: that stays in
   `events_to_time_matrix`, which the piano sheet still uses.
8. **MIDI without a BPM.** 500 ticks per beat at 500,000 us per beat, so 1 tick = 1 ms; no time
   signature; one track per hand. Notes are cut at the next onset of their key before writing.
9. **gzip level 5, JSON only.** Starlette's `GZipMiddleware` compresses audio too (including range
   answers used for seeking); its level 9 takes 35 ms for 95 KB on the largest piece, level 5 takes
   5 ms for 103 KB. SSE was already excluded by Starlette 1.0.
10. **One synthetic piece rounds on save.** "Even and swung" (`11111111`, made by
    `scripts/make_demo_pieces.py`) holds 16 times with a fifth decimal. Every save, before and after
    this phase, keeps four. The library test compares at four decimals.

# 3. Measurements (task 2.3.3)

Ubuntu machine, `TestClient` (so each time includes routing, validation and encoding, but no
network), 34 pieces. "Sheet" is `POST /time/{uuid}/score` at 40 ms with the saved anchor or 500 ms.
"Warm" is the median of 3 requests after the first, when the hand split is cached. "Before" is
commit `729bd5c`. "Sheet gzip" is the size served now (level 5); before this phase nothing was
compressed. "Columns" is the wire form of plan section 6.4 (read `events.json` + build: 2.0 ms
median). The COO columns time both hands of the piece, built and checked the old way (Python loops)
and the new way (NumPy), outside the request.

| Piece | Notes | events.json KB | Sheet KB | Sheet gzip KB | Columns KB | Columns gzip KB | Warm ms before | Warm ms after | Warm ms after, gzip | First request ms | COO build ms loop / NumPy | Cell check ms loop / NumPy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| a1c30047 1973, James Blunt | 2,730 | 158 | 997 | 69 | 52 | 19 | 34.5 | 24.6 | 29.5 | 545 | 4.8 / 2.6 | 1.9 / 1.4 |
| f73116dd 2002, Anne-Marie | 1,615 | 94 | 490 | 48 | 30 | 11 | 21.4 | 15.2 | 18.0 | 496 | 2.8 / 1.8 | 0.8 / 0.6 |
| 1a16a836 7 Years, Lukas Graham | 1,458 | 86 | 588 | 54 | 27 | 10 | 24.7 | 18.8 | 22.6 | 410 | 3.9 / 2.3 | 1.3 / 0.9 |
| b2db46eb 99 Red Balloons, Nena | 2,599 | 151 | 816 | 69 | 49 | 19 | 30.1 | 22.1 | 27.0 | 926 | 3.8 / 2.0 | 1.4 / 1.0 |
| b064f815 Airplanes, B.o.B | 2,056 | 120 | 682 | 57 | 38 | 15 | 21.4 | 15.9 | 18.8 | 514 | 3.5 / 2.0 | 1.3 / 0.9 |
| b99bc3ae AITANA - SUPERESTRELLA | PIANO TUTORIAL / COVER | 1,516 | 90 | 436 | 45 | 27 | 11 | 16.2 | 12.5 | 15.2 | 1148 | 2.5 / 1.7 | 0.7 / 0.5 |
| b80e6f5a Birds of a Feather | 1,449 | 84 | 522 | 48 | 27 | 10 | 21.0 | 16.2 | 19.2 | 304 | 3.2 / 1.9 | 1.1 / 0.7 |
| bef90052 Bonfire Heart, James Blunt | 1,677 | 97 | 776 | 66 | 32 | 13 | 29.1 | 21.1 | 25.3 | 1043 | 4.7 / 2.3 | 1.9 / 1.3 |
| f285e4b7 Can't Stop the Feeling, Justin Timberlake | 2,675 | 156 | 804 | 81 | 50 | 20 | 33.7 | 26.1 | 30.3 | 1059 | 4.0 / 2.4 | 1.3 / 0.9 |
| 22222222 Classical mix: tresillos, runs and holds | 138 | 7.6 | 32 | 3.8 | 2.2 | 0.8 | 2.9 | 2.6 | 2.6 | 57 | 0.2 / 0.2 | 0.0 / 0.0 |
| d64acd29 Club Can't Handle Me, David Guetta | 3,512 | 204 | 1011 | 85 | 66 | 25 | 39.8 | 27.9 | 33.4 | 1199 | 4.0 / 2.2 | 1.5 / 1.0 |
| e578f3c0 Die Young, Kesha | 2,485 | 145 | 727 | 68 | 46 | 18 | 27.9 | 21.1 | 25.4 | 726 | 3.4 / 2.0 | 1.2 / 0.8 |
| 3c8d4cfa Drivers License, Olivia Rodrigo | 1,733 | 101 | 784 | 54 | 33 | 12 | 27.5 | 19.5 | 22.5 | 385 | 4.5 / 2.5 | 1.9 / 1.2 |
| ddd8bce8 Elektronomia - The Other Side | Synthesia Piano Cover | 4,295 | 256 | 1107 | 71 | 81 | 22 | 40.8 | 30.1 | 35.9 | 4267 | 3.9 / 2.4 | 1.3 / 0.8 |
| 11111111 Even and swung | 33 | 3.3 | 9.8 | 1.6 | 0.5 | 0.2 | 2.1 | 1.3 | 1.3 | 12 | 0.1 / 0.1 | 0.0 / 0.0 |
| 3633a0c3 Fate of Ophelia, Taylor Swift | 2,026 | 118 | 685 | 60 | 38 | 14 | 26.5 | 20.1 | 23.7 | 445 | 3.6 / 2.2 | 1.3 / 0.9 |
| 56543911 Grace Kelly, Mika | 2,144 | 124 | 692 | 54 | 40 | 16 | 24.3 | 17.9 | 21.3 | 504 | 3.3 / 1.8 | 1.3 / 0.8 |
| 4cb9cb38 Hips Don't Lie, Shakira | 1,614 | 94 | 504 | 49 | 30 | 11 | 21.7 | 16.6 | 19.6 | 807 | 2.8 / 1.7 | 0.9 / 0.6 |
| 6eb7af4e I Knew You Were Trouble | 1,713 | 100 | 568 | 53 | 31 | 13 | 22.6 | 16.6 | 20.6 | 576 | 3.0 / 1.7 | 1.1 / 0.8 |
| 0815f602 La Tortura, Shakira | 2,154 | 125 | 650 | 57 | 40 | 14 | 22.9 | 17.0 | 19.9 | 513 | 3.3 / 2.0 | 1.1 / 0.8 |
| c0edc9b0 Moonlight Shadow, Mike Oldfield | 2,384 | 139 | 790 | 75 | 45 | 18 | 36.3 | 20.0 | 24.9 | 678 | 4.1 / 2.2 | 1.5 / 1.0 |
| 51b12412 Party in the USA | 1,738 | 101 | 564 | 55 | 32 | 13 | 22.9 | 18.1 | 22.7 | 774 | 3.1 / 1.9 | 1.1 / 0.7 |
| 2ed0f379 Poker Face, Lady Gaga | 1,985 | 116 | 606 | 54 | 37 | 14 | 27.2 | 21.1 | 24.4 | 419 | 3.1 / 2.0 | 1.0 / 0.7 |
| 12f777af Raise Your Glass | 1,814 | 105 | 557 | 58 | 33 | 14 | 19.9 | 15.0 | 18.4 | 595 | 3.0 / 1.9 | 0.9 / 0.7 |
| 68e277fe Shut Up and Dance, Walk the Moon | 1,992 | 118 | 494 | 51 | 36 | 14 | 20.2 | 15.8 | 19.0 | 384 | 2.3 / 1.7 | 0.5 / 0.4 |
| aa07c1c0 Stay the Night, James Blunt | 1,470 | 86 | 474 | 50 | 27 | 11 | 19.6 | 15.1 | 18.1 | 587 | 2.8 / 1.7 | 0.8 / 0.6 |
| dff5097c Stronger, Kelly Clarkson | 2,076 | 121 | 730 | 62 | 39 | 15 | 28.4 | 22.1 | 25.7 | 431 | 3.8 / 2.1 | 1.4 / 0.9 |
| a585f9eb Superestrella, Aitana | 1,343 | 78 | 598 | 45 | 25 | 9.9 | 20.8 | 15.2 | 18.3 | 904 | 3.9 / 2.0 | 1.6 / 1.1 |
| 92255337 The One That Got Away, Katy Perry | 1,618 | 94 | 598 | 52 | 30 | 11 | 23.3 | 18.2 | 21.2 | 520 | 3.6 / 2.1 | 1.2 / 0.9 |
| 96768e80 The Other Side, Jason Derulo | 2,019 | 118 | 557 | 50 | 37 | 12 | 22.3 | 19.5 | 22.1 | 667 | 2.6 / 1.7 | 0.7 / 0.5 |
| fb0b0989 The Winner Takes It All | 2,692 | 157 | 1467 | 100 | 52 | 21 | 45.7 | 29.1 | 35.2 | 1463 | 8.8 / 4.1 | 4.0 / 2.8 |
| f3680cb8 Titanium, David Guetta | 2,221 | 129 | 715 | 62 | 42 | 15 | 27.9 | 20.3 | 24.2 | 630 | 3.7 / 2.3 | 1.3 / 0.8 |
| e3d7c376 What Makes You Beautiful | 2,161 | 126 | 631 | 54 | 40 | 14 | 24.6 | 19.4 | 22.7 | 466 | 3.0 / 1.9 | 1.0 / 0.7 |
| 19187d10 Wild Ones, Sia | 1,645 | 94 | 538 | 45 | 30 | 12 | 17.8 | 13.2 | 15.8 | 456 | 2.6 / 1.4 | 1.0 / 0.7 |
| **Median** | 1,988 | 117 | 619 | 54 | 37 | 14 | 23.8 | 18.5 | 22.3 | 560 | 3.3 / 2.0 | 1.2 / 0.8 |

What the numbers say:

- **Size.** The piano sheet answer is unchanged (634 KB median, 1.5 MB at most) and is now sent at
  56 KB median, about 11 times smaller. The columns form is 37 KB median (14 KB compressed), which
  matches the plan's estimate (40 KB and 12 KB for 2,000 notes). `events.json` is 117 KB median.
- **Warm request.** 24 ms to 19 ms median without gzip, 46 ms to 29 ms for the largest piece (The
  Winner Takes It All, 2,692 notes, 92,000 cells). gzip adds about 4 ms median (6 ms for the
  largest), and saves about 580 KB of transfer on each sheet change, which is worth far more
  through the SSH tunnel.
- **The loops were not the big cost here.** Outside the request the COO build is 3.3 ms (loop)
  against 2.0 ms (NumPy), and the cell check 1.2 ms against 0.8 ms: `tolist()` dominates both. The
  larger gains came from removing the repeated work around them (the check ran 4 times per request,
  FastAPI's second validation, the file read). cProfile had made the loops look three times worse.
- **The first request of a piece is the real wait**: 560 ms median, 4.3 s for the slowest
  (`ddd8bce8`, 4,295 notes). It is the hand split, cached per piece. `GET /matrix/{uuid}/events`
  (the old piano roll) pays it on every call: 548 ms median. Phase 4 (split cache) and Phase 5
  (saved hands) remove both.

# 4. Findings that change the plan

- Section 6.2: the types (float ms in memory, whole ms on the wire) and the two extra fields.
- Sections 6.3 and 6.4: schema `1.1`, `nextId`, the `-` hand character, the measured sizes.
- Sections 9.7 and 10.5: the plan said the sheet payload is 666 KB and takes about 0.5 s to build
  with Python loops. On Ubuntu the payload is 634 KB median and a warm build is 19 ms; the 0.5 s is
  the hand split of the first request. The plan's rows now say so.

# 5. Notes for later phases

**Phase 3 (containers, proxy).** The Vite proxy must pass `Content-Encoding: gzip` through untouched
(it does by default). A `curl` without `--compressed` gets plain JSON, because the middleware
compresses only when the client asks.

**Phase 4 (engine, stream).**

- Feed each MuScriptor event to `pmn.muscriptor.MuScriptorAssembler.add`. After each
  `ProgressEvent`, `closed_since(position)` gives the rectangles closed since the last message and
  `open_notes` the ones still sounding: those are the `closed` and `open` lists of plan section 9.3.
  Ids are given at `NoteStartEvent`, in arrival order, from `first_id` (pass the piece's `nextId`).
- At the end, `assembler.notes(end_ms=duration, lag_correction_ms=...)` applies the lag correction
  to every onset and release, never before 0, and closes notes still open at `end_ms`.
- Save with `events_file.write_piece(uuid, Piece(notes, header, duration_ms, title))` and a header
  with `engine="muscriptor-large"`, `lagCorrectionMs`, `nextId`, and the revisions of Phase 5; or
  with `events_from_notes` and `pipeline.save_note_events`.
- `pipeline.transcribe_audio` already records `engine=model.name` and continues the ids.

**Phase 5 (piece API).** `GET /pieces/{uuid}/notes` is `events_file.read_piece` then
`columns.to_columns(notes, revision=..., hands_revision=..., duration_ms=...)` (2 ms median). The
operations of `PATCH` work on a `Notes` (`copy()`, change arrays, `write_piece`); a new note takes
`piece.header.next_id`. The revision bumps belong there; nothing bumps them now. The two hand
matrices for the saved hands are `dense.to_hand_grids(notes, frame_ms, duration_ms)`.

**Phase 7 (live view).** The columns arrive sorted by onset then key, integers, `hand` as one string.

**Phase 8 (hand move on the sheet).** In the warm request that remains, about a quarter of the time is
the figure naming walking every column in Python (`PianoMatrix.onsets_in_column` from
`notation/figures.py` and `attack_seconds_of_hand`, about 5,600 calls per request on the largest
piece). One `np.nonzero(grid == ONSET)` per hand would replace them. Not done here: it is outside
the format, and the warm request is already far under the 300 ms target.

# 6. Files

New: `aitu-backend/src/aitu_backend/pmn/` (8 modules), `aitu_backend/compression.py`,
`tests/test_pmn.py`, `tests/test_compression.py`, `tests/fixtures/pmn/` (the Phase 1 events of the
first 20 s of Superestrella, and MuScriptor's own notes for them), `scripts/bench_payloads.py`,
`context/backend/piano-matrix-notation.md`, `measurements/phase-2-payloads-{before,after}.json`.

Changed: `transcription/engine.py` (`NoteEvent.id`), `transcription/pipeline.py` (save and load
through `pmn.events_file`, the header, the engine on a new transcription),
`transcription/time_pipeline.py` (`model_construct` envelope), `matrix/model.py` (`to_coo_payload`),
`schemas/matrix.py` (vectorised check), `api/time_score.py` (`_hands`, `_json`), `main.py` (gzip),
`pyproject.toml` and `uv.lock` (`mido`), the index, the backend README and `paths-and-data.md`.
