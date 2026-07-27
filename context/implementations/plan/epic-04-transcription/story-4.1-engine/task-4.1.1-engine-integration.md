# Task 4.1.1 — Transcription engine integration

`transcription/engine.py`: model wrapper behind a stable interface so engines can be swapped when we hit limitations (decision process: try one, if results disappoint, move to the next candidate from the research doc).

## Subtask 4.1.1.1 — Interface

```python
class TranscriptionEngine(Protocol):
    def transcribe(self, wav_path: Path) -> list[NoteEvent]: ...

class NoteEvent(BaseModel):
    midi_note: int; start: float; end: float; velocity: int
```

An engine may additionally expose `transcribe_with_progress(wav_path, reporter)` when it can
publish real internal work units. The pipeline detects this capability without forcing it onto
fallback engines.

## Subtask 4.1.1.2 — ByteDance engine (default)

- `piano_transcription_inference` package; `device="cpu"` on this Mac, expose a `device` setting
  for future GPU hosts. The package does not pin an obsolete torch version.
- Download and validate the checkpoint in application code because upstream shells out to
  `wget`, which macOS does not provide. Use a partial file and atomic move so interrupted
  downloads cannot masquerade as valid checkpoints.
- Consume upstream's in-memory `est_note_events`; no temporary MIDI parse is needed.
- Mirror upstream's overlapping mini-batch inference loop to report truthful
  `model segment N/total` events while preserving its deframing and regression post-processing.

## Subtask 4.1.1.3 — Basic Pitch fallback + benchmark

Second engine implementing the same Protocol. Keep a small benchmark script (`notebooks/transcription-benchmark/`) running both engines on the same clips, printing missed/false notes and runtimes — the human judges which engine wins on real recordings.

## Acceptance

A short local clip completes with the real default engine; the engine is selectable via config.
Automated tests cover checkpoint handling and progressive internal segments. Musical plausibility
remains a human trial with a known piano recording rather than a committed binary fixture.
