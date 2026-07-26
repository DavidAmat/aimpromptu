> Context: [rendering-pipeline.md](../../../context/frontend/rendering-pipeline.md) · [notation-spec.md](../../../context/music/notation-logic/02-notation-spec.md.md)

# matrixToNotation

Pipeline in `aitu-frontend/src/music/matrixToNotation.ts`: sparse COO → `VexPiece[]`
timeline for one clef.

## sparseToActiveCells(payload)

Decodes parallel arrays into `{ row, col, isOnset }[]`.

- `isOnset = (onset[i] !== -1)`.
- Length mismatch across `rows`/`cols`/`onset` → `Error`.

## activeCellsToNoteEvents(payload, rows?)

Groups cells by row, sorts by column. Per row:

1. Map row → custom note (`rowIndexToCustomNote`) → VexFlow key (`customNoteToVexFlow`).
2. Accidental baked into `vexKey` (e.g. `f#/5`).
3. Walk columns: sustain (`!isOnset`) on consecutive column extends `durationSteps`;
   otherwise flush previous event and start new at `startStep = col`.

Orphan sustain (gap or no prior onset) starts a new event (same as backend promote rule).

Sort output by `startStep`, then `vexKey`.

## beatsPerStep

```typescript
timeStepSeconds * (tempoBpm / 60)
```

One matrix column = this many beats.

## decomposeSpan(steps, beatPerStep)

Converts step count to VexFlow duration tokens. `DURATIONS` table (longest first):

| Beats | Token | Dots |
|-------|-------|------|
| 4 | `w` | 0 |
| 3 | `h` | 1 |
| 2 | `h` | 0 |
| 1.5 | `q` | 1 |
| 1 | `q` | 0 |
| 0.75 | `8` | 1 |
| 0.5 | `8` | 0 |
| 0.375 | `16` | 1 |
| 0.25 | `16` | 0 |

`MIN_BEATS = 0.25`. Off-grid beats rounded to nearest 1/16 with warning.

Greedy: pick longest fit, subtract, repeat. Fallback: single sixteenth.

## sparseToVexPieces(matrix, tempoBpm, timeStepSeconds, rows?)

1. `events = activeCellsToNoteEvents(...)`.
2. Build `startsAt: Map<startStep, NoteEvent[]>`.
3. Cursor walks `[firstStart, lastEnd)`:
   - **Silence:** if no events at cursor, find next onset column, emit rest(s) for gap.
   - **Chord:** notes at cursor; `chordSteps = min(durationSteps)` (MVP single-voice:
     truncate simultaneous notes to shortest).
   - `emit(cursor, decomposeSpan(chordSteps, beatPerStep), chord?)`.

`emit` creates one `VexPiece` per duration token. First token gets `startStep`; continuation
tokens get `startStep: -1` (no lyric anchor).

`VexPiece`: `{ keys, duration, dots, isRest, startStep }`.

## sliceMatrixColumns(matrix, start, end)

Filters cells with `start <= col < end`, rebases columns to `col - start`. Shape becomes
`[rowCount, end - start]`.

Used for two-hand line wrap so treble and bass share the same time window. A note sounding
before the window appears as sustain at column 0; decoder treats leading sustain as fresh
onset (no ties).

## noteEventsToVexPieces(score)

If `score.matrix` set, delegates to `sparseToVexPieces` on it. Else returns `[]`.
Two-hand path uses `sparseToVexPieces` directly in `PianoSheet`.
