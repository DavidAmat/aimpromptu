# Task 8.4.1 — Notes falling view

`/playground/notes-falling`: Synthesia-style. Same playback engine and filters as the roll view; different geometry.

## Subtask 8.4.1.1 — Geometry

- Piano SVG horizontal at the bottom of the surrounding div; its top bar is Y=0 in the plot's coordinate system.
- Vertical rectangles fall from the top; rectangle X and width calibrated per key from `keyPositions.ts` (black keys narrower).
- Note name (ES: `Do`, `Do-#`, `Re-b`…) printed inside each rectangle, rotated 90 degrees.
- Falling rectangles are light gray; at Y=0 the rectangle turns light blue, the key highlights, and the part below Y=0 is clipped — the piano "swallows" the rectangle.

## Subtask 8.4.1.2 — Velocity and windowing

Fall velocity derived from plot height, BPM and granularity so a note whose onset is at time T touches Y=0 exactly at T (e.g. a note due at 02:00 appears at the top ~10 s earlier and falls for 10 s). Only render rectangles inside the visible time window — never the whole melody at once; new ones enter from the top as time progresses.

## Subtask 8.4.1.3 — Shared options

Same toolbar as the roll view (speed, BPM, granularity, range, sound source, pause/seek). Two-hands colors as elsewhere.

## Acceptance

Manual trial: play a scale; every rectangle lands on its key exactly when it sounds.
