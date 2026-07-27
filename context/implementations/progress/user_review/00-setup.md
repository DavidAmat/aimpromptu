# 0 — Setup

Get both services running and every check green. About 15 minutes, most of it downloads.

---

## 1. Install the prerequisites

```bash
brew install ffmpeg
ffmpeg -version          # any 6.x or 7.x is fine
```

**Why ffmpeg.** Every audio that enters the app — uploaded, recorded or downloaded from YouTube —
is converted once into a plain mono 16 kHz WAV. After that, nothing else in the system has to care
whether you gave it an mp3, an m4a or a browser recording. ffmpeg does that conversion.

---

## 2. Backend

```bash
cd aitu-backend
uv sync                          # base install, fast
uv sync --extra transcription    # the piano model: ~200 MB, a few minutes
```

The second command is what makes real transcription possible. Skip it and everything still runs,
but every piece transcribes to silence.

> **Python version.** The project is pinned to Python 3.12.13, and that is correct — torch ships
> Apple Silicon wheels for 3.10 through 3.14, and 3.12 is the most battle-tested. Nothing needs
> changing.

Now check it:

```bash
uv run python -c "
from aitu_backend.transcription.engine import available_engines
print(available_engines())
"
```

Expected: `{'bytedance': True, 'basic-pitch': False, 'silent': True}`

`bytedance: True` means the model is installed. `basic-pitch: False` is fine — it is the optional
second engine, only useful if the first one disappoints.

### Run the checks

```bash
make lint      # flake8 + mypy
make test      # pytest — expect ~450 passed
make hooks     # installs the git pre-commit hook, once
```

### Start it

```bash
make serve
```

Leave this terminal running. Then, in a browser: **http://127.0.0.1:8765/docs**

You should see the API explorer with six groups: `scores`, `audio`, `matrix`, `notation`,
`library`, `youtube`. Endpoints belonging to unbuilt epics are there too — they answer politely
with "not implemented yet" and name the epic that will fill them.

---

## 3. Frontend

In a **second terminal**:

```bash
cd aitu-frontend
npm install
npm run lint     # expect no output
npm run build    # expect "✓ built"
npm run dev
```

Open **http://localhost:5173**

You should land on **Playground → Upload / Input**, dark background, "AImpromptu" in blue at the
top left, and a small green **API online** chip at the top right.

> **If the chip says "API offline"** the backend is not running or is on a different port. The
> frontend expects `http://127.0.0.1:8765`; override with `VITE_AITU_API_URL` if you moved it.

---

## 4. The reference recording

Before going further, get your piano ready. Guide 2 will ask you to play:

> **Do Re Mi Fa Sol — one note per second, at 60 BPM, no sustain pedal, each note ringing its
> full second.**

That is five seconds of the simplest thing that can be obviously right or obviously wrong, and
several later guides reuse it.

---

## If it goes wrong

| Symptom | Cause |
|---|---|
| `uv sync` fails on torch | Check you are on Python 3.12 (`uv run python -V`) |
| `make test` skips lots of audio tests | ffmpeg is not on `PATH` |
| `available_engines()` shows `bytedance: False` | You skipped `uv sync --extra transcription` |
| `/docs` won't load | The backend terminal will show the error — usually a port already in use |
| Frontend blank page | Check the browser console; a stale `dist/` can be removed with `rm -rf dist` |

Next: [1 — Skeleton](epic-01-skeleton.md)
