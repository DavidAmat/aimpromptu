# Task 13.1.1 — Composing live

> **Rewritten 2026-08-12 for the wall-clock model.** See
> [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

## Subtask 13.1.1.1 — An empty piece

Creating a piece writes an empty `events.json` and a `frameMs`. There is no BPM to choose and no
granularity to choose; the only question at creation is the name.

A piece with no events draws an empty pair of staves and no ladder. The ladder arrives with the
first passage, named the usual way from the peak plot.

## Subtask 13.1.1.2 — The passage stage

Reuse the Epic 11 session without a target window: play, transcribe, look at the passage's sheet and
its peak plot, delete and play again as often as you like. The passage is only added to the piece
when the user accepts.

## Subtask 13.1.1.3 — Placing it

Three placements, and this is where the epic differs from Epic 11:

- **Append** — the passage goes after the last note, at a silence the user sets in seconds.
- **Insert at a moment** — the passage is opened at a timestamp, and everything after that moment
  moves later by the passage's length. Allowed here, and stated plainly to the user, because
  inserting is the point.
- **Replace a marked stretch** — exactly Task 11.1.1, length preserved.

Every editorial mark after an insertion point is anchored to a frame, so an insertion moves those
marks by the same number of frames. Do that in the same operation and say how many moved; do not
leave it for the user to notice.

## Subtask 13.1.1.4 — Speed

A passage played slowly is scaled by the factor the user chose, exactly as in Task 11.2.1. With no
target window there is nothing to fit to, so the factor is the whole answer: play at half speed,
choose 2 times slower, and the passage occupies half the time it took to play.

## Acceptance

Manual trial: two passages, one played at half speed, appended one after the other with a
one-second silence between them, and the whole piece read as one sheet with a single named ladder.
