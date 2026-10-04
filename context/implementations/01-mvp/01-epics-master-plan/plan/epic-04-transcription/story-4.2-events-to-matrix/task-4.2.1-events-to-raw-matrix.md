# Task 4.2.1 — Note events to raw matrix

`transcription/events_to_matrix.py`: NoteEvents -> raw PianoMatrix, always at fusa granularity first.

## Subtask 4.2.1.1 — Grid construction

Given `tempoBpm` (user input, default 60) and fusa granularity, compute `timeStepSeconds` and total
column count from the selected physical audio item's duration. A persisted segment contains only
its clip, so event and matrix time both begin at zero. Its absolute root-source offset is metadata
for labels and navigation, not matrix arithmetic.

## Subtask 4.2.1.2 — Event placement

- midi_note -> row via `matrix/keys.py` (60 = C4 = `Do-4`); notes outside the 88 keys dropped with a warning.
- Onset column: snap `start` per Task 2.3.2 onset rules. Emit `1`.
- Sustain columns: duration fitted per Task 2.3.2 greedy rules. Emit `-1`s.
- Overlapping events on the same key resolve per the transition rules (a new onset overrides a sustain).

## Subtask 4.2.1.3 — Validation and output

Run the validator in strict mode; persist as the raw artifact (`processing_step = "raw"`, granularity fusa). The raw matrix is the immutable source every recompute starts from.

## Acceptance

Synthetic tests: hand-built NoteEvents for the notation-spec examples reproduce the expected matrices, including the 1.1 s / 0.6 s rounding example from `project-features.md`.
