# Task 11.2.1 — Slow re-record flow

Recording the replacement, per `03-editing-logic.md`.

## Subtask 11.2.1.1 — Recording speed options

Simple choices: Original speed, 2x slower, 4x slower -> `recordingBpm = trackBpm / slowdownFactor`. Track tempo, recording tempo and capture granularity stay independent concepts (granularity changes precision, never speed).

## Subtask 11.2.1.2 — Metronome and beat display

Metronome clicks at the recording tempo during capture (WebAudio scheduled clicks); UI shows current beat and current time frame within the selected range so the performer knows where they are.

## Subtask 11.2.1.3 — Manual stop and trimming

User stops manually; recording may overrun. Trim to `expectedRecordingSeconds = selectedBeats * 60 / recordingBpm`. Preserve the raw untrimmed audio in the session. Show waveform + playback of the take before processing.

## Subtask 11.2.1.4 — Capture granularity

Optional finer granularity during recording for more precise timings; result later collapses to the track granularity with the normal merge rules.

## Acceptance

Manual trial: record 4 beats at 2x slower with the metronome; trimmed length exactly 8 s.
