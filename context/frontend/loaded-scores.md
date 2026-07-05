# Loaded scores

Displays scores from `GET /scores` with user-adjustable layout.

## Components

### ScoreStack (`ScoreStack.tsx`)

Maps `scores: MatrixScore[]` to one `<section class="score-section">` per score.
Optional `score.title` as `<h2>`. Each score gets a `PianoSheet` with the shared layout
props passed from `App.tsx`.

Key: `` `${score.title ?? "score"}-${index}` ``.

### LayoutControls (`LayoutControls.tsx`)

Reusable spacing inputs. Used here for **loaded scores** (global state in `App.tsx`) and
again inside `SequenceComposer` (local state).

| Control | Default | Range | Step |
|---------|---------|-------|------|
| Note spacing (px per note) | 30 | 18–120 | 2 |
| Lyrics gap (px) | 10 | 0–60 | 1 |
| Lyrics font size (px) | 12 | 8–24 | 1 |

Values clamped on change; invalid numeric input ignored (`readFiniteNumber`).

`pxPerNote` drives how many notes fit per line in `PianoSheet` (one hand: note-count wrap;
two hands: time-window wrap uses the same spacing for note area width).

## User flow

1. App fetches `/scores` on mount.
2. User adjusts spacing above the score stack.
3. All loaded scores re-render via `PianoSheet` `useEffect` (ResizeObserver + prop deps).

## Where to look deeper

- [app-shell.md](app-shell.md) — fetch and global state
- [rendering-pipeline.md](rendering-pipeline.md) — how `PianoSheet` uses layout props
- [components.md](../../documentation/services/frontend/components.md) — component props
- [piano-sheet.md](../../documentation/services/frontend/piano-sheet.md) — VexFlow layout math
