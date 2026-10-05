# Pieces, steps and revisions

The flow page ([frontend/flow-page.md](../frontend/flow-page.md)) takes a piece through five steps:
Source, Audio, Notes, Hands, Sheet. Each step is made from the one before it, so a change in an
early step can leave a later one out of date. The user's rule (implementation 08) is that an old
piano sheet must never be shown as if it were current after a change of a note or a hand. This page
says how the backend records what each step was made from, and how it answers which steps are
ready. The code is `aitu-backend/src/aitu_backend/pieces/` and `api/pieces.py`.

## 1. The revisions

A **revision** is a number that goes up by one each time the thing it counts changes. Each step
records the revision of the step before it when it is saved:

| Stored in | Number | Goes up when | Also records |
|---|---|---|---|
| `metadata.json` | `audioRevision` | Cuts that change are saved on the Audio tab | - |
| `events.json` header | `notesRevision` | A transcription finishes, or a notes edit is saved (move, resize, add, delete, restore) | `audioRevision`: the one the notes were transcribed from |
| `events.json` header | `handsRevision` | **Any** change of `events.json`: a transcription, a notes edit, a hand | - |
| `events.json` header | `handsNotesRevision` | A hand edit leaves every live note with a hand; a new transcription sets it to 0 | - |
| `rhythm.json` | `handsRevision` | Set by the backend when the reading is saved (`PUT /time/{uuid}/rhythm`) | the `handsRevision` the piano sheet was saved for |

Every writer of `events.json` goes through one function, `pipeline.save_edit`, which raises the
numbers. `handsRevision` is therefore the finest version of the file, and the only number the piano
sheet compares with.

## 2. The state of each step

`GET /pieces/{uuid}/status` compares those numbers and answers, for each step, `state` (`missing`,
`running`, `ready` or `stale`), `enabled`, `reason` (the words for a tooltip or a banner) and
`details`. It also answers `resume`, the step the piece opens on (the furthest one that is ready),
and every revision.

| Step | Ready when | Otherwise |
|---|---|---|
| Source, Audio | The audio exists | - |
| Notes | `events.json` exists and its `audioRevision` is the current one | `running` while a transcription job runs; `stale` after the cuts changed ("Transcribe again") |
| Hands | Every live note the piano sheet can place has a hand | `missing`, "Predict hands first", or "N notes have no hand" |
| Sheet | `rhythm.json`'s `handsRevision` equals `events.json`'s | `missing` (no reading: the Sheet tab draws the sheet from the defaults, and **Save** makes it ready), or `stale`: the Sheet tab opens with a banner and asks for **Write the sheet** again |

A step after one that is not ready is disabled, except a stale Sheet tab, which opens with its
banner. Two details matter:

- **Notes the piano sheet cannot place.** A note shorter than one 40 ms column, or one that shares
  its column with another note of its key, gets no hand from the hand split and does not appear on
  the piano sheet. It stays red on the Hands tab for the user to delete or assign, but it does not
  keep the Hands step from being ready (`details.unplaced`).
- **An old piece** whose hands were never saved but which has a saved sheet reads Hands `ready`
  with `saved: false`, so it keeps opening on the Sheet tab. Its piano sheet still computes the hand
  split each time, as before implementation 08.

## 3. What each change makes stale

| Saved change | Notes | Hands | Sheet |
|---|---|---|---|
| The selected region (cuts) | stale: transcribe again (decision Q-2) | stale | stale |
| A new transcription | new | missing | missing (the reading goes to `history/vN/`) |
| A rectangle moved, resized or deleted | - | still valid | stale |
| A rectangle added | - | the new note gets a hand from the quick rule, marked as guessed | stale |
| A hand changed on the Hands tab | - | - | stale |
| A change made on the Sheet tab (a hand, a note taken off or added) | - | - | stays ready: the page that made it draws it at once |

**The quick rule.** A note added after the hands were saved copies the hand of the closest pitch
among the notes that start within 1 s or still sound at its onset (`transcription/saved_hands.py`).
The Hands tab draws it with a dashed border until the user confirms it or predicts again.

## 4. The routes

| Route | What it does |
|---|---|
| `GET /pieces/{uuid}/status` | The state of every step (section 2). About 5 to 25 ms |
| `GET /pieces/{uuid}/notes` | The notes in the wire columns of the piano matrix notation, with `revision`, `handsRevision`, `stale` and `guessed`. 11 KB sent for Superestrella |
| `PATCH /pieces/{uuid}/notes` | A list of operations: `move` (times, optional key), `delete`, `restore`, `add`, `hand`. With `baseRevision` (and optional `baseHandsRevision`): an old number answers 409, a refused operation 422 with the reason, and nothing is written. Answers the new revisions, the ids of added notes and the notes the backend changed (a neighbour shortened by the one-note-per-key rule, a guessed hand) |
| `POST /pieces/{uuid}/hands/predict` | The hand split's answer, one hand per note id. Writes nothing: the page shows it as unsaved changes, and **Save** sends `hand` operations. `replace: true` predicts the hands the user set too |
| `POST /pieces/{uuid}/hands/predict/job` | The same as a job with real progress on `GET /matrix/progress/{jobId}`. About 1 s for a 3-minute piece |

The cuts have their own routes, `GET` and `PUT /audio/{uuid}/cuts`, with `baseRevision` too. Once
cuts are saved, `GET /audio/{uuid}/file` serves the edited audio (`piece-r<N>.flac`), which is in the
time of the notes; the original stays on disk for the Audio tab.

## 5. The saved hands (decision D-31, changed)

Before implementation 08 the hand split was computed again on every request and never shown. Now it
runs once, when the user presses **Predict hands**, and the result is saved as a hand per note in
`events.json`. When every live note has a hand, the piano sheet paints the two hand matrices from
those hands instead of running the inference: the same cells on all 34 pieces of the library, in
17 ms instead of 670 ms (median). The note under D-31 in
[`decisions.md`](../implementations/01-mvp/03-time-based-concept/decisions.md) explains the sequence.

A hand moved on the piano sheet (`PUT /time/{uuid}/hands`) is written by note id into the same
saved hands, so the Hands tab shows it too. On an old piece the first move saves every hand as the
sheet draws it, then applies the move.

## Where to look deeper

- The format of `events.json` and the wire columns: [piano-matrix-notation.md](piano-matrix-notation.md)
- The engine that writes the notes: [muscriptor.md](muscriptor.md)
- Every field of every route: [`documentation/services/backend/endpoints.md`](../../documentation/services/backend/endpoints.md)
- The design and its tests: [plan section 8](../implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-plan.md),
  `aitu-backend/tests/test_pieces.py`
