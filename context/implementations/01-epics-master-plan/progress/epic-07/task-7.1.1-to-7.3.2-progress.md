# Epic 7 — Matrix tab · progress report

Covers Tasks 7.1.1, 7.2.1, 7.2.2, 7.3.1 and 7.3.2. Status: **done, pending your manual trial.**
Date: 2026-07-27.

> Follow-up: Story 7.4 was completed later in the same continuation session. See
> [`task-7.4.1-progress.md`](task-7.4.1-progress.md) and
> [`task-7.4.2-progress.md`](task-7.4.2-progress.md). The report below remains the historical
> handoff for Stories 7.1–7.3.

## Summary

The Matrix tab is real. A transcription is now something you can look at.

| Task | Delivered |
|------|-----------|
| 7.1.1 grid | `components/matrix/MatrixGrid.tsx` — 88 key columns, frame rows, circles, edges, frozen header |
| 7.2.1 pills | raw / collapsed / clean / two-hands, hand colours from `palette.ts` |
| 7.2.2 export/import | `GET /matrix/{uuid}/export` (dense or sparse) + `POST /matrix/import` |
| 7.3.1 recompute | BPM and resolution changed in place, redrawn from the raw matrix |
| 7.3.2 frame search | jump by frame number or `mm:ss.mmm` |

## The grid

Columns are the 88 keys; the header shows the English name (`C4`) with the Spanish name (`Do-4`)
**rotated 90°** above it, which is what lets the columns stay 26 px wide. Black keys get a darker
column so the keyboard shape is readable at a glance — not in the task file, but without it 88
identical columns are impossible to navigate.

Rows are time frames, labelled `f: 12 [00:03.000 – 00:03.250]`, and scrolling down moves forward in
time. The header row and the frame labels are both frozen.

Cells follow the spec: a **filled circle** for an onset, a **pale circle** for a sustain, nothing
for silence. Connector lines run from the bottom of a circle to the top of the one below whenever
the note continues, so a held note reads as a solid head with a pale tail.

**Two-hands** replaces black/grey with the palette's hand colours — dark/light Blue for the right,
dark/light Green for the left — drawn into the same grid, left hand first so a collision (which
should not happen) shows the right on top. A legend under the grid names the four colours.

### Row virtualization

The task file says "consider row virtualization if performance demands". It demanded: a five-minute
piece at semicorchea is ~1200 rows, each an SVG with 88 columns of separators — around 100,000 DOM
nodes. Only the visible slice plus a 12-row overscan is rendered, with spacer boxes standing in for
the rest, so the scrollbar and the layout are unchanged but the node count stays constant. This was
cheaper to do now than to retrofit.

## Export and import

`GET /matrix/{uuid}/export?step=&granularity=&tempoBpm=&sparse=` returns a **download** —
`Content-Disposition` with a name like `do-re-mi_clean_semicorchea_sparse.json` — rather than a
plain body, so the browser saves something you can recognize a week later.

Both forms are self-contained. The dense one carries `columnHeaders` (all 88 keys, EN + ES) and
`rowTimestamps`, which is what makes it readable without the app.

`POST /matrix/import` accepts either form (the envelope's `sparse` flag says which), **normalizes**
it, and stores it under a synthetic audio uuid so every Playground tab reads it exactly like a
transcription. Two decisions worth recording:

- **Normalize rather than reject.** A hand-edited file easily contains a sustain with no onset.
  Promoting it to an onset is a better answer than refusing the file, and the response says how
  many cells were corrected — the UI shows that as a note, not an error.
- **A two-hands import merges back into one matrix.** The split is cheap and deterministic, so
  storing one matrix and re-splitting on demand beats storing two that could drift apart.

The imported matrix is written as **both** the step file and the raw file, because an import has no
audio behind it — without that, recompute would have nothing to work from and the resolution
dropdown would break on imported pieces.

## Recompute and search

BPM and resolution are edited on the page itself. Changing either re-requests the matrix, and the
backend derives it from the stored raw matrix — no re-transcription. The page says so under the
controls, because otherwise the instant response looks like it did not do anything.

Frame search takes a bare integer as a frame number and anything else as a time (`1:23.500`, `83`,
`1:23`), reusing `parseTime` from Epic 3. Out-of-range input gets a specific message —
*"That is past the end — the piece lasts 74.50 s."* The grid scrolls the target to a third of the
way down rather than flush to the top, so you can see what leads into it. Epic 8's deep link from
the Piano Roll will set the same `focusFrame` prop.

## Errors found and how they were solved

1. **The export test seeded the wrong granularity.** I stored a semicorchea matrix as the *raw*
   file, but the pipeline always reads raw as fusa and collapses from there — so a semicorchea
   request halved it to 3 columns. The fixture now seeds fusa, which is what a real transcription
   writes. Worth knowing: **the raw file is fusa by definition**; anything else is a bug in the
   writer, not the reader.
2. **`_VIEW_EPIC` and the `not_implemented` import** were left dangling once the last two
   placeholders in `api/matrix.py` became real. Removed; the smoke test's `501` list is down to
   notation and playlists.

## Deviations from the task file

- Export is a **`GET`**, not a `POST`. A download is a navigation, and `GET` means the button can
  be a plain link with no JavaScript.
- Added black-key column shading and the colour legend.
- Row virtualization (see above).
- `MatrixGrid` takes an `onCellClick` prop that nothing uses yet — the seam for Story 7.4.

## Verification

```
pytest              # 464 passed (12 new in tests/test_matrix_export.py)
mypy, flake8, black # clean
npx tsc -b, npm run lint, npx vite build   # clean
```

The acceptance criterion — *"export dense and sparse, re-import both, grids identical"* — is two
tests, plus: the download filename, dense headers and timestamps, a two-hands export labelling both
hands, the two-hands round trip re-splitting correctly, normalization reporting its count, a
malformed import returning `422`, a real file round trip through disk, an imported matrix being
recomputable to a coarser resolution, and the endpoint's split matching a local `split_hands`.

**No frontend runtime test** — still no test runner in this repo.

## Manual trial for the supervisor

The full guide is [`user_review/epic-07-matrix-tab.md`](../user_review/epic-07-matrix-tab.md).
The short version, after transcribing your `Do Re Mi Fa Sol` recording:

1. **Playground → Matrix.** Five filled circles stepping down and to the right — that is your scale,
   and it is the first time the app shows you what it heard.
2. Click **raw** → many more rows, same shape. Click **clean** → tails shortened. Click
   **two-hands** → the colours split at middle C.
3. Change **Resolution** to Corchea → the grid halves its rows **instantly**. That is the promise
   of the raw-matrix design, visible for the first time.
4. Type `2` into **Go to frame or time** → it scrolls there. Type `0:03.000` → same place.
5. **Sparse JSON** → a file downloads. **Input tab → Matrix JSON** → choose it → it comes back.

## Follow-up seams

- Story 7.4 subsequently used `MatrixGrid`'s `onCellClick` seam and the Task 2.4.2 primitives.
- Epic 8 subsequently reused `focusFrame` for its Matrix deep link and the waveform data for its
  roll watermark.
- The grid renders the **dense** form only. If a piece ever gets big enough that the dense payload
  is the bottleneck, the fix is a windowed endpoint (`?fromFrame=&toFrame=`), not sparse rendering
  in the browser — the backend stays heavy.
