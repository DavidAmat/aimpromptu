> Context: [context/implementations/time-based-concept/README.md](../../../context/implementations/time-based-concept/README.md)

# 1. The time matrix: schema 2.0 field reference

**Status: stub.** Nothing in the pipeline builds a time matrix yet. This file exists from Phase 0
so that the field names have one home while the backend phases and the renderer phases are
implemented in parallel. Each section is filled in by the phase named in it.

The reasoning behind the change is in
[`PRD.md`](../../../context/implementations/time-based-concept/PRD.md), the numbered decisions are
in [`decisions.md`](../../../context/implementations/time-based-concept/decisions.md), and the
interface this file documents is frozen in
[`contract.md`](../../../context/implementations/time-based-concept/contract.md).

## 1.1 What changed and why

A matrix column used to do two jobs at once: it was where a note sits on the page, and it was the
rhythmic value of that note. Because it was both, the column width had to come from a tempo, and the
tempo was a number a person typed in. A grid that cannot express the music then produces the same
wrong figure every time, and one rounding error shifts every note after it.

The two jobs are now separate numbers. Position comes from measured wall-clock time, and the figure
comes from a ladder of millisecond values that the user names. A column is a fixed 40 ms, so column
numbers never move; a wrong figure changes a glyph and nothing else.

## 1.2 Where the code lives

| Concern | Module | Phase |
|---|---|---|
| Schema 2.0 models | `schemas/time_matrix.py` | P0.2, done |
| Frame ↔ millisecond conversion | `matrix/time_grid.py` | P1.1 |
| Chord grouping on raw times | `transcription/grouping.py` | P1.2 |
| Events → time matrix | `transcription/events_to_matrix.py` | P1.3 |
| Gaps between onsets | `matrix/intervals.py` | P2.1 |
| Peak finding | `matrix/peaks.py` | P2.2 |
| Ladder building and preview | `matrix/ladder.py` | P2.3 |
| Figure vocabulary and selection | `notation/figures.py` | P3.1, P3.2 |
| Passages | `matrix/passages.py` | P3.4 |

The TypeScript mirror of `schemas/time_matrix.py` is `vexflow-v2/src/matrix/types.ts`. The two files
are the same contract written twice, so a field renamed in one has to be renamed in the other in the
same task.

## 2. The models

All of them travel as camelCase JSON. Build them with snake_case keyword arguments, as everywhere
else in this package.

### 2.1 `TimeMatrixEnvelope`

| Field | JSON | Meaning |
|---|---|---|
| `schema_version` | `schemaVersion` | Always `"2.0"`. A hard break from 1.x. |
| `frame_ms` | `frameMs` | Length of one column in milliseconds, 40 by default. |
| `frame_count` | `frameCount` | Number of columns. Both hands must span exactly this many. |
| `duration_seconds` | `durationSeconds` | Wall-clock length of the source audio. |
| `matrix_processing_step` | `matrixProcessingStep` | `raw` or `two-hands`. |
| `r_matrix`, `l_matrix` | `rMatrix`, `lMatrix` | Sparse COO, unchanged from 1.x. |

`tempoBpm` and `granularity` are gone. `timeStepSeconds` survives only as a derived property,
`frame_ms / 1000`, and is not stored.

Cell values keep their meaning: `1` onset, `-1` measured sustain, `0` silence. The sustain is a
measurement and never decides a printed figure.

### 2.2 `FigureLadder`

Nine figures: `redonda`, `blanca`, `dottedBlanca`, `negra`, `dottedNegra`, `corchea`,
`semicorchea`, `fusa`, `semifusa`. Those are all of them, and the two dotted entries are the only
dotted figures that exist.

The user names one figure and gives it a millisecond value; every other figure follows by
proportion. `ms_by_figure` always carries all nine, so the renderer never re-derives one.

### 2.3 `Passage`, `PrintedNote`, `FigureOverride`, `LayoutHints`, `TimeScorePayload`

Field-by-field detail is filled in by P3.4 and P3.7, when the endpoint that returns them exists. For
now the shapes are in `schemas/time_matrix.py` and in
[`contract.md`](../../../context/implementations/time-based-concept/contract.md) §4 and §5.

## 3. Endpoints

None yet. `GET /matrix/{uuid}/peaks` and `POST /matrix/{uuid}/ladder-preview` arrive in P2.4 and
P2.5, and `GET /score/{uuid}` in P3.7. This section is filled in then, in the style of
[`endpoints.md`](endpoints.md).

## 4. Migration

Filled in by P4.5. The short version: an artifact with `events.json` is re-derived at 40 ms, and a
hand-edited artifact with no raw events is marked `needsRederivation` and surfaced in the library.
No stored artifact is ever silently reinterpreted.

## 5. Where to look deeper

- [`context/implementations/time-based-concept/`](../../../context/implementations/time-based-concept/README.md) — the plan, the decisions and the progress trail
- [`schemas.md`](schemas.md) — the 1.x models this schema replaces
- [`transcription-pipeline.md`](transcription-pipeline.md) — the pipeline as it stands before Phase 4 rewires it
