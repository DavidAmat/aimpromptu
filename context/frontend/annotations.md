# What a reader can say about a piece

Every editorial decision the app offers, where the control is, and what it changes. None of it
changes the recording except where this page says so.

## The two selections, and the two toolboxes

There are two ways to pick something on the sheet, and each opens its own panel **beside what you
picked**. Both panels can be dragged, and once dragged they stay where you put them.

- **Noteheads** — click one, ⌘-click to add, or drag a rubber band across the staves. Opens the
  **note toolbox**; every control applies to the whole set.
- **A stretch of time** — shift-drag across the column numbers above the staves. Opens the
  **frames toolbox**, which is about a stretch rather than about notes.

A stretch that carries an edit draws **two corner marks in its own colour**, so it can be seen
without being selected. Click a corner to open that stretch again; each edit it holds has its own
**Remove**.

Both ends of a marked stretch can be pulled to any column. A group is about a second, far coarser
than the note a reader is aiming at, so without handles there was no way to say "up to there".

## About notes

| Control | What it does |
|---|---|
| **Figure** | Name every chord in the selection at once. Nothing moves in time |
| **Fingering 1–5** | One number per note. Several on a chord print stacked, low to high |
| **Play it with the other hand** | Corrects the split |
| **Start a new beam here** | Refused unless the whole chord is picked — a beam holds every note of a chord |
| **Take it off the page** | For a note the transcriber invented out of a pedal blur |
| **Octave brackets** | Four chips per hand over any stretch you mark. Nothing is suggested |
| **Grace note** | A small note leaning on one note, crushed or leaned on, at a step or a third |

Two of these are worth testing carefully, because they reach further than they look.

**Moving a note between hands also changes what its old and new neighbours are called.** A note's
printed length is the gap to the next onset in the same hand, so check the two notes either side of
the one you moved. The correction is written onto the recording rather than kept as an overlay, so
everything downstream follows it.

**Taking a note off the page does the same thing**, for the same reason — the neighbour is
lengthened to cover it, which is the point. It is staged rather than applied: a floating bar carries
**Save** and **Discard**, and nothing reaches the recording until Save.

Renaming a tresillo loses its `3`, on purpose. The name says "draw it as this" and the bracket says
the opposite.

## About stretches

| Tab | What it does |
|---|---|
| **Key** | A stretch can have its own signature |
| **Speed** | Say what a gap is worth from this column on |
| **Words** | A line of words drawn under the lower staff across the stretch |
| **Small** | Print the stretch cue-sized, per hand or across both staves |

**Words are hand-independent**: they belong to the piece rather than to a staff. A lyric never
widens the layout, because the spacing of the page comes from the notes and never from an
annotation.

**Cue size is asked for, never inferred.** A florid run in one hand set at full size crowds the
other hand off the system; set smaller it takes less width and reads as decoration, which is what it
is. It may move the notes inside the mark and nothing outside it.

## About the whole piece

- **Name the beat** — click a bar in the peak plot, give it a name, write the sheet.
- **Write it one step longer / shorter** — the same playing in longer or shorter note values.
  Neither reading is more correct; pick the one that is easier to read.
- **Key signature** — the app measures a suggestion from the notes and you accept or change it. A
  transcription has no key, so everything used to print in C; on one real piece that was 242
  accidentals that did not need to be there.
- **Smaller / Larger** — how big every mark over and under the staff is drawn. One number rather
  than one per kind, because a reader crowding a dense passage wants all of them smaller.
- **Trills** — the app finds alternating runs and offers them. A suggestion only: a missed trill
  costs nothing, a wrong one hides notes that were really played.

## Keeping it

**Save this rhythm with the piece**, on a small bar that **floats over the sheet** and follows you
down the page. Drag it by its grip, put it away, bring it back.

The bar exists because of a real failure: a long piece went unsaved simply because the button was
past every stave.

Everything is stored in one file beside the recording, `rhythm.json`, and **none of it is in the
recording**. Losing it does not change the music; it costs a person their reading of the piece.

**Remove all** clears every editorial decision and forgets the saved reading, so a reload does not
bring it back. It takes two presses and disarms itself. One of those decisions reaches into the
recording — hidden notes — so it puts those notes back before dropping the list.

Transcribing the piece again clears the reading on purpose: it is a set of column numbers over the
notes that were there before, and a new transcription is a different set of notes.

## Why a column number is a safe address

Every mark above is keyed by column, and **a column never moves** as long as the piece's wall-clock
length does not change. That is what lets a fingering survive a ladder change, a re-recorded
passage, a change of key, and a reload.

The two places length does change are composing and inserting a passage, and there marks move with
their notes in the same write — see [`../backend/editing.md`](../backend/editing.md).

## Where to look deeper

- [`documentation/services/backend/rhythm-and-annotations.md`](../../documentation/services/backend/rhythm-and-annotations.md)
  — `rhythm.json` field by field
- [rendering.md](rendering.md) — what the renderer does with them
- [`../implementations/03-time-based-concept/user-reviews.md`](../implementations/03-time-based-concept/user-reviews.md)
  — the click-by-click walk through all of it
