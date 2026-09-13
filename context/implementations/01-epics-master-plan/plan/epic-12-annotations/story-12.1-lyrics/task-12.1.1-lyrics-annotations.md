# Task 12.1.1 — Lyrics

> **Rewritten 2026-08-12 for the wall-clock model.** The authoring home changed and the storage
> changed. See [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

Expect trial and error in the UI here; keep the loop short.

## Subtask 12.1.1.1 — Writing a line

The natural home is the Rhythm tab, on the sheet itself: mark a stretch of columns the way you
already do for a passage or a group rename, play that stretch of the recording to hear the words,
and type the line. The line is drawn under the staff across the marked stretch. Long lines may wrap
to a second line or use a smaller size.

The Piano Roll can offer the same thing over its own selection, since both views select the same
frames.

## Subtask 12.1.1.2 — Iterating

Nothing to render separately: the sheet is already showing the passage, so the text appears as it is
typed and the user shortens the range or the words until it reads well.

## Subtask 12.1.1.3 — Storage and drawing

In `rhythm.json` beside the other editorial marks, keyed by frame range and hand-independent. The
package draws the text under the staff of the frame range, and it must behave when that range is
partly compressed silence: a lyric over a long rest keeps its start, and it never widens the
layout — the sheet's spacing comes from the notes (D-22, D-23), never from an annotation.

**Remove all** clears lyrics with everything else, and the count in its confirmation includes them.

## Acceptance

Manual trial: two lines over a verse, still correct after resizing the window and after a PDF
export, and cleared by **Remove all**.
