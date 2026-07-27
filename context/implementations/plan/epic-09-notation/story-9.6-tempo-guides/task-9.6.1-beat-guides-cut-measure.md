# Task 9.6.1 — Beat guides and cut-measure

## Subtask 9.6.1.1 — Beat guides

Subtle gray dashed vertical lines at every beat (e.g. one per second at 60 BPM), traversing both treble and bass staves so hand alignment is visible. Time-frame numbers rendered at the top of the dashed lines. Toggleable. Must survive responsive rewrap (positions derive from the score layout, never absolute px).

## Subtask 9.6.1.2 — Cut measure up to here

User places the cursor on a beat guide inside a measure and picks "Cut measure up to here": the following note is pushed to the start of a new measure and the remaining tempo fills with silences. Under the hood this is Task 2.4.2 tempo insertion — add silence columns at that frame (addition unit at least the piece granularity). Example: 4/4 measure Do Re Mi Fa in negras, cut at Mi -> Fa becomes the next measure's first note.

## Subtask 9.6.1.3 — Re-render

After the matrix change, re-run score generation for the artifact and refresh; the user sees the new barring immediately.

## Acceptance

Manual trial of exactly the Do-Re-Mi-Fa example from `project-features.md`.
