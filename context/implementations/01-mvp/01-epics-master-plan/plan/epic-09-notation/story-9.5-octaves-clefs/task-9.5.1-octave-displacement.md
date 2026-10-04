# Task 9.5.1 — Octave displacement and clef switching

Applied after the hand-split (which for now is the simple C4 threshold).

## Subtask 9.5.1.1 — Thresholds

Configurable per hand, stored in version metadata:

- very low notes (either hand on bass clef): below threshold-1 -> 8vb; below threshold-2 -> 15mb
- high notes (right hand): above threshold-1 -> 8va; above threshold-2 -> 15ma

## Subtask 9.5.1.2 — Left-hand rule

Avoid 8va/15ma in the left hand. For left-hand passages above its high threshold, switch that passage to a small treble clef instead (temporary clef change directive in the score format), keeping notation readable.

## Subtask 9.5.1.3 — Rendering

Score builder emits ottava/clef-change directives grouped over passages (not per note); frontend maps them to VexFlow ottava brackets and clef changes.

## Acceptance

Tests with synthetic extreme-register passages produce the expected directives per hand.
