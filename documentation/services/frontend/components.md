> Context: [app-shell.md](../../../context/frontend/app-shell.md) · [compose-panel.md](../../../context/frontend/compose-panel.md) · [loaded-scores.md](../../../context/frontend/loaded-scores.md)

# Components

React components in `aitu-frontend/src/components/` plus root `App.tsx`.

## App.tsx

| Concern | Detail |
|---------|--------|
| API base | `VITE_AITU_API_URL` or `http://127.0.0.1:8765` |
| Fetch | `GET /scores` on mount |
| Global layout | `pxPerNote`, `lyricsGap`, `lyricsFontSize` state |
| Children | `LayoutControls` → `ScoreStack` or error/loading → `SequenceComposer` |

## ScoreStack

**Props:** `scores`, `pxPerNote`, `lyricsGap`, `lyricsFontSize`.

Renders `scores.map` → section per score → `PianoSheet`. No local state.

## LayoutControls

**Props:** spacing values + three `on*Change` callbacks.

Exported constants:

```typescript
DEFAULT_PX_PER_NOTE = 30   // min 18, max 120
DEFAULT_LYRICS_GAP = 10    // min 0, max 60
DEFAULT_LYRICS_FONT_SIZE = 12  // min 8, max 24
```

Used in `App` (loaded scores) and `SequenceComposer` (composed passage) — separate state
instances.

## SequenceComposer

**Props:** `apiBase: string`.

**State:** title, tempo, time step, key signature, three text areas (right/left/lyrics),
local layout controls, `score`, `error`, `busy`.

**Actions:** `handleRender` → validate frames → `POST /sequence` → `PianoSheet` on success.

**parseFrames:** one line per matrix column; trims trailing blanks.

Client validates hand frame-count match before request (backend also 422s).

## PianoSheet

**Props:** `score`, `pxPerNote`, `lyricsGap`, `lyricsFontSize`.

See [piano-sheet.md](piano-sheet.md). No React state beyond refs/id; all drawing in
`useEffect` + `ResizeObserver`.

## File layout

```
src/
  App.tsx
  components/
    LayoutControls.tsx
    ScoreStack.tsx
    SequenceComposer.tsx
    PianoSheet.tsx
  music/
    types.ts
    notes.ts
    matrixToNotation.ts
```

Music logic stays under `music/`; VexFlow isolation in `PianoSheet.tsx` per
[09-coding-conventions.md](../../../context/09-coding-conventions.md).
