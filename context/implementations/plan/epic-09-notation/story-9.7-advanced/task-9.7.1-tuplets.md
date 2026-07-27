# Task 9.7.1 — Tuplets (nice to have, end of project)

Manual-only feature. The user selects a passage in the Playground and groups its notes as a tuplet (3, 5, 6, 7, 8…).

## Subtask 9.7.1.1 — Selection and grouping

From a selected time-frame range, group the contained notes of one hand as an N-tuplet. Typical use: fast notes wrongly rendered as a chord, or as thirty-seconds with rests in between, become a readable triplet.

## Subtask 9.7.1.2 — Render-only semantics

The underlying matrix never changes. The tuplet lives in the annotations block (hand, column range, N); the score builder replaces that range's literal rendering — dropping the artificial rests, spacing notes as the tuplet subdivision — and emits a VexFlow tuplet directive.

## Subtask 9.7.1.3 — Removal

Deleting the annotation restores literal rendering.

## Acceptance

Manual trial: a fast three-note run at fusa granularity rendered as a clean triplet, matrix bit-identical before/after.
