# App shell

`aitu-frontend/src/App.tsx` — root layout, score loading, global layout state.

## API connection

```typescript
const matrixApiBase = (
  import.meta.env.VITE_AITU_API_URL ?? "http://127.0.0.1:8765"
).replace(/\/$/, "");
```

Trailing slash stripped. Env var name only — no secrets in docs.

## State

| State | Type | Purpose |
|-------|------|---------|
| `pxPerNote` | `number` | Horizontal spacing for loaded scores (default from `LayoutControls`). |
| `lyricsGap` | `number` | Lyric offset above staff. |
| `lyricsFontSize` | `number` | Lyric text size. |
| `scores` | `MatrixScore[] \| null` | Fetched scores; `null` while loading. |
| `loadError` | `string \| null` | Fetch failure message. |

Layout defaults and bounds live in `LayoutControls.tsx` (`DEFAULT_PX_PER_NOTE` = 30, etc.).

## Mount order

1. Hero section (static copy).
2. `LayoutControls` — global spacing for loaded scores.
3. Score area:
   - Error panel if `loadError` (hints to run `make serve` in aitu-backend).
   - Loading text while `scores === null`.
   - `ScoreStack` when loaded.
4. `SequenceComposer` — always below loaded scores; receives `apiBase`.

`SequenceComposer` has its **own** independent layout state (does not share the global
controls above).

## GET /scores

`useEffect` on mount:

```typescript
fetch(`${matrixApiBase}/scores`)
```

Non-OK response → `loadError`. Network/parse errors caught similarly. Cleanup sets
`cancelled` flag to avoid stale updates.

## Where to look deeper

- [loaded-scores.md](loaded-scores.md) — `ScoreStack` rendering
- [compose-panel.md](compose-panel.md) — compose section
- [components.md](../../documentation/services/frontend/components.md) — wiring detail
