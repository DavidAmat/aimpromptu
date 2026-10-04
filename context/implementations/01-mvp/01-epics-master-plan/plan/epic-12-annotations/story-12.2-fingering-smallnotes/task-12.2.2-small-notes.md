# Task 12.2.2 — Small notes and grace notes

> **Shipped 2026-09-13.** Both halves. The grace-note feature the drawing package was missing
> turned out to be small — cue-size ink and the existing flag glyph, no new font metrics — so
> the sizing this file asked for came back cheap. See
> [`../../../progress/epic-12/epic-12-progress.md`](../../../progress/epic-12/epic-12-progress.md).
>
> **Rewritten 2026-08-12 for the wall-clock model.** See
> [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

## Subtask 12.2.2.1 — Cue-size a stretch

Mark a stretch and print its notes smaller, so a florid passage in one hand takes less width and
stops crowding the other hand. Never inferred; the reader asks for it.

This one has a consequence to check rather than assume: the sheet's spacing is measured from
content, and a beamed run is already set tighter than an unbeamed one (D-33). Smaller noteheads
therefore change the widths inside the marked stretch. That is acceptable inside the mark, and
nothing outside it may move — the same property D-21 protects. Pin it with a test that compares the
x positions before and after.

## Subtask 12.2.2.2 — Acciaccatura and appoggiatura

Click a note, add a grace note before it. It is a mark, not an event: it is not in `events.json`, it
is not played back, and it does not take a column of its own. The package draws the grace group
attached to the note it belongs to.

This needs a feature in `@aimpromptu/grid-notation` — it has no grace-note glyph group today. Size
that before promising the UI.

## Acceptance

Manual trial: a florid right-hand run printed cue-size with the left hand unmoved; one acciaccatura
added and removed cleanly.
