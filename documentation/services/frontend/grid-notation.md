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
(0.26.2), partial group-cell painting under a frame range (0.32.0), `setSystemGap` (0.33.0),
`SYSTEM_ROOM` and `resolveSystemGap` (0.34.0), octave brackets measured from their notes (0.35.0), `setStaffGapAt` (0.36.0), an open bracket beating a proposed one (0.37.0).

The package is at **0.37.0** as of 2026-09-16.

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
| `beamJoinAt(hand, frame)` | The other half of it: *do not start a group here*, which stands down the arpeggio rule |
| `keySignature`, `annotations.keyChanges` | The key, and where a passage leaves it |
| `annotations.clefChanges` | Where one hand leaves the clef it normally reads |
| `annotations.ottavas` | Octave brackets, each with the reader's `hidden` — no ink, and the notes stay where the bracket puts them |
| `onOttavaResize` | Which end of a bracket the reader pulled and where it landed, reported once per gesture. While the tip is held the package paints a `.grid-ottava-drag` overlay over the whole page — the stretch it would cover on every line it crosses, the column the end would drop into, and the columns either side of it. Amber, not the selection purple, and gone on pointer-up |
| `annotations.fingers`, `.lyrics`, `.trills`, `.passages`, `.graceNotes` | Everything from `rhythm.json` |
| `onLyricLayout` | Where the reader dragged a lyric's block and how wide they left it, reported once per gesture |
| `annotations.evenSpacings` | Runs of one hand set an equal distance apart |
| `annotationScale` | One number for every mark, not one per kind |
| `systemGap` | The distance between two system **boxes** — the reader's white space, less `SYSTEM_ROOM` |
| `staffGaps`, `onStaffGapsChange` | Lines the reader spread on their own, and the way the answer comes back |
| `noteSpacingPx` | Extra room between one note and the next, charged to onset columns only |
| `staves` | `"grand"`, or `"single"` when a hand is empty |
| `frameGroup`, `frameMeasure`, `silenceGroupPx` | The layout hints (D-23, D-27) |
| `passageHeaders` | `negra = 480 ms · ≈125 BPM`, in place of a tempo mark |
| `beamGroups: true`, `rests: false` | Beams on, no rest glyphs (D-16) |

**No `pixelsPerFrame`.** Left to itself the renderer makes each column as wide as what is drawn in
it, so a column where nothing starts collapses to a sliver. Setting a fixed width turns that off,
and with it the property that distance reads as how much is happening.

**The space between lines is driven through `setSystemGap`, never through the build.** It is the
twin of `staffGap` one level up — that one sets how far apart the two staves of a system are, this
one how far apart the systems are — and it is a separate number on purpose, because a reader who
wants more room between lines does not want the two hands pulled apart to get it. The constructor
takes the reader's gap for the first drawing and `TimeScoreView` calls the setter for every change
after that, so dragging the slider lays the page out again instead of rebuilding every note.

**`systemGap` is not the white space, and the page's slider is.** A system is not its staves: over
them is the frame-number strip, a block for the words above that, and a band at each end for the
corner marks — `SYSTEM_ROOM`, about 160 pixels. At `systemGap: 0` two lines are still that
far apart, which is more white than the staves are tall, so a reader moving the slider to its
minimum saw a page that had barely changed. `TimeScoreView` subtracts `SYSTEM_ROOM` before handing
the number over, which is why the slider can read 0 and mean it.

Negative values are therefore ordinary rather than exotic, and `resolveSystemGap` floors them **per
render**: a printed page draws no corner marks and no frame numbers, so it has less room to give
back, and the same number that puts two lines exactly together on screen lands on paper's own
tightest instead of pushing one line through the next. One function, used by the drawing and by the
paginator, for the same reason `resolveSystemPadding` is.

The playhead and the two range handles are placed against the last render, and `setSystemGap`
replaces that render, so both are put back immediately afterwards. That is why the effect that
applies the gap is written **above** the one that places the playhead: effects run in the order
they are written.

**Four things move sideways, and all of them are setters too.** `setNoteSpacing(px)`,
`setSpacings(ranges)`, `setEvenSpacings(runs)` and `zoom` re-measure the columns and lay the page out
again; `setSystemGap` and `setStaffGaps` only
move things down the page. The horizontal ones therefore re-wrap, which is why the effects that
apply them put the playhead and the range handles back the same way the vertical ones do.

Both of the new ones exist because the control on the page is a **handle**. The space between notes
and the spacing of one stretch were a slider and a pair of step buttons; a slider that ran through
the build would tear down and rebuild every note on every pixel of the drag, which is §2.4's trap
with a different name on it. `TimeScoreView` reads both from refs inside the build and drives every
change after that through the setter.

