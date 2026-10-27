# Pieces, steps and revisions

The flow page ([frontend/projects.md](../frontend/projects.md)) takes a piece through four steps:
Source, Audio, Notes, Sheet (the Hands step was removed by implementation 03, Phase 5: the AI decides the hands
with the sheet; its code, **Predict hands** among it, was removed in Phase 10, 2026-10-27). Each step is made from the one before it, so a change in an
early step can leave a later one out of date. The user's rule (implementation 08) is that an old
piano sheet must never be shown as if it were current after a change of a note or a hand. Since
implementation 03 the sheet keeps that rule by itself: a sheet stored for older notes is laid again
on the current ones when it is drawn. This page
says how the backend records what each step was made from, and how it answers which steps are
ready. The code is `aitu-backend/src/aitu_backend/pieces/` and `api/pieces.py`.

## 0. A piece is a part of a project

Since implementation 02, Phase 3, a piece is a **part** of a **project** (plan sections 8.3 and
8.8). A normal project has one part; an integrated playlist (Phase 10) has one per sub-song, each
with its own notes, sheet, timeline, revisions, steps and staleness, exactly as a piece had before.
The uuid of every route of this page is the **id of a part**, and a project made by this app has
the id of its first part, so a project of one part has one uuid. A migrated piece kept its uuid
(plan P-6).

Each project has an **owner** and a **layer** (Personal Vault, Private Library, Public Library),
recorded in the `projects` table; its part finds them through the `parts` table
(`storage/locate.py`). Every route checks the user of the session against them before anything
else (Phase 4, [../08-security.md](../08-security.md)). Where the files are:
[../07-database.md](../07-database.md).

**The step of a project** (Phase 5) is the lowest `resume` of its parts, shown on the Projects page.
Working it out reads the notes and the sheet of every part (about 25 ms a part, 0.9 s for 39
projects), so it is kept in `projects.step`: any write of a part's `notes.pmn`, `sheet.f1`, `sheet.json` or
`timeline.json` clears it (`bundle.step_changed`), and `GET /projects` works out again only the rows
it finds cleared (`db/tools.refresh_step`). A running transcription or video reading is read from
the job queue at each list, so the row says "Transcribing" or "Reading" at once.

## 1. The revisions

A **revision** is a number that goes up by one each time the thing it counts changes. Each step
records the revision of the step before it when it is saved:

| Stored in | Number | Goes up when | Also records |
|---|---|---|---|
| `timeline.json` | `audioRevision` | Cuts that change are saved on the Audio tab, or a file is added (**add audio**) | - |
| `notes.pmn` header | `notesRevision` | A transcription finishes, or a notes edit is saved (move, resize, add, delete, restore) | `audioRevision`: the one the notes were transcribed from |
| `notes.pmn` header | `handsRevision` | **Any** change of `notes.pmn`: a transcription, a notes edit, a hand | - |
| `notes.pmn` header | `handsNotesRevision` | A hand edit leaves every live note with a hand; a new transcription sets it to 0 | - |
| `sheet.f1` record | `handsRevision` | Set when the sheet is stored (an AI run, an edit of the sheet) | the `handsRevision` the sheet was written for |

The files are in the part's folder of the project bundle (`parts/<partId>/`); before Phase 3
they were `metadata.json`, `matrices/events.json` and `matrices/rhythm.json`. Every writer of
`notes.pmn` goes through one function, `pipeline.save_edit`, which raises the
numbers. `handsRevision` is therefore the finest version of the file, and the only number the piano
sheet compares with: a `sheet.f1` written for another value is laid again on the current notes.

The old sheet's `sheet.json` also recorded a `handsRevision`, set when the reading was saved
(`PUT /time/{uuid}/rhythm`). Implementation 03, Phase 10 removed that route and the Sheet step's
`stale` state that compared it, and `revisions.sheetHands` of the status answer with it.

## 2. The state of each step

`GET /pieces/{uuid}/status` compares those numbers and answers, for each step, `state` (`missing`,
`running`, `ready` or `stale`), `enabled`, `reason` (the words for a tooltip or a banner) and
`details`. It also answers `resume`, the step the piece opens on (the furthest one that is ready),
and every revision.

| Step | Ready when | Otherwise |
|---|---|---|
| Source, Audio | The audio exists | A part with no audio and no notes (a new empty project) has Source `missing` and every later step closed: "Add an audio first". A part made **from scratch** (Phase 8: its source is `composed`, it has notes and no audio yet) is `scratch`: Source and Audio `missing`, the Audio tab closed ("Record or paste a passage first."), and it opens on the Sheet step; the page shows only the sheet until a passage brings audio |
| Notes | `notes.pmn` exists and its `audioRevision` is the current one | `running` while a transcription job runs (for a video project, while **Read notes** runs, job key `video-read:<uuid>`); `stale` after the cuts changed or audio was added ("Transcribe again"). A video project says "Read the notes of the video" instead of "Transcribe" |
| Sheet | A sheet is stored: `sheet.f1` (implementation 03, Phase 5), or an old `sheet.json` (vexflow-v2), whose marks the new sheet carries | Enabled as soon as the notes are ready. `running` while the AI writes the sheet (job key `sheet-llm:<uuid>`); `missing` otherwise ("Not written yet."). `details`: `newSheet` (a `sheet.f1` is stored) and, while the AI writes, `jobId`. No `stale` and no `legacy` since implementation 03, Phase 10 (2026-10-27) |

