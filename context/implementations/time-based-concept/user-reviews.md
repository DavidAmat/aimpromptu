# End-to-end review

One walk, in the app, from a piece to printed sheet music. Everything below has been opened and
checked on screen first.

> **Up to date as of 2026-08-10, the day this plan closed.** Steps 1–10 are the original walk;
> steps 11–15 cover everything added after it was first written. If you are doing the round of real
> piano music, this is the order to try things in.

```bash
cd aitu-backend  && uv run python scripts/make_demo_pieces.py   # once, to put the demo pieces in
cd aitu-backend  && make serve                                  # http://localhost:8765
cd aitu-frontend && npm run dev                                 # http://localhost:5173
```

The first command writes two pieces into your library. They are written by hand rather than
recorded, so the right answer is known before you open anything — which is what makes them worth
looking at. Your own recordings work exactly the same way.

## The walk

### 1. Pick a piece

1. Open `http://localhost:5173` → **Playground → Upload / Input**.
2. Under **Audio library**, click **classical-mix**.

Or upload a file, record something, and press **Run transcription** — in **Transcription settings**
there are two fields now. Leave **Time resolution** at *40 ms — normal* and choose an engine.

There is no tempo to type in and no note-figure resolution to choose. The playing is written down
exactly as it happened; what the notes are called is decided in step 3.

### 2. Look at how the piece was played

Go to the **Rhythm** tab.

Each bar is a gap that keeps repeating between one note and the next, measured before anything was
rounded. The height is how often that gap happens.

On **classical-mix** the right hand should show seven bars: 60, 120, 160, 240, 480, 720 and 960 ms.
That is one bar per figure in the piece, and it is the picture working — seven different note lengths
were played and seven piles came back.

Switch **Hand** between right, left and both. The left hand has one bar at 160 ms, because it plays
the same thing all the way through. Each hand is measured on its own: the gap between a right-hand
run and a held left-hand chord is not a rhythm.

### 3. Name one gap

1. Click the **480 ms** bar. It turns solid.
2. In **Name it**, leave it as **Negra (quarter)**.
3. Press **Write the sheet**.

The line next to the button reads `negra = 480 ms · ≈125 BPM`, and every other bar picks up the name
it takes from your choice. All seven should say **0% off**, and the 160 ms one should say
**corchea de tresillo** rather than a badly fitting corchea — three notes dividing a beat have no
name in a vocabulary of halves, so they are recognised instead of rounded.

### 4. Read the sheet

The staff appears below.

What to check, and this is the point of the whole change:

- The **left hand is the same figure all the way through**, in groups of three under a ⌐3⌐ bracket.
  The old app wrote an even run as a mix of sixteenths and dotted eighths, every time.
- The **two hands do not line up**, and that is correct — the left hand's notes sit between the right
  hand's, which is what most classical piano writing looks like.
- Each tresillo is **beamed on its own**. Two in a row must not run together into one group of six.
- The **fast run in the right hand has three beam levels**, and the run before it has two — a beam
  gains a level for each step down the figures.
- There are **no rests**. Distance on the page is time, so a silence is the space it takes.
- A **dashed line** every so often, and a **label above the staff** where a stretch begins. The
  dashed lines are the only thing saying the horizontal axis is wall clock; without them the spacing
  reads as ordinary note-value spacing, which would be wrong.
- The sheet **stops where the playing stops**.

At the end, after the tresillos, the left hand plays two long runs — sixteen corcheas and then
sixteen semicorcheas, climbing two octaves and coming back. Each is **one beam of sixteen**, drawn
flat and far above the staff. That is what step 7b is about.

### 5. Hear it against the sheet, and see where you are

Press **Play the recording** above the staff. What plays is the recording itself, never anything
rebuilt from the page. If the notes you see and the notes you hear drift apart, the page is wrong.

A **line runs down both staves** at the moment the recording is at, and the page scrolls when the
music reaches the next system. The line is read from the recording sixty times a second, so it does
not drift away from the sound the way a timer of its own would.

**Click the bar under the buttons** to move to a point in the piece. The recording and the line both
jump there, which is how you look at one particular passage without waiting for the piece to reach
it.

### 6. Change your mind about the whole piece

Two ways, and they are worth trying in this order.

**Write it longer or shorter.** Under the name there are two buttons: **Write it one step longer**
and **Write it one step shorter**. Press one and then **Write the sheet**. The same playing comes
back in longer or shorter note values: `negra = 480 ms` becomes `blanca = 480 ms`, every pile in the
plot is relabelled, and a page of semicorcheas becomes a page of corcheas. Neither reading is more
correct — pick the one that is easier to read.

