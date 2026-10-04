# Piano Roll and Notes Falling, back on the wall clock

**Commit `5cd4d77`, 2026-08-10.** Reported 2026-09-13 by Task 14.1.1.3.

## Why

Both views were deleted with the tempo model in P4.2, because they drew a matrix built from a BPM
and a note resolution. **The layout was never the problem** — it was the best look the project had
ever had at a transcription, and losing it meant losing the only way to check what the model heard
before committing to reading it.

So they are restored from Epic 8 and given a source that exists: `GET /matrix/{id}/events`, the
notes in the engine's own seconds.

## What changed in the views

- **A rectangle is as long as the note was actually held**, not a whole number of beat
  subdivisions. Two notes 30 ms apart are drawn 30 ms apart.
- **The roll's guides are seconds with a clock time on them.** There is no frame number anywhere,
  and no BPM or Resolution control in the toolbar.
- **The falling window is a lead time in seconds** that the reader chooses, where it used to be
  eight beats converted through the piece's tempo.
- **The notes the artifact filter throws away are drawn on request**, dashed, and are never sounded
  — so the filter can be checked instead of taken on trust.

## Two faults from Epic 8, fixed rather than restored

**The vertical keyboard turned the wrong way.** It turned clockwise, which put the treble at the
bottom of the roll and the key fronts facing away from the notes. It now turns the other way, and
`laneTop` is the single place that flip lives.

**`height="auto"` was set as an SVG attribute**, which is not a length, so every falling view logged
an error. It is a style now.

## Backend

`RawNoteEvent` gains a `hand`, filled from the standard split at `frameMs` so the colours agree with
the sheet.

It is **a label and nothing else**: the start and end times are untouched, a manual hand correction
still wins, and a split that fails leaves the notes uncoloured rather than failing the request.

## Dropped on purpose

**Dragging a rectangle to another key.** It saved a matrix cell edit through an endpoint that no
longer exists, and its successor is correcting the *hand*, which is written onto the recording.

## Verified

In a browser, against a real recording: 2643 notes on both views, hands split 1490 right and 1149
left, the keyboard highlight aligned with the cursor, and the Rhythm tab unchanged. Backend suite
green.

## What this changed downstream

`user-reviews.md` and `CLOSURE.md` both said, in so many words, that there is no piano-roll view and
no falling-notes view. That stopped being true on the day this landed and stayed wrong in those two
documents for a month. Both are corrected as of 2026-09-13.
