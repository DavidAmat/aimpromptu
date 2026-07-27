# Transcription benchmark

Runs every installed engine over the same clips and prints what each heard, so a
human can judge which one wins on real recordings.

```bash
cd aitu-backend
uv run python notebooks/transcription-benchmark/benchmark.py my-scale.wav
uv run python notebooks/transcription-benchmark/benchmark.py --store   # everything in the audio store
```

Per engine it prints the elapsed time, the note count, the most common pitches, and
**the first eight notes with their timings** — that last line is what you actually
recognize by eye. Engines that are not installed print a `[skip]` line rather than
crashing the run.

For a `Do Re Mi Fa Sol` take at 60 BPM, expect roughly:

```
bytedance        3.41s  5 notes over 4.98s — most common: Do-4 x1, Re-4 x1, ...
                 first: Do-4@0.00s Re-4@1.00s Mi-4@2.00s Fa-4@3.00s Sol-4@4.00s
```

## The default engine

```bash
uv sync --extra transcription
```

That is all. The 165 MB model checkpoint downloads on first use.

## Basic Pitch — why it is not a project extra

Spotify's Basic Pitch is the plan's benchmark/fallback engine, but **it cannot be
installed alongside this project**:

- basic-pitch 0.4.0 (the newest release) requires `tensorflow(-macos) >=2.4.1,<2.15.1`.
- The first tensorflow release with **cp312** wheels is **2.16.1** — on macOS *and*
  Linux.
- So basic-pitch is capped at Python 3.11, while this project is on 3.12.

Worse, `uv lock` resolves **every extra for every platform**, so merely *declaring*
a `basic-pitch` extra makes the whole project unresolvable — `uv sync --extra
transcription` fails with a tensorflow error even though you never asked for
basic-pitch. That is why the extra was removed.

### Running it anyway, in its own environment

If the default engine disappoints and you want the comparison, give Basic Pitch a
Python 3.11 environment of its own. It never has to share ours — the two engines
only need to agree on the *note events* they produce.

```bash
cd aitu-backend
uv venv --python 3.11 .venv-basicpitch
uv pip install --python .venv-basicpitch/bin/python basic-pitch soundfile

# Transcribe the same clip and dump its notes as JSON:
.venv-basicpitch/bin/python - <<'EOF' > /tmp/basic-pitch-notes.json
import json, sys
from basic_pitch.inference import predict
_, midi, _ = predict("data/audio/<uuid>/normalized.wav")
print(json.dumps(sorted(
    ({"midi": n.pitch, "start": round(n.start, 3), "end": round(n.end, 3)}
     for i in midi.instruments for n in i.notes),
    key=lambda n: (n["start"], n["midi"]))))
EOF

# Then compare against the default engine's first notes:
uv run python notebooks/transcription-benchmark/benchmark.py data/audio/<uuid>/normalized.wav
```

If Basic Pitch turns out to be the better engine for real recordings, the decision
to make is a project-level one — most likely dropping to Python 3.11 for the whole
backend, or waiting for a basic-pitch release that drops the tensorflow pin. The
`TranscriptionEngine` interface means no other code changes either way.
