> Context: [context/backend/time-model.md](../../../context/backend/time-model.md) ·
> [context/implementations/03-time-based-concept/contract.md](../../../context/implementations/03-time-based-concept/contract.md)

# The time matrix: schema 2.0 field reference

Every model the backend and the drawing package agree on, field by field. The models live in
`aitu-backend/src/aitu_backend/schemas/time_matrix.py`; the TypeScript mirror is
`vexflow-v2/src/matrix/types.ts`. **The two files are the same contract written twice**, so a field
renamed in one has to be renamed in the other in the same change.

The reasoning behind the model is in
[`PRD.md`](../../../context/implementations/03-time-based-concept/PRD.md); the numbered decisions
this file cites (`D-nn`) are in
[`decisions.md`](../../../context/implementations/03-time-based-concept/decisions.md).

---

## 1. What a column is, and why it matters here

A matrix column used to do two jobs at once. It was where a note sits on the page, and it was the
rhythmic value of that note. Because it was both, the width of a column had to come from a tempo
somebody typed in — and a grid that cannot express the playing produces the same wrong figure every
time.

The two jobs are now two different numbers, and every model below follows from that split:

- **Position is measured wall-clock time.** One column is a fixed number of milliseconds,
  `frameMs`, 40 by default (D-01). The column index of an onset is `round(onset_ms / frameMs)`
  (D-02), so the same recording always produces the same columns.
- **The figure is a name the reader chose.** It is carried on `PrintedNote.figure` and it decides
  which glyph is drawn and nothing else. Renaming a note moves nothing.

The practical consequence, and the property most of the product rests on: **a column never moves.**
Anything keyed by frame — a fingering, a lyric line, a beam break, a passage boundary — stays valid
for as long as the piece's wall-clock length does not change.

There is no `tempoBpm` and no `granularity` anywhere in schema 2.0. `timeStepSeconds` survives only
as a derived property, `frame_ms / 1000`, and is never stored.

---

## 2. The models

All of them travel as camelCase JSON, produced by Pydantic aliases. Build them with snake_case
keyword arguments, as everywhere else in this package.

### 2.1 `TimeMatrixEnvelope`

Everything needed to interpret one wall-clock matrix.

| Field | JSON | Type | Meaning |
|---|---|---|---|
| `schema_version` | `schemaVersion` | `"2.0"` | A hard break from 1.x. |
| `sparse` | `sparse` | `true` | Always sparse. |
| `frame_ms` | `frameMs` | `float > 0` | Length of one column in milliseconds. Default 40 (D-01). |
| `frame_count` | `frameCount` | `int ≥ 0` | Number of columns. Both hands must span exactly this many. |
| `duration_seconds` | `durationSeconds` | `float ≥ 0` | Wall-clock length of the source audio. |
| `title` | `title` | `string?` | |
| `key_signature` | `keySignature` | `string?` | Major-key name: `C`, `Bb`, `F#`. |
| `matrix_processing_step` | `matrixProcessingStep` | `"two-hands"` | The only member left; see below. |
| `r_matrix` | `rMatrix` | `SparseCooMatrix` | Right hand. |
| `l_matrix` | `lMatrix` | `SparseCooMatrix` | Left hand. |

`frame_count * frame_ms` may exceed `duration_seconds` by less than one frame, because the last
onset is rounded to a whole column.

**There is always exactly one shape: two hands.** A one-hand piece is two hands with an empty
`lMatrix` and `LayoutHints.hideLeftHand` set, which keeps every consumer on one code path.
`TimeMatrixProcessingStep` therefore has a single member. `raw`, `collapsed` and `clean` are all
gone: there is one grid, so there is nothing to collapse to, and the hands are split immediately
after the grid is built (D-31), so a matrix that has not been split never leaves the backend.

Cell values keep their 1.x meaning: `1` onset, `-1` measured sustain, `0` silence. The sustain is
stored **in full**. Capping it at one redonda needs a ladder, and no ladder exists until the reader
has named a peak, so the cap is applied when the score payload is built (D-06). The sustain is a
*measurement* and never decides a printed figure — that comes from D-14.

A validator rejects an envelope whose two hands do not both span `frameCount` columns.

### 2.2 `FigureLadder`

The millisecond value of every figure, fixed by the one figure the reader named.

| Field | JSON | Type | Meaning |
|---|---|---|---|
| `anchor_figure` | `anchorFigure` | `FigureName` | The figure the reader named. |
| `anchor_ms` | `anchorMs` | `float > 0` | What they said it lasts. |
| `ms_by_figure` | `msByFigure` | `{FigureName: float}` | All nine figures, always complete. |

The app never chooses a ladder. Interval statistics fix it only up to a rational factor — a beat and
twice that beat explain the same gaps equally well — so the app presents and the reader decides
(D-09). Naming one figure fixes every other by proportion (D-10).

`msByFigure` carries all nine values rather than the anchor alone, so the renderer never re-derives
one and the two sides cannot disagree. A validator rejects an incomplete or non-positive table.

