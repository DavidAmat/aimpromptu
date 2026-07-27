# Epic 8 — Piano roll and notes falling views

Two animated visualizations of a piano matrix over the piano SVG: the horizontal Piano Roll (piano rotated vertical at the left, rectangles flowing leftwards) and the Synthesia-style Notes Falling view (piano horizontal at the bottom, rectangles falling). Shared playback engine with original audio and synthesized piano tones.

Read first: `project-features.md` sections "Piano Roll tab", "UI Visualisation of the matrix", "Piano roll view", "Notes falling"; `context/music/piano_svg/01-piano-svg.md`.

## Story 8.1 — Piano SVG assets

- Task 8.1.1 piano svg assets: white-key base + normal black-key layer + pressed white/black
  overlays, key coordinate table, PressedKey highlight component.

## Story 8.2 — Piano roll view

- Task 8.2.1 roll view layout: vertical piano left, note rectangles with ES names, dashed numbered frame lines, horizontal scroll, full-height fit.

## Story 8.3 — Playback engine

- Task 8.3.1 playback engine: play the selected physical audio item or synthesized transcription,
  speed/BPM/granularity/local-range filters, cursor, pause/seek, key-press highlighting, waveform
  watermark. Persisted segments start locally at zero.

## Story 8.4 — Notes falling view

- Task 8.4.1 notes falling: falling rectangles calibrated to key widths, velocity from window size + BPM + granularity, windowed rendering, swallow effect at Y=0.

## Story 8.5 — Drag editing (nice to have)

- Task 8.5.1 drag note editing: draggable rectangles onto other keys/frames with landing guides, staged changes, Save to matrix.

## Exit criteria

Manual trial: transcribe a recorded scale (or a persisted segment of it), watch it in both views
with keys lighting up in sync with either the physical source audio or the synthesized piano, over
a local playback range. Confirm neighbouring black keys remain above pressed white-key overlays.
