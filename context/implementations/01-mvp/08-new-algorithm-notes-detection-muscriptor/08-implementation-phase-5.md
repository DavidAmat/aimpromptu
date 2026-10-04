# 08 Phase 5: The piece API, revisions and the hand split as a step

The plan is [`08-plan.md`](08-plan.md) sections 4, 6.4, 8 and 9.7, and section 12, Phase 5. The
status lookup is [`08-checklist.md`](08-checklist.md). This report is for the agents of later
phases: what was built, the choices made inside the phase, the measurements, and what Phases 6 to
9 must know.

The session first closed Phase 4 (after the BIOS update): `make up` healthy, `GET /matrix/engine`
reports `muscriptor-large (cuda, float16)` loaded, `make test-backend` 996 passed and the known
failure, both GPU tests ran. See the Phase 4 report, section 4.

# 1. What was done

| Task | Result |
|---|---|
| 5.1.1 status | `GET /pieces/{uuid}/status` (`pieces/status.py`): per step `state`, `enabled`, `reason`, `details`; `resume`; `revisions` (`audio`, `notes`, `notesAudio`, `hands`, `handsNotes`, `sheetHands`) |
| 5.1.2 notes | `GET /pieces/{uuid}/notes`: `pmn.columns.to_columns` plus `stale` and `guessed`, built from `events_file.read_piece` (NumPy, no pydantic per note) |
| 5.1.3 operations | `PATCH /pieces/{uuid}/notes` (`pieces/edits.py`): `move`, `delete`, `restore`, `add`, `hand`; `baseRevision`, optional `baseHandsRevision`; 409, 422; the answer's `added` and `changed` |
| 5.1.4 predict | `POST /pieces/{uuid}/hands/predict`: `pipeline.inferred_split` (cached) read back by `saved_hands.hands_of_split`; writes nothing |
| 5.2.1 chain | `pipeline.save_edit` for every writer; `PieceHeader.hands_notes_revision` (`handsNotesRevision`); `SavedRhythm.hands_revision` stamped by `PUT /time/{uuid}/rhythm`; a transcription raises `handsRevision` and sets `handsNotesRevision` 0 |
| 5.2.2 quick rule | `saved_hands.quick_hand` / `fill_quick_hands`; `NoteEvent.hand_guessed`, `Notes.hand_guessed`, `handGuessed` on disk |
| 5.2.3 tests | `tests/test_pieces.py` (30), plus 1 in `test_pmn.py`, 1 in `test_transcription_leakage.py` |
| 5.3.1 saved hands | `pipeline.split_of` paints the saved hands (`saved_hands.split_with_saved_hands`) when every live note has one; the inference and the pins otherwise |
| 5.3.2 D-31 | Note under D-31 in `../03-time-based-concept/decisions.md`, and its index line |
| 5.3.3 sheet hands | `PUT /time/{uuid}/hands` resolves the cell to a note id in the cached split, writes by id, `sheet_follows`; the first change on a piece without saved hands saves every hand as drawn |

Every writer of `events.json` now goes through `save_edit`: the old piano roll's removal
(`PUT /matrix/{uuid}/events/removed`), the three Sheet tab routes (`PUT /time/{uuid}/hands`,
`/removed`, `/notes`), the range edit and the composed passage (`editing/session.py`), the video
reader (`video/piece.py`, as `new_notes`). The routes that read, check and write hold
`pipeline.piece_lock(uuid)`.

Two small fixes were needed on the way:

- `events_to_matrix` records `event_ids`, `(column, row) -> note id` of the note that owns each
  onset cell (the one `event_seconds` records). Every mapping between a split and the notes uses
  it, instead of matching `(row, round(start, 4))`.
- `leakage.merge_leaked_onsets` built the merged note as a new `NoteEvent`, which lost its `id`
  and `hand`. It is now a copy of the note that absorbs the phantom. Nothing visible changed: the
  old pins matched by time, and the saved hands give identical cells on every ByteDance piece.

