# Task 4.1.1 — follow-up: the `basic-pitch` extra had to go

Date: 2026-07-27. Found by the supervisor running `uv sync --extra transcription` on a Mac M4.

## The symptom

```
× No solution found when resolving dependencies:
  ╰─▶ Because ... basic-pitch==0.4.0 depends on tensorflow >=2.4.1,<2.15.1 ...
      and tensorflow>=2.4.1,<=2.15.0.post1 has no wheels with a matching Python
      version tag (e.g., `cp312`) ... your project's requirements are unsatisfiable.
      hint: Wheels are available for `tensorflow` (v2.15.0.post1) with the following
      Python ABI tags: `cp39`, `cp310`, `cp311`
```

Asking for the **transcription** extra failed because of the **basic-pitch** extra.

## Why

Two facts, both verified against PyPI:

1. **basic-pitch 0.4.0 pins `tensorflow(-macos) >=2.4.1,<2.15.1`.** On macOS the requirement is
   `tensorflow-macos<2.15.1` for `python_version > "3.11"`, so Python 3.12 is squarely in scope.
2. **The first tensorflow release with cp312 wheels is 2.16.1** — on macOS *and* Linux:

   | Version | Wheel tags (both `tensorflow` and `tensorflow-macos`) |
   |---------|------------------------------------------------------|
   | 2.13.0 – 2.15.0 | cp39, cp310, cp311 |
   | **2.16.1+** | cp39, cp310, cp311, **cp312** |

   So the entire range basic-pitch allows is Python ≤3.11. **basic-pitch 0.4.0 cannot be installed
   on Python 3.12 on any platform.**

And the reason it broke an unrelated extra: **`uv lock` performs universal resolution.** It solves
for every extra on every platform, so a declared-but-unsatisfiable extra makes the *whole project*
unresolvable. `--extra transcription` never got a chance.

## The fix

The `basic-pitch` extra is removed from `pyproject.toml`, with the reasoning written where the next
person will hit it. `uv sync --extra transcription` now resolves.

Nothing else changed structurally:

- `BasicPitchEngine` **stays** in `transcription/engine.py`. The interface is the point — if
  basic-pitch drops the pin, or a run happens elsewhere, no other code moves.
- Its `EngineUnavailable` message now explains the Python-version conflict and points at the
  recipe, instead of suggesting an install command that cannot work.
- `available_engines()` reporting `basic-pitch: False` is now **expected and correct**, and the
  setup guide says so.

## Running Basic Pitch anyway

`notebooks/transcription-benchmark/README.md` (new) has the full recipe: a separate Python 3.11
venv, transcribe the same clip, dump its notes as JSON, compare against the default engine's
output. The two engines only need to agree on *note events*, so they never have to share an
environment.

If Basic Pitch turns out to be better on real recordings, the decision becomes a project-level one
— most likely dropping the whole backend to Python 3.11, or waiting for a basic-pitch release
without the tensorflow pin. Worth knowing before that conversation: **Python 3.12 is otherwise the
right choice** — torch, numba and llvmlite all ship cp312 macOS arm64 wheels, and
`piano_transcription_inference` pins nothing.

## Files touched

| File | Change |
|------|--------|
| `aitu-backend/pyproject.toml` | extra removed, with the explanation inline |
| `transcription/engine.py` | `BasicPitchEngine` docstring + install hint |
| `notebooks/transcription-benchmark/README.md` | **new** — the separate-venv recipe |
| `notebooks/transcription-benchmark/benchmark.py` | docstring |
| `context/02-tech-stack.md`, `context/04-local-development.md` | corrected |
| `user_review/00-setup.md`, `user_review/epic-04-transcription.md` | corrected |
| `epic-04/task-4.1.1-progress.md` | the stale "just install the extra" line |

## Verification

```
pytest              # 464 passed
mypy, flake8, black # clean
```

`uv lock` / `uv sync` still cannot be run in the sandbox (no Python 3.12 available), so **the
resolution itself needs confirming on the Mac** — that is one command:

```bash
cd aitu-backend && uv sync --extra transcription
```
