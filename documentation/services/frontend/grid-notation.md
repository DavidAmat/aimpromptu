> Context: [context/frontend/rendering.md](../../../context/frontend/rendering.md) ·
> [context/music/notation-logic/02-notation-spec.md](../../../context/music/notation-logic/02-notation-spec.md)

# Grid notation: how the sheet is drawn

Everything on the staff is drawn by `@aimpromptu/grid-notation`. This app supplies the score payload
and the reader's annotations; the package does all the engraving.

The VexFlow stack it replaced — `PianoSheet.tsx`, `renderScore.ts`, `matrixToNotation.ts`,
`notes.ts` and the backend-built `ScoreDocument` — is gone.

---

## 1. The package

[`@aimpromptu/grid-notation`](../../../../vexflow-v2/documentation/README.md) is a local TypeScript
package, developed in the sibling `vexflow-v2` checkout and installed from disk:

```json
"@aimpromptu/grid-notation": "file:../../vexflow-v2"
```

npm turns that into a symlink, so editing the package and rebuilding it there is picked up here —
`pip install -e`, with one important difference: **npm does not build the dependency for you.**
After any change in `vexflow-v2`, run `npm run build` (or `npm run check`) there, or `dist/` stays
stale.

`vite.config.ts` excludes it from `optimizeDeps` for the same reason: Vite pre-bundles linked
dependencies and caches the result.

### The stale-`dist` trap

This has cost real time once and will again, so it is worth stating as a rule. `dist/` is in the
package's `.gitignore`, the symlink is live, and there is no version anywhere in this app's
lockfile. So what runs in the browser is **whatever `dist/` was last built from** — and nothing
warns when that is eleven releases behind the source beside it. That is exactly what happened
between 0.16.0 and 0.26.2: the package's git log said 0.26.2 while `dist/` was still 0.15.0, and the
app quietly kept engraving with the old code.

Pulling the package is therefore never enough. Rebuild it, and if a documented feature seems to be
missing, **check the build before checking the docs**:

```bash
grep -c planAccidentalColumns ../../vexflow-v2/dist/index.d.ts   # 0.26.2
```

Useful markers, one per release worth dating: `suggestKeySignature` (0.16.0), `FrameClock` (0.17.0),
`StavesMode` (0.18.0), `planMerge` (0.19.0), `renderScorePages` (0.25.0), `planAccidentalColumns`
(0.26.2), partial group-cell painting under a frame range (0.32.0).

The package is at **0.32.0** as of 2026-09-13.

---

## 2. Why it exists

VexFlow lays notes out from accumulated tick arithmetic inside measures. A piano matrix has no
measures and no metre — it has **columns of wall clock** — and the one property the whole project
depends on is that a right-hand and a left-hand event in the same column print at the same x.
Tick-based layout can only approximate that, and the approximation drifts.

This package makes columns the horizontal source of truth: **one `time → x` map, shared by both
staves, the ruler and every overlay** (D-22). The hands cannot come apart, because nothing computes
their positions separately. It also means the question "which hand is limiting this region"
disappears rather than being answered.

Two consequences worth knowing before reading a score:

- **Columns are not evenly spaced.** A column is as wide as what it draws, so horizontal distance
  reads as *density*, not duration. Silence is charged per frame group rather than per column
  (D-23), so a five-second rest is a few closely spaced dashed lines instead of five seconds of
  blank page. Time is read from the dashed lines and the column labels.
- **The score re-wraps, it never scales.** A narrower window puts the music on more lines at the
  same size. Do not give the host `width: 100%` expecting it to shrink; let it scroll.

---

## 3. The seam

There is **one** file that touches the package: `src/components/time/TimeScoreView.tsx`. It imports
`GridNotationRenderer`, plus three helpers — `frameAtPoint`, `placeCursor` and
`suggestKeySignature` — and nothing else in the app does.

There is **no conversion layer**. The renderer reads the payload's own envelope: `rMatrix` /
`lMatrix`, `1` onset / `-1` sustain / `0` silence, and `frameMs` naming the column length. So there
is no score model in this app to keep in step with the backend.

### What the view passes in

