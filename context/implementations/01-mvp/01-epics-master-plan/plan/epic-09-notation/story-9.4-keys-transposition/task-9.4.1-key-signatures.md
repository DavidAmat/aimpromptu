# Task 9.4.1 — Key signatures and naturals

## Subtask 9.4.1.1 — Initial key

On first transcription-to-score the user must specify the desired key signature (dropdown; VexFlow specs `C`, `G`, `Bb`, …). Stored in the version metadata; accidentals render relative to it (existing `applyAccidentals` behavior).

## Subtask 9.4.1.2 — Passage key changes

User selects a passage (start/end frames) in the Playground and assigns it a different key signature — a visual way to hand-minimize accidentals. Stored as an annotation (column range -> key); the score builder emits key-change directives at the right measures.

## Subtask 9.4.1.3 — Per-measure suggestion

Algorithm: for each measure count the accidentals every candidate key would produce; suggest the minimizer. Surface as a suggestion the user applies per measure — never auto-apply (intentional accidentals like A# in E major are normal and must survive).

## Subtask 9.4.1.4 — Naturals over doubles

Prefer natural signs to double sharps/flats in spelling decisions; overall goal is minimal accidentals for readability.

## Acceptance

Test: an E-major passage keeps its A# under the suggestion; a mis-keyed passage's suggestion reduces accidental count.
