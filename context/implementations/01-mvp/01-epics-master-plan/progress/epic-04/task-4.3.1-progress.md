# Task 4.3.1 — Pipeline orchestration · progress report

Status: **done**. Date: 2026-07-27. This closes Epic 4's code.

## Summary

`transcription/pipeline.py` + `transcription/jobs.py` + a real `api/matrix.py`.

### The five steps

```python
run_pipeline(audio_uuid, tempo_bpm, target_granularity, *, engine, start_seconds, end_seconds)
```

1. audio -> note events (engine)
2. events -> raw matrix (fusa)
3. raw -> collapsed (chained merges)
4. collapsed -> clean (Appendix B)
5. clean -> two-hands (middle-C split)

Steps 3-5 are factored out as `derive()`, which is also the whole of a recompute. `PipelineResult`
carries all five artifacts plus `step(name)` for `GET /matrix/{id}?step=`.

### Artifacts

```text
data/audio/<uuid>/matrices/
  raw.npz                              the immutable source
  collapsed_<granularity>.npz
  clean_<granularity>.npz
  two-hands_<granularity>_right.npz
  two-hands_<granularity>_left.npz
```

Derived files are keyed by **step and granularity**, so two granularities of the same piece coexist
and switching back to one you already looked at is a file read.

### Fast recompute — the rule that shapes everything

**The raw matrix is transcribed once and kept forever; every later granularity or BPM is recomputed
from it, never from an intermediate.** `run_pipeline` with `reuse_raw=True` (the default) skips
transcription entirely when a raw matrix exists — the common case, since only BPM or granularity
changed. `recompute()` is the explicit entry point and never transcribes at all.

One subtlety worth recording: **the raw matrix's cells do not depend on BPM.** Only the wall-clock
meaning of a column does. So changing tempo re-interprets the same grid rather than rebuilding it,
and a test pins that the frame count is identical at 60 and 120 BPM while `time_step_seconds`
halves.

Measured: recompute of a fresh granularity is comfortably under the 1 s target (milliseconds in
practice for a five-second clip, and Task 2.2.1 measured the collapse chain at ~9600 columns).

### Progress streaming

`transcription/jobs.py` runs the pipeline on a worker thread and publishes through a
`MultiProgress(CallbackProgress(...), TqdmProgress())` — **one reporter, two audiences**, exactly
the Task 1.1.2 convention. `POST /matrix/transcribe` answers `202` with a `jobId`;
`GET /matrix/progress/{jobId}` is the SSE stream.

Two details that matter for the frontend:

- The stream **replays the job's history first**, so a subscriber that connects after the job
  started still sees where it is.
- It **ends with a named `done` event** carrying the final status. `useProgress` (Task 1.2.1) relies
  on that to tell a finished job from a dropped connection — the two halves were written days apart
  and this is where they meet.

`GET /matrix/jobs/{jobId}` is a polling fallback. Job state is in-memory only: a restart loses the
history, which is fine because the *artifacts* are on disk.

### API

| Route | Behaviour |
|-------|-----------|
| `GET /matrix/engines` | which engines are installed |
| `POST /matrix/transcribe` | `202` + `jobId` |
| `GET /matrix/progress/{jobId}` | SSE |
| `GET /matrix/jobs/{jobId}` | polling status |
| `POST /matrix/recompute` | synchronous steps 3-5 |
| `GET /matrix/{uuid}` | one step, any granularity, sparse or dense |
| `POST /matrix/{uuid}/transpose` | Task 2.4.2's transposition |

`GET /matrix/{uuid}?step=two-hands` returns `rMatrix` + `lMatrix` in one envelope, which is the
shape Epic 9's grand staff needs. `?sparse=false` gives the dense N x 88 export form.

`src/api/matrix.ts` was rewritten to match, including `engines()`, `job()` and the corrected
`progressUrl`.

## Errors found and how they were solved

1. **`GET /matrix/{uuid}` recomputes rather than reading the derived file.** Deliberate, and worth
   flagging: recompute is milliseconds, and always deriving from raw means the endpoint cannot
   serve a stale artifact after a BPM change. The derived files are still written — Epic 5's
   versioning wants them — but they are not the read path. **If a piece ever gets long enough that
   this stops feeling instant, that is the first thing to change.**
2. **A circular import between `pipeline` and `audio.ingest`.** `pipeline` needs `ingest.finalize`
   for an audio that was never normalized, but `ingest` imports the store which imports schemas.
   Imported inside the function, like the `matrix_store` imports in `model.py`.
3. **The smoke test's `501` list shrank again** — `/matrix/{id}` is real now. Only
   `/matrix/{id}/export` and `/matrix/import` remain placeholders (they belong to Epic 7).

