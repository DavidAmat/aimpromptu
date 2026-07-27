# Task 3.4.1 — Waveform range selector

Audacity-like component used wherever a sub-range of an audio must be chosen (Input tab, playground-by-range transcription, editing epic).

## Subtask 3.4.1.1 — Waveform display

Draw the full waveform from the backend peaks endpoint (canvas or SVG). Show total duration; zoom is out of scope for now.

## Subtask 3.4.1.2 — Range handles

Two draggable selectors over the waveform; a time tooltip on top of each handle while dragging. Manual text inputs for start and end accepting `mm:ss.mmm` (e.g. `03:03.123`), kept in sync with the handles.

## Subtask 3.4.1.3 — Playback

- Play full audio, or play only the selected range: cursor line advances with time and stops at the range end.
- Pause/restart to range start.
- Component emits `{startSeconds, endSeconds}` to its parent; only the segment is later transcribed, never the full audio, when a range is active.

## Acceptance

Manual trial: load a known song, select `00:10`–`00:15` by dragging, refine via text inputs, play the range and watch the cursor stop at the edge.
