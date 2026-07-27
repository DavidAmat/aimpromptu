# Task 3.2.1 — Upload endpoint and formats

`api/audio.py` upload route + `audio/formats.py`.

## Subtask 3.2.1.1 — Upload

`POST /audio/upload` (multipart): detect format by file suffix (`.mp3`, `.aac`, `.m4a`, `.wav`; reject others with 422), store original in the audio store, return uuid + metadata.

## Subtask 3.2.1.2 — Normalization

Convert once on ingest to mono WAV at the transcription sample rate using ffmpeg (subprocess; ffmpeg is a documented local prerequisite). Keep both original and normalized files in the uuid folder. Compute `durationSeconds` here.

## Subtask 3.2.1.3 — Waveform peaks

`GET /audio/{uuid}/waveform?points=N`: downsampled min/max peak pairs computed backend-side (numpy over the normalized WAV), cached as `waveform.json` in the uuid folder. Feeds the range selector and the piano-roll watermark; frontend never decodes audio itself for drawing.

## Acceptance

Upload each supported format; verify normalized WAV, duration and waveform endpoint. Manual trial: upload a phone recording, see its waveform.
