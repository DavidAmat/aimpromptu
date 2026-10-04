# Task 11.3.1 — Replacement preview and accept · progress

Status: **done** on 2026-08-13. Same Re-record tab as 11.1.1 / 11.2.1.

## What was implemented

The take is transcribed as played (`POST .../transcribe`, same job/SSE machinery as Input). Event
times are scaled afterwards. Stretched audio is never sent to the engine.

Preview redraws only the marked stretch, using the ladder of the passage the window belongs to,
plus the take's own peak plot. A factor off by two puts every pile one step from the ladder.

Three listens from the same panel: take as played, take scaled into the window (`atempo`), original
window. Speed can be changed and previewed again without recording. Re-recording keeps the same
window. Accept shows a confirmation (notes out/in, marks dropped by kind, whether audio will be
spliced, length unchanged).

If audio splice fails or is turned off, the edit still commits and
`matrices/audio-mismatches.json` records the window.

## Manual trial

A hard 3-second passage, played at 4× slower, previewed, factor corrected once (e.g. switch to 2×
and preview again), accepted. The new notes are only inside the stretch; the note after the window
has the same onset; playback follows the sheet.

Piano Roll and Notes Falling: set the existing playback range, press **Re-record this stretch**.
Same session UI. Note rubber-banding is unchanged.

## For the next worker

Preview is `POST /audio/{uuid}/edits/{session}/preview` and is fast once take events exist. Changing
speed is PATCH then preview, not a new transcription.