Checks: backend `pytest` natively and `make test-backend` in the container: 1,028 passed, 1 failed
(the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas`, Phase 0 report 2.1).
`black` and `flake8` clean on the changed files; `mypy` reports no new error (the old ones:
two unused ignores in `engine.py`, `matrix.py:394`, three lines of `time_score.py`). No frontend
file changed; a Playwright screenshot of the piano sheet of `b99bc3ae` draws with no console error.

# 2. Choices made inside the phase

## 2.1 The revisions

- `handsRevision` goes up on **every** change of `events.json`, not only on hand changes: the
  plan's table says "anything above changes, or a hand changes". It is therefore the one number
  the piano sheet compares with, and the finest version of the file.
- `handsNotesRevision` (new) answers "were the hands of these notes saved as a whole?". It is set
  to the current `notesRevision` when a hand edit leaves every live note with a hand, and reset to
  0 by a new transcription or a video read. Two things depend on it: the quick rule runs only when
  it is above 0, and an old piece (0) with a saved sheet reads its Hands step as `ready`,
  `saved: false`.
- `rhythm.json`'s `handsRevision` is stamped by the backend on `PUT /time/{uuid}/rhythm`; the
  client's value is ignored. `None` (every reading saved before) reads as 0, and every piece today
  has `handsRevision` 0, so every existing sheet reads `ready`.
- `pipeline.save_rhythm` never stamps. The range edit rewrites `rhythm.json` (marks in the window
  dropped or moved) and keeps its old number, so a range edit makes the sheet stale, as any notes
  edit outside the Sheet tab does.

## 2.2 Where the result differs from the plan's table (section 8.3)

1. **A new transcription makes the Sheet tab `missing`, not `stale`.** Phase 4 kept the removal of
   `rhythm.json` after the history copy: its marks are column numbers over the old notes, and
   after a cut every column moves. The user writes the sheet again either way.
2. **Every Sheet tab edit keeps a current sheet ready**: a hand change, a note taken off, a note
   added. `RhythmPage.save` saves the reading and then calls `PUT /time/{uuid}/removed` for the
   hidden notes; with the rule limited to hands, saving the reading would make it stale at once.
3. **The quick rule** copies the closest pitch among the notes that start within 1 s or still
   sound at the onset (the nearest in time breaks a tie), then middle C. "The nearest in time"
   alone picks the bass or the melody at random in a chord.

The plan's section 8.3 now says the same.

## 2.3 The saved hands paint the same cells as the inference

`split_with_saved_hands` builds the whole keyboard with `events_to_time_matrix` exactly as the old
path does (same grouping, snapping, filters), then gives each run of cells the hand of its first
cell with NumPy: the onset cell takes the hand of the note in `event_ids`, and a sustain the hand of
the last start on its row (`np.maximum.accumulate` over the start columns). An orphan sustain is
written as an onset, which is what the inference's decoder does. This is identical to the
inference's own painting (`hands.events.split_grids`) whenever each onset has the same hand.

`scripts/check_saved_hands.py` runs the old split on every piece, reads it back as one hand per
note, saves those on a copy and paints: **34 of 34 identical at 40 ms and at 20 ms**, 0 cells
different, including `b99bc3ae` (26 pinned hands) and `22222222` (1 pinned).

## 2.4 Predict hands

- It writes nothing. The page shows the answer as unsaved changes, and **Save** sends two `hand`
  operations (all the right-hand ids, all the left-hand ids). This keeps the plan's rule that
  nothing is written before the user presses **Save**.
- `replace: false` (default) lays the saved hands that were not guessed over the inference, as
  the old behaviour lays pins, so a hand the user corrected survives a second prediction; a
  guessed hand is predicted again. `replace: true` predicts every note.
- A note the matrix did not place (shorter than one column, dropped by a filter, merged, or sharing
  its cell with an earlier note of its key) gets the quick rule's hand from the placed notes, so the
  hands are always complete after a save.
- The answer's order is the order of `GET /notes` (onset, then key, then id), and it carries `id`
  so the page does not depend on that order.

## 2.5 The first hand change on an old piece

On a piece without saved hands, `PUT /time/{uuid}/hands` first writes the hand of every live note as
the cached split draws it (`hands_of_split`), then applies the change. The reader sees the same
sheet (checked in `test_the_first_hand_change_on_the_sheet_saves_every_hand_as_the_sheet_draws_it`:
only the moved note's 5 cells change hand). From then on the sheet is painted from the saved hands.
Without this, every hand move on the 34 old pieces would run the inference again (0.4 to 5.3 s).

## 2.6 Smaller points

- `split_cache.forget(uuid)` drops one piece only; `save_edit` calls it, because two saves can fall
  in the same mtime tick. The keys are now any tuple whose first item is the uuid (the inferred
  split uses `(uuid, frameMs, mtime, "keep" | "all")`).
- A PATCH that changes nothing (for example a `hand` operation to the hand a note already has)
  answers `saved: false` and writes nothing.
- `delete` marks the note removed (the existing flag): it keeps its id, leaves every view, and
  `restore` puts it back with its hand. An operation on a removed note other than `hand`,
  `delete` or `restore` is refused.
- The same-key rule runs only on keys an operation touched, and only on pairs where one note was
  placed or moved by an operation, so overlaps already in old ByteDance files stay as they were.
- `time_score.forget_split_cache` is kept (nothing calls it now inside the backend); its callers
  moved to `save_edit`.

# 3. Measurements

## 3.1 The saved hands against the inference

`scripts/check_saved_hands.py` in the backend container, all 34 transcribed pieces. Raw answer:
[`measurements/phase-5-saved-hands.json`](measurements/phase-5-saved-hands.json).

| Column | Pieces identical | Inference median | Painted median | Inference max | Painted max |
|---|---:|---:|---:|---:|---:|
| 40 ms | 34 / 34 | 670 ms | 17 ms | 5,299 ms | 32 ms |
| 20 ms | 34 / 34 | 681 ms | 25 ms | 5,439 ms | 46 ms |

## 3.2 The routes

`scripts/bench_pieces.py` through the HTTP routes of the running backend container, on temporary
copies of three pieces (deleted afterwards; the library was not changed). Raw answer:
[`measurements/phase-5-pieces.json`](measurements/phase-5-pieces.json).

| | `b99bc3ae` Superestrella tutorial | `a585f9eb` Superestrella | `ddd8bce8` (largest) |
|---|---:|---:|---:|
| Notes | 1,497 | 1,343 | 4,295 |
| `GET /status` | 24 ms | 5 ms | 16 ms |
| `GET /notes` (raw / sent) | 4 ms (27 / 11 KB) | 3 ms (25 / 10 KB) | 7 ms (81 / 22 KB) |
| First sheet, old piece (the inference runs) | 1,538 ms | 1,147 ms | 5,455 ms |
| Sheet hand move, first on an old piece: PUT + sheet | 12 + 35 ms | 11 + 34 ms | 28 + 136 ms |
| Sheet hand move, saved hands: PUT + sheet | 9 + 33 ms | 8 + 36 ms | 21 + 74 ms |
| Predict hands, first / again | 1,490 / 9 ms | 1,222 / 9 ms | 5,407 / 22 ms |
| Save the prediction (PATCH, 2 ops) | 9 ms | 5 ms | 12 ms |
| A move (PATCH) | 8 ms | 8 ms | 21 ms |
| Sheet after the move | 34 ms | 34 ms | 135 ms |

Before this phase a hand move on the piano sheet cost the hand split again: the "first sheet" row
(1.1 to 1.5 s on Superestrella). It is now about 45 ms on the backend. The sheet answer is 436 to
598 KB of JSON, 45 KB sent with gzip. The 300 ms target of plan section 9.7 also counts the
transfer and the drawing in the browser: that is Phase 8.

# 4. Notes for later phases

**Every phase.** Nothing of Phases 3, 4 and 5 is committed yet. `GET /pieces/{uuid}/status` of
`b99bc3ae` is a quick live check: an old piece with a sheet answers hands `ready`, `saved: false`,
and `resume: "sheet"`.

**Phase 6 (the flow page).**
- Enable the tabs from `steps[i].enabled` and show `steps[i].reason` as the tooltip; open a piece
  on `resume`. `notes.details.jobId` is the running transcription to follow.
- The Audio tab's cuts make `notes` stale; the status then says `resume: "audio"` and the
  PATCH of notes is refused with 409 until the next transcription.
- The frontend has no client for `/pieces` yet (`aitu-frontend/src/api/`); `SavedRhythm` in
  `api/timeScore.ts` does not declare `handsRevision` (the backend sends it; nothing reads it yet).

**Phase 7 (the Notes tab).**
- `GET /pieces/{uuid}/notes` gives the columns and `revision` / `handsRevision`; send both as
  `baseRevision` / `baseHandsRevision` with every PATCH, and take the new ones from the answer.
- After a save, apply `added` (`tempId` to `id`) and replace each note of `changed` (the same-key
  rule may have shortened a neighbour; the quick rule may have given hands).
- Undo after a save: `restore` puts a deleted note back with its id and hand; a `move` back
  restores the old times.
- The live stream's ids (Phase 4) are the saved ids, so the notes drawn during the stream keep
  their identity after the final `GET /notes`.

**Phase 8 (the Hands and Sheet tabs).**
- **Predict hands** is `POST /hands/predict {baseRevision, frameMs}` (use the reading's `frameMs`
  when there is one); show the answer as unsaved; **Save** is a PATCH with two `hand` operations.
  `replace: true` is the "predict every note again" choice.
- An old piece reads hands `ready`, `saved: false`: its Hands tab has no hands to show until it
  calls predict. Showing the prediction at once, unsaved, looks the same as the sheet it has.
- Draw a note of `guessed` with a dashed border; a `hand` operation on it confirms it.
- **The stale banner.** `PUT /time/{uuid}/rhythm` stamps the current `handsRevision`, so **any**
  save of the reading makes the Sheet tab ready. When the status says `sheet: stale`, the page must
  not save the reading on its own before the user presses **Write the sheet**.
- The sheet's hand move needs no frontend change: `PUT /time/{uuid}/hands` is 8 to 12 ms and the
  sheet request after it 33 to 36 ms on Superestrella. Measure the transfer and the drawing.

**Phase 9 (documentation).** `context/backend/piano-matrix-notation.md` is up to date for Phase 5.
The new routes are not yet in `documentation/services/backend/`.

# 5. Files

New: `aitu-backend/src/aitu_backend/api/pieces.py`, `aitu-backend/src/aitu_backend/pieces/`
(`__init__.py`, `status.py`, `edits.py`), `aitu-backend/src/aitu_backend/transcription/saved_hands.py`,
`aitu-backend/tests/test_pieces.py`, `aitu-backend/scripts/check_saved_hands.py`,
`aitu-backend/scripts/bench_pieces.py`, `measurements/phase-5-saved-hands.json`,
`measurements/phase-5-pieces.json`.

Changed: `api/__init__.py`, `api/matrix.py`, `api/time_score.py`, `transcription/pipeline.py`,
`transcription/split_cache.py`, `transcription/events_to_matrix.py`, `transcription/leakage.py`,
`transcription/engine.py` (`hand_guessed`), `pmn/notes.py`, `pmn/events_file.py`, `pmn/columns.py`,
`schemas/rhythm.py`, `editing/session.py`, `video/piece.py`, `tests/test_pmn.py`,
`tests/test_transcription_leakage.py`; `context/backend/piano-matrix-notation.md`,
`../03-time-based-concept/decisions.md` (D-31), the plan (sections 4, 6.3, 6.4, 8.2, 8.3, 9.7) and
the checklist. Phase 4: its report (section 4) and the checklist.
