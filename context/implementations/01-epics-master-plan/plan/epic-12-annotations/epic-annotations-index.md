# Epic 12 — Annotations (nice to have)

> **Rewritten 2026-08-12 for the wall-clock model.** One of the three tasks shipped during the
> refactor. See [`../wall-clock-rewrite.md`](../wall-clock-rewrite.md).

Marks on top of the drawn sheet: lyrics, finger numbers, cue-size notes and grace notes. None of
them touches the recording. They live with the other editorial decisions in `rhythm.json`, keyed by
frame, and they have to survive the sheet re-wrapping to a narrower window, the compression of
silence (D-23) and the printed page (P8.7).

Read first: [`../wall-clock-rewrite.md`](../wall-clock-rewrite.md), then `project-features.md`
sections "Song Lyrics", "Piano Finger numbers" and "Cue-sized notes and Fioritura".

## Story 12.1 — Lyrics

- Task 12.1.1 lyrics: mark a stretch of the sheet, write the line, iterate until it reads well.

## Story 12.2 — Fingering and small notes

- Task 12.2.1 finger numbers: **shipped in P8.1.** What remains is the text size and the toggle.
- Task 12.2.2 small notes: cue-size a marked stretch; acciaccatura and appoggiatura marks.

## Exit criteria

Manual trial: a piece shows lyrics under the staff and fingering over a hard passage, both survive a
window resize and a PDF export, and both can be hidden in the performance view.
