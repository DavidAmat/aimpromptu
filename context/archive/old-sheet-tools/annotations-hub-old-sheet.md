# The old sheet's page, selections and saving (the record)

Moved here from [annotations.md](../../frontend/annotations.md) by implementation 05, Phase 5 (2026-11-01). These
sections describe the old sheet (vexflow-v2), whose code was removed in implementation 03, Phase 10 (2026-10-27):
its page, its defaults of a first write, its two selections, its undo, its saving and the column address of its marks.
The new sheet's tools are in [annotations.md](../../frontend/annotations.md).

## The sections of the old sheet

The sections below describe the old sheet (vexflow-v2), whose code was removed in implementation 03, Phase 10
(2026-10-27). They are kept because they say what was moved to the new sheet and what was dropped; the routes they
name (`/time/...`) and the `sheet.json` they save no longer exist as a way of writing (an old `sheet.json` is
still read).

## The page

The page is the sheet (plan section 11.2 of implementation 02). From top to bottom:

- **The title lines**: the title (the project's name until one is written in the **Info** tab),
  and under it the subtitle and the artist.
- **A scrub bar**: the time of the playhead and the length of the piece. Drag it to move the
  recording.
- **The piano sheet**. It wraps to the width of the window, and wraps again when the window is
  made wider or narrower.
- **The floating bar** (draggable, can be hidden): play or pause (also Space), undo, redo, the
  **sheet toolbox**, **Record a passage at the end** (Phase 9), **Paste** (⌘V, Phase 8), **Print to PDF**, **Save**, and
  `⋯` with *Show the keyboard*, *Find trills*, *Bring back N notes taken off* (when some are) and
  *Remove all*.

There is no button to write the sheet: it is drawn as soon as the page opens. The one exception is
a **stale** sheet (the notes or the hands changed after it was saved): it opens with a banner and
waits for **Write the sheet**, then **Save** makes it the sheet of the project again.

Every icon on the page has a tooltip saying what it does. The old cards above the sheet (the plot
of gaps, *Name it*, *Does the piece change speed?*) and the captions under the controls are gone
(plan section 11.1). Their explanations are on these pages.

## The defaults of a first write

Four things the reader used to choose by hand are chosen when a sheet is first written (a project
with no saved sheet, or after **Remove all**). Each is the baseline of the page, not an undo step,
and an ordinary edit after that:

| Default | How | Where to change it |
|---|---|---|
| **The figures** | The highest pile of gaps (the one holding the most) is a **negra** (D-09 as changed by implementation 02). The backend chooses the pile: `GET /time/{uuid}/default-reading` | Sheet toolbox, **Transpose → Figures** |
| **The key signature** | The one that prints the fewest accidentals, measured on the drawn notes | Sheet toolbox, **Key**; a passage in the range toolbox, **Key** |
| **The left hand's clef** | The treble clef over every run of four or more left-hand chords written two ledger lines or more above the bass staff (the clef rule, [rendering.md](../../frontend/rendering.md)) | Range toolbox, **Clef** |
| **Octave brackets** | Over every run of three or more chords written three ledger lines or more outside its staff, measured in the key just chosen, never over a passage the clef rule moved | Range toolbox, **Octave**; again with *Group high notes under 8va* in **Layout** |

The pile is measured once, when the sheet is first written, and its length is saved with the
sheet: a sheet opened again is drawn from the saved length, not from a pile measured again on the
notes, so a paste, a cut or a split of a part (Phase 10) does not rename its figures.

The negra is a convention, not a measurement: statistics cannot tell a negra from a corchea, so a
piece can come out twice too fast or too slow. One **Transpose → Figures** renames every note and moves
nothing.

## The two selections, and the two toolboxes

There are two ways to pick something on the sheet, and each opens its own panel **beside what you
picked**. Both panels can be dragged, and once dragged they stay where you put them.

- **Noteheads**: click one, ⌘-click to add, or drag a rubber band across the staves. Opens the
  **note toolbox**; every control applies to the whole set. It also takes the recording to where
  those notes are (the first column of the set), so the keyboard panel draws the chord you clicked.
  The page does not scroll: you are already looking at the notes.
- **A stretch of time**: click above the staves. The stretch starts where you clicked and runs for
  one group; shift-click another cell to extend it, or pull either end to any column. Opens the
  **range toolbox** (titled *Frames*). Its first row is **Both / Right / Left**: pick one hand and
  the highlight shrinks to that hand's staff, and **Clef** and **Octave** act on that hand alone.

**Either selection can be handed to the other** from the icon in the panel's title bar: from notes,
*Select the frames of these notes*; from a stretch, *Select the notes in this stretch* (every note
that begins inside it, on the staves in scope).

A stretch that carries an edit draws **two corner marks in its own colour**, so it can be seen
without being selected. Click a corner to open that stretch again on the tab of what it carries.

**The range toolbox opens to the left of where the stretch starts**, or below the staves when there
is no room, and stays there: a stretch grows to the right as you drag its handle, so a panel on that
side would end up on top of it. The note toolbox opens to the right.

## Taking it back

**Command-Z takes the last edit back, Shift-Command-Z puts it back** (Control-Z and Control-Y on
Windows), and so do the two arrows of the floating bar, whose tooltips say what they are about:
*Undo: Main figure*. In a text field the keys do what they do in any text field. **One press is one
step**, however many things it changed. At least 20 steps are kept (the history keeps 100).

Six edits are written onto the **recording** rather than onto this page:

| Edit | Does Command-Z reach it? |
|---|---|
| **A note added on the keyboard panel** | Yes. It is marked removed again, and the sheet is drawn again |
| **A hand swap** | Yes. The hand each note had before is written back, and the sheet is drawn again |
| **A notes transposition** | Yes. Every note moves back by the same interval, the notes it took off the keyboard come back, and the key and the marks move back with them |
| **A paste** (Phase 8) | Yes. The part is put back as it was before the paste, notes, audio and saved sheet; Redo pastes it again ([projects.md](../../frontend/projects.md) section 5) |
| **A promotion of a re-recorded passage** (Phase 9) | Yes. The part is put back as it was before the promotion, notes, audio and saved sheet; Redo promotes again ([recording-in-sheet.md](../../frontend/recording-in-sheet.md)). The sheet opens with it as its last step |
| **Remove all** | No. It asks first, deletes the saved sheet and puts the notes taken off back on the recording |

Until Phase 9 a re-record and a recorded passage were two panels of this page that undo could not
reach; the page of a passage replaced both.

## Keeping it

**Save** is on the floating bar, always visible. Nothing is written before it. A **dot on Save**
says there are changes it would keep: a sheet never saved, a change since the last save, or a stale
sheet. Undoing back to the saved state takes the dot away. A refused save is said in a message at
the bottom of the window that stays until it is closed.

Everything is stored in one file beside the notes, `sheet.json` (the *metadata* of the app
context; `rhythm.json` until implementation 02, Phase 3), and **none of it is in the recording**,
except the notes taken off the page, which Save also takes out of the matrix. Transcribing the piece again
clears the file on purpose: its column numbers point at the notes that were there before.

## Why a column number is a safe address

Every mark is keyed by column (a frame), and **a column never moves** as long as the piece's
wall-clock length does not change. That is what lets a fingering survive a change of figures, a
passage re-recorded into its window, a change of key, and a reload. The places length does change are
a paste and a re-recorded passage put in whole, and there marks move with their notes in the same
write; see
[`../../backend/editing.md`](../../backend/editing.md).
