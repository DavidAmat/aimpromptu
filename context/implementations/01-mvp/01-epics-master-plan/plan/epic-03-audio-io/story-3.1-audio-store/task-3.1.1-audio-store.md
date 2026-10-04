# Task 3.1.1 — Audio store

`audio/store.py` + `api/audio.py`: the working area every audio input lands in, keyed by uuid.

## Subtask 3.1.1.1 — Folder and metadata

On ingest create `data/audio/<uuid>/` containing the original file and `metadata.json`:

- `fileName` (user alias, e.g. "Levels - Avicii"), `source`
  (`upload | recording | youtube | segment`), `format`, `durationSeconds`, `createdAt`, optional
  `youtubeUrl`
- a `segment` requires `sourceAudioUuid` (the root audio) and an absolute
  `sourceTimeRange`; the stored `original.wav`, `normalized.wav`, duration and waveform contain
  only the selected passage
- alias always editable via a rename endpoint

## Subtask 3.1.1.2 — Library endpoints

- `GET /audio` list (uuid, alias, source, duration) — powers "load from library" in the Input tab
- `GET /audio/{uuid}` metadata; `GET /audio/{uuid}/file` streamed audio for playback
- `PATCH /audio/{uuid}` rename/edit metadata; `DELETE /audio/{uuid}`
- `POST /audio/{uuid}/trim` creates a named physical child segment. Re-trimming a segment keeps
  lineage against the root source rather than nesting relative offsets. Selecting the whole file
  is rejected as a no-op.

## Subtask 3.1.1.3 — Future MinIO note

Keep all filesystem access behind `store.py` functions so a future MinIO-backed implementation is a drop-in swap. Do not build MinIO now.

## Acceptance

CRUD round-trip tests over a temp data dir, plus physical duration/waveform and nested absolute
lineage tests for segment creation.
