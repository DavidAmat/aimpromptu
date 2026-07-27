# Task 12.1.1 — Lyrics annotations

Expect UI trial-and-error here; keep the loop tight.

## Subtask 12.1.1.1 — Authoring flow

A Song Lyrics section in the Playground (natural home: Piano Roll view): select a time-frame range, optionally listen to the original audio of that range, type the lyric line. The text spans a div sized to the selected range length; multi-line and smaller text sizes allowed for long lines.

## Subtask 12.1.1.2 — Iterate with render

A render button shows the selected passage's notation with the lyrics below it, so the user iterates (shorter range, shorter text, multi-line…) until it reads well.

## Subtask 12.1.1.3 — Storage and rendering

Stored in the version's `metadata.json` (frame-range -> text). Score builder converts to VexFlow text annotations positioned by frame (the existing time-frame-indexed lyrics rendering is the base); wraps with the sheet.

## Acceptance

Manual trial: two lyric lines over a verse, surviving window resize and visible/hided by the performance-view toggle.
