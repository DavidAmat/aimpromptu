# Task 9.7.2 — Trills and chord grouping (nice to have)

The "render as simple and clean as possible" rules.

## Subtask 9.7.2.1 — Chord grouping threshold

Notes within the same temporal window are a chord; a slightly arpeggiated chord still renders as a single chord (no arpeggio symbol — arpeggio ornaments are ignored entirely). A finer sub-threshold decides "truly simultaneous"; beyond it, notes stay independent events.

## Subtask 9.7.2.2 — Trill detection

Detect two notes alternating continuously at high speed and render as "tr" over the base note instead of the literal note storm. Caution documented in `project-features.md`: at the finest granularity a very fast trill may be undersampled (C D C D sampled as C C D C…); prefer detecting trills from raw NoteEvents (pre-matrix, inside Epic 4's events pipeline) and storing the trill as an annotation (hand, column range) rather than trusting the matrix sampling.

## Subtask 9.7.2.3 — Other ornaments

All other ornaments are ignored by design — performers interpret them; they cannot be reliably inferred from audio.

## Acceptance

Manual trial: record a trill and a rolled chord; sheet shows "tr" and a single chord respectively.
