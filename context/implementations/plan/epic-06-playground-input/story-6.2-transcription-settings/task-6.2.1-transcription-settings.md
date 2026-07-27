# Task 6.2.1 — Transcription settings and launch

## Subtask 6.2.1.1 — Settings

For audio sources: BPM numeric input (default 60) and temporal resolution dropdown (`Negra`, `Corchea`, `SemiCorchea`, `Fusa`). Remember: transcription always produces the raw matrix at fusa first, then collapses to the chosen resolution.

## Subtask 6.2.1.2 — Range restriction

Embed the waveform range selector (Task 3.4.1). A partial selection is not a transient pipeline
option: the user names and creates a new, physically trimmed audio item first. Its metadata keeps
the root source audio uuid and the absolute start/end time in that source. The new item exposes
only the truncated waveform and normalized file, and provides **Back to original** so another
section can be chosen. Transcription remains disabled until a partial selection has been saved.

This makes an audio segment, its matrix and all later Playground views one coherent artifact,
while preserving enough lineage to show where the segment came from.

## Subtask 6.2.1.3 — Run and handoff

Run button -> a fresh `run_pipeline` (Task 4.3.1) for the selected physical audio file, with an SSE
progress bar -> on completion store the artifact uuid in the Playground context and navigate to
the Matrix tab. The ByteDance engine reports its real model segments, and the UI maps model and
post-processing stages monotonically across one bar instead of resetting it between stages.

## Acceptance

Manual trial: upload a piece, select and save a named 10-second segment, confirm the visible
waveform is only that segment, transcribe at Corchea/60 BPM, and land on the Matrix tab showing a
SEGMENT banner plus local/original timestamps. Return to Input, use **Back to original**, run the
full source, and confirm Matrix now says ENTIRE TRACK rather than reopening the former segment.
