# End-to-end review

One walk, in the app, from a piece to sheet music. Everything below has been opened and checked on
screen first.

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
- The sheet **stops where the playing stops**.

At the end, after the tresillos, the left hand plays two long runs — sixteen corcheas and then
sixteen semicorcheas, climbing two octaves and coming back. Each is **one beam of sixteen**, drawn
flat and far above the staff. That is what step 7b is about.

### 5. Hear it against the sheet

Press **Play the recording** above the staff. What plays is the recording itself, never anything
rebuilt from the page. If the notes you see and the notes you hear drift apart, the page is wrong.

### 6. Change your mind about the whole piece

Go back to step 3, click the **240 ms** bar instead and name that one the negra, then press
**Write the sheet** again.

Every figure moves one step up the ladder: what was a negra is now a blanca, and the fastest run is
now semicorcheas. Nothing is re-timed and nothing is reordered — the piece you hear is the same
piece.

The notes do shift horizontally, and that is expected: a run that becomes beamed closes up, because
a beam carries the eye across a group and the space between the noteheads stops doing any work. What
must not happen is a **rename in one stretch of the piece disturbing another stretch** — that is what
step 8 is for.

### 7. Change one note

Click a notehead. A picker appears under the staff: choose a figure and that one note is drawn
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

## What is not in this walk yet

| Screen | State |
|---|---|
| A marker moving along the staff while the recording plays | not built. The bar under the buttons shows how far through you are. |
| Saving a named rhythm with the piece | not built. Naming it again takes one click. |
| Making the whole piece one step longer or shorter in one go | not built. Renaming the gap in step 3 does the same thing today. |

## What was removed

The Playground had seven tabs and now has two, **Upload / Input** and **Rhythm**. The five that went
were **Matrix**, **Piano Roll**, **Notes Falling**, **Notes Falling (raw)** and **Music Notation**.
All five asked for a tempo and a note resolution and drew from a grid built out of them, which is
the model this refactor replaces, so they could not be kept once that code was deleted (P4.2).

What went with them, stated plainly: there is no piano-roll view of a transcription, no
falling-notes view, no way to edit a cell by hand, and no matrix JSON import or export. The two
entry points that produced a matrix without a recording, **Text notation** and **Matrix JSON**, are
gone from Upload / Input for the same reason: a sheet is written from the recorded onsets, and
neither of those had any.

If one of those views should come back on the wall-clock path, it is worth saying so before Phase 8
rather than after.
