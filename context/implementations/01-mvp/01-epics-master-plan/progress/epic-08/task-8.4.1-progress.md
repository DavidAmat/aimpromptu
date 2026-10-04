# Task 8.4.1 — Notes Falling · progress

Status: **done and browser-verified** on 2026-07-27.

## Delivered

The falling view renders only notes whose rectangles intersect the visible future window.
Horizontal geometry comes directly from `keyPositions.ts`; fall velocity is plot height divided
by an eight-beat window derived from BPM and granularity. A note's lower tip reaches the keyboard
at its onset. The plot clips everything below the landing line, producing the swallow effect,
while the pressed key and rectangle use the light-blue active state.

Spanish names are rotated inside the rectangles, and the view shares every player control with
Piano Roll.

## Verification and manual trial

The five-note staircase landed C4 through G4, C4 highlighted at time zero, playback advanced
without console errors, and only six current rectangles were mounted. Run the real scale and
listen for each landing to coincide exactly with its onset.
