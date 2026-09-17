# Rendering: how the sheet is drawn

The staff is drawn by `@aimpromptu/grid-notation`, a TypeScript package developed in the sibling
`vexflow-v2` checkout and installed from disk. One file in this app touches it:
`components/time/TimeScoreView.tsx`.

## Why the project has its own renderer

VexFlow lays notes out from accumulated tick arithmetic inside measures. A piano matrix has no
measures and no metre — it has **columns of wall clock** — and the one property the whole project
depends on is that a right-hand and a left-hand event in the same column print at the same x.
Tick-based layout can only approximate that, and the approximation drifts.

The package makes columns the horizontal source of truth: **one `time → x` map, shared by both
staves, the ruler and every overlay**. The hands cannot come apart, because nothing computes their
positions separately.

## How far apart the lines are

The white space between one set of pentagrams and the next is a slider beside the key signature,
saved with the piece. **The number on it is the white space itself**: at 0 the staves of one line
sit directly under the staves of the line above, and at 72 — the default — there are 72 pixels
between them.

That plainness took some doing, and the reason is worth knowing. A **system** is not its staves.
Over them is a strip that holds the frame numbers, over that a block for the words, and a band at
each end for the corner marks: some 160 pixels in all, `SYSTEM_ROOM` in the package. The
package's own `systemGap` is the distance between two *boxes*, so setting it to nought still leaves
the lines further apart than the staves are tall. A reader asked for a number and got one that did
nothing they could see. `TimeScoreView` takes the room off before handing the number over, and the
package floors the result per render so no setting can pull one line through the next. Room a lyric
or an octave bracket needs is added back by the drawing, because the words live in it.

It is **vertical**, so it is nowhere in the `time → x` map: no column changes width, no note moves
sideways, and `vexflow-v2/tests/system-gap.test.ts` pins that.

## Magnifying the page

**Hold Command (Control on Windows) and scroll over the sheet** and it is drawn larger, up to four
times. The chip beside **Show frame numbers** says what it is at and puts it back.

It is a **magnifier and not a change to the music**: the drawing is scaled on screen, so no column
is measured again, the page wraps exactly where it did, and nothing about a note moves relative to
anything else. One is the floor, because the natural size is already the page laid out for this
window and drawing it smaller would show no more music. It is for working on a crowded passage —
picking one notehead out of a chord, putting the end of a stretch on the right column — where the
page at its natural size is smaller than a pointer is accurate.

Two things it has to get right, and both are in `TimeScoreView`. The point under the pointer stays
under it, by scrolling the page back by however far the anchor drifted; and **every measurement
taken from a pointer is divided by it**, because the stage's box on screen is the magnified one
while the drawing's own units are not. It is how the page is being looked at, so it is not in
`SheetEdits`, not undoable and not saved. The gap **inside** a system, between
the two staves of one hand pair, is a separate number and is dragged on the page itself.

### One line spread on its own

The handle between the two staves of a line spreads **that line**. It used to write one number for
the whole page, so a reader opening out a chord that needed the room got every line on the score
opened out with it.

Each answer is keyed by a **column inside the line**, never by the line's place down the page: the
score re-wraps to the window, so "the third line" is different music at another width. Where a
re-wrap brings two answers onto one line the wider wins — both were a reader asking for room, and
giving less than was asked for is the only outcome that loses something.

Lines can therefore be different heights, which the paginator is told about: it budgets each line at
its own height rather than at one average, or a page would take more lines than fit.

### Where an octave bracket starts and stops

The bracket is measured from the **notes it covers**, not from the columns the reader dragged
across. It used to run from `xForFrame(fromColumn)` to `xForFrame(toColumn)`, and `toColumn` is
exclusive — so the hook came down on the x of the first note the bracket does *not* cover. A
notehead is centred on its column, so the hook landed on that notehead, and a reader looking at it
could not tell whether it was inside the bracket or outside. That is the one question a bracket
exists to answer.

Now the `8va` begins just before the first notehead it covers and the hook falls just after the last
one, cut to a fraction of the way to the neighbour where that neighbour is close. Both ends land in
a gap and never on a note. `vexflow-v2/tests/ottava-span.test.ts` pins it.

### Which brackets the page proposes

`suggestOttavas` measures how far outside its staff a hand is written, in **ledger lines** rather
than in pitch, and offers a bracket where a run of chords is far enough out for long enough. It
proposes; the reader keeps, moves or clears.

