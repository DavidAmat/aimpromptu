# Task 9.4.2 — Transposition

## Subtask 9.4.2.1 — Operation

UI over Task 2.4.2 transposition (matrix row shift up/down by semitones), available during the audio-to-matrix flow — useful when the recording itself is transposed and hard to match to the original key.

## Subtask 9.4.2.2 — Section preview

Before committing: pick a short time range, render it as notation at the candidate transposition (fast path — only that slice through the score builder), so the user verifies detected key, BPM and granularity fit the audio. Accept applies the shift to the working matrix; cancel discards.

## Acceptance

Manual trial: transcribe a piece, preview +2 semitones on a 5-second slice, accept, verify the full score shifted.
