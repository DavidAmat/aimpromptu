# Task 1.2.1 — App shell and navigation

Replace the current single-page MVP with the full app shell. The old page's rendering pipeline (`matrixToNotation.ts`, `PianoSheet.tsx`, `src/music/*`) is kept and will be reused by Epic 9; the page layout itself can be deleted.

## Subtask 1.2.1.1 — Sections and tabs

Introduce routing (react-router) with this navigation tree:

```text
/youtube                     YouTube to Audio
/playground/input            Playground > Upload / Input
/playground/matrix           Playground > Matrix
/playground/piano-roll       Playground > Piano Roll
/playground/notes-falling    Playground > Notes Falling
/playground/notation         Playground > Music Notation
/library                     Piano Library (tracks, playlists)
/library/play/:id            Performance view (read-only)
```

Each page starts as a placeholder component with the tab chrome in place. Playground tabs share a "current working artifact" context (selected input file / uuid) so switching tabs keeps the loaded piece.

## Subtask 1.2.1.2 — Typed API client

One `src/api/client.ts` with a typed fetch wrapper, base URL from `VITE_AITU_API_URL`, and per-router modules mirroring the backend `api/` files. No component calls `fetch` directly.

## Subtask 1.2.1.3 — Progress streaming plumbing

A `useProgress` hook consuming SSE (`EventSource`) from backend progress endpoints, rendering a MUI progress bar. Used later by transcription and recompute flows.

## Acceptance

All routes navigable, working-artifact context persists across Playground tabs, lint passes.
