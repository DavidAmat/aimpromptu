# Task 6.2.1 — Transcription settings and launch · progress report

Status: **done, pending your manual trial.** Date: 2026-07-27. This closes Epic 6.

> UI verification skipped per your instruction. The end-to-end run also depends on a working
> transcription engine, which has never executed — see the Task 4.1.1 report.

## Summary

`src/components/input/TranscriptionSettings.tsx` — BPM, granularity, engine, range summary, Run,
and the progress bar. Wired into `/playground/input` beneath the range selector.

### Settings

- **BPM**, numeric, default 60, bounded 20–300. Stored on the working artifact, so it survives tab
  switches and reloads.
- **Temporal resolution**: `Negra`, `Corchea`, `Semicorchea`, `Fusa` — the four the task file names.
  (`redonda`, `blanca` and `semifusa` are legal matrix granularities but meaningless as
  transcription *targets*; the reasoning is written down in `src/music/granularities.ts`.)
  Helper text: *"Changeable later without re-transcribing"*, which is true and is the whole point
  of the raw-matrix design.
- **Engine** dropdown, populated from `GET /matrix/engines`. Uninstalled engines are listed but
  disabled, and if **no** real model is installed the panel shows a warning naming the fix:
  *"...only the `silent` engine is available and every piece will come out empty. Install one with
  `uv sync --extra transcription`."* Without that, an empty matrix would look like a bug in the
  pipeline rather than a missing download.

### Range restriction

The range comes from the working artifact, where the Task 3.4.1 selector puts it. A range is only
treated as *restricting* when it is actually narrower than the file — dragging a handle and
dragging it back should not silently change what gets transcribed. The panel states which case you
are in: *"Transcribing only 03:01.000 – 03:22.000"* or *"Transcribing the whole audio."*

### Run and handoff

`POST /matrix/transcribe` -> `jobId` -> `useProgress(matrixApi.progressUrl(jobId))` ->
`<ProgressBanner>`. On the stream's terminal `done` event the page navigates to the Matrix tab.

This is the first place all of Epic 1's plumbing meets Epic 4's: the SSE hook written in Task 1.2.1
consumes the frames emitted by the job runner written in Task 4.3.1, and the named `done` event is
the contract between them. **That contract has never been exercised against a live server** — it is
the single most likely thing to need a fix tomorrow.

The handoff is by `audioUuid`, not an artifact id: the pipeline writes its artifacts under the
audio's uuid folder, so the Matrix tab reads them straight back with
`GET /matrix/{uuid}?step=&granularity=`.

## Errors found and how they were solved

Nothing broke, but one thing is worth flagging as a **known gap**: the Matrix tab is still a
placeholder (Epic 7). So after a successful run the app navigates to a page that says *"Coming in
Epic 7"*. That is correct behaviour for where the plan is, not a bug — but it means the trial below
ends at a `curl`, not at a picture.

## Deviations from the task file

- Added the engine dropdown and the no-engine warning.
- The Run button is disabled with no audio loaded and explains why, rather than being hidden.

## Verification

```
npx tsc -b, npm run lint      # clean
npx vite build                # 667 modules, 579 kB (184 kB gzipped)
```

The backend half of this flow is covered by `tests/test_transcription.py` (36 tests), including the
`202` + job + `done` sequence over HTTP with a stub engine. What is untested is the browser end of
the SSE connection.

## Manual trial for the supervisor — Epic 6's acceptance criterion

**Prerequisite**: `cd aitu-backend && uv sync --extra transcription` (see the Task 4.1.1 report —
expect the model checkpoint to download on first use).

1. `make serve` and `npm run dev`.
2. **Playground > Upload / Input > Upload audio**. Upload a piano piece you know.
3. In **Range**, drag out roughly ten seconds of a passage you can hum.
4. In **Transcription settings**: BPM to whatever that passage is actually played at,
   resolution **Corchea**.
5. Press **Run transcription**.

**What correct looks like:** the progress bar names each stage in turn — `transcribe`, `events`,
`collapse`, `clean`, `two-hands` — then the app lands on the **Matrix** tab. That tab is still an
Epic 7 placeholder, so to see the result:

```bash
ls aitu-backend/data/audio/<uuid>/matrices/
# raw.npz  collapsed_corchea.npz  clean_corchea.npz  two-hands_corchea_right.npz  two-hands_corchea_left.npz

curl -s "127.0.0.1:8765/matrix/<uuid>?granularity=corchea&step=clean" | python3 -m json.tool | head -20
```

**Things most likely to go wrong, in order:**

1. The engine itself (Task 4.1.1) — most likely by a wide margin.
2. The SSE stream not reaching the browser. If the bar sits at 0% but the terminal shows tqdm
   progress, the job is fine and the stream is the problem — check the browser console for the
   `EventSource` connection.
3. The `done` event not arriving, leaving the bar at 99% forever. Same diagnosis, opposite symptom.

Then confirm the promise this whole design rests on: **change the resolution and it should not
re-transcribe.**

```bash
time curl -s -X POST 127.0.0.1:8765/matrix/recompute -H 'Content-Type: application/json' \
  -d '{"audioUuid":"<uuid>","tempoBpm":60,"granularity":"semicorchea"}' > /dev/null
```

That should return in milliseconds with no model activity in the backend terminal.

## For the next worker

- **Epic 7** is the natural next step and unblocks the visual half of every trial above: the Matrix
  tab is where a transcription finally becomes something you can look at.
- The in-situ BPM/granularity switch (Story 7.3) is `POST /matrix/recompute` — do **not** re-run
  `/matrix/transcribe` for it.
- `useProgress` + `<ProgressBanner>` is the pattern for any long backend job; Epic 11's slow
  re-recording will want it too.
