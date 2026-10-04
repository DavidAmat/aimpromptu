# Task 8.2.1 — Piano roll view layout

`/playground/piano-roll`: static piano, notes laid out horizontally in time.

## Subtask 8.2.1.1 — Layout

- Piano SVG rotated 90 degrees at the leftmost edge; to its right, the note area div.
- Notes are rectangles: left edge = onset, length = sustain duration, right edge = release. One lane per key, aligned with its piano key.
- Dashed vertical lines mark time frames, numbered (frame numbers on the guides).
- Two-hands coloring same as the Matrix tab (Green left, Blue right); one-hand uses the default rectangle color.
- The surrounding div centers vertically and fits the whole piano in the viewport height, with the filter bar still visible; the note area scrolls horizontally to reach any passage (scroll locked while playing).

## Subtask 8.2.1.2 — Same data controls as Matrix tab

Loads the working artifact's matrices; BPM and granularity changeable here too — recompute via the same fast path, artifacts saved back and reloaded.

## Subtask 8.2.1.3 — Waveform watermark

The selected physical audio item's waveform is rendered as a faint background watermark of the
note area, moving with the same horizontal time axis. A persisted segment already owns a truncated
waveform, so the frontend does not slice or offset root-audio peaks.

## Acceptance

Manual trial: a scale renders as stair-stepped rectangles aligned to their piano keys, frame guides numbered correctly.
