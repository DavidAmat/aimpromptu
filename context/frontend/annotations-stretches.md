# The range toolbox, copy and paste

What the Sheet step can say about a marked stretch of frames: the range toolbox (titled *Frames*), copy and paste, and
taking a stretch out. The overview of the page, the selections and undo is [annotations.md](annotations.md). The
other toolboxes: [annotations-notes.md](annotations-notes.md) (the note toolbox) and
[annotations-sheet.md](annotations-sheet.md) (the sheet toolbox). The range toolbox of the old sheet is the record in
[old-sheet-tools/annotations-stretches.md](../archive/old-sheet-tools/annotations-stretches.md).

Code: `aitu-frontend/src/pages/piece/sheet/frames/FramesRangeToolbox.tsx` (the toolbox), `FrameRangeFields.tsx` (the
frame numbers), `FramesSheetPage.tsx` (`copyFrames`, `pastePassage`, `deleteFrames`, `startPassage`).

## Mark a stretch

A stretch is a run of columns of the sheet, each column one frame (40 ms). Mark it in the strip above the upper staff
of a line (it shows faintly under the pointer): a click takes one column, a drag takes columns across, on to the next
lines too, and Shift-click extends the stretch. The stretch is a lavender band, and the range toolbox opens beside it.

The sheet draws a grey dashed line every 100 frames, with the frame number and the time on its top, so that a reader
can name a place in words.

**One selection at a time**: picking notes drops the stretch, and marking a stretch drops the picked notes. Each
toolbox hands its selection to the other from its title bar.

## The frame numbers

The first line of the range toolbox says **From frame [283] to frame [495]**: the frame numbers of the first and the
last column of the stretch, as the sheet prints them. Type other numbers and then press Enter, or leave both fields:
the columns from one frame to the other are marked. Going from one field to the other applies nothing. Escape puts
the numbers of the stretch back.

## The range toolbox

The panel is titled *Frames*, with the time of the stretch under it. Its title bar holds these actions, from left to
right. Each one is one step of Undo, and the ones that change the sheet are off while the AI writes it.

| Action | What it does |
|---|---|
| **Record this passage** (a record icon) | Opens the page of the stretch, where it is recorded again ([recording-in-sheet.md](recording-in-sheet.md)). Not shown on a version or a source sheet (a read-only sheet) |
| **Start a new part here** (a split icon) | The stretch's start cuts the project in two: what follows it becomes a new part of the project. Shown on a project's sheet only, and not when the stretch starts at the first frame |
| **Delete these frames: their notes and their audio** (a bin icon) | Takes the stretch out (see *Delete these frames* below). Not on a read-only sheet |
| **Copy this stretch** (⌘C) | Keeps a reference to the stretch for a Paste (see *Copy and paste*) |
| **Enhance this stretch with AI, with your own words** (the AI mark) | Asks the AI to write the stretch again. Off when no note begins inside the stretch. Enhance with AI of a stretch is told in [annotations.md](annotations.md) |
| **Select the N notes in this stretch** (the arrows icon) | Picks the notes that begin inside the stretch on the staff chosen (off when there are none) |

Under the title come the frame numbers, then the row **Which staff**: **Both**, **Right** or **Left**. It narrows the
band on the sheet and the Clef and Octave tabs to one hand; the other hand keeps its own setting.

Then three tabs. A tab with a dot (an orange dot) means that this stretch already carries that setting.

**Key** (the armadura of the stretch, drawn on both clefs):

- a menu of the armaduras, and ✓ writes the chosen one over the stretch; 🗑 gives back the key of the piece, when the
  stretch has its own;
- when another armadura prints fewer signs over the stretch than the one in force, a button names it: **Use D major
  here (2 fewer signs)**. The backend finds it (`GET /sheet/{uuid}/stretch`: the key at the start and the one with the
  fewest signs).

**Clef**: for each hand in scope, the chips **Treble** and **Bass**; the hand's own clef comes back after the stretch
(🗑 gives it back at once). **Clefs by the rule** writes the clefs the clef rule of the sheet gives the stretch
([rendering.md](rendering.md)).

**Octave**: the chips **8va**, **15ma**, **8vb** and **15mb** for each hand in scope. A chip pressed again, or 🗑, takes
the octave line off. The chips are off where the hand plays nothing in the stretch. A bass clef takes no 8va or 15ma:
the chip says to write the stretch in the treble clef first.

Not on the new sheet: the spacing of a stretch, its speed, and an octave line that is hidden or dragged on the page.
The user dropped them when the toolbox was rebuilt (implementation 03, Phase 7). Trills and small notes are in the note
toolbox.

## Copy and paste

**Copy** keeps a reference to a stretch: the part, its start and end in milliseconds, and its title. It travels in this
browser (`state/passageClipboard.ts`) and as text on the system clipboard, so a Paste works in another tab of the app.
No note and no audio is copied until the paste.

- **Copy this stretch** (the range toolbox), **Copy the frames of these notes** (the note toolbox), or ⌘C. ⌘C with
  notes picked and no stretch marked copies from the first picked note to the later of two ends: the column after the
  last picked note, and the end of the longest picked note.
- A read-only sheet (a version of My library, a source of From other projects, the requests review) has no paste. Its
  small *Frames* panel has **Copy this stretch** and the screen's own action.

**Paste** puts the copied passage in, with its notes, its sheet and its audio ([editing.md](../backend/editing.md)):

- on the floating bar, **Paste** (⌘V). Its tooltip names the copy: *Paste “Song” 0:12 – 0:20 over the marked frames*;
  without a stretch marked it says *at the cursor*;
- on a blank sheet, **Paste the copied passage** in the empty state.

With a stretch marked, the passage replaces it: the stretch is taken out first, then the passage goes in its place.
Otherwise it goes in at the cursor. Everything after it moves later by its length. The paste is one step of Undo.
It is refused, with the reason on the page, while the AI writes the sheet, and when the copy's part cannot be read
any more (*The copied passage is not there any more.*).

## Delete these frames

**Delete these frames** (the bin icon of the range toolbox) takes the stretch out, as if it had never been recorded
nor transcribed. Its notes go, and its audio is taken out: the Audio step can restore it. Everything after the stretch
moves earlier. Its key, clef and speed changes inside it move to its start, when music follows. It is one step of
Undo, and Undo puts the part back as it was, audio included.

The stretch must hold frames; it is refused while the AI writes the sheet, and when the part has no notes yet.

## Where to look deeper

- [annotations.md](annotations.md): the hub, the selections, undo and saving
- [annotations-notes.md](annotations-notes.md): the note toolbox (its copy of the frames of picked notes)
- [annotations-sheet.md](annotations-sheet.md): the sheet toolbox
- [recording-in-sheet.md](recording-in-sheet.md): the page of a passage, opened by **Record this passage**
- [rendering.md](rendering.md): the clef rule and how the sheet is drawn
- [../backend/editing.md](../backend/editing.md): what a paste and a take-out write, and their undo
- [`documentation/services/backend/editing-and-compose.md`](../../documentation/services/backend/editing-and-compose.md):
  the modules and the rules of a paste, a cut and a take-out
- [old-sheet-tools/annotations-stretches.md](../archive/old-sheet-tools/annotations-stretches.md): the old sheet's range
  toolbox (the record)
