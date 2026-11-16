# Copy this style: this run

In this run you do not write the whole song. The user selected a stretch of the sheet and edited it by hand: the
**reference**. It is written the way the user wants this kind of passage to read: its rhythm and its figures, its
note names, its chord shapes (an octave made a third, a note left out or added), its beam groups, its clefs and 8va
lines, its decoration notes and its ornaments. The user then asked: "take this as the reference for the rest of the
song". The app found the other places of the song that play the same kind of passage (the **passages**): repeated,
with small changes (another note, another ending, more or less ornament, maybe in another key).

**The purpose**: the song reads the same way each time the passage comes back. A reader who learned the reference
recognises each passage at once.

The run has two kinds of request:

1. **The check** (the first request): you read the reference and each passage, and say which passages are really
   the same kind of passage.
2. **One request per passage kept**: you write the passage again the way the reference is written.

## How you write a passage

Write the **target** (the passage as the sheet has it now) the way the **reference** is written:

- **its rhythm and its figures**: where the reference plays a rhythm, a figure or a held note, the target plays it
  the same way at the matching place;
- **its chord shapes**: where the reference made an octave a third, or left a note of a chord out, or added one, do
  the same at the matching column of the target;
- **its beam groups, its clefs and 8va lines, its decoration notes and its ornaments**, the same way.

Where the target plays **other notes** than the reference (another note of the melody, another chord, another
ending), keep the target's own notes and its harmony, and write them in the reference's way. Never copy a pitch of
the reference into the target when the target plays another one there: copy the way of writing, not the notes.

**The melody stays.** Each note of the top line of the right hand keeps its frame and its pitch (or the same name an
octave higher or lower), unless the reference has no note at the matching column.

**The column map** of each request pairs the columns of the reference with the columns of the target that play the
same place of the passage. Use it to find what the reference did at each place. The **shift** says how many
semitones higher the target plays the reference (0: the same key).

## What you may change, and what overrides the rules above

These rules of this run override the rules of the whole sheet where they differ:

- **You set the figures.** The figure you write for a note is the figure the sheet prints. Write the figure of the
  reference's way of writing; when a note keeps its figure, write the one the target shows.
- **Decoration notes.** The app draws a thirty-second or shorter (one or two of them) just before a longer note as a
  small decoration note. To write a decoration note where the reference has one, write it with that figure, just
  before its main note.
- **Notes left out and added.** A note of the target that you leave out, and a note you add, are each declared after
  the note lines, as in a whole run:

  ```
  # leave out f1822 G2
  # add f4556 D1
  ```

  Change notes only where the reference's way of writing asks for it (the reference has a third where the target
  has an octave; the reference plays fewer notes or a held note where the target plays more), and only as many as
  that needs. A note added has a name of the target's own harmony there. An undeclared change is an error.
- **One hand.** When the user chose one hand, the other hand of the target is shown apart and stays exactly as it
  is: do not write it.

The hard rules stay: every note inside the passage's frames, a beam group of at most 8 notes, no note written four or
more ledger lines above its staff, no 15ma in the bass clef, and a hand changes to its other clef only for a passage
of 5 of its onsets or more (a shorter high stretch of the left hand stays in the bass clef, under 8va when it is too
high for ledger lines).

## The answer of a passage

One block in triple backticks: the two header lines of the target, the note lines of the passage (the hands
rewritten only), then the `# leave out` and `# add` lines, then one or two `# explain:` lines for the user, in very
simple words: what you copied from the reference, and what you kept of the passage's own (`# explain: The left hand
plays the reference's held fifths. The melody keeps its own last note.`).
