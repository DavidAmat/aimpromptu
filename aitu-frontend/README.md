# aitu-frontend

React 19 + TypeScript + Vite app. It brings a recording in, shows how it was actually played, and
draws the sheet with `@aimpromptu/grid-notation` — a renderer built for this project, because
nothing off the shelf lays music out on a wall clock.

**Documentation:** [context/frontend/](../context/frontend/README.md) ·
rendering: [rendering.md](../context/frontend/rendering.md)

```bash
npm install && npm run dev
```

Backend: `http://127.0.0.1:8765` (override with `VITE_AITU_API_URL`).

## Source layout

```text
src/
  api/        # typed client, one module per backend router — no component calls fetch
  hooks/      # useProgress (SSE), selection, staged removals, element size
  layout/     # AppLayout, PlaygroundLayout, routes.ts (every path lives here)
  pages/      # one component per route
  state/      # WorkingArtifactProvider — the piece shared across Playground tabs
  ui/         # palette.ts, theme.ts, timestamps.ts and the shared MUI wrappers
  music/      # matrix contracts mirrored from the backend, note names, overrides
  piano/      # the 88-key SVG keyboard
  playback/   # the transport, the scrub bar, how a note rectangle is drawn
  print/      # the PDF writer
  components/
    time/     # PeakPlot, TimeScoreView (the ONLY file that touches the renderer)
    notes/    # the note toolbox and the staged-removals bar
    audio/    # recorder, upload, waveform and range selection
    input/    # transcription settings, compose a new piece
    editing/  # re-record a passage, add a passage
    library/  # playlists
    common/   # the floating bar and the draggable toolbox shell
```

## Rules

- **Colors** come from `src/ui/palette.ts` only. No hex literal in a component or stylesheet.
- **Requests** go through `src/api/`. No `fetch` in a component.
- **Routes** come from `src/layout/routes.ts`. No URL string literal in a component.
- **Components** are MUI. Aceternity UI is allowed for decoration only; every functional
  control stays MUI so behavior is consistent.
- **The renderer** is reached from `components/time/TimeScoreView.tsx` and nowhere else.
- **No component derives a note's figure.** The printed figure comes from the backend and is
  passed through.

```bash
npm run lint
npm run check:render   # draw a real score headlessly — layout failures are silent otherwise
```

**After pulling `../vexflow-v2`, rebuild it** (`npm run build` there). npm does not build a linked
dependency, and a stale `dist/` fails silently: the app keeps engraving with the old code and
nothing warns.
