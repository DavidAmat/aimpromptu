# Task 11.2.1 — Playing the passage again, slower

> **Rewritten 2026-08-12 for the wall-clock model.** The old version measured everything in beats at
> a track BPM and a recording BPM. Neither exists. See
> [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

## Subtask 11.2.1.1 — Speed choice

Four options, and the window length in seconds is shown beside them:

- **Original speed** — the take should last about as long as the window.
- **2 times slower**, **4 times slower** — the take should last twice or four times the window.
- **Fit to the window** — no promise made in advance; the scale factor is measured from the take
  when it is finished.

The factor is a property of the take, not of the piece. Nothing about it is stored on the piece
after accept, because the take has already been scaled into place.

## Subtask 11.2.1.2 — Hearing what you have to replace

Before recording, play the marked window of the original audio, at normal speed or slowed by the
same factor, so the player hears the passage at the speed they are about to play it.

## Subtask 11.2.1.3 — The click track

Optional, and it is a sound only. If the piece has a saved rhythm, the clicks follow that passage's
ladder: a negra of 480 ms means a click every 480 ms, multiplied by the slowdown factor — 960 ms at
half speed. If the piece has no saved rhythm the user sets the click interval in milliseconds.

Nothing about the click track is recorded, stored or used by the splice. It exists so a player can
keep an even hand while playing slowly. This is not a BPM returning through a side door: no figure,
no column and no printed value is derived from it.

## Subtask 11.2.1.4 — Stopping and trimming

The user stops the recording manually and may overrun. The expected length is
`windowSeconds * factor`; the take is trimmed to it, from its **first onset**, not from the moment
recording started, so a slow start does not shift the whole passage. The untrimmed audio stays in
the session so the user can extend the trim rather than record again.

With **Fit to the window** there is nothing to trim to: the take runs from its first onset to the
end of its last note, and that length gives the factor.

## Subtask 11.2.1.5 — There is no capture granularity

The old plan let the user record at a finer granularity and collapse it afterwards. That concept is
gone. The take is transcribed to raw events in seconds like everything else, and `frameMs` is only
the clock you look at it on. If a fast passage needs a finer look, change the view, not the capture.

## Acceptance

Manual trial: mark a 3-second window, choose 2 times slower, play with the click track, stop late,
and see the take trimmed to 6 seconds from its first note.