A step after one that is not ready is disabled. (One leftover in `pieces/status.py`: a closed Sheet
step still says `stale` instead of `missing` when an old `sheet.json` is stored and the notes are not
ready.) The sheet is never stale for the page: a sheet stored for older notes or hands is laid again
on the current ones (`part_sheet.build`, [`aitu_backend/sheet/README.md`](../../aitu-backend/src/aitu_backend/sheet/README.md)
section 12). No project row holds the step `hands` any more; the database check of `projects.step` still allows it
(no migration was made for it).

## 3. What each change makes stale

| Saved change | Notes | Hands (in `notes.pmn`) | Sheet |
|---|---|---|---|
| The selected region (cuts) | stale: transcribe again (decision Q-2) | - | closed until the notes are transcribed again |
| A new transcription | new | none | missing: both sheets go to the part's history, and the new notes ask the AI (`sheet.pending`) |
| A rectangle moved, resized or deleted | - | still valid | laid again on the notes |
| A rectangle added | - | the new note gets a hand from the quick rule, marked as guessed | the same |
| The AI wrote the sheet | - | written by the AI (saved hands before it go to the history) | ready |
| A change made on the sheet (a hand, a note taken off or added, a reading edit) | as the change says | as the change says | stays ready: stored again for the new hands, one step of the sheet's log |

**The quick rule.** A note added after the hands were saved copies the hand of the closest pitch
among the notes that start within 1 s or still sound at its onset (`transcription/saved_hands.py`).

## 4. The routes

| Route | What it does |
|---|---|
| `GET /pieces/{uuid}/status` | The state of every step (section 2). About 5 to 25 ms |
| `GET /pieces/{uuid}/notes` | The notes in the wire columns of the piano matrix notation, with `revision`, `handsRevision`, `stale` and `guessed`. 11 KB sent for Superestrella |
| `PATCH /pieces/{uuid}/notes` | A list of operations: `move` (times, optional key), `delete`, `restore`, `add`, `hand`. With `baseRevision` (and optional `baseHandsRevision`): an old number answers 409, a refused operation 422 with the reason, and nothing is written. Answers the new revisions, the ids of added notes and the notes the backend changed (a neighbour shortened by the one-note-per-key rule, a guessed hand) |

**Predict hands** (`POST /pieces/{uuid}/hands/predict` and its `/job`) had no page since implementation 03,
Phase 5 and was removed in Phase 10 (2026-10-27). The sheet moves notes between hands with
`POST /sheet/{uuid}/hands`.

The cuts have their own routes, `GET` and `PUT /audio/{uuid}/cuts`, with `baseRevision` too. Once
cuts are saved, `GET /audio/{uuid}/file` serves the edited audio (`piece-r<N>.flac` in the part's
cache), which is in the time of the notes; the stored file stays unchanged for the Audio tab. A part
without cuts whose stored file is compressed (an MP3) plays a lossless copy of it (`listen-<name>.flac`), because
a jump inside an MP3 can land up to about 0.6 s away from the time the player reports.

## 5. The saved hands (decision D-31, changed)

Before implementation 08 the hand split was computed again on every request and never shown.
Implementation 08 saved its result as a hand per note in `notes.pmn` when the user pressed **Predict
hands** (removed in implementation 03, Phase 10). When every live note has a hand, the piano sheet paints the two hand matrices from
those hands instead of running the inference: the same cells on all 34 pieces of the library, in
17 ms instead of 670 ms (median). The note under D-31 in
[`decisions.md`](../implementations/01-mvp/03-time-based-concept/decisions.md) explains the sequence.

**Implementation 03, Phase 5.** The AI decides the hands now: its run writes them into `notes.pmn` at the end
(`part_sheet.job.commit`). A hand moved on the sheet (`POST /sheet/{uuid}/hands`) is written by note id into the
same saved hands, so Notes Falling shows it too; on an old piece the first move saves every hand as the sheet draws
it, then applies the move. The hand split (`aitu_backend/hands/`) stays: it gives the starting hands of the
algorithm and of the AI's input (`pipeline.starting_hands`). The old sheet's hand route (`PUT /time/{uuid}/hands`)
and **Predict hands** were removed in Phase 10 (2026-10-27).

## Where to look deeper

- The format of `notes.pmn` and the wire columns: [piano-matrix-notation.md](piano-matrix-notation.md)
- Where the files are: [../07-database.md](../07-database.md)
- The engine that writes the notes: [muscriptor.md](muscriptor.md)
- Every field of every route: [`documentation/services/backend/endpoints.md`](../../documentation/services/backend/endpoints.md)
- The design and its tests: [plan section 8](../implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-plan.md),
  `aitu-backend/tests/test_pieces.py`
