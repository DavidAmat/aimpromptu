# Task 9.3.1 — Stems, beams and ties

Engraving rules inside the backend score builder (with VexFlow directives on the wire).

## Subtask 9.3.1.1 — Stem direction

- Single note: below the middle staff line -> stem up; above -> down; on the line -> contextual choice.
- Beamed group: one direction for the whole group, chosen by the group's average pitch (visual center of gravity).
- Polyphony (two voices in one hand): upper voice stems up, lower voice stems down — overrides pitch rules.

## Subtask 9.3.1.2 — Beaming

- Beam maximal runs of ≥2 consecutive same-duration beamable notes (corchea and shorter); keep the existing "lone eighth keeps its flag" behavior.
- Arpeggiated-accompaniment break: when a note X has a higher previous note and a higher following note inside an arpeggiated pattern, break the beam at X and start a new one — clearer harmonic/rhythmic groups.

## Subtask 9.3.1.3 — Ties policy

We do not want ties, except when a note crosses a barline and must keep sounding into the next measure. Within a measure, choose the single best-fitting duration (Task 2.3.2 already minimizes figures). The measure grid from Task 9.1.1 decides when a span crosses a barline -> emit `tieToNext`.

## Acceptance

Golden tests per rule; manual trial with an Alberti-bass-style accompaniment checking the beam break.
