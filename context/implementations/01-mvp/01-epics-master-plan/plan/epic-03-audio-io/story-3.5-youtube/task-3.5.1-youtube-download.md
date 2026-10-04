# Task 3.5.1 — YouTube to audio

Dedicated app section: paste a YouTube URL, download its audio via the backend.

## Subtask 3.5.1.1 — Backend download

`POST /youtube/download` with `{url, fileName}`:

- use `yt-dlp` (the maintained fork of youtube-dl) as a Python dependency
- extract best-quality audio, convert to mp3 via ffmpeg
- store in the audio store (`source = "youtube"`, alias = user's `fileName`, keep `youtubeUrl` in metadata)
- long downloads report progress through the ProgressReporter/SSE channel
- single-user manual usage; if rate limits are hit, surface the yt-dlp error message clearly

## Subtask 3.5.1.2 — Tab UI

URL input + file name input + download button + progress bar; on success show the entry with a link to open it in Playground Input.

## Subtask 3.5.1.3 — Batch downloads (nice to have)

Accept a list of `{url, fileName}` rows and download sequentially with a queue view. Skip until the single flow is stable.

## Acceptance

Manual trial: download one piano-only video, confirm mp3 in the store with correct alias and playable waveform.
