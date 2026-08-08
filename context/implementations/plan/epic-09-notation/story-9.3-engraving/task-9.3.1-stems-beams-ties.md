# Task 9.3.1 — Stems, beams and ties

Engraving rules inside the backend score builder (with VexFlow directives on the wire).

## Subtask 9.3.1.1 — Stem direction

- Single note: below the middle staff line -> stem up; above -> down; on the line -> contextual choice.
- Beamed group: one direction for the whole group, chosen by the group's average pitch (visual center of gravity).
- Polyphony (two voices in one hand): upper voice stems up, lower voice stems down — overrides pitch rules.

## Subtask 9.3.1.2 — Beaming

- Beam maximal runs of ≥2 consecutive same-duration beamable notes (corchea and shorter); keep the existing "lone eighth keeps its flag" behavior.
- Arpeggiated-accompaniment break: when a note X has a higher previous note and a higher following note inside an arpeggiated pattern, break the beam at X and start a new one — clearer harmonic/rhythmic groups.

## Subtask 9.3.1.3 — No-tie policy

We do not want ties. Never repeat a pitch merely to connect it to the previous measure.

Within each hand's measure:

- keep a leading rest before its first onset, so delayed entrances align across hands;
- sustain every note/chord to the next onset instead of drawing an interior rest;
- give all notes struck as one chord that shared duration, even if the matrix releases some early;
- expand the final event toward the barline using one legal figure;
- if a small unwritable remainder is at the measure end, draw a trailing rest;
- if that remainder is between onsets, emit an invisible timing spacer, not a rest glyph.

At a barline, let the preceding event fill to the barline. If the next onset is later, begin the
following measure with a visible rest. `tieToNext` remains in the transport format for compatibility
but the builder always sets it to false.

## Acceptance

Golden/tests per rule; manual trial with an Alberti-bass-style accompaniment checking the beam
break, a sparse melody with no middle rests, and a chord whose recorded releases differ.
