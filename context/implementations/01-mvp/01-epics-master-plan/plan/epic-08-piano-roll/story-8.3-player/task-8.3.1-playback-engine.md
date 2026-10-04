# Task 8.3.1 — Playback engine

Shared player powering both animated views (and reused by the matrix player).

## Subtask 8.3.1.1 — Transport

Play/pause/restart; seek by clicking the timeline or typing a timestamp (`00:04`); boxes showing current time and current frame number. Time source: `AudioContext` clock. While playing, notes scroll left (roll view) or fall (falling view); when a rectangle tip touches the piano, that key is pressed (blue highlight, held for the rectangle length) and the rectangle turns light blue.

## Subtask 8.3.1.2 — Two sound sources

- Original audio: the selected stored physical file, via an audio element synced to the transport.
  For a persisted segment this file and its waveform contain only the segment and local time starts
  at zero.
- Transcribed piano: synthesized from the matrix. Prefer real per-key Grand Piano samples downloaded locally (find a good free set, e.g. University of Iowa MIS or the Salamander Grand Piano, and commit a downscaled subset); fallback: a frequency table of the 88 keys with a simple envelope via WebAudio.

Buttons choose which source plays for the current selection; both respect the toolbar's local
playback range and restart to that local selection start. This playback filter does not create a
new artifact; persistent source segmentation happens only in Input.

## Subtask 8.3.1.3 — Filters

Toolbar: player speed, BPM, granularity, local time range (e.g. 00:00–00:02 within a saved
segment). Any change rebuilds the player state from scratch on the refreshed matrices/range.

## Acceptance

Manual trial: play the original recording of a scale while watching keys light; then play the transcription and compare by ear — this A/B is the core transcription-quality feedback loop.
