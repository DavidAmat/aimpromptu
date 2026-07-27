# Epic 9 — Music notation

Turning clean/two-hands matrices into responsive HTML sheet music with VexFlow. The backend digests matrices + annotation metadata into a VexFlow-ready score format (frontend stays thin); the frontend renders staves that rewrap with browser width. This epic also carries the music-specific engraving rules from `project-features.md`.

Read first: `project-features.md` sections "Music notation", "Music Specifics", "Tempo", "Right and Left Alignment", "Metadata", "Backend ease the task for Frontend"; existing code `PianoSheet.tsx`, `matrixToNotation.ts` (the working MVP to evolve, not discard); `documentation/services/frontend/piano-sheet.md`.

## Story 9.1 — Score format

- Task 9.1.1 vexflow score format: backend translation matrix -> measures/voices/durations/chords/rests + annotation overlay format; the frontend only draws.

## Story 9.2 — Notation tab

- Task 9.2.1 notation tab ui: artifact picker, grand-staff or single-hand render, responsive wrapping, save-annotations and promote-to-library buttons.

## Story 9.3 — Engraving rules

- Task 9.3.1 stems, beams and ties: stem direction rules, beam grouping with arpeggio beam-break, ties only across barlines.

## Story 9.4 — Keys and transposition

- Task 9.4.1 key signatures and naturals: initial key choice, per-passage/per-measure key changes, minimal-accidental suggestion, naturals over double accidentals.
- Task 9.4.2 transposition: matrix row shift with short-range render preview.

## Story 9.5 — Octaves and clefs

- Task 9.5.1 octave displacement: 8va/8vb/15ma/15mb by configurable per-hand thresholds; left hand prefers a temporary treble clef over 8va.

## Story 9.6 — Tempo guides and measure ops

- Task 9.6.1 beat guides and cut-measure: dashed beat lines with frame numbers; "Cut measure up to here" inserting silence columns.

## Story 9.7 — Advanced ornaments (nice to have, end of project)

- Task 9.7.1 tuplets: manual tuplet grouping over a selected passage (render-only, matrix untouched).
- Task 9.7.2 trills and chord grouping: trill ("tr") detection of fast alternations; near-simultaneous notes as chords (no arpeggio symbols).

## Exit criteria

Manual trial ladder (simplest first): single negra scale one hand -> chords -> two hands aligned -> dotted durations -> key signature with accidentals. Each rung verified against how a human would engrave it.
