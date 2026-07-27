# Epic 4 — Transcription

Audio to piano matrix. Wraps a piano-transcription model, converts its note events into the raw fusa matrix, and orchestrates the full pipeline raw -> collapsed -> clean -> two-hands with persisted artifacts and streamed progress.

Read first: `context/research/piano-transcription/piano-transcription-python-solutions.md`, `context/music/notation-logic/01-matrix-notation-logic.md` appendices B–D.

## Story 4.1 — Engine

- Task 4.1.1 engine integration: `piano_transcription_inference` (ByteDance) as first engine behind an interface; Basic Pitch as benchmark fallback; CPU on this Mac, CUDA-ready flag.

## Story 4.2 — Events to matrix

- Task 4.2.1 events to raw matrix: MIDI-like note events -> raw matrix at fusa granularity using the Task 2.3.2 approximation rules.

## Story 4.3 — Pipeline

- Task 4.3.1 pipeline orchestration: one call runs the four steps, persists all artifacts per input uuid, recomputes any granularity from raw quickly, streams progress to the UI.

## Exit criteria

Manual trial: record/upload a one-hand C-major scale at steady 60 BPM; the pipeline yields a raw matrix whose onsets match the played notes, and clean/two-hands artifacts exist on disk. Iterate engines only if this trial fails badly.
