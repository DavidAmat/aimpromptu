# 3 — Transcription (Epic 4)

**What this epic did:** turned audio into the piano matrix. This is the part of the project that
has never actually run — the model would not install in the sandbox — so **this guide is the most
important one**, and the most likely to find a real bug.

About 20 minutes. You need `uv sync --extra transcription` done (see [setup](00-setup.md)) and the
recording from [guide 2](epic-03-audio-io.md).

---

## 3.1 — First: does the model load at all?

```bash
cd aitu-backend
uv run python -c "
from aitu_backend.transcription.engine import create_engine
e = create_engine('bytedance')
print('engine ready:', e.name, 'on', e.device)
"
```

**The first run downloads a 165 MB checkpoint** and shows a progress bar. It goes to
`~/piano_transcription_inference_data/`. Later runs skip it.

Expected output ends with: `engine ready: bytedance on cpu`

> **Two things worth knowing.**
>
> **Why the download is ours.** The model package normally fetches its own checkpoint using
> `wget` — a tool macOS does not ship. On your Mac that would fail *silently*, leave an empty
> file, and then die inside the model loader with an error that says nothing about a missing
> download. So the backend fetches it itself, verifies the size, and only then hands over.
>
> **Why "cpu" and not the M4 GPU.** The model package only moves itself onto a GPU when the device
> is CUDA (an NVIDIA card). Passing `mps` would be accepted and then quietly ignored. On an M4 the
> CPU is fast enough — a one-minute clip takes seconds — so this is a note, not a problem.

---

## 3.2 — Does it hear the right notes? ⭐

This is the acceptance test for the whole epic.

```bash
uv run python notebooks/transcription-benchmark/benchmark.py --store
```

This runs every installed engine over every audio in your store and prints what each one heard.

**For your `Do Re Mi Fa Sol` recording, the `first:` line should read roughly:**

```
bytedance        3.41s  5 notes over 4.98s — most common: Do-4 x1, Re-4 x1, ...
                 first: Do-4@0.00s Re-4@1.00s Mi-4@2.00s Fa-4@3.00s Sol-4@4.00s
```

**What to check, in order of importance:**

1. **Five notes**, not four, not fifteen.
2. **Ascending** — Do, Re, Mi, Fa, Sol.
3. **About one second apart.**
4. The octave matches where you actually played (`-4` is the octave from middle C up).

Small timing wobbles are expected and fine — that is what the rounding step exists for. What
matters is that it heard the notes you played.

**If the notes are wrong**, do not change anything else yet:

```bash
uv sync --extra basic-pitch
uv run python notebooks/transcription-benchmark/benchmark.py --store
```

That runs the second engine on the same audio, and prints both side by side. **Send me the
output** — choosing between engines on real recordings is exactly the decision this script exists
to inform, and it is your call, not mine.

---

## 3.3 — The full pipeline

Now the same thing through the app. Make sure `make serve` is running.

Find your recording's id:

```bash
curl -s 127.0.0.1:8765/audio/ | python3 -m json.tool | grep -E '"uuid"|"alias"'
```

Start a transcription (paste your id in place of `<uuid>`):

```bash
JOB=$(curl -s -X POST 127.0.0.1:8765/matrix/transcribe \
  -H 'Content-Type: application/json' \
  -d '{"audioUuid":"<uuid>","tempoBpm":60,"granularity":"negra"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["jobId"])')

curl -N 127.0.0.1:8765/matrix/progress/$JOB
```

**You should see a stream of lines naming each stage in turn**, then it ends:

```
data: {"stage": "transcribe", ...}
data: {"stage": "events", ...}
data: {"stage": "collapse", ...}
data: {"stage": "clean", ...}
data: {"stage": "two-hands", ...}
event: done
```

> **What those five stages are.** This is the whole idea of the project, in order:
>
> 1. **transcribe** — the model listens and reports "this key, from this second to that second".
> 2. **events** — those timings are placed on a fine grid (32nd notes) and rounded to whole
>    squares. A note that lasted 1.03 seconds becomes exactly one beat.
> 3. **collapse** — that fine grid is merged down to the resolution you asked for. Fewer, bigger
>    squares — a less cluttered page.
> 4. **clean** — long held notes are cut short the moment anything else is played. Musically a
>    simplification; on paper the difference between a readable score and a wall of tied notes.
> 5. **two-hands** — everything from middle C up goes to the right hand, everything below to the
>    left.
>
> The result of **step 2** is saved forever. Everything after it can be redone from that in
> milliseconds — which is the next check.

Now look at what it heard:

```bash
curl -s "127.0.0.1:8765/matrix/<uuid>?granularity=negra&step=clean" | python3 -c "
import sys, json
m = json.load(sys.stdin)['matrix']
rows = ['La-0','La#-0','Si-0'] + [f'{n}-{o}' for o in range(1,8)
        for n in ['Do','Do#','Re','Re#','Mi','Fa','Fa#','Sol','Sol#','La','La#','Si']] + ['Do-8']
print([(col, rows[row]) for row, col, on in zip(m['rows'], m['cols'], m['onset']) if on != -1])
"
```

**Expected:** `[(0, 'Do-4'), (1, 'Re-4'), (2, 'Mi-4'), (3, 'Fa-4'), (4, 'Sol-4')]`

One note per column, columns 0 to 4, ascending. **That is a piano matrix**, and it is the thing
every later epic draws, plays and engraves.

And the files:

```bash
ls aitu-backend/data/audio/<uuid>/matrices/
# raw.npz  collapsed_negra.npz  clean_negra.npz
# two-hands_negra_right.npz  two-hands_negra_left.npz
```

---

## 3.4 — The promise: changing resolution is instant

```bash
time curl -s -X POST 127.0.0.1:8765/matrix/recompute \
  -H 'Content-Type: application/json' \
  -d '{"audioUuid":"<uuid>","tempoBpm":60,"granularity":"semicorchea"}' > /dev/null
```

**What you should see:** it returns in **well under a second**, and the backend terminal shows
**no model activity at all**.

> **Why this matters.** Transcribing is slow; everything after it is arithmetic. Because the fine
> grid from step 2 is kept, changing the resolution — or the tempo — just redoes steps 3 to 5 from
> it. That is what will make the resolution dropdown in the Matrix tab feel instant instead of
> making you wait for the model again.

---

## What "working" looks like

- The engine loads and reports `cpu`.
- The benchmark hears **five ascending notes about a second apart**.
- The progress stream names all five stages and ends with `done`.
- The matrix has one onset per column, ascending.
- Five `.npz` files exist.
- Changing resolution returns in milliseconds with no model activity.

## If it goes wrong

| Symptom | Likely cause | What to do |
|---|---|---|
| `EngineUnavailable` | The extra was not installed | `uv sync --extra transcription` |
| Download stalls | Zenodo is slow; it is a 165 MB one-off | Retry; a partial file is discarded, not kept |
| Model loads but finds no notes | Recording too quiet, or not piano | Check you can hear it in the preview player |
| Finds far too many notes | Background noise, or a very reverberant room | Try the Basic Pitch engine and compare |
| Notes right, timing wrong | The BPM you entered is not the BPM you played | This is expected and important — see below |
| A crash inside the model | The one part never executed | **Send me the traceback**; it will be a one-line fix |

> **On tempo.** Everything here is snapped onto a grid derived from the BPM you typed. If you
> played at 63 and said 60, notes drift by a whole square every twenty beats. That is a property
> of the design, not a bug — but if your notes are consistently landing one square late, try
> entering the tempo you actually played.

Next: [4 — Playground Input](epic-06-playground-input.md)
