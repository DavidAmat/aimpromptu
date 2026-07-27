# Task 12.2.1 — Finger numbers

## Subtask 12.2.1.1 — Authoring

Primary flow in the Piano Roll view: select a time-frame range, click a note rectangle, type the finger number (1–5). Chords accept stacked multi-finger values rendered on separate lines (e.g. "2" over "4" over "5"). Stretch goal: clicking a note directly on the rendered sheet (harder; do second).

## Subtask 12.2.1.2 — Storage and rendering

Stored per (hand, column, row) in the annotations block. Score builder emits VexFlow fingering annotations above/below the note; annotation text size tunable per piece.

## Acceptance

Manual trial: finger a 5-note passage plus one chord with "1/4"-style stacking; toggle off in performance view.
