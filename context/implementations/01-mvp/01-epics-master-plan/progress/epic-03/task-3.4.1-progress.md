# Task 3.4.1 — Waveform range selector · progress report

Status: **done, pending your manual trial.** Date: 2026-07-27.

> UI verification skipped per your instruction. Type-checks, lints and builds clean; nobody has
> dragged a handle yet.

## Summary

| File | Role |
|------|------|
| `src/components/audio/WaveformView.tsx` | draws peaks, selection shading and cursor |
| `src/components/audio/WaveformRangeSelector.tsx` | handles, text inputs, playback |
| `src/audio/time.ts` | `mm:ss.mmm` parse/format |
| `GET /audio/{uuid}/range` | server-side slice (backend, now real) |

`WaveformView` is deliberately split out with a `watermark` prop, because **Story 8.2 needs the
same drawing behind the piano roll** and should not inherit the drag logic.

### Display

One SVG rect per bucket from `GET /audio/{uuid}/waveform`, min to max, centred on the zero line.
The frontend never decodes audio. Total duration is labelled at both ends; zoom is out of scope
as the task says.

### Handles

Two draggable handles as absolutely-positioned overlays, with a MUI `Tooltip` showing
`mm:ss.mmm` **while dragging** (the task's requirement — it is `open={dragging === which}`, not
hover). Pointer events are bound to `window` during a drag, so the handle keeps following the
cursor outside the waveform, and **the handles cannot cross**: each is clamped by the other.

Text inputs accept `mm:ss.mmm` and stay in sync. `parseTime` is forgiving — `3:03`, `183`,
`183.5` and `03:03.123` all work — and **returns `null` rather than a guess** when the text is not
a time, so a half-typed value does not make the handles jump. On blur or Enter the value is
committed and clamped; if it was unparseable the field snaps back to the current value.

### Playback

Plain `<audio>` seeking within the already-downloaded file: **no round trip per range**, and the
cursor is just `currentTime` sampled on `requestAnimationFrame`. The follow loop stops the element
and parks the cursor at the range end. **Play all** ignores the selection; **Stop** rewinds to the
range start.

The component emits `{startSeconds, endSeconds}` to its parent — **once, at pointer-up**, not on
every drag frame. `/playground/input` feeds that straight into the working artifact's
`rangeStartSeconds` / `rangeEndSeconds`, so Epic 6 will transcribe only the selection.

### Backend `/audio/{uuid}/range`

Implemented (it was a `501` placeholder) using `formats.slice_wav`. Not on the selector's hot path
— it exists for callers that need the *bytes*: Epic 6's "transcribe only this passage" and Epic
11's tempo-compressed preview. `422` on a backwards range, `409` if the audio was never
normalized.

## Errors found and how they were solved

1. **`react-hooks/set-state-in-effect`.** The loader reset `peaks`/`error` synchronously in the
   effect. Rewritten with the now-standard pattern: one state object tagged with
   `${audioUuid}:${points}`, freshness derived during render, no synchronous `setState`.
2. **Double emission.** The range was emitted both from `applyRange` and from an effect watching
   `dragging`, so a text edit fired the callback twice. The effect is gone; the pointer-up handler
   emits once.
3. **Handle crossing.** Dragging start past end produced a negative-width selection. Each handle is
   now clamped by the other inside the same state update, so it can only ever reach zero width.

## Deviations from the task file

- Range playback is **client-side**, not via the backend endpoint. It is faster (no re-download per
  range), the cursor is exact, and pause/restart is free. The backend endpoint still exists for the
  cases that need bytes.
- Added `WaveformView` as a separate component (see above).

## Verification

```
npx tsc -b, npm run lint, npx vite build   # clean
pytest tests/test_audio_store.py           # 42 passed — includes the new range endpoint
pytest                                     # 348 passed overall
```

The backend range endpoint is covered end to end: slicing 1.0-2.0 s out of a 3 s tone returns a
WAV that really is 1 s long, and a backwards range is a `422`. The frontend interaction is not
covered — no test runner in this repo, and dragging needs a DOM.

## Manual trial for the supervisor — this is the acceptance criterion

Use the recording you made in Task 3.3.1, or upload a song you know well.

1. **Playground > Upload / Input**, click the audio in **Audio library**.
2. The **Range** panel draws the waveform. For the five-note scale you should see five clusters.
3. **Drag the left handle to about `00:10`** and the right to `00:15`. While dragging, a tooltip
   above the handle shows `mm:ss.mmm` live. The selection shades in lavender.
4. **Refine with the text inputs**: type `00:10.500` into Start, press Enter. The left handle jumps
   there and "4.500 selected" updates. Type nonsense (`abc`) and confirm the field snaps back
   rather than moving the handle.
5. **Play range**: a pink cursor sweeps the selection and **stops exactly at the right handle** —
   that is the check that matters. Then **Play all** and confirm it plays the whole file.
6. Try dragging the left handle past the right — it should stop, not cross.

Because the selection is stored on the working artifact, switching to another Playground tab and
back must keep it.

## For the next worker

- **Epic 6, Story 6.2**: the range is already on the working artifact
  (`rangeStartSeconds` / `rangeEndSeconds`). Pass it to `matrixApi.transcribe` and transcribe only
  the selection when it is narrower than the whole file.
- **Epic 8, Story 8.2**: reuse `<WaveformView watermark />` for the piano-roll background; do not
  recompute peaks in the browser.
- **Epic 11**: `GET /audio/{uuid}/range` gives you the bytes of a passage for the slow-recording
  preview.
- `src/audio/time.ts` is the only place that knows the `mm:ss.mmm` format. Use it everywhere.
