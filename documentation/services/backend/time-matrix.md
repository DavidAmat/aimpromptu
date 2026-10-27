> Context: [context/backend/time-model.md](../../../context/backend/time-model.md) ·
> [aitu-backend/src/aitu_backend/sheet/README.md](../../../aitu-backend/src/aitu_backend/sheet/README.md)

# The time matrix: what stays of schema 2.0

`aitu-backend/src/aitu_backend/schemas/time_matrix.py` held the schema 2.0 contract between the
backend and the vexflow-v2 sheet (`@aimpromptu/grid-notation`): the envelope, the figure ladder,
the passages, the printed notes, the layout hints and the score payload. Implementation 03, Phase 10
(2026-10-27) removed them with that sheet; their field reference is now
[`deprecated/time-matrix.md`](../../deprecated/time-matrix.md). The sheet is now an F1 frames sheet
(`sheet.f1`), written by the AI or the algorithm and drawn by the backend
(`aitu_backend.sheet.engrave.frames`, SVG): see the sheet's own README, sections 9 to 17.

## 1. What the module keeps

| Name | What it is | Read by |
|---|---|---|
| `DEFAULT_FRAME_MS` | One matrix column, 40 ms (D-01). | `matrix/time_grid.py`, the routes that take `frameMs` |
| `FigureName` | The nine figure names (D-12): `redonda`, `blanca`, `dottedBlanca`, `negra`, `dottedNegra`, `corchea`, `semicorchea`, `fusa`, `semifusa`. | `part_sheet/build.py`, `part_sheet/legacy.py`, `editing/passages.py`, `schemas/rhythm.py` |
| `FIGURE_NEGRAS` | The length of each figure in negras (`redonda` 4.0 down to `semifusa` 0.0625). The old sheet's reference figure (`anchorFigure`) is read through it. | `part_sheet/build.py` (`reading_of`), `editing/passages.py` |
| `PrintedHand` | `"right"` or `"left"`: the staff a mark of the old sheet names. | `schemas/rhythm.py` |
| `FigureOverride` | A figure set by hand for one note (`hand`, `row`, `startFrame`, `figure`), D-17. | `schemas/rhythm.py` (an old `sheet.json`) |
| `BeamBreak` | A note that starts a new beam group (`hand`, `startFrame`), D-34. | `schemas/rhythm.py` (an old `sheet.json`) |

The last two are kept only because an old `sheet.json` holds them: its marks are carried onto the
new sheet (`part_sheet/legacy.py`, implementation 03, Phase 9) and still move with a paste
(`editing/marks.py`). Nothing in the app writes a new `sheet.json`. See
[`rhythm-and-annotations.md`](rhythm-and-annotations.md).

## 2. What a column is

The idea of schema 2.0 is still the base of the sheet: **position is measured wall-clock time.** A
column is `frameMs` milliseconds (40 by default), the column of an onset is
`round(onset_ms / frameMs)` (D-02), and so a column never moves. Anything keyed by frame (a finger,
a lyric, a beam mark, a figure set by hand) stays on its music for as long as the part's wall-clock
length does not change. The hand split runs on this grid
([`events-to-sheet.md`](events-to-sheet.md)), and an F1 frames sheet names its notes by the same
40 ms columns (`F1 frames frameMs=40 quarterMs=500`).

What changed is who names the figures. Under schema 2.0 the reader named one figure from the gap
peaks and a ladder named every other (D-09, D-10). Since implementation 03 the AI (a reference
request) or the algorithm (`proposal.beat`) chooses the reference figure, `quarterMs` of
`sheet.f1`, and **Transpose figures** is the user's override (D-09 as changed; see
[`context/backend/time-model.md`](../../../context/backend/time-model.md)).

## 3. The rederivation flag

`pipeline.needs_rederivation()` reads `needs-rederivation.json`, the flag the one-off migration to
schema 2.0 left beside an artifact it could not rebuild. A piece that has it answers its reason
instead of notes (`409` on the notes routes). The migration script was deleted in implementation 02,
Phase 3.

## 4. Where to look deeper

- [`events-to-sheet.md`](events-to-sheet.md): from the stored notes to the hand split the sheet starts from
- [`endpoints.md`](endpoints.md): the whole HTTP surface (`/sheet`, section 4.1)
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md): the old `sheet.json`, still read
- [`paths-and-data.md`](paths-and-data.md): where these files sit on disk
- [`deprecated/time-matrix.md`](../../deprecated/time-matrix.md): every field of the removed payload
