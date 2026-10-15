# Editing a piece: paste, and Recording in Sheet

Two ways a part changes after it has been transcribed, other than a note edit on its Notes, Hands or
Sheet step. **Paste** (implementation 02, Phase 8) puts a stretch of any part the user may read into
it. **Recording in Sheet** (Phase 9) re-records a stretch of it, or records a new passage into it,
on a page of its own. Both write in one go, with one rule for the length, and both are one step of
the sheet's undo.

Until Phase 9 a re-record (Epic 11) and a recorded passage (Epic 13) were two panels of the sheet
over a staged session (`/audio/{uuid}/edits`), and neither could be undone. The page of a passage
replaced both; the staged session and its routes are gone.

## The length rule

**A passage occupies a whole number of columns.** Its length is rounded up to the next frame before
anything is written, so every column after the insertion point moves by the same integer and a mark
lands on the column it was shifted to. The cost is at most one frame of silence at the join (40 ms).

**Everything after the passage moves, notes and marks in the same write** (rule 2 as changed by
Q-3), through one operation: `compose.insert_events` for the notes, `marks.py` for every mark. An
edit that keeps the length (a promotion fitted into the window) moves nothing.

## Paste a passage

**Copy** (the range toolbox, the note toolbox, ⌘C) keeps a reference to a stretch of a part: the
part and the stretch in milliseconds. No notes and no audio travel with it. **Paste** (the
floating bar, ⌘V) asks the backend to put that stretch in at the cursor, or in place of the marked
stretch, in one write:

- **the notes** whose onset is inside the stretch, cut where it ends, with new ids and their hand;
- **the marks** of the sheet inside it, at their new columns; the key, each hand's clef and the
  speed in force where the copy starts are written where the passage starts, so it reads as it did
  in its song, and what the target had is written again after it;
- **the audio**: the ranges of stored files the stretch plays become entries of the target's
  timeline. No audio byte is copied; a file the passage lands inside is split in two around it;
- **everything after** moves by the passage's length.

The source can be any part the user may read: their own work, their library, a library shared with
them, the Public Library. A stretch pasted over is taken out first: its notes and marks go, and its
audio becomes cuts that the Audio step can restore.

## Recording in Sheet

**Record this passage** (the range toolbox) opens the page of the marked stretch; **Record a
passage** (the floating bar, a blank sheet) opens a new passage at the end of the piece. The page
shows two sheets ([`../frontend/projects.md`](../frontend/projects.md) section 6):

- **Current**: a copy of the marked frames, made by a paste into an empty part, so it has the notes,
  the marks, the key and the clefs of the stretch, and plays its audio (ranges of the stored files).
- **Proposal**: a take. A take is recorded in the browser (or added from a file), the stretch of it
  to keep is chosen on its waveform, and **Write the proposal** runs the condensed steps as one job:
  the transcription, the hand split, and a first sheet written **with the passage's key and
  figure**, so the two sheets read alike. The whole sheet page draws it, with every toolbox.

The passage and its takes are **projects of the user's Personal Vault, hidden from every list**
(`kind = 'passage'`): a take is an ordinary part, so the steps of a project work on it unchanged.
They are deleted when the passage is promoted or discarded, when the project is deleted, and when
it is saved to the library.

**The speed** (×0.25 to ×4) says how many times as fast the take goes into the song. A take played
twice as slowly reads right at ×2: the Proposal names its figures with the song's figure times the
speed. **The window**, as long as the Current, lies over the Proposal; it is dragged by its grip,
and **Fit** finds the speed at which the whole take fills it.

**Promote** writes the take into the part, through the paste, in one write:

| | The audio | The length of the song |
|---|---|---|
| **Fit to the window**, **Keep the original audio** | Unchanged | Unchanged: only the notes and marks of the passage are replaced by the take's under the window, scaled into it |
| **Fit to the window**, **Use my recording** | The take under the window, played at the speed with its pitch kept, replaces the passage's audio | Unchanged |
| **Replace the whole passage** | The whole kept take, at the speed | Longer or shorter by the difference: everything after moves. The dialog says by how much |

The marks of the passage are dropped (the dialog names them by kind); the marks the reader put on the
Proposal come with the take, and a figure renamed there is kept as a speed change. Back on the whole
sheet nothing shows that the passage was re-recorded.

## Undo

**A paste and a promotion are one step of the sheet's undo.** Before writing, the part is kept as a
snapshot of its history: its notes, sheet, timeline and the names of its files. Undo puts that state
back, keeping the pasted or promoted one, which redo puts back. A promotion is made on another page,
so the sheet opens with it as its last step.

## Every mark moves

One module, `editing/marks.py`, lists every mark of `sheet.json` by the column or the range it is
keyed by, and moves, cuts out and copies them. A pasted or promoted passage tears a range it lands
inside (it ends where the passage starts, and goes on after it), because the music put in is not
part of it. A new kind of mark is added there, or no length change moves it.

## Where to look deeper

- [`documentation/services/backend/editing-and-compose.md`](../../documentation/services/backend/editing-and-compose.md)
  — the modules, the routes and every rule
- [`documentation/services/backend/rhythm-and-annotations.md`](../../documentation/services/backend/rhythm-and-annotations.md)
  — the marks that are moved
- [`../frontend/projects.md`](../frontend/projects.md) — the pages: Copy and Paste, the page of a passage
- [time-model.md](time-model.md) — why the length rule matters