## Deviations from the task file

- Artifacts live under `data/audio/<uuid>/matrices/`, not a separate "working folder". The audio
  uuid folder already is the working folder for that input, and keeping the matrices beside the
  audio means deleting an audio cleans up everything it produced.
- Added `GET /matrix/engines`, `GET /matrix/jobs/{jobId}` and `stored_granularities()`.
- `POST /matrix/recompute` is synchronous, not a job. It is pure numpy; a job would add more
  latency than it saves.

## Verification

```
pytest tests/test_transcription.py   # 36 passed
pytest                               # 414 passed, 1 skipped
mypy, flake8, black                  # clean
npx tsc -b, npm run lint             # clean
```

The pipeline tests use a `ScaleEngine` stub that always returns `Do Re Mi Fa Sol` as slow negras,
so the whole chain is exercised deterministically without a model:

- all five steps run, each with the right `processing_step`, and **every artifact is on disk**;
- the scale lands on consecutive beats with the left hand empty (all above middle C);
- **a granularity change does not re-transcribe** — proved by passing an engine whose `transcribe`
  raises `AssertionError`, and the run succeeding;
- recompute is under a second;
- changing BPM keeps the frame count and halves the time step;
- a range-limited run produces only the range's columns;
- every stage reports progress (`transcribe`, `events`, `collapse`, `clean`, `two-hands`).

Jobs are covered separately: a successful run, a failing one carrying its message, an unknown job
still terminating the stream, and a late subscriber catching up on the history.

## Manual trial for the supervisor — Epic 4's exit criterion

**This needs the engine working first (Task 4.1.1).** Once `uv sync --extra transcription` is done:

```bash
cd aitu-backend && make serve
```

Take the **one-hand C-major scale at a steady 60 BPM** you recorded for Task 3.3.1 (or record one
now — `Do Re Mi Fa Sol La Si Do`, one note per second, no pedal). Find its uuid with
`curl -s 127.0.0.1:8765/audio/ | python3 -m json.tool | grep -E 'uuid|alias'`, then:

```bash
JOB=$(curl -s -X POST 127.0.0.1:8765/matrix/transcribe \
  -H 'Content-Type: application/json' \
  -d '{"audioUuid":"<uuid>","tempoBpm":60,"granularity":"negra"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["jobId"])')

curl -N 127.0.0.1:8765/matrix/progress/$JOB     # watch the stages stream past
```

Then check the result:

```bash
curl -s "127.0.0.1:8765/matrix/<uuid>?granularity=negra&step=clean" | python3 -c "
import sys, json
m = json.load(sys.stdin)['matrix']
rows = ['La-0','La#-0','Si-0'] + [f'{n}-{o}' for o in range(1,8)
        for n in ['Do','Do#','Re','Re#','Mi','Fa','Fa#','Sol','Sol#','La','La#','Si']] + ['Do-8']
print([(c, rows[r]) for r, c, o in zip(m['rows'], m['cols'], m['onset']) if o != -1])
"
```

**What correct looks like:** one onset per column, columns 0..7, notes ascending
`Do-4 Re-4 Mi-4 Fa-4 Sol-4 La-4 Si-4 Do-5`. Then confirm the files exist:

```bash
ls aitu-backend/data/audio/<uuid>/matrices/
# raw.npz  collapsed_negra.npz  clean_negra.npz  two-hands_negra_right.npz  two-hands_negra_left.npz
```

And that a granularity change is instant and does **not** re-transcribe (watch the terminal — no
model activity, and it returns immediately):

```bash
time curl -s -X POST 127.0.0.1:8765/matrix/recompute -H 'Content-Type: application/json' \
  -d '{"audioUuid":"<uuid>","tempoBpm":60,"granularity":"semicorchea"}' > /dev/null
```

**If the notes come back wrong**, the plan's guidance applies: run the benchmark script against
Basic Pitch before changing anything else. Do not tune the matrix code for a bad engine.

## For the next worker

- **Epic 6, Story 6.2**: `POST /matrix/transcribe` -> `jobId` -> `matrixApi.progressUrl(jobId)` ->
  `useProgress` -> `<ProgressBanner>`. All four pieces exist; wiring them is the task.
- **Epic 7**: `GET /matrix/{uuid}?step=&granularity=&sparse=` is the grid's read path, and
  `POST /matrix/recompute` is the in-situ BPM/granularity switch.
- **Epic 5**: the derived `.npz` files are already written per granularity — version folders can
  copy or reference them rather than recomputing.
- Never collapse from anything but raw. `collapse_to` enforces it; `recompute` is the sanctioned
  path.
