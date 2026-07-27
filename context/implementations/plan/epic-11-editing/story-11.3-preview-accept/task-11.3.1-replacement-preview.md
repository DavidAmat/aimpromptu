# Task 11.3.1 — Replacement preview and accept

"Transcribe and preview at current track tempo".

## Subtask 11.3.1.1 — Transcribe then scale

Transcribe the original slow recording first (avoids time-compression artefacts), then scale event timestamps: `targetTime = recordedTime * recordingBpm / trackBpm`. Build the temporary matrix at track tempo via the normal events-to-matrix path.

## Subtask 11.3.1.2 — Passage-only render

Render only the edited passage through the score builder (few seconds of music — must be fast, no full-score regeneration).

## Subtask 11.3.1.3 — Optional audio preview

"Play at current track tempo": pitch-preserving time compression of the recorded audio (e.g. ffmpeg `atempo`). For listening only — notation always comes from the transcription of the original recording.

## Subtask 11.3.1.4 — Decision loop

From the preview the user can: play raw/converted audio, inspect waveform, temporary matrix and passage notation, re-record (same or slower speed, different capture granularity), accept (Task 11.1.1 semantics) or cancel.

## Acceptance

Manual trial: full loop on a hard 4-beat passage recorded at 4x slower, accepted, and verified in the final score.
