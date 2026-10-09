# Editing a piece: re-record, compose, and paste

Three ways a recording changes after it has been transcribed. Re-record and compose share one
session model and differ in exactly one thing: whether the piece is allowed to get longer. Paste
(implementation 02, Phase 8) is the third, and it uses the same rule as compose: everything after
the insertion point moves.

## Re-record a passage — the length never changes

You mark a stretch of the sheet, play it again at any speed you like, look at a preview of it fitted
into that same stretch, and accept or cancel.

**A re-recorded passage is written back into exactly the window it replaces.** Mark three seconds,
play the passage over twelve, and the take is scaled back into those three seconds on accept.

The column count therefore never changes, and that one property buys everything else: the recording
still lines up with the page, the playhead still lands where it did, and every passage boundary, key
change, renamed figure, beam break and fingering **after** the edited window keeps working without
renumbering.

It is the same property a ladder change has (D-21) — correcting the end of a piece must never make a
reader re-read the beginning.

The underlying operation is a plain splice of a span of columns and it does not care about length.
Fewer columns and more columns are both possible. **Range editing does not offer them, on purpose.**

### What it costs

Marks anchored **inside** the replaced window are dropped, because the notes they were about are not
there any more. The count is reported by kind before the button is pressed, because a fingering that
has silently gone looks exactly like one that was never there.

## Compose a piece — length may change

**Compose** on Upload / Input starts a piece with nothing in it: an empty `notes.pmn`, a column
length, and no audio file at all. The first accepted passage is what creates a recording.

**Add a passage** on Piano Sheet is the stage. Play, cut the recording the way Input does, read that
stretch, look at the passage **on its own** with its own peak plot, play it again as often as you
like. Nothing is written until **Put it in the piece**.

Three placements:

- **Append** — after the last note, at a silence you choose in seconds. Moves nothing.
- **Insert at a moment** — everything from that column on moves later by the passage's length.
  Notes and editorial marks in the same write, and you are told how many of each and by how many
  columns before you press the button.
- **Replace** — the re-record splice above, unchanged.

This is allowed here for the reason the restriction existed everywhere else: when you are composing
there is nothing after the insertion point to protect — or when there is, moving it is precisely
what you asked for.

### The rule that makes an insertion exact

**A passage occupies a whole number of columns.** Its length is rounded up to the next frame before
anything is written, so every column after the insertion point moves by the same integer and a mark
lands on the column it was shifted to rather than one either side. The cost is at most one frame of
silence at the join — 40 ms.

Membership is decided by **column** rather than by onset in seconds, which is the one place
composing departs from the replacement splice. It was found on a real engine run: a note whose onset
is a few milliseconds before the moment but which rounds into that same column would be stranded
inside the new passage, visibly in the middle of the new music, with its fingering gone on ahead
without it.

Since implementation 02, Phase 8 the take goes into the part's **audio timeline** as one more file
(a range of the axis, like a pasted passage), instead of the whole part being written again as one
16 kHz file: the files already there keep their own quality, and the notes stay current with the
audio.

## Paste a passage — length changes, notes, marks and audio together

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
- **everything after** moves by the passage's length, which is a whole number of columns.

The source can be any part the user may read: their own work, their library, a library shared with
them, the Public Library. A stretch pasted over is taken out first: its notes and marks go, and its
audio becomes cuts that the Audio step can restore.

**Undo is exact.** The paste keeps the part as it was (notes, sheet, timeline, the names of its
files) as an earlier state of its history first. Undo puts that state back, keeping the pasted one,
which redo puts back.

## The preview always draws the passage, not the page

While re-recording, the preview shows the take fitted into the window, so you can compare it against
what was there.

While composing there is no window to fit into and nothing to compare against, so the preview draws
the passage **alone**. What you are deciding is whether this is the passage you meant to play; the
piece it is going into answers a different question, on the sheet, after it is accepted.

## Playing along

The original window can be played back slowed with the pitch preserved, and a metronome can click
while you record. Clicks every X milliseconds are a **sound in the player's ears** and nothing
derived from them is stored — there is still no BPM anywhere.

## History

Accepting snapshots the previous `notes.pmn`, `sheet.json` and `timeline.json` (and since Phase 8
the part's entry of `project.json`, the names of its files) into
`.database/history/<projectId>/parts/<partId>/v<N>/` and advances a version counter. A version here
means *the music changed*. A paste snapshots the same way, and its undo restores the snapshot. Since implementation 02, Phase 3 the new recording is a new file of the
audio store and the timeline points at it, so the snapshot never copies audio.

If the audio splice fails, the window is recorded as not matching the sheet rather than failing the
edit: the notes were written correctly and only the sound is behind, so saying so is more useful
than rolling back a correct result.

## Every mark moves

One module, `editing/marks.py`, lists every mark of `sheet.json` by the column or the range it is
keyed by, and moves, cuts out and copies them. A composed passage widens a range it lands inside; a
pasted one tears it (it ends where the passage starts, and goes on after it), because the pasted
music is not part of it. Before Phase 8 the clef changes, the beam joins, the spacings and the
staff gaps did not move on an insert.

## Where to look deeper

- [`documentation/services/backend/editing-and-compose.md`](../../documentation/services/backend/editing-and-compose.md)
  — the modules, the routes and every rule, copy and paste included
- [`documentation/services/backend/rhythm-and-annotations.md`](../../documentation/services/backend/rhythm-and-annotations.md)
  — the marks that are dropped or moved
- [time-model.md](time-model.md) — why the length rule matters