| Option | What it carries |
|---|---|
| `frameCount`, `timeStepSeconds` | `frameMs / 1000` — used **only** to turn a column into a clock time |
| `availableWidth` | The measured box; the music re-wraps into it |
| `printedFigureFor(hand, frame)` | **The backend's answer.** The view never derives a figure |
| `tupletFor(hand, frame)` | `3` for a tresillo |
| `beamBreakAt(hand, frame)` | The reader's grouping decision (D-34) |
| `keySignature`, `annotations.keyChanges` | The key, and where a passage leaves it |
| `annotations.ottavas` | Octave brackets |
| `annotations.fingers`, `.lyrics`, `.texts`, `.passages`, `.graceNotes` | Everything from `rhythm.json` |
| `annotationScale` | One number for every mark, not one per kind |
| `staves` | `"grand"`, or `"single"` when a hand is empty |
| `frameGroup`, `frameMeasure`, `silenceGroupPx` | The layout hints (D-23, D-27) |
| `passageHeaders` | `negra = 480 ms · ≈125 BPM`, in place of a tempo mark |
| `beamGroups: true`, `rests: false` | Beams on, no rest glyphs (D-16) |

**No `pixelsPerFrame`.** Left to itself the renderer makes each column as wide as what is drawn in
it, so a column where nothing starts collapses to a sliver. Setting a fixed width turns that off,
and with it the property that distance reads as how much is happening.

**Guides are turned off by pushing `frameMeasure` past the last column.** A step beyond the end
draws no interior dashed line, which is how the overlay toggle works without a second drawing mode
in the package.

### Building it once

The renderer owns real DOM and a lot of state — the selection, the open toolbox, the scroll
position. It is built **once per piece**, later changes are driven through its methods, and it is
destroyed on unmount.

Which is why the effect that builds it depends on the music and the key, **never on the callbacks**.
Callbacks change identity on every parent render, and depending on them would tear the renderer down
constantly. They live in a ref the effect reads at call time.

The same reasoning applies upward: `RhythmPage` keeps live annotations in refs rather than state.
Feeding them back in as props would rebuild the renderer on every keystroke and close the toolbox
the reader is typing in.

### Things positioned imperatively

The playhead and the two range handles are placed from `placeCursor` against the last render, not
from React state. They move with redraws the host never asked for — a re-wrap, a change of width —
and state holding pixels would be a frame behind every one of them.

The range handle grip is a **square** where the playhead's is a circle. The two are often within a
few pixels of each other, and the shape is what says which one you are about to take hold of. The
two ends are clamped apart rather than allowed to cross: an inverted range reads as empty everywhere
downstream, and a reader could not tell that from a bug.

---

## 4. What the package decides, and what it does not

**It decides grouping and engraving.** Beams, stems, accidentals against the key, clefs, ledger
lines, where a line breaks, how a page re-wraps.

**It does not decide any note's name.** The figure of every printed note is chosen on the backend
from a ladder the reader named, and arrives through `printedFigureFor`. That keeps the ladder, the
proportional comparison (D-11) and the closed vocabulary (D-12) in one place, and it is why renaming
a note changes a glyph and moves nothing.

### The one automatic grouping rule with an escape

A beamed run is set **tighter** than the same notes unbeamed (D-33): a beamed onset keeps 35 % of
the usual space after it, and the empty columns inside a run shrink by the same fraction — but only
columns nothing else has claimed, so a column carrying the other hand keeps its width.

The cost, stated plainly: the width of a column now depends on the printed figure, and renaming a
ladder changes printed figures. **So the notes inside a renamed passage shift horizontally.** D-21
still holds — nothing outside the renamed passage moves, which is the property that matters. What
does not hold is the stronger "renaming moves nothing at all", which was true before beaming
existed. `vexflow-v2/tests/ladder-locality.test.ts` pins both halves.

The package cuts a run at a **returning low note**, which catches the common arpeggio. It cannot
catch the rest, because where a phrase restarts is a reading of the music rather than a property of
it. That is what `beamBreakAt` is for, and it is applied **last**, after every automatic split
(D-34).

