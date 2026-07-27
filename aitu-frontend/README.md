# aitu-frontend

React + TypeScript + Vite app. Consumes **aitu-backend** and renders sheet music with VexFlow.

**Documentation:** [context/frontend/](../../context/frontend/README.md)

```bash
npm install && npm run dev
```

Backend: `http://127.0.0.1:8765` (override with `VITE_AITU_API_URL`).

## Source layout

```text
src/
  api/        # typed client, one module per backend router — no component calls fetch
  hooks/      # useProgress (SSE)
  layout/     # AppLayout, PlaygroundLayout, routes.ts (every path lives here)
  pages/      # one component per route, placeholders until their epic lands
  state/      # WorkingArtifactProvider — the piece shared across Playground tabs
  ui/         # palette.ts, theme.ts and the shared MUI wrappers
  music/      # matrix -> notation logic (reused by Epic 9)
  components/ # PianoSheet and the VexFlow renderer (reused by Epic 9)
```

## Rules

- **Colors** come from `src/ui/palette.ts` only. No hex literal in a component or stylesheet.
- **Requests** go through `src/api/`. No `fetch` in a component.
- **Routes** come from `src/layout/routes.ts`. No URL string literal in a component.
- **Components** are MUI. Aceternity UI is allowed for decoration only; every functional
  control stays MUI so behavior is consistent.

`npm run lint` before committing.
