# Task 1.2.1 — App shell and navigation · progress report

Status: **done**. Date: 2026-07-26.

> Implemented **after** Task 1.2.2 (theme first) — see that report for why.

## Summary

**Routing** (`react-router-dom@^7.18`, `BrowserRouter` in `main.tsx`). Every path is declared once
in `src/layout/routes.ts`; no component writes a URL string.

| Path | Page |
|------|------|
| `/` | redirect to `/playground/input` |
| `/youtube` | `YouTubePage` |
| `/playground` | redirect to `/playground/input` |
| `/playground/input` | `InputPage` |
| `/playground/matrix` | `MatrixPage` |
| `/playground/piano-roll` | `PianoRollPage` |
| `/playground/notes-falling` | `NotesFallingPage` |
| `/playground/notation` | `NotationPage` |
| `/library` | `LibraryPage` |
| `/library/play/:id` | `PerformancePage` |
| `*` | `NotFoundPage` |

Two nested layouts: `AppLayout` (brand bar, top section tabs, backend-status chip) and
`PlaygroundLayout` (the five tabs plus the working-piece banner). Each page renders a
`Placeholder` naming the epic and story that fills it, so the shell documents the plan.

`BackendStatus` (app bar, right) pings `/health` once and shows "API online"/"API offline" —
the backend has to be running for anything to work, so surfacing it beats a failed request per page.

**Working-artifact context** — split across three files so React Fast Refresh stays happy
(a `.tsx` exporting both a component and non-components trips `react-refresh/only-export-components`):

| File | Contents |
|------|----------|
| `state/workingArtifactContext.ts` | `WorkingArtifact` type, defaults, context object |
| `state/WorkingArtifactProvider.tsx` | the provider component |
| `state/useWorkingArtifact.ts` | the hook (throws outside the provider) |

It holds `artifactId`, `audioUuid`, `label`, `tempoBpm`, `granularity`, `matrixProcessingStep` and
the optional audio range, and mirrors itself into `sessionStorage` so a reload mid-session does not
lose the piece. `PlaygroundLayout` renders it as three pills plus a Clear button.

**Typed API client** — `src/api/client.ts` (base URL from `VITE_AITU_API_URL`, `ApiError` carrying
`status` + backend `detail`, plus an `ApiError.notImplemented` getter for the `501` placeholders,
query-string building, `upload()` for multipart) and one module per backend router:
`scores.ts`, `audio.ts`, `matrix.ts`, `notation.ts`, `library.ts`, `youtube.ts`, re-exported from
`src/api/index.ts`. Types for the shapes later epics will return (`AudioItem`, `MatrixEnvelope`,
`Granularity`, `MatrixProcessingStep`, `PlaygroundTrack`, `LibraryTrack`, `Playlist`, …) are
declared now so pages can be written against them.

**Progress plumbing** — `src/hooks/useProgress.ts` opens an `EventSource` on the URL it is given
(`null` = idle), decodes the backend's `ProgressEvent` frames (same field names as
`aitu_backend/progress.py`), tracks the stage list, and closes on the terminal `done` event, on
error or on unmount. `src/components/ProgressBanner.tsx` renders that state as a MUI
`LinearProgress` with the stage name and percentage.

## Errors found and how they were solved

1. **`react-hooks/set-state-in-effect` (ESLint error, not a warning).** The first version called
   `setStatus("running")` synchronously inside the effect. Rewritten so all stream data lives in
   **one state object tagged with the URL it belongs to**, and `status` is *derived* during render
   (`url === null ? "idle" : outcome`). Stale values from a previous URL are discarded by comparing
   the tag, and `reset()` bumps a generation counter that re-runs the effect. No `setState` in the
   effect body at all. Worth copying wherever a later epic subscribes to something.
2. **MUI v9 system props.** Same `TS2769` wave described in the 1.2.2 report; `justifyContent` /
   `alignItems` / `fontWeight` moved into `sx`.
3. **Rolldown `INEFFECTIVE_DYNAMIC_IMPORT`.** `api/index.ts` lazily imported `./client` for the
   `health()` helper while six siblings imported it statically. Made it a static import.
4. **`vite build` fails in the Linux sandbox** with `EPERM: unlink .../dist/...` — the mounted
   volume refuses deletes, so Vite cannot empty a pre-existing `dist/`. Built with
   `--outDir /tmp/aitu-dist` instead. On the Mac `npm run build` works normally.

## Deviations from the task file

- The old single-page MVP layout was removed from `App.tsx`, as the task allows. **Kept on disk
  and still type-checking**: `src/components/{PianoSheet,ScoreStack,SequenceComposer,LayoutControls}.tsx`,
  `src/music/*` and `src/App.css`, all for Epic 9 to reuse. They are currently unreferenced —
  that is deliberate, not dead code to delete.
- Added `BackendStatus` and `NotFoundPage`, which the task did not name.
- `sessionStorage` persistence of the working artifact is an addition; the task only required the
  context to survive tab switches.

## Verification

```
npx tsc -b                                    # clean
npm run lint                                  # clean
npx vite build --outDir /tmp/aitu-dist        # 479 modules, 417 kB (134 kB gzipped)
```

Runtime checks were **not** performed — per the supervisor's instruction to skip UI checks.

## Manual trial for the supervisor

```bash
cd aitu-backend && uv sync && make serve      # terminal 1
cd aitu-frontend && npm install && npm run dev # terminal 2
```

1. Open `http://localhost:5173/` — it should land on **Playground > Upload / Input**, dark theme,
   with an **API online** chip top right.
2. Click through all five Playground tabs, then **YouTube to Audio** and **Piano Library**.
   Every page shows a blue "Coming in Epic N" box naming its story.
3. Visit `/library/play/demo` directly — the performance placeholder shows `Piece: demo`.
4. Working-artifact check: the Playground bar reads `none loaded · 60 BPM · semicorchea · clean`.
   Switch tabs — those pills must not reset. Reload the page — they must survive (sessionStorage).
5. Stop the backend and reload: the chip must flip to **API offline**.
6. Visit `/nonsense` — the not-found page with a "Go to the Playground" button.

The old text-notation page is gone by design; if you want it back for comparison, it is in git
history at `e663fbc:aitu-frontend/src/App.tsx`.

## For the next worker

- Add endpoints to `src/api/<router>.ts` and export from `src/api/index.ts`. Never `fetch` in a page.
- Add paths to `src/layout/routes.ts`, never a literal in a component.
- Epic 4/6: `matrixApi.transcribe()` returns a `jobId`; feed `matrixApi.progressUrl(jobId)` into
  `useProgress` and render `<ProgressBanner>`. The backend must terminate the stream with a named
  `done` SSE event — the hook relies on it to distinguish success from a dropped connection.
- The `MatrixEnvelope` type in `src/api/matrix.ts` is the TS mirror of the Task 1.3.1 Pydantic model;
  keep the two in step.