A break that would strand the first note alone is not an error: that note takes a flag, which is
what a lone corchea is.

---

## 5. Key suggestion

`suggestKeySignature(music, { fromColumn, toColumn, activeKeySignature })`, measured on the same
spelling rule the page prints with — so the number reported is the ink actually saved rather than a
second opinion about it.

**It never applies itself.** A transcription has no key, so everything used to print in C; on one
real piece that was 242 accidentals that did not need to be there. The suggestion is offered and the
reader accepts or changes it.

---

## 6. Printing

The pages are drawn by the package (`renderScorePages`), which re-wraps the music to the paper
exactly the way it re-wraps it to a narrower window. Nothing is scaled down to fit: a line that will
not fit across an A4 page breaks earlier and carries on below.

That is what makes **the margin the control**. Narrower margins give every line more room before it
has to break.

The last step — reading the drawn pages off the DOM and writing PDF operators — is this app's, in
`src/print/`. See [score-pdf.md](score-pdf.md).

---

## 7. Persistence

The reader's decisions go to the backend as `rhythm.json` through `PUT /time/{uuid}/rhythm`, and
nothing about the drawing is stored. See
[../backend/rhythm-and-annotations.md](../backend/rhythm-and-annotations.md).

Octave brackets live in the renderer's own state and reach the backend through the same save body
as everything else. They were the exception until 2026-09-13: `SavedRhythm` had no field for them,
so they were dropped on save and did not survive a reload. See
[../backend/rhythm-and-annotations.md](../backend/rhythm-and-annotations.md#ottavas-ottava--null).

There is no `grid-notation.json` and no `/notation/*` route. Those belonged to the VexFlow-era
editor, where the package owned the markup envelope and the host stored it verbatim. The wall-clock
model made every annotation a backend model instead, keyed by column.

---

## 8. What went with the old editor

Stated so nobody looks for them: `GridScore`, `ScoreReadingControls`, `NotationPage`,
`music/gridNotation.ts`, `music/mergeOnsets.ts` and `planHostMerge`, `api/notation.ts`, the
`/notation/artifacts`, `/{id}/matrix`, `/{id}/grid-state` and `/{id}/merge-onsets` routes, the
cell-edit patch path, insert-and-remove-frames, and the bar-line and tie reading aids.

**Merging a splintered chord** is gone with them and is worth a sentence, because the problem it
solved has not disappeared: when the transcription hears one note of a chord a fraction early, it
gets its own column and prints as a stray short note in front of the chord. The wall-clock answer is
different — chord grouping now runs on the **raw times before snapping** (D-04), with a fixed 40 ms
non-chaining window, so the splinter is joined at the source rather than repaired on the grid.

**The frame clock** is gone for the same kind of reason. `frameTimestamps` existed so a renderer
could follow a non-uniform tempo map. There is no tempo map, and there is no tempo: a column is a
fixed number of milliseconds and converting one to a moment is multiplication.

---

## 9. Checking the drawing

```bash
npm run check:render
```

A notation renderer fails loudly at draw time and **silently at layout time**. A wrong option name
throws and you see it; a score that draws no noteheads, loses a hand, or stops beaming renders a
blank-looking page with no error at all. Neither typecheck nor lint can see either one, so
`scripts/check-render.mjs` draws a real two-hand envelope into jsdom and asserts against the stable
DOM contract the package documents. Plain `.mjs` on purpose: no build step, no native dependency.

The fixture is a schema 2.0 envelope and the check builds a `GridNotationRenderer` with a
`printedFigureFor`, mirroring `TimeScoreView`. It crosses the Spanish-to-English figure seam the app
crosses (`negra` → `quarter`), so a change on either side of that map is caught.

It was broken from P6.9 until 2026-09-13, when its fixture was still 1.x and the package refused it.

---

## 10. Where to look deeper

- `../../vexflow-v2/documentation/` — the package's own client documentation, seven numbered files
- [components.md](components.md) — where `TimeScoreView` sits in the tree
- [score-pdf.md](score-pdf.md) — the PDF writer
- [../backend/time-matrix.md](../backend/time-matrix.md) — the payload it draws
