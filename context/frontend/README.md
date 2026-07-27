# aitu-frontend

React 19 + TypeScript + Vite app that renders sparse-COO piano scores as sheet music with
**VexFlow 5**. Consumes JSON from aitu-backend; owns **all** music rendering.

## UI areas

Structured by feature, not by source file:

| Area | Doc | Components |
|------|-----|------------|
| App shell | [app-shell.md](app-shell.md) | `App.tsx` — fetch `/scores`, global layout state |
| Loaded scores | [loaded-scores.md](loaded-scores.md) | `ScoreStack`, shared `LayoutControls` |
| Compose panel | [compose-panel.md](compose-panel.md) | `SequenceComposer` — `POST /sequence` |
| Rendering | [rendering-pipeline.md](rendering-pipeline.md) | `matrixToNotation.ts`, `PianoSheet.tsx`, `notes.ts` |
| Timestamps | [timestamps.md](timestamps.md) | `audio/time.ts`, `ui/timestamps.ts` — the `mm:ss.cc` / `f:N · start` rule |

## Data flow

```
GET /scores  or  POST /sequence  →  MatrixScore  →  matrixToNotation  →  PianoSheet (VexFlow SVG)
```

Notation contract: [shared/notation-spec.md](../shared/notation-spec.md).

## Run

```bash
cd aitu-frontend && npm install && npm run dev
```

Backend expected at `http://127.0.0.1:8765`; override with `VITE_AITU_API_URL`.
See [04-local-development.md](../04-local-development.md).

## Where to look deeper

- [rendering-pipeline.md](rendering-pipeline.md) — sparse decode → VexFlow
- [documentation/services/frontend/](../../documentation/services/frontend/) — matrix-to-notation,
  piano-sheet, notes, components
- [shared/notation-spec.md](../shared/notation-spec.md) — notation contract