### 2.3 `FigureName` — the closed vocabulary

Nine members, and these are all of them (D-12):

```
redonda  blanca  dottedBlanca  negra  dottedNegra  corchea  semicorchea  fusa  semifusa
```

**Dots exist on `blanca` and `negra` only.** That restriction is deliberate rather than an
omission. With the dotted corchea banned, a swing pair of 211 ms and 125 ms both resolve to
`corchea`, which is exactly what a printed sheet of a shuffled piece shows. Allowing the dot pulls
the long half of the pair to a dotted corchea and recreates the ragged mix the wall-clock model
exists to remove.

`FIGURE_NEGRAS` in the same module gives each figure's length in negras (`redonda` 4.0 down to
`semifusa` 0.0625). A ladder is that table scaled by the anchor.

`MAX_PRINTED_FIGURE` is `redonda`: a longer gap prints a redonda and the remainder is silence
(D-15).

This is not the same vocabulary as `Granularity` in `schemas/matrix.py`. That enum named the
resolution of a column and has no part in schema 2.0; this one names a printed figure.

### 2.4 `Passage`

A stretch of the piece with its own ladder.

| Field | JSON | Type | Meaning |
|---|---|---|---|
| `id` | `id` | `string` | |
| `start_frame` | `startFrame` | `int ≥ 0` | Inclusive. |
| `end_frame` | `endFrame` | `int > 0` | **Exclusive.** |
| `ladder` | `ladder` | `FigureLadder` | |
| `header_label` | `headerLabel` | `string` | What the header prints, e.g. `negra = 320 ms · ≈188 BPM` (D-20). |

Boundaries are drawn by hand; there is no automatic segmentation (D-19). They are keyed by frame,
and a frame is absolute wall clock, so changing a passage's ladder relabels its notes and moves
nothing outside it (D-21).

The header prints both the millisecond value and the equivalent BPM. That is the only place a BPM
number appears in the product, and it is printed text rather than a stored or computed quantity:
some readers think in BPM and the two carry the same information.

### 2.5 `PrintedNote`

One glyph the renderer draws, with its figure already resolved by the backend.

| Field | JSON | Type | Meaning |
|---|---|---|---|
| `hand` | `hand` | `"right" \| "left"` | |
| `row` | `row` | `0…87` | Row 0 is MIDI 21 (`La-0`). |
| `start_frame` | `startFrame` | `int ≥ 0` | |
| `printed_frames` | `printedFrames` | `int ≥ 1` | Onset to next onset in the same hand (D-14), capped at one redonda (D-15). |
| `printed_ms_exact` | `printedMsExact` | `float ≥ 0` | The same gap before snapping, so the UI can show the fitting error. |
| `figure` | `figure` | `FigureName` | |
| `fit_error` | `fitError` | `float ≥ 0` | `abs(log2(printedMsExact / ladder.msByFigure[figure]))`. |
| `group_id` | `groupId` | `int ≥ 0` | Members of one chord group share it (D-04). |
| `tuplet` | `tuplet` | `int ≥ 2 \| null` | Only `3` today: a tresillo. |
| `tuplet_id` | `tupletId` | `int ≥ 0 \| null` | The three notes of one tresillo share it. |

Choosing the figure happens on the backend and not in the renderer, so the ladder, the proportional
comparison (D-11) and the closed vocabulary all live in one place.

`fitError` is shown to the reader and **never used for layout**: the column is the same width
whichever figure is printed. It is compared proportionally rather than in milliseconds, because with
a negra of 320 ms a 120 ms gap is exactly 40 ms from both 160 and 80 — a coin toss in absolute
terms, and 25 % against 50 % proportionally, where corchea wins cleanly and always.

A tresillo carries the **ordinary** figure: a tresillo of a negra is three corcheas, each with
`figure = corchea` and `tuplet = 3`. The number and its bracket are what make it a tresillo, so the
glyphs stay conventional, and `fitError` is zero for them because they are exactly what the mark
says they are (D-32).

### 2.6 `FigureOverride`

A figure the reader set by hand for one note (D-17).

| Field | JSON | Type |
|---|---|---|
| `hand` | `hand` | `"right" \| "left"` |
| `row` | `row` | `0…87` |
| `start_frame` | `startFrame` | `int ≥ 0` |
| `figure` | `figure` | `FigureName` |

It changes that one glyph and nothing else: no reflow, no renumbering, no effect on any other note.
That is only possible because the figure no longer decides where anything sits.

### 2.7 `BeamBreak`

A note the reader asked to start a new beam group (D-34).

| Field | JSON | Type |
|---|---|---|
| `hand` | `hand` | `"right" \| "left"` |
| `start_frame` | `startFrame` | `int ≥ 0` |

