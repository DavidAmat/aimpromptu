# Task 4.1.1 — Transcription engine integration · progress report

Status: **done in code, unverified against a real model.** Date: 2026-07-27.

> **The one thing you must check tomorrow**: no engine has ever run. `torch` would not install in
> the sandbox (an aarch64 Linux wheel download that ran past every timeout I gave it), so
> `ByteDanceEngine.transcribe` has never executed. Everything around it is tested; the model call
> itself is written from the package's documented API and needs your eyes. Details and the exact
> trial are at the bottom.

## Summary

`transcription/engine.py` — one interface, three implementations.

```python
class TranscriptionEngine(Protocol):
    name: str
    def transcribe(self, wav_path: Path) -> list[NoteEvent]: ...

class NoteEvent(BaseModel):
    midi_note: int; start: float; end: float; velocity: int
```

`NoteEvent` validates what the task file only described: MIDI `0..127`, velocity `0..127`,
non-negative start, and `end > start`.

| Engine | Package | Role |
|--------|---------|------|
| `bytedance` | `piano_transcription_inference` | **default** — the research doc's first pick |
| `basic-pitch` | `basic_pitch` | benchmark and fallback |
| `silent` | — | returns nothing |

`create_engine(name, **options)` builds by name; `available_engines()` reports which ones can
actually be constructed here, and is exposed at `GET /matrix/engines` so the UI can grey out an
option instead of letting you pick something that will fail.

### Three decisions worth reading

**1. Both real engines import their package lazily, inside `__init__`.** The backend starts, the
API serves, and all 414 tests run on a machine with neither installed. Asking for a missing engine
raises `EngineUnavailable` naming the exact install command — the failure tells you what to run,
not just that it failed.

**2. `SilentEngine` is a real, shipped engine, not test scaffolding.** It lets the entire pipeline,
the artifacts, the SSE stream and the whole UI be exercised end to end with no model installed.
That is how the API tests cover the pipeline, and it is how you can click through Epic 6's Input
tab tomorrow before deciding whether to download half a gigabyte of torch.

**3. Torch is an optional extra, not a base dependency.**

```toml
[project.optional-dependencies]
transcription = ["piano_transcription_inference", "torch", "librosa", "pretty_midi"]
basic-pitch = ["basic-pitch"]
```

`uv sync` stays fast and the base install stays small; `uv sync --extra transcription` pulls the
model stack. The task file anticipated dependency resolution fighting the main environment — an
extra is the least invasive answer, and the documented fallback (a separate venv driven as a
subprocess) remains available **without changing any caller**, which is the entire point of the
Protocol.

### Benchmark script (subtask 4.1.1.3)

`notebooks/transcription-benchmark/benchmark.py` runs every installed engine over the same clips
and prints, per engine: elapsed time, note count, the most common pitches, and **the first eight
notes with their timings** — because that last line is what you actually recognize by eye.

```bash
uv run python notebooks/transcription-benchmark/benchmark.py my-scale.wav
uv run python notebooks/transcription-benchmark/benchmark.py --store   # everything in the store
```

Engines that are not installed print a `[skip]` line with their install command rather than
crashing the run.

## Errors found and how they were solved

1. **torch would not install in the sandbox.** Three attempts, the last running well past twenty
   minutes on an aarch64 Linux wheel. Rather than block the epic, I made the engines lazy and the
   dependency optional — which is a better design anyway, and is what made the rest of Epic 4
   fully testable. See the caveat at the top.
2. **`create_engine` typing.** The engine registry maps names to heterogeneous constructors, which
   mypy cannot reconcile with the Protocol return type. Widened `**options` to `Any` rather than
   scattering ignores; the runtime `isinstance(engine, TranscriptionEngine)` check in the tests is
   what actually guards the contract, and `Protocol` is `runtime_checkable` for exactly that.

## Deviations from the task file

- Added `SilentEngine` and `GET /matrix/engines` (neither in the task file).
- The benchmark is a **script**, not a notebook. It is meant to be run from the terminal on real
  recordings and diffed between engine versions; a notebook adds ceremony without adding insight.
  It lives at `notebooks/transcription-benchmark/` as the task file specifies.
- `pretty_midi` is listed in the extra but not used: `piano_transcription_inference` returns note
  events directly (`est_note_events`), so parsing a MIDI file back would be a detour. Kept as a
  dependency because Basic Pitch does return a `pretty_midi` object.

## Verification

```
pytest tests/test_transcription.py   # 36 passed
pytest                               # 414 passed, 1 skipped
mypy, flake8, black                  # clean
npx tsc -b, npm run lint             # clean
```

What is covered: the `NoteEvent` contract including its rejections, both stub engines satisfying
the Protocol at runtime, unknown engine names, the "missing package names the install command"
behaviour, and `available_engines()`.

What is **not** covered: `ByteDanceEngine.transcribe` and `BasicPitchEngine.transcribe`. Both are
written against the packages' documented shapes but have never run.

## Manual trial for the supervisor — please do this one first

```bash
cd aitu-backend
uv sync --extra transcription        # expect a few hundred MB and a few minutes
uv run python -c "
from aitu_backend.transcription.engine import available_engines
print(available_engines())           # bytedance should now be True
"
```

Then, on the five-note scale you recorded in Task 3.3.1:

```bash
uv run python notebooks/transcription-benchmark/benchmark.py --store
```

**What correct looks like:** for a `Do Re Mi Fa Sol` take at 60 BPM, the `first:` line should read
roughly `Do-4@0.00s Re-4@1.00s Mi-4@2.00s Fa-4@3.00s Sol-4@4.00s` — five notes, ascending, about a
second apart. The exact octave depends on where you played.

**Likely failure points, in order:**

1. `PianoTranscription(device=..., checkpoint_path=...)` — the constructor signature.
2. The first run downloads the model checkpoint (~170 MB) to `~/piano_transcription_inference_data/`.
   Expect a pause and no progress bar.
3. `result["est_note_events"]` and its `midi_note` / `onset_time` / `offset_time` keys — this is
   the part I am least sure of.

If any of those is wrong it will be a one-line fix in `ByteDanceEngine.transcribe`, and the
traceback will point straight at it. Paste it to me and I will correct it.

If the model's output is poor on real recordings, that is the decision point the plan anticipates.
**Basic Pitch cannot be a project extra** (see the 2026-07-27 follow-up report) — it needs its own
Python 3.11 venv, and `notebooks/transcription-benchmark/README.md` has the recipe. Nothing outside
`engine.py` changes either way.

## For the next worker

- Everything downstream takes `list[NoteEvent]`. Never let a model's own types leak past this file.
- Add a new engine by writing a class with `name` and `transcribe`, then adding it to `ENGINES`.
- `DEFAULT_ENGINE` is the one place to change the default.
- `device` is already a constructor parameter on both real engines — a CUDA host needs no
  refactor, just `create_engine("bytedance", device="cuda")`.
