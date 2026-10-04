# Contract — `aitu-backend` ↔ `@aimpromptu/grid-notation`

**Freeze this before any code is written.** Phases 1–4 (backend) and Phases 5–6 (renderer) are meant
to run in parallel, and this file is the only thing that makes that safe.

Shapes below are the intent, expressed in TypeScript. The Pydantic mirror lives in
`aitu_backend/schemas/` and must be generated from or checked against the same field names.

---

## 1. What replaces what

| Today | Becomes | Note |
|---|---|---|
| `MatrixEnvelopeMetadata.tempoBpm` | *(gone)* | no BPM in the matrix at all (D-01) |
| `MatrixEnvelopeMetadata.granularity` | `frameMs: number` | pure wall clock |
| `MatrixEnvelopeMetadata.timeStepSeconds` | `frameMs / 1000` | keep as a derived convenience only |
| `BEATS_PER_FRAME[granularity]` | *(gone)* | a frame has no beat value |
| `FrameClock.frameTimestamps` | *(unused)* | frames are uniform by construction now |
| bar / metre / time signature | *(gone)* | D-28 |

`Granularity` survives **only** as the name of a figure in the ladder — it is no longer a property of
the grid.

## 2. The matrix envelope

```ts
interface TimeMatrixEnvelope {
  schemaVersion: '2.0';
  sparse: true;
  /** Length of one column in milliseconds. D-01. */
  frameMs: number;              // default 40
  frameCount: number;
  /** Wall-clock length of the source audio; frameCount * frameMs may exceed it by < 1 frame. */
  durationSeconds: number;
  title?: string;
  keySignature?: string;
  matrixProcessingStep: 'raw' | 'two-hands';   // 'collapsed' and 'clean' no longer exist
  rMatrix: SparseMatrix;
  lMatrix: SparseMatrix;
}
```

`SparseMatrix` is unchanged (`binary-coo`, `shape: [88, n]`, `rows`, `cols`, `onset`).
Cell values keep their meaning: `1` onset, `-1` measured sustain (capped per D-06), `0` silence.

**The renderer must not derive a duration from the sustain cells.** Sustain is measurement; the
printed figure comes from D-14. Sustain is available for the piano-roll views and for diagnostics.

## 3. The ladder

```ts
type FigureName =
  | 'redonda' | 'blanca' | 'dottedBlanca' | 'negra' | 'dottedNegra'
  | 'corchea' | 'semicorchea' | 'fusa' | 'semifusa';   // D-12, closed set

interface FigureLadder {
  /** The figure the user named, and the millisecond value they gave it. D-09, D-10. */
  anchorFigure: FigureName;
  anchorMs: number;
  /** Every figure's duration in ms, derived from the anchor by proportion. Sent explicitly so the
   *  renderer never re-derives it and the two sides can never disagree. */
  msByFigure: Record<FigureName, number>;
}
```

`dottedBlanca` and `dottedNegra` are the only dotted entries (D-12). A ladder is complete: the
backend always sends all nine values.

## 4. Passages

```ts
interface Passage {
  id: string;
  /** Keyed by frame index. Frames are absolute wall clock, so these never move. */
  startFrame: number;
  endFrame: number;            // exclusive
  ladder: FigureLadder;
  /** What the header prints, e.g. "negra = 320 ms · ≈188 BPM". D-20. */
  headerLabel: string;
}
```

Passages tile the piece with no gaps and no overlaps. A piece with one ladder has exactly one
passage covering `[0, frameCount)`. Boundaries are user-drawn (D-19).

## 5. The score payload

This is what the renderer actually consumes.

