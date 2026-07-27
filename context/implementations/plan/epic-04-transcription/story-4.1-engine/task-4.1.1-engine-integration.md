# Task 4.1.1 — Transcription engine integration

`transcription/engine.py`: model wrapper behind a stable interface so engines can be swapped when we hit limitations (decision process: try one, if results disappoint, move to the next candidate from the research doc).

## Subtask 4.1.1.1 — Interface

```python
class TranscriptionEngine(Protocol):
    def transcribe(self, wav_path: Path) -> list[NoteEvent]: ...

class NoteEvent(BaseModel):
    midi_note: int; start: float; end: float; velocity: int
```

## Subtask 4.1.1.2 — ByteDance engine (default)

- `piano_transcription_inference` package; `device="cpu"` on this Mac, expose a `device` setting for future GPU hosts.
- The package pins old torch versions: isolate carefully in `uv` extras; if dependency resolution fights the main env, run it as a subprocess with its own venv — document whichever works.
- Parse resulting MIDI with `pretty_midi` into NoteEvents.

## Subtask 4.1.1.3 — Basic Pitch fallback + benchmark

Second engine implementing the same Protocol. Keep a small benchmark script (`notebooks/transcription-benchmark/`) running both engines on the same clips, printing missed/false notes and runtimes — the human judges which engine wins on real recordings.

## Acceptance

A committed short piano clip transcribes into plausible NoteEvents with the default engine; engine selectable via config.
