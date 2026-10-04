# Task 12.2.1 — Finger numbers

> **Closed 2026-09-13.** The mark size is **Smaller** / **Larger** under the sheet, per piece;
> the performance-view toggle was already there. Fingering from the Piano Roll selection was
> **not built**: the task file said to try the sheet first and only build it if the sheet turned
> out to be slower in use, and nobody has reported that it is. See
> [`../../../progress/epic-12/epic-12-progress.md`](../../../progress/epic-12/epic-12-progress.md).
>
> **Rewritten 2026-08-12: mostly shipped.** See
> [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

**Already done (P8.1).** Click a note on the sheet, the note toolbox opens beside it, and 1 to 5 is
one click. On a chord the numbers stack in notehead order, so the number for the top note is on top.
They are stored with the piece's other editorial marks and printed on the PDF.

## Subtask 12.2.1.1 — What remains

- A text size for annotations, per piece, so fingering does not crowd a dense passage.
- The hide and show toggle in the performance view (Task 10.2.1).
- Fingering from the Piano Roll selection, if that turns out to be a faster way to finger a long
  run than clicking noteheads one at a time. Try the sheet first; only build this if the sheet is
  actually slower in use.

## Acceptance

Manual trial: finger a five-note run and one chord, make the numbers smaller, hide them in the
performance view and show them again.