The rule that matters when reading its output: **a bracket already open is what a second one has to
beat.** A chord is judged on its own account by `kindFor`, which knows nothing about what is open,
so a lone very high note asks for `15ma` — and it used to get one, over a single note, in the middle
of an `8va` a reader was already holding. Now a different bracket is only proposed where a run of
onsets wants it, or where one chord is left hopeless *even under the open bracket*, and how far out
a chord is is measured under that bracket rather than against the bare staff.

### The corner marks

A stretch carrying an edit draws two corners, and until 0.34.0 they were measured from the **edge of
the system box** rather than from the staves. The two are a long way apart: the box begins above the
frame-number strip, so a corner sat some eighty pixels clear of the music it was about, while the
band reserved for it — immediately above the staff — stayed empty. It read as page furniture rather
than as a mark on a passage, and it paid for the room twice.

## Two things a reader notices

**Columns are not evenly spaced.** A column is as wide as what it draws, so horizontal distance
reads as *density*, not duration. A column where nothing starts collapses to a sliver, and silence
is charged per group rather than per column, so a five-second rest is a few closely spaced dashed
lines instead of five seconds of blank page.

The dashed lines are the only thing on the page saying the horizontal axis is wall clock. Without
them the spacing would read as ordinary note-value spacing, which would be wrong.

**The score re-wraps, it never scales.** A narrower window puts the music on more lines at the same
size. That is also how printing works: the paper is another width.

## What this app does not decide

**Any note's name.** The figure of every printed note is chosen on the backend, from a ladder the
reader named, and passed straight through. `TimeScoreView` never works out what a note should be
called from how many columns it covers — a column is a slice of time and says nothing about note
values.

That is the whole point of the model, and it is what makes renaming cheap: a wrong figure changes a
glyph and nothing else.

## One automatic rule with a visible cost

A beamed run is set **tighter** than the same notes unbeamed. A beam carries the eye across a group,
so the whitespace between its noteheads is doing no work and full width makes a run read as loose
separate notes.

The cost, stated plainly: the width of a column now depends on the printed figure, and renaming a
ladder changes printed figures. **So the notes inside a renamed passage shift horizontally.**

Nothing outside the renamed passage moves, which is the property that matters — correcting the end
of a piece must never make a reader re-read the beginning. What does not hold is the stronger
"renaming moves nothing at all", which was true before beaming existed.

## Where a beam breaks

The package groups what is regular: one hand, one key, one clef, no tuplet boundary. A long run
climbing through an arpeggio has none of those inside it, so it beams as one shapeless slope with
stems reaching across two octaves — where a player hears two gestures.

It does cut a run at a **returning low note**, which catches the common arpeggio. It cannot catch
the rest, because where a phrase restarts is a reading of the music rather than a property of it.

So there is one grouping input that is a judgement: select a note, press **Break the beam here**,
and that note begins the next group. It is applied last, after every automatic split, because a
person's answer beats the rules rather than competing with them.

## The stale-`dist` trap

Worth knowing before you debug anything about the drawing.

The package is a symlink, `dist/` is in its `.gitignore`, and there is no version of it anywhere in
this app's lockfile. So what runs in the browser is **whatever `dist/` was last built from**, and
nothing warns when that is several releases behind the source beside it. It has happened: the
package's git log said 0.26.2 while `dist/` was still 0.15.0, and the app quietly kept engraving
with the old code.

**Pulling the package is never enough — rebuild it.** If a documented feature seems missing, check
the build before checking the docs.

## Checking the drawing

```bash
npm run check:render
```

A notation renderer fails loudly at draw time and **silently at layout time**. A wrong option name
throws and you see it; a score that draws no noteheads, loses a hand, or stops beaming renders a
blank-looking page with no error at all. Neither typecheck nor lint can see either one.

26 checks, mirroring what `TimeScoreView` does: a schema 2.0 envelope, a `GridNotationRenderer`, and
each note's figure handed in rather than derived. It was broken from P6.9 until 2026-09-13 — the
fixture was still 1.x and nothing said so, which is exactly the silent failure it guards against.

## Where to look deeper

- [`documentation/services/frontend/grid-notation.md`](../../documentation/services/frontend/grid-notation.md)
  — the seam, every option passed in, and what went with the old editor
- [`../backend/time-model.md`](../backend/time-model.md) — why the layout is what it is
- [printing.md](printing.md) — the same drawing, on paper
- `../../vexflow-v2/documentation/` — the package's own client documentation
