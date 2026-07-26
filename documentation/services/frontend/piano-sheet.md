> Context: [rendering-pipeline.md](../../../context/frontend/rendering-pipeline.md) · [notation-spec.md](../../../context/music/notation-logic/02-notation-spec.md.md)

# PianoSheet

VexFlow rendering in `aitu-frontend/src/components/PianoSheet.tsx`. Low-level API
(`Renderer`, `Stave`, `StaveNote`, `Voice`, `Beam`, `Accidental`, `Dot`) — not EasyScore.

## Props

| Prop | Type | Purpose |
|------|------|---------|
| `score` | `MatrixScore` | Sparse score + metadata. |
| `pxPerNote` | `number` | Horizontal pixels per note in note area. |
| `lyricsGap` | `number` | Lyric baseline offset above staff. |
| `lyricsFontSize` | `number` | Lyric font size (px). |

## Mode detection

`twoHand = Boolean(score.r_matrix && score.l_matrix)`.

- One hand: `useMemo` → `noteEventsToVexPieces(score)`.
- Two hands: pieces computed per line inside `useEffect`.

## pieceToStaveNote(piece, clef)

- Dots encoded in duration string (`qd`, `8d`) for correct ticks/beaming; glyphs via
  `Dot.buildAndAttach`.
- Rests: `keys: ["b/4"]`, duration suffixed with `r`.
- Chords: `StaveNote({ clef, keys, duration })`.
- Accidentals **not** added manually — `Accidental.applyAccidentals` after voice built.

## buildBeams(notes)

`BEAMABLE = {"8", "16", "32"}`. Scan notes in order:

- Beamable non-rest → add to `run`.
- Else `flush()` — if `run.length > 1`, `new Beam(run)`.

Beams drawn **before** `voice.draw` (beamed notes hide flags).

## drawStave(...)

Creates `Stave`, optional clef + key signature (`keySig !== "C"`), draws context.

`Voice({ numBeats: 4, beatValue: 4 })`, `setStrict(false)`, `addTickables(notes)`,
`Accidental.applyAccidentals([voice], keySig ?? "C")`,
`Formatter().joinVoices([voice]).format([voice], noteAreaWidth)`, `voice.draw`, then beams.

## drawLyrics(...)

For each frame `c` in `[colStart, colEnd)`:

- Look up `score.lyrics[c + lyricColOffset]`; skip empty.
- Build anchor points from piece `startStep >= 0` note-head x positions.
- Interpolate x for any frame between anchors; stave note-start/end as outer anchors.
- Center text: `fillText(x - textWidth/2, yLyric)`.

Lyrics independent of note onsets — sustains and silences get interpolated positions.

## One-hand layout

Constants: `LEFT_MARGIN=16`, `RIGHT_MARGIN=16`, `CLEF_ROOM=70`, `ROW_BASE_HEIGHT=120`.

```
usableWidth = max(420, clientWidth) - margins - CLEF_ROOM
perLine = max(2, floor(usableWidth / pxPerNote))
lines = chunkIntoLines(pieces, perLine)
```

Per line: `noteAreaWidth = linePieces.length * pxPerNote`; key sig repeats (`clefRoom`).

`lineRanges`: contiguous frame ranges for lyrics — chain from 0 to `totalColsSingle`.

## Two-hand grand staff

Constants: `BRACE_ROOM=16`, `GRAND_STAVE_GAP=100`, `GRAND_ROW_HEIGHT=240`.

Wrap by **time**, not note count:

```
colsPerLine = max(2, perLine)
lineCount = ceil(totalCols / colsPerLine)
```

Per line: `sliceMatrixColumns(r_matrix, start, end)` and same for `l_matrix` →
`sparseToVexPieces` each → treble + bass `drawStave`.

Connect with `StaveConnector`: `BRACE`, `SINGLE_LEFT`, `SINGLE_RIGHT`.

Lyrics on treble only; `drawLyrics(..., colStart=0, colEnd=colsThisLine, lyricColOffset=start)`.

## Key signature layout room

`KEY_ACCIDENTAL_COUNT` from `KEY_SIGNATURES` accidental string length.
`keySigRoom = count * 12 + (keySig === "C" ? 0 : 8)`.

## Lifecycle

`useEffect` depends on `elementId`, `twoHand`, `pieces`, `score`, layout props.
`ResizeObserver` on container re-runs render. Cleanup clears SVG innerHTML.

Unique DOM id: `vexflow-${useId()}` (colons stripped).

## Where to look deeper

- [matrix-to-notation.md](matrix-to-notation.md) — upstream pipeline
- [notes.md](notes.md) — key signatures table
- [vexflow-reference.md](../../archive/vexflow-reference.md) — historical EasyScore notes (current code uses low-level API)
