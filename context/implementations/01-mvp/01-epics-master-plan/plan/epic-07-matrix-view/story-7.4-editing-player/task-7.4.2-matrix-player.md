# Task 7.4.2 — Matrix player (nice to have)

Play the matrix as sound with a running cursor.

## Subtask 7.4.2.1 — Playback

A cursor highlights the current row and advances at the real row duration (`timeStepSeconds`). On each row: trigger tones for `1` cells; keep `-1` cells sounding at damped amplitude.

## Subtask 7.4.2.2 — Sound source

Reuse the piano tone sampler built in Task 8.3.1 (per-key samples or synthesized fallback). Do not build a second audio engine.

## Acceptance

Manual trial: play a transcribed scale; the heard notes match the circles as the cursor passes.
