# Task 7.4.1 — Cell editing (nice to have)

Direct note editing in the grid, backed by the Task 2.4.2 primitives.

## Subtask 7.4.1.1 — Palette and placement

An edit-mode toggle with a small palette (onset, sustain). Click an empty grid point to place; placement rules enforced live: a `-1` only allowed under a `1` or an existing `-1` of the same key's previous frame.

## Subtask 7.4.1.2 — Selection and deletion

Click selects a circle; shift-click multi-selects. Delete removes selections applying deletion rules (removing a `1` removes its chained `-1`s).

## Subtask 7.4.1.3 — Validate and save

Every edit round-trips through the backend validator; invalid edits rejected with a visible reason. Save writes to the working artifact (and from there the normal version-save flow of Epic 5 applies), so all tabs see the edited matrix.

## Acceptance

Manual trial: add a wrong note to a scale, hear/see it downstream (piano roll or notation), delete it, save.
