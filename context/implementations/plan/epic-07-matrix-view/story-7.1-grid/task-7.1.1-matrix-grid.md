# Task 7.1.1 — Matrix grid

The core visualization component (`MatrixGrid.tsx`). Reused by every processing step view.

## Subtask 7.1.1.1 — Layout

- Columns: piano keys. Header shows the EN abbreviated name (`C3`) and above it, rotated 90 degrees in smaller type, the Spanish name (`Do 3`), so columns pack densely.
- Rows: time frames, newest downwards. A whole-track row uses `f:0 · 00:00.00` (frame index =
  Python row index). A segment row uses `f:0 · 00:00.00 ↗ 02:14.50`, showing local time followed
  by the corresponding root-audio time. Only the frame start is printed.
- Subtle vertical separator lines between key columns.
- Header row frozen while scrolling (spreadsheet-style); scrolling down always advances time.
- Long pieces make a tall virtualized grid: only visible rows plus overscan are mounted.

## Subtask 7.1.1.2 — Cells

- `1`: solid black filled circle (no number). `-1`: light gray circle. `0`: nothing.
- Circles centered under their column header.

## Subtask 7.1.1.3 — Onset-sustain edges

Vertical connector lines: from the bottom edge of a `1` circle to the top edge of the `-1` below it (same key, consecutive frames), then gray edges chaining subsequent `-1`s — reading as one connected note: solid head, gray tail.

## Subtask 7.1.1.4 — Data source

Renders from the dense form of the currently selected artifact + step, fetched from the backend (backend does the sparse->dense digestion; frontend stays thin).

Above the grid, identify the audio context explicitly: **ENTIRE TRACK** with duration, or
**SEGMENT** with root-source alias and absolute start/end metadata. Segment Matrix/playback time
remains local and starts at zero.

## Acceptance

Manual trial: view the text-notation example from the spec and visually verify circles, edges and
row labels frame by frame. Then open a saved audio segment and confirm its banner and each visible
row show unambiguous local/root timing.
