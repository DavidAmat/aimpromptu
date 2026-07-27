# Epic 12 — Annotations (nice to have)

Metadata overlays on top of the rendered score: song lyrics, piano finger numbers, and small/grace notes. Annotations live in the version's `metadata.json` annotations block (matrix-index terminology from Task 1.3.2) and never modify the piano matrix. Rendering must survive responsive rewrap — no fixed positions.

Read first: `project-features.md` sections "Song Lyrics", "Piano Finger numbers", "Cue-sized notes and Fioritura…"; the existing lyrics support in the current renderer (`documentation/services/frontend/piano-sheet.md`).

## Story 12.1 — Lyrics

- Task 12.1.1 lyrics annotations: select a time-frame range, write the lyric line, iterate with passage renders; stored per version.

## Story 12.2 — Fingering and small notes

- Task 12.2.1 finger numbers: per-note finger annotations (1–5, chord stacks like "2/4/5"), tunable text size.
- Task 12.2.2 small notes: user-designated cue-size passages and acciaccatura/appoggiatura marks.

## Exit criteria

Manual trial: a promoted song shows lyrics under the staff and fingers over a tricky passage, both toggleable in the performance view and stable across window resizes.