**Or name a different pile.** Go back to step 3, click the **240 ms** bar instead and name that one
the negra, then press **Write the sheet** again.

Every figure moves one step up the ladder: what was a negra is now a blanca, and the fastest run is
now semicorcheas. Nothing is re-timed and nothing is reordered — the piece you hear is the same
piece.

The notes do shift horizontally, and that is expected: a run that becomes beamed closes up, because
a beam carries the eye across a group and the space between the noteheads stops doing any work. What
must not happen is a **rename in one stretch of the piece disturbing another stretch** — that is what
step 8 is for.

### 7. Change one note

Click a notehead. The **note toolbox** opens beside it. Choose a figure and that one note is drawn
differently. Nothing else on the page moves, and **Undo this one** puts it back.

Try it on a note inside a beamed run and call it a **negra**. The beam splits in two around it — a
negra cannot be under a beam, so the grouping follows the name. That is the rule you want: the page
never shows a beam over a note that does not belong in one.

### 7b. Break a long beam

Scroll to the two long left-hand runs at the end. Each is one beam of sixteen notes: flat, far above
the staff, with every stem stretched up to reach it. It says nothing about the shape of the music.

1. Click the **ninth note** of the corchea run — the highest one, where the line turns and starts
   coming back down.
2. Press **Break the beam here**.

The run becomes two beams, one rising into the turn and one falling out of it, each following the
notes underneath it. Do the same on the semicorchea run and the second beam level survives intact.

Press it again on the same note to **Join the beam again**.

Nothing about the music changes — no note is renamed, nothing moves in time. This is only how the
page is grouped, and it is the one grouping decision the app cannot make for you: where a long run
stops being one gesture is something you hear, not something in the timings.

One case it *does* make for you: a run that comes back down to its own bottom note is already split
there automatically, because a figure returning to where it started is two figures. You only need to
say where that is not the answer.

### 7c. Keep your reading

Everything you have done since step 3 — which pile is the beat, the notes you renamed, the beams you
broke — is yours, and none of it is in the recording. Press **Save this rhythm with the piece** on
the floating bar over the sheet.

Reload the browser and open **Rhythm** again on the same piece. The anchor, the renamed notes and the
beam breaks should all be back, and the line under the button should say when you last saved.

Transcribing the piece again clears it on purpose: a saved reading is a set of column numbers over
the notes that were there before, and a new transcription is a different set of notes.

### 8. If the piece changes speed

Some pieces slow down or speed up halfway through. Under **Does the piece change speed?**:

1. Drag across the column numbers above the staves at the point where it changes.
2. Type what a gap is worth in milliseconds from there on.
3. Press **Add the change**, then **Write the sheet** again.

The list then shows both stretches, for example *From the start: negra = 480 ms · ≈125 BPM* and
*From column 144: negra = 960 ms · ≈63 BPM*.

Only the second stretch is renamed, and **nothing before the boundary moves by a pixel**. That is the
one thing worth testing hard: correcting the end of a piece must not make you re-read the beginning.
**Remove all changes** puts the piece back to one speed.

### 9. Change the time resolution

Go back to **Upload / Input**, set **Time resolution** to *20 ms — fine*, and walk through steps 2
to 4 again on the same piece.

The bars in the plot should sit in the same places, because they are measured from the playing and
not from the grid. The sheet is drawn on a finer grid, and the figures do not change.

### 10. The other demo piece

Repeat steps 1 to 3 with **even-and-swung**, and name the **240 ms** bar a corchea.

This one is the plot's own test. It plays a straight run and then the same notes shuffled, so there
are three bars: **240 ms** for the straight run, and **302** and **178** for the long and short
halves of the shuffle, whose lengths add up to one beat.

Both halves of the shuffle should print as **corcheas** — a row of even eighths, which is exactly
what a printed sheet of a swung piece shows and what a player expects to read. The old app wrote that
as a mix of dotted eighths and sixteenths, which is the ugliness this refactor exists to remove.

---

## Added after the original walk

Everything below arrived between 2026-08-08 and the close of the plan. Try it on a real recording
rather than a demo piece — all of it exists because of something that went wrong on one.

### 11. Selecting, and the two toolboxes

There are two ways to pick something on the sheet, and each opens its own panel **beside what you
picked**. Both panels can be dragged, and once dragged they stay where you put them.

- **Drag a rubber band across the staves**, or **Command-click** noteheads one at a time → the
  **note toolbox**. Every control in it applies to the whole set.
- **Shift-drag across the column numbers** above the staves → the **frames toolbox**, which is about
  a *stretch of time* rather than about notes.