`evenSpacings` is applied **last of everything**, because being even is a statement about the
finished result: any rule running after it would make the run uneven again. The distance is the
widest gap the run already has, times the reader's `scale` (`MIN_EVEN_SPACING_SCALE`…
`MAX_EVEN_SPACING_SCALE`). At `1` nothing has to give way; **below `1` the glyphs may touch, and that
is deliberate** — the widest gap is usually wide on account of the other hand, so evening to it makes
a run as wide as its worst moment, and a reader who can see their own hand has room to spare is
right about it. Each column keeps a sliver so the grid stays a function. The change goes on
proportionally across the columns of each gap rather than all at its end, so the other hand's notes
keep their place inside it.

`noteSpacingPx` is charged to **columns that carry an onset and to no others**. Scaling every column
would be a zoom: the held notes and the silences would stretch along with the notes, and how long
nothing happened is the one thing a wall-clock page already says well. A stretch that wants more
than the rest of the page is `annotations.spacings`, which scales every column inside it — including
the silent ones — because that is what "make this passage wider" means.

**A clef change is a transition, exactly as a key change is.** `annotations.clefChanges` holds one
entry per point where a hand starts printing a different clef, and the package draws the whole
transition: a thin barline and the incoming clef on that staff alone. A beam never crosses one, the
same way it never crosses a key change, and the column before it reserves the block's width
unconditionally — measured on the *widest* clef, so flipping a passage back and forth cannot move
where the line wraps.

The reservation is **added to** what that column already asked for, not maxed against it. The block
is drawn leftward from the frame the new clef starts on, so it lands inside the previous frame's
column — and that frame's notes are drawn from the same column's left edge rightward. Two things in
one column, so the column holds both. Taking the greater of the two sized it for whichever was wider
and drew both in it, and a chord immediately before a change ran into the barline with nothing
between them but the block's own leading padding.

**`keyTransitionWidth` is still reserved with a `max`**, and has the same shape of defect; it shows
less because a key block draws both clefs and a row of naturals and so is almost always the wider of
the two.

**The staff gap is per line, and the page holds it.** `setStaffGapAt(column, gap)` spreads the one
line that column falls on; `setStaffGap` is still the page's own, which every line that has not been
spread takes. The renderer reports a drag through `onStaffGapsChange` and `RhythmPage` keeps the
list, because the renderer is rebuilt on the reader's next edit and anything it alone remembered
would go with it. Lines can be different heights as a result, and `planPages` takes a
`systemHeights` list so a page is never given more lines than fit.

**A click on a ruler cell starts the range at the pointer**, not at the group's own first column,
and keeps the group's length. A group is about a second of music and the cell is the whole of it, so
selecting the group left the click somewhere in the middle of the result and a reader aiming at a
note had to drag the left handle back to where they had just pointed. The frame is read through
`grid.frameAtX` rather than by dividing the cell evenly, because columns are not the same width —
a linear guess lands on the wrong column exactly where the music is densest. A keyboard press has no
pointer and keeps the group's start. `TimeScoreView` clamps the far end to the piece, since the last
group can now name a column past it.

**The passage header has a block of its own at the top of every system, and is measured from the top
of the box rather than from the staff.** It used to sit twelve pixels over the treble staff, which is
also where an octave bracket goes, so a piece opening under `8va` printed the ladder and the bracket
through each other. `PASSAGE_HEADER_BLOCK` (16 px) is added to `extraTopPadding` whenever the page
carries any header, and `drawPassageHeaders` is handed a `baselineY` rather than the staff top.

The measuring point matters as much as the room. Everything else above a staff sits at a fixed
offset from it — the frame numbers, the corner marks — except an **octave bracket**, which is placed
from the *notes*: it clears the highest one, so over a passage that reaches above the staff it climbs
and there is no fixed height it stays under. A header measured up from the staff can always be caught
by one, and was, as soon as the column numbers came off and the strip above the staff halved. The
baseline is `trebleTopY − padding.top − extraTopPadding + PASSAGE_HEADER_DROP`: the top of the
system box, which is the one line everything above the staff has to fit under.

Reserved on every system rather than only on the ones carrying a header, so every line stays the same
height and the paginator keeps counting them the simple way.
`rangeMarkers` stays on — the corners are how a reader sees which stretches carry an edit, and the
way back to one. The **hover preview is gone from the package**: a corner used to outline its whole
stretch while hovered, and on a page where the reader also marks stretches of their own that fired
while the pointer was merely on its way to the ruler. Removed rather than made optional, so nothing
can turn it back on by accident; the corner's `<title>` names the columns.

**`frameLabels` is a live option now, not only a print one.** `setFrameLabels(show)` re-renders
without re-measuring — the numbers are a strip above the staves, so no column changes width — and
the page drives it from the **Show frame numbers** pill, which starts off. `systemGapFor` in
`TimeScoreView` subtracts a smaller room when they are off, because `padding.top` drops from
`GRAND_STAFF_TOP_PADDING` to `GRAND_STAFF_TOP_PADDING_BARE`; without that the same number on the
space-between-lines slider meant two different gaps depending on a switch that has nothing to do
with it.

