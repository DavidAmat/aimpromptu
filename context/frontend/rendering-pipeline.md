# Rendering pipeline

Sparse-COO JSON → VexFlow SVG. All music logic under `src/music/`; drawing in `PianoSheet.tsx`.

Notation contract: [notation-spec.md](../shared/notation-spec.md).

## Pipeline stages

```
SparseMatrix (rows/cols/onset)
  → sparseToActiveCells
  → activeCellsToNoteEvents
  → sparseToVexPieces (durations, chords, rests)
  → PianoSheet (StaveNote, beams, accidentals, lyrics, wrap)
```

One-hand convenience: `noteEventsToVexPieces(score)` when `score.matrix` is set.

Two-hand: `PianoSheet` calls `sparseToVexPieces` per clef on column-sliced matrices.

## Key behaviors (code-verified)

### Durations and dots

`durationBeats = steps * timeStepSeconds / (60 / tempoBpm)`. Greedy decomposition prefers
fewest symbols, one dotted note when possible (e.g. 1.5 beats → dotted quarter). Off 1/16
grid → snap + `console.warn`.

### Beams

**Not** VexFlow `generateBeams`. Custom rule: beam every maximal run of ≥2 consecutive
beamable notes (eighth or shorter, non-rest). Lone eighth keeps its flag. Rests and longer
notes break the run.

### Key signatures

Accidental baked into pitch (`Fa#-5` → `f#/5`). `Accidental.applyAccidentals` decides
display glyph vs key (e.g. `Fa#-5` in Sol-Mayor shows no sharp).

### Layout

Barless: no bar lines, no time signature, soft (`setStrict(false)`) voice. Key signature
repeats each line start.

- **One hand:** wrap by note count (`chunkIntoLines`).
- **Two hands:** wrap by time window (`sliceMatrixColumns` + same column slice for both
  hands); braced grand staff (treble + bass).

### Lyrics

Time-indexed per frame; interpolated x between note-head anchors and stave edges. Drawn
over sustains and silences. Two-hand: lyrics above treble; `lyricColOffset` = window start.

## Module map

| File | Role |
|------|------|
| `types.ts` | `SparseMatrix`, `MatrixScore`, `NoteEvent`, `VexPiece` |
| `notes.ts` | 88-key rows, Spanish→VexFlow, `KEY_SIGNATURES` |
| `matrixToNotation.ts` | Decode, events, duration decomposition, timeline |
| `PianoSheet.tsx` | VexFlow renderer |

## Where to look deeper

- [matrix-to-notation.md](../../documentation/services/frontend/matrix-to-notation.md)
- [piano-sheet.md](../../documentation/services/frontend/piano-sheet.md)
- [notes.md](../../documentation/services/frontend/notes.md)
- [documentation/archive/vexflow-reference.md](../../documentation/archive/vexflow-reference.md) — legacy VexFlow notes (superseded by low-level API in PianoSheet)
