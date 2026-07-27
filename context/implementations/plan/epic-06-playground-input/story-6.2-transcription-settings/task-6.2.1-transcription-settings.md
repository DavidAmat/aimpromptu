# Task 6.2.1 — Transcription settings and launch

## Subtask 6.2.1.1 — Settings

For audio sources: BPM numeric input (default 60) and temporal resolution dropdown (`Negra`, `Corchea`, `SemiCorchea`, `Fusa`). Remember: transcription always produces the raw matrix at fusa first, then collapses to the chosen resolution.

## Subtask 6.2.1.2 — Range restriction

Embed the waveform range selector (Task 3.4.1). When a range is set, only that segment is transcribed — the "load a .mp3 and transcribe just 03:01–03:22" iteration flow from `project-features.md`.

## Subtask 6.2.1.3 — Run and handoff

Run button -> `run_pipeline` (Task 4.3.1) with SSE progress bar -> on completion store the artifact uuid in the Playground context and navigate to the Matrix tab.

## Acceptance

Manual trial: upload a piece, select a 10-second range, transcribe at Corchea/60 BPM, land on the Matrix tab showing the result.
