# Rendering: how the sheet is drawn

Two sheets live side by side while implementation 03 replaces the old one (plan:
[`implementations/03-apply-poc-research/03-plan.md`](../implementations/03-apply-poc-research/03-plan.md)).

## The new sheet (implementation 03, Phases 5 and 6)

The Sheet step, a version of My library and Play mode show the **new sheet** first: the sheet without compases,
tempo, puntillos or silencios that the backend draws (`aitu_backend.sheet.engrave.frames`, the Leipzig glyphs and
Verovio's drawing rules). The page asks `GET /sheet/{part}?width=N` for the width it has (about 8.5 px a staff
space) and gets one SVG and a cursor map: one row per drawn column (its line, its x, its time) and one box per
line. The code is `pages/piece/sheet/frames/`:

- `FramesSheetPage.tsx`: the page (title lines, the player, the floating bar with Undo, Redo, **Enhance with AI**
  and **Edit in the old sheet**), and since Phase 6 the notes picked and the keys (⌘Z, ⇧⌘Z, Escape);
- `FramesNoteToolbox.tsx` (Phase 6): the note toolbox of the new sheet, beside the notes picked: **Hand** since
  Phase 6, every other note tool since Phase 7 (see [annotations.md](annotations.md), "The new sheet");
- `FramesRangeToolbox.tsx` (Phase 7): the range toolbox (*Frames*: Both / Right / Left, Key, Clef, Octave);
  `EnhanceStretchDialog.tsx`: **Enhance with AI** of a stretch with the user's words; `readingTools.ts`: what the
  two toolboxes share;
- `FramesSheetView.tsx`: the SVG as the backend wrote it, scaled to the page, and an overlay in the same units:
  the cursor (a line between two columns by their times), the lit noteheads of its column, the pale veil on the
  part Sonnet works on, and the blank staves that a part coming back from Sonnet is written into, column by
  column (about two seconds); since Phase 6 also the picking of notes (a click on a notehead, ⌘ or Shift to add,
  a box dragged across the staves), and since Phase 7 the marking of a stretch in the strip above the upper staff
  of a line, drawn as a lavender band over the staves in scope;
- `geometry.ts`: the research viewer's arithmetic (where the cursor is, the time under a click);
- `useFramesSheet.ts`: the loads, Sonnet's job followed on its stream (`event: sheet`), Sonnet started by
  itself on a new transcription, and an edit (one request whose answer is the sheet drawn again);
- since Phase 8: `FramesSheetToolbox.tsx` (Title, Key, Transpose, Lyrics, View), `FramesPreviewDialog.tsx` (the
  preview of a transposition), `FramesPdfDialog.tsx` (Print to PDF), `useFramesLyrics.ts` (the old Lyrics tab and
  its piece helpers on the sheet's `lyric` lines); the lyrics are drawn by the backend (`<text data-lyric>`), and
  the view picks, drags and lights them.

Hooks for the browser checks: `[data-frames-sheet]` (`data-source`, `data-llm`, `data-working`),
`data-note="<frame>:<midi>"` on each notehead, `[data-lit]`, `[data-frames-cursor]` (`data-ms`),
`[data-segment-state=working]`, `[data-revealing]`; since Phase 6 `[data-selected]` on the picked noteheads,
`[data-pick-box]`, `[data-frames-note-toolbox]`, and `sheet-undo`, `sheet-redo` (`data-testid`); since Phase 7
`[data-range-strip]`, `[data-range-band]` (`data-start`, `data-end`), `[data-frames-range-toolbox]`, and the
`data-testid` of each tool (`figure-4`, `beam-join`, `grace`, `ornament-trill`, `notes-remove`, `range-enhance`,
`stretch-words`, ...); since Phase 8 `[data-lyric]` (`data-lyric-lit`, `data-lyric-picked`), `[data-lyric-landing]`,
`[data-frames-sheet-toolbox]`, `[data-pdf-page]`, and `sheet-toolbox`, `sheet-print`, `line-space`, `piece-key`,
`pdf-download` (`data-testid`). The checks are `npm run check:frames-sheet` (`--live` spends a few cents of Sonnet on a 40 s
clip), `npm run check:frames-edit` (picking, the hand, undo and redo, and the time of one edit) and
`npm run check:frames-tools` (every tool of the two toolboxes and the range selection; `--live` makes one stretch
request, about $0.01) and `npm run check:frames-toolbox` (Phase 8: the sheet toolbox, lyrics, the keyboard panel,
Print to PDF, the lyrics in Play mode).

The engine stays in the backend (implementation 03, Phase 6, task 4): one edit takes about a quarter of a second
from the click to the new drawing on the page, most of it in the backend's rules (the stored sheet laid again on
the new hands), which a browser port of the drawing alone would not remove.

## The old sheet (vexflow-v2), until implementation 03, Phase 8

The old sheet keeps every editing tool and is one press away from the new one. The passage page, From other
projects and the requests review still open on it (their work is a marked stretch). The staff is drawn by
`@aimpromptu/grid-notation`, a TypeScript package developed in the sibling `vexflow-v2` checkout and installed
from disk. One file in this app touches it: `components/time/TimeScoreView.tsx`. The sections below are about it.

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

### Which clefs the page proposes

`suggestClefRanges` (0.43.0, implementation 02, Phase 7, plan section 11.7) proposes the **treble
clef** for a left-hand run, and the page takes it on a first write with the key and the brackets. A
chord is **high** when its lowest note is at least `minLedgerLines` (2) ledger lines above the bass
staff (E4 and up, where a stem reaches the right hand). A run of `minRunOnsets` (4) high chords or
more prints in the treble clef; one lower chord (`bridgeOnsets`) stays inside it only if it prints
no more ledger lines on the treble staff than on the bass, so a low chord is never written under the
treble staff. The run must save ledger lines, ends at the next left-hand onset at the latest, and
gives no change at frame 0. Shorter runs are left to `suggestOttavas`; a proposed bracket is cut
where a clef change begins.

**Measured on the 38 pieces with notes:** 10 pieces get runs (62 in all), almost all on tutorials
whose left hand plays high (Superestrella's tutorial, The Other Side); 28 get none. One ledger line
instead of two reaches 16 pieces, mostly over middle C; six chords instead of four leaves 18 runs.

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
