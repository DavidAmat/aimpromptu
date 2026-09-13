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