```ts
interface TimeScorePayload {
  schemaVersion: '2.0';
  envelope: TimeMatrixEnvelope;
  passages: Passage[];          // ordered, tiling, non-overlapping
  notes: PrintedNote[];         // both hands, ordered by (startFrame, hand, row)
  overrides: FigureOverride[];  // D-17
  beamBreaks: BeamBreak[];      // D-34
  layout: LayoutHints;
}

interface PrintedNote {
  hand: 'right' | 'left';
  row: number;                  // 0..87, row 0 = MIDI 21
  startFrame: number;
  /** Onset-to-next-onset in the same hand, in frames. D-14. Capped at one redonda. D-15. */
  printedFrames: number;
  /** The exact gap in ms before snapping, so the renderer can show the fitting error. */
  printedMsExact: number;
  figure: FigureName;           // already resolved by the backend, per D-11/D-12
  /** |log2(printedMsExact / ladder.msByFigure[figure])|. Surfaced in the UI, not used for layout.
   *  Zero for a note inside a tuplet: the mark says exactly what it is. */
  fitError: number;
  /** How many notes this one is grouped with against the ladder, or absent for an ordinary note.
   *  3 for a tresillo. D-32. */
  tuplet?: number;
  /** The notes of one group share this, so a run of tresillos does not merge into one bracket.
   *  Unique across both hands. D-32. */
  tupletId?: number;
  /** Members of the same chord group share this. D-04. */
  groupId: number;
}

interface FigureOverride {
  hand: 'right' | 'left';
  row: number;
  startFrame: number;
  figure: FigureName;
}

interface BeamBreak {
  hand: 'right' | 'left';
  /** This note starts a new beam group. D-34. */
  startFrame: number;
}

interface LayoutHints {
  /** Frames per selectable group. D-27. */
  frameGroup: number;           // e.g. 25 at 40 ms = 1 s
  /** Frames per dashed line. D-27. */
  frameMeasure: number;         // e.g. 100 at 40 ms = 4 s
  /** Pixels a fully-silent frame group collapses to. D-23. */
  silenceGroupPx: number;
  /** Draw one staff only, for a piece whose other matrix is empty. I-02. */
  hideLeftHand?: boolean;
  hideRightHand?: boolean;
}
```

There is no alignment window. Onsets played near-simultaneously are grouped on the raw times before
snapping, so by the time the renderer sees them they already share a frame, and one frame is one x
(D-24, I-03).

**The backend resolves the figure, not the renderer.** The ladder, the proportional comparison
(D-11), the vocabulary restriction (D-12) and tresillo detection (D-32) all live in one place. The
renderer draws what it is told and applies `overrides` on top.

## 6. Who owns what

| Concern | Owner |
|---|---|
| snapping onsets to frames (D-02) | backend |
| chord grouping on raw times (D-04) | backend |
| peak finding, ladder fitting (D-07…D-10) | backend |
| choosing a figure for a gap (D-11, D-12, D-15) | backend |
| finding tresillos (D-32) | backend |
| drawing the 3 and its bracket (D-32) | **renderer** |
| passage boundaries and per-passage ladders (D-19…D-21) | backend, set by the user via the app |
| the `time → x` map (D-22, D-23, D-25, D-26) | **renderer** |
| sharing an x across hands (D-24) | **renderer** |
| frame groups and dashed lines (D-27) | **renderer** |
| applying per-note overrides (D-17) | **renderer** (backend stores them) |
| beam grouping, and the reader's breaks (D-34) | **renderer** (backend stores them) |
| playback times (D-29) | frontend, straight from `events.json` |

## 7. Compatibility

`schemaVersion: '2.0'` is a hard break. The renderer keeps the 1.x reader for one release so stored
artifacts can still be opened while Phase 4's migration runs, then it is deleted. There is no
automatic 1.x → 2.0 conversion inside the renderer: conversion is a backend job with the raw events
in hand.

## 8. On disk

Decided in P4.4 and recorded here because it is the one part of the storage layout a second
implementation would have to match.

**A transcription stores one file.** `data/audio/<uuid>/matrices/events.json` holds the engine's
output in seconds. Every matrix, peak, ladder and score is derived from it per request and none of
them is written (P4.2). `frameMs` is therefore a query parameter, not a stored property, and there is
no file on disk that can disagree with the screen.

A piece the migration could not carry over also has `needs-rederivation.json` beside it, holding a
`reason` written to be shown to a reader as it stands (P4.5). Its presence means the piece cannot be
drawn, and transcribing it again removes it.

**A saved version folder is `v<N>_f<frameMs>`,** for example `v2_f40`, and the matrix inside it is
`piano_matrix_v2_f40.npz` with `_right` / `_left` variants when both hands are stored. The suffix
used to be a granularity code (`v2_gsc`).

The version number and the suffix mean different things, and keeping both is deliberate: a version
is a **musical state** and the frame length is a **view** of it. `v1_f40` and `v1_f20` are the same
take on a coarser and a finer wall clock, so saving at a second frame length pins the version number
instead of advancing it. `v2` means the music changed.

A fractional frame length writes with the point removed, `f12_5` for 12.5 ms, so nothing in a folder
name reads as a file extension. A folder written under the old scheme is refused rather than guessed
at, and skipped when the next version number is chosen.

**The portable text format carries `frameMs`** and nothing else about timing (P4.7). It used to
carry a `tempoBpm` and a `timeStepSeconds`, which said the same thing twice and could disagree.
