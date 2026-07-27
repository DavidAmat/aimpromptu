# Epic 3 — Audio I/O

Getting audio into the system and managing it: uploads, browser recording, waveform display,
time-range selection, physically saved segments with source lineage, YouTube downloads, and the
audio working store. Implemented early on purpose — recording capability is the prerequisite for
all human-in-the-loop testing of later rendering epics.

Read first: `project-features.md` sections "From audio to matrix", "YouTube to Audio", "Upload / Input tab"; `context/04-local-development.md`.

## Story 3.1 — Audio store

- Task 3.1.1 audio store: uuid working folders under `data/audio/`, `metadata.json` with editable
  file-name alias, list/rename endpoints, physical segment creation and lineage, personal audio
  library ("load from library").

## Story 3.2 — Upload and formats

- Task 3.2.1 upload endpoint: accept mp3/aac/m4a/wav by suffix, normalize via ffmpeg, waveform peaks endpoint.

## Story 3.3 — Browser recording

- Task 3.3.1 browser recording: MediaRecorder capture, SoundCloud-style live bar waveform, save to the audio store with a name.

## Story 3.4 — Range selection

- Task 3.4.1 waveform range selector: Audacity-like waveform, two draggable selectors with time
  tooltips, manual `mm:ss.cc` inputs, play-range with moving cursor, and a read-only mode for a
  persisted truncated segment.

## Story 3.5 — YouTube

- Task 3.5.1 youtube download: yt-dlp via backend, best-quality mp3, user file name into metadata, tab UI; batch download queue as a nice-to-have subtask.

## Exit criteria

An audio can arrive via upload, mic recording or YouTube URL; it lands in a uuid folder with
metadata; the UI can show its waveform, select and play a sub-range, then persist that selection as
a named physical segment whose metadata preserves its absolute root-source times. Manual trial:
record a simple C-major scale, save a sub-range, and confirm only the truncated waveform plays.
