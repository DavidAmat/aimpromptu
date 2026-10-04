# Task 8.3.1 — Playback engine · progress

Status: **done; synthesized source browser-verified** on 2026-07-27.

## Delivered

- Shared AudioContext-clock transport: play, pause, restart, timeline seek, current frame/time.
- Original normalized audio or matrix-driven piano source.
- Equal-tempered 88-key WebAudio fallback with an attack/decay envelope; no second engine exists
  for Matrix.
- Active-key set shared by both piano orientations.
- Speed, BPM, granularity and local range controls rebuild playback from the selected physical
  audio item's start. Saved segments therefore use local time zero while metadata preserves their
  original-source offset.

The task permits synthesized fallback when local grand-piano samples are unavailable; that is the
implemented POC path, avoiding a large third-party sample bundle and its licensing footprint.

## Verification and manual trial

Synthesized playback ran in Matrix, Piano Roll and Notes Falling without console errors. The
imported matrix has no audio, so the original-audio A/B remains the required human trial: use the
slow real scale, play Original audio, then Transcribed piano, and confirm keys land at the same
moments.
