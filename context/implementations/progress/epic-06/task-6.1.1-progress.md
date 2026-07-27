# Task 6.1.1 — Input sources UI · progress report

Status: **done, pending your manual trial.** Date: 2026-07-27.

> UI verification skipped per your instruction. Type-checks, lints and builds clean.

## Summary

`/playground/input` now has all five source modes behind an MUI tab strip.

| Mode | Component | Notes |
|------|-----------|-------|
| Upload audio | `AudioUpload` (Epic 3) | -> `POST /audio/upload` -> waveform preview |
| Record | `AudioRecorder` (Epic 3) | live bars, preview, name, save |
| Audio library | `AudioLibraryList` (Epic 3) | alias, duration, source chip, delete |
| Text notation | **`TextNotationInput`** (new) | -> `POST /sequence`, no engine involved |
| Matrix JSON | **`MatrixJsonInput`** (new) | dense or sparse, the file says which |

**Every mode ends by populating the working artifact** — the acceptance criterion. Audio modes set
`audioUuid` and clear any stale range; the two matrix modes clear `audioUuid` and set the tempo,
granularity and processing step from what was loaded.

The layout adapts: audio sources get a two-column view with the range selector and the
transcription settings beside them; the two matrix sources take the full width and hide the
settings entirely, because BPM and granularity are already baked into what they carry.

### Text notation

Two hands use **separate text areas**, not the inline `__` separator from `TODO.md`. The notation
spec already prefers this ("Text input uses **separate** right-hand and left-hand text areas (not
inline `__` separators)"), and the reason shows up in the UI: the hands must have the same frame
count, and two columns make a mismatch visible — the left field turns red and says
*"7 frame(s) — must match the right hand's 8"* before you can press anything.

Frame counting is live under each field. Trailing blank lines are dropped (almost always a stray
Enter) but interior ones are kept, because those are silences.

Pre-filled with the eight-frame example from the notation spec, and a "Reset to example" button.

### Matrix JSON

Validated locally before anything is sent, with messages that name what is missing —
*"This says `sparse: false` but carries neither `denseMatrix` nor `denseRMatrix`."* The backend's
Pydantic models remain the real gate; this just turns a future `422` into a sentence. On success it
shows the tempo, granularity, processing step, sparse/dense and frame count as chips, so you can
see you loaded what you meant to.

## Errors found and how they were solved

1. **`react-refresh/only-export-components`** on `TranscriptionSettings`, which exported a constant
   alongside the component. Moved `TRANSCRIPTION_GRANULARITIES` to `src/music/granularities.ts`.
   Third time this rule has bitten in this project — worth remembering: **a `.tsx` file exports
   components and nothing else.**
2. **`MatrixScore` was not re-exported from `src/api`.** The music contracts live in
   `src/music/types.ts`; `src/api/index.ts` now re-exports the ones components need, so a component
   has a single import path for both the calls and the shapes they carry.

## Deviations from the task file

- Separate text areas rather than the `__` separator (see above).
- Text notation and matrix JSON **do not yet persist** anything: they populate the working artifact
  in memory. Persisting them needs `POST /library/playground` with a name for the piece, which is
  the Matrix tab's save button (Epic 7) — asking for an artist and track name before the user has
  even seen the result would be the wrong moment.

## Verification

```
npx tsc -b, npm run lint      # clean
npx vite build                # 667 modules, 579 kB (184 kB gzipped)
```

No runtime test — there is still no frontend test runner in this repo.

## Manual trial for the supervisor

Open **Playground > Upload / Input** and walk the five tabs:

1. **Text notation** — press **Parse notation** on the pre-filled example. Expect
   *"Parsed 8 frame(s)"* and the Playground bar to switch to "Text notation". Then turn on
   **Two hands**, put four lines in the left field, and confirm it turns red and the button
   disables.
2. **Matrix JSON** — you have no exports yet (that is Epic 7), so try a wrong file: any `.json`
   should be rejected with a message naming the missing field, not a stack trace.
3. **Upload / Record / Audio library** — as in the Epic 3 trials.

The thing to judge: **does the tab strip make the five sources feel like one tab, or five?** The
task file asked for one tab with five modes, and that is a design call I would rather you make
after seeing it.

## For the next worker

- **Epic 7's save button** is what makes text notation and JSON durable. Until then they live only
  in the working artifact.
- New source modes go in `src/components/input/`; register them in the `SOURCES` array in
  `InputPage.tsx` with their `audio` flag, which is what drives the layout.
- `GRANULARITY_BEATS` (from `src/music/types.ts`) converts the artifact's granularity into the
  `timeStepSeconds` the `/sequence` endpoint wants — do not hardcode 0.5.
