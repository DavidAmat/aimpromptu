# Task 4.3.1 — Pipeline orchestration

`transcription/pipeline.py` + `api/matrix.py`: the single entry point the UI calls.

## Subtask 4.3.1.1 — Steps

`run_pipeline(audio_uuid, tempo_bpm, target_granularity)`:

1. audio -> NoteEvents (engine)
2. events -> raw matrix (fusa)
3. raw -> collapsed (chained merges to `target_granularity`)
4. collapsed -> clean (sustain cleaning)
5. clean -> two-hands (threshold split)

All five artifacts persist under the working folder for that input uuid so every Playground tab
reads the same state. A partial passage reaches this entry point as its own physically trimmed
audio uuid; a fresh Run explicitly replaces any previous transcription for that selected uuid.

## Subtask 4.3.1.2 — Fast recompute

Changing BPM or granularity re-runs only steps 3–5 from the stored raw matrix (never re-transcribes, never merges from an intermediate). Target: interactive latency (<1 s) so the Matrix tab in-situ switching feels instant.

## Subtask 4.3.1.3 — Progress streaming

Transcription dominates runtime: report step + percent through ProgressReporter;
`GET /matrix/progress/{job_id}` SSE endpoint consumed by `useProgress`. tqdm mirrors the same
reporter in the terminal. ByteDance reports each real overlapping model segment. The browser maps
download, transcription, events, collapse, clean and two-hands into fixed whole-job bands and
never moves the bar backward when a stage-local fraction resets.

## Subtask 4.3.1.4 — GPU awareness

No GPU work now, but keep matrix steps numpy-vectorized and the engine device-parameterized so a CUDA host accelerates without refactoring (see "GPU Optimization" note in `project-features.md`).

## Acceptance

End-to-end test on a committed clip: all artifacts written; recompute of a new granularity touches only steps 3–5 and is sub-second.