**A range drag says so.** `onSelectRange(range, { adjusting: true })` when the reader is pulling one
end of a stretch that already exists. From inside the view the two gestures look identical; to a
host they are not, and treating an adjustment as a fresh selection made `RhythmPage` re-place its
panel on every pixel of the drag — next to the *handle*, so the panel walked along underneath the
stretch being dragged out.

**A marked stretch can name a hand.** `FrameRangeSelection` takes an optional `hand`, and the ruler
paints the highlight over that hand's staff instead of over the whole system. It addresses nothing —
the columns are the address — and every consumer that does not care may ignore it. It is there so
that the **Clef** and **Octave** pills, which act on one hand, do not show a band across music they
will not touch.

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

The same reasoning applies upward. `RhythmPage` holds every edit in one object behind
`useEditHistory`, and the setters that write to it are made once and are the same function on every
render. A setter that changed identity would land in this effect's dependency list and rebuild every
note on every render of the page, closing the toolbox the reader is typing in.

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

The package cuts a run at a **returning low note**, which catches the common arpeggio. The note has
to fall at least `ARPEGGIO_DIP` staff steps — a third — below **both** its neighbours. One step was
the old threshold and it made every passing note a boundary: a level run of corcheas wandering
`sol la sol la` came out as four beams with nothing at the seams for a reader to see, which is what
implementation 07 was reported for. A real arpeggio always comes back by a leap, so the stricter
test keeps the case the rule exists for and drops the case it never should have caught.
`arpeggioDip: 1` restores the old rule for anyone who wants it.

It still cannot catch the rest, because where a phrase restarts is a reading of the music rather
than a property of it. That is what `beamBreakAt` is for, and it is applied **last**, after every
automatic split (D-34). `beamJoinAt` is the same statement in the other direction — *do not start a
group here* — and it stands down the low-note rule and nothing else: a beam still never crosses a
key change, a clef change, a cue boundary or a tuplet boundary, because those are not guesses about
phrasing, they are things a beam cannot be drawn over.

A break that would strand the first note alone is not an error: that note takes a flag, which is
what a lone corchea is.

### The one spacing rule that reads a figure

Space on this page is measured from the ink in a column, which is right and has one blind spot: a
blanca draws no more ink than a corchea, so a run of corcheas running into a blanca put the two
noteheads exactly as close together as two corcheas. `LONG_NOTE_APPROACH_SPACES` opens the column
**before** an onset that is two or more rungs of the ladder longer than the note before it, and only
when that note was a corchea or shorter. One rung — a corchea into a negra — is the ordinary texture
of a piece and is left alone.

It is charged once at the boundary, per extra rung, and never as a width per figure. Giving every
figure a width is the thing a wall-clock grid must not do (D-18, D-22): it would put the printing
back inside the layout and make the page's horizontal scale depend on what the reader called things
rather than on when they happened.

---

## 5. Key suggestion

`suggestKeySignature(music, { fromColumn, toColumn, activeKeySignature })`, measured on the same
spelling rule the page prints with — so the number reported is the ink actually saved rather than a
second opinion about it.

**It never applies itself.** A transcription has no key, so everything used to print in C; on one
real piece that was 242 accidentals that did not need to be there. The suggestion is offered and the
reader accepts or changes it.

`suggestOttavas` works the same way, and carries one rule worth knowing when reading its output: a
bracket it has already opened is what a second one has to beat. `kindFor` judges each chord alone,
so a lone very high note asks for `15ma` — and used to get one, over a single note, inside an `8va`
the reader was already holding. A different bracket now needs a run of onsets wanting it, or one
chord left hopeless *under the open bracket*, which is what how-far-out is measured against.

---

## 6. Printing

The pages are drawn by the package (`renderScorePages`), which re-wraps the music to the paper
exactly the way it re-wraps it to a narrower window. Nothing is scaled down to fit: a line that will
not fit across an A4 page breaks earlier and carries on below.

That is what makes **the margin the control**. Narrower margins give every line more room before it
has to break.

The printed pages start from the space between lines the screen is set to, and the print panel's own
slider overrides it — `renderPages` spreads the caller's options last. So a reader who opened the
lines out to keep two runs of ledger lines apart gets the same page on paper without asking twice.

The last step — reading the drawn pages off the DOM and writing PDF operators — is this app's, in
`src/print/`. See [score-pdf.md](score-pdf.md).

---

## 7. Persistence

The reader's decisions go to the backend as `rhythm.json` through `PUT /time/{uuid}/rhythm`, and
nothing about the drawing is stored. See
[../backend/rhythm-and-annotations.md](../backend/rhythm-and-annotations.md).

The space between lines goes with them, as `lineSpacing` — the reader's white space, not the
package's `systemGap`. It is a reading of the page like the mark
size, so it belongs to the piece rather than to the app, and a reading that reset on every reload
would make the control not worth having — which is exactly what happened to octave brackets below.

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