The twin of `FigureOverride`, and kept for the same reason. Beaming groups what is regular — one
hand, one key, one clef, no tuplet boundary — and a long run climbing through an arpeggio has none
of those inside it, so it beams as one shapeless slope. Where a phrase restarts is a reading of the
music rather than a property of it, and this is the only place that reading can come from. It is
applied **last**, after every automatic split.

Keyed by the note's own column and nothing else, so it survives a ladder change untouched.

### 2.8 `LayoutHints`

Wall-clock aggregation levels and spacing hints for the renderer.

| Field | JSON | Type | Meaning |
|---|---|---|---|
| `frame_group` | `frameGroup` | `int > 0` | Frames per selectable group, e.g. 25 at 40 ms = 1 second (D-27). |
| `frame_measure` | `frameMeasure` | `int > 0` | Frames per dashed vertical line, e.g. 100 at 40 ms = 4 seconds (D-27). |
| `silence_group_px` | `silenceGroupPx` | `float > 0` | What a fully silent frame group collapses to (D-23). |
| `hide_left_hand` | `hideLeftHand` | `bool` | Draw one staff only. |
| `hide_right_hand` | `hideRightHand` | `bool` | |

`frameGroup` and `frameMeasure` have **no musical meaning**. A group is what the reader can select;
a measure is where a dashed line is drawn. There are no bar lines and no time signature (D-28).

Silence is compressed so that a five-second rest reads as a few closely spaced dashed lines rather
than five seconds of blank page. Without the dashed lines, the horizontal spacing would read as
ordinary note-value spacing, which would be wrong — they are the only thing on the page saying the
axis is wall clock.

There is no alignment window here. Onsets played near-simultaneously were grouped on the raw times
before snapping, so they already share a frame, and one frame is one x (D-24).

### 2.9 `TimeScorePayload`

What the renderer consumes, and the response body of `GET` and `POST /time/{uuid}/score`.

| Field | JSON | Type |
|---|---|---|
| `schema_version` | `schemaVersion` | `"2.0"` |
| `envelope` | `envelope` | `TimeMatrixEnvelope` |
| `passages` | `passages` | `Passage[]` — ordered, tiling, non-overlapping |
| `notes` | `notes` | `PrintedNote[]`, both hands, ordered by `(startFrame, hand, row)` |
| `overrides` | `overrides` | `FigureOverride[]` |
| `beam_breaks` | `beamBreaks` | `BeamBreak[]` |
| `layout` | `layout` | `LayoutHints` |

A validator enforces the tiling: passages must start at 0, each must begin exactly where the
previous one ended, and the last must end at `frameCount`. A piece with one ladder has exactly one
passage covering every frame.

---

## 3. Endpoints

The routes that carry these models are under `/time`. Field-level request and response detail is in
[`endpoints.md`](endpoints.md#4-time--the-wall-clock-score); the live authority is the generated
OpenAPI page at `http://127.0.0.1:8765/docs`.

| Route | Returns |
|---|---|
| `GET /time/{uuid}/peaks` | The distribution of gaps — the plot the reader clicks. |
| `POST /time/{uuid}/ladder-preview` | A `FigureLadder` and every peak labelled under it. |
| `GET /time/{uuid}/score` | A `TimeScorePayload`. |
| `POST /time/{uuid}/score` | The same, with the reader's page edits folded in first. |
| `GET /time/{uuid}/trills` | Alternating runs, offered as suggestions. |
| `GET` `PUT` `DELETE /time/{uuid}/rhythm` | The saved reading — see [`rhythm-and-annotations.md`](rhythm-and-annotations.md). |

**Nothing here is cached and nothing is written.** Every response is derived from the stored
`events.json` on each request, so asking for the same piece at 20 ms instead of 40 is a different
query string rather than a migration. That costs a second or two on a five-minute piece and buys a
system with no stale state in it.

---

## 4. Migration from 1.x

`aitu-backend/scripts/migrate_to_time_matrix.py`, tested by `tests/test_migration.py`.

An artifact that has its `events.json` is re-derived at 40 ms. An artifact with no recorded events —
a grid that was hand-edited under the old model, which nothing can rebuild — is marked with
`needs-rederivation.json` beside it and surfaced rather than converted. **No stored artifact is
ever silently reinterpreted**; a grid written under one set of assumptions and read under another
puts every note at the wrong time, and a warning the reader can see is the only honest answer.

`pipeline.mark_needs_rederivation()` writes the flag and `pipeline.needs_rederivation()` reads it.

---

## 5. Where to look deeper

- [`events-to-sheet.md`](events-to-sheet.md) — the derivation path: one stored file to a drawn staff
- [`endpoints.md`](endpoints.md) — the whole HTTP surface
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md) — `rhythm.json`, the reader's decisions
- [`paths-and-data.md`](paths-and-data.md) — where these files sit on disk
- [`../frontend/grid-notation.md`](../frontend/grid-notation.md) — the package that draws the payload
- [`contract.md`](../../../context/implementations/03-time-based-concept/contract.md) — the frozen
  interface, §2 and §5