A stretch that carries an edit draws **two corner marks in its own colour**, so you can see it
without selecting it. Click a corner to open that stretch again; each edit it holds has its own
**Remove**.

### 12. What you can say about notes

Pick some noteheads and try each of these:

- **Figure** — name every chord in the selection at once. Pick a whole ragged passage, choose one
  name, and it is written evenly. Nothing moves in time: a column is a slice of wall clock and a
  figure is only a label, so renaming forty chords leaves every onset exactly where it was. A
  tresillo you rename this way loses its `3`, on purpose — the name says "draw it as this" and the
  bracket says the opposite.
- **Fingering 1–5** — one number on every note picked. On a single chord, several numbers are read
  low to high against the noteheads low to high and print stacked in that order.
- **Play it with the other hand** — the split is worked out by an algorithm that cannot see your
  hands, and you can see at a glance where it is wrong. **This one is worth testing carefully:**
  moving a note between hands also changes what its old and new neighbours are called, because a
  note's printed length is the gap to the next onset in the same hand. Check the two notes either
  side of the one you moved.
- **Start a new beam here** — refused unless the whole chord is picked, because a beam holds every
  note of a chord.
- **Take it off the page** — for a note the transcriber invented out of a pedal blur. The neighbour
  is lengthened to cover it, which is the point.

Move the chords an octave bracket was over to the other staff, and the bracket should **disappear**
rather than stretch across an empty staff. Undo the move and it comes back — nothing was deleted,
it just stopped being about anything.

### 13. Keys and octaves

- **Key signature**, beside the sheet: the app measures a suggestion from the notes and you accept
  or change it. A transcription has no key, so everything used to print in C — on one real piece
  that was 242 accidentals that did not need to be there.
- A stretch can have **its own key**, set from the frames toolbox.
- **Octave brackets** are in the note toolbox: four chips per hand over any stretch you mark.
  Nothing suggests them any more. A page you have not touched should carry **no** `8va`, `8vb`,
  `15ma` or `15mb` at all.

Known gap: a key change part-way through a piece can be drawn but is not stored.

### 14. Saving, and starting over

The **Save this rhythm with the piece** and **Remove all** buttons sit on a small bar that **floats
over the sheet** and follows you down the page; drag it by its grip, put it away, bring it back.
Before this, a long piece went unsaved simply because the button was past every stave.

**Remove all** clears every editorial decision — the key and its changes, the speed changes, renamed
figures, beam breaks, octave brackets, hidden notes, hand moves and fingerings — and forgets the
reading saved with the piece, so a reload does not bring it back. It takes two presses and disarms
itself.

### 15. Put it on paper

Press **PDF** on the floating bar. A panel opens with the paper size, the margins, a title and a
preview of the actual pages.

- The preview is not a picture of the file. It is the same drawing the file is written from, so what
  you approve and what you download cannot drift apart.
- The music **re-wraps to the page**, the way it re-wraps to a narrower window. That makes the
  margin the control that decides how much music a line holds — on a 4:52 piece, 5 mm gives 11
  pages, 14 mm gives 12, 35 mm gives 17, and nothing changes size at any of them.
- Expect about **five lines to a page**, four on page one because it carries the title.
- The file is vector, not a photograph: sharp at any zoom, and the music font travels with it, so it
  looks the same anywhere.

What to check: nothing outside the margins on any page, no two lines touching, and the dashed guides
still there — they stay on paper on purpose.

---

## What is still not built

| | State |
|---|---|
| Shifting **one stretch** a step longer, rather than the whole piece | Not built. The buttons in step 6 move every stretch together, because the score request carries one figure name for all of them. |
| A **key change** part-way through a piece | Drawn but not stored. The package can draw one; nothing saves it. |
| Piano roll, falling notes, editing a cell by hand, matrix import/export | Deleted with the tempo model (P4.2) and not rebuilt. |

## What was removed

The Playground had seven tabs and now has two, **Upload / Input** and **Rhythm**. The five that went
were **Matrix**, **Piano Roll**, **Notes Falling**, **Notes Falling (raw)** and **Music Notation**.
All five asked for a tempo and a note resolution and drew from a grid built out of them, which is
the model this refactor replaces, so they could not be kept once that code was deleted (P4.2).

Stated plainly: there is no piano-roll view of a transcription, no falling-notes view, no way to edit
a cell by hand, and no matrix JSON import or export. The two entry points that produced a matrix
without a recording, **Text notation** and **Matrix JSON**, are gone from Upload / Input for the same
reason: a sheet is written from the recorded onsets, and neither of those had any.

Bringing any of them back on the wall-clock path is a feature request for the next plan, not
unfinished work from this one.
