# The wall-clock model

What replaced tempo, why, and the rules everything downstream obeys. This is the single most
important idea in the project: almost every other design decision follows from it.

The reasoning at length is in
[`PRD.md`](../implementations/01-mvp/03-time-based-concept/PRD.md); the numbered decisions are
[`decisions.md`](../implementations/01-mvp/03-time-based-concept/decisions.md) (D-01 … D-34). They stay
frozen as a record; the ones a later implementation changed say so below (D-09 twice, D-12, D-14, D-32).

**Since implementation 03** (opened 2026-10-23) the sheet is the new sheet: an F1 frames sheet
(`sheet.f1`) written by the AI or the algorithm and drawn by the backend as SVG
([`aitu-backend/src/aitu_backend/sheet/README.md`](../../aitu-backend/src/aitu_backend/sheet/README.md),
sections 9 to 17). Phase 10 (2026-10-27) removed the old sheet (vexflow-v2) and the code that measured
the gaps and built the ladder.

## The problem it solves

The app used to write music the way a metronome hears it. You told it a tempo and a note
resolution, it built a grid of *note figures*, and it fitted your playing into that grid.

Playing that was even came out ragged. A run of equal notes printed as a mix of sixteenths and
dotted eighths, **every time**, because no human plays exactly on a grid, and the grid was not
asking.

## The two numbers

A column used to be one thing doing two jobs. It is now two separate numbers.

**Where a note sits is measured wall-clock time.** A column is a fixed slice of real time, 40 ms by
default, and the column index of an onset is `round(onset_ms / frameMs)`. Nothing is fitted to
anything, and the same recording always gives the same columns.

**What a note is called is a label, chosen once for the piece.** One reference figure (how long a
negra lasts) names every other figure by proportion. Who chooses it changed over time (see "Who
names the figures" below): first the reader, from a picture of the gaps; since implementation 03 the
AI or the algorithm, with **Transpose figures** as the reader's override.

**Renaming moves nothing.** Changing the reference figure re-times nothing.

## The five rules

Every feature in the product obeys these.

**1. The stored notes are the piece.** A feature that changes the music changes the notes. A
feature that changes only how the music *reads* is stored beside them: in `sheet.json` for the old
sheet, in `sheet.f1` since implementation 03 (the hands stay in `notes.pmn`). The matrix and the hand
split are derived from the notes per request. The old sheet was derived whole on each request too;
the new sheet is stored, because writing it costs an AI run, and it is laid again on the current
notes when they change. Since implementation 02, Phase 3 the notes are `notes.pmn` (milliseconds),
in the part's folder of the project bundle; until then they were `events.json` (seconds), which is
still the shape the code works in.

**2. A column never moves.** Anything keyed by frame stays valid as long as the piece's wall-clock
length does not change. This is what makes editorial marks survive edits, and it is why a
re-recorded passage fitted into its window keeps the length. Where the length changes on purpose (a
paste, a whole take put in place of a passage, implementation 02), every note and mark after it
moves in the same write.

**3. No BPM, no bar lines, no time signature, no metre.** A metronome is still allowed as a *sound
in the player's ears* (clicks every X milliseconds), but nothing derived from it is stored. The old
sheet printed one BPM number, as text in a passage header beside the millisecond value. Implementation
03 confirmed this rule (plan section 3.1, the user's decision of 2026-10-23) and took it further: the
new sheet has no compases, no tempo, no puntillos and no silencios, and prints no BPM at all. The
algorithm may estimate a pulse internally (`proposal.beat`) to choose its figures and beams; nothing
of it is printed.

**4. Granularity is gone as a concept.** There is no raw / collapsed / clean / two-hands ladder of
resolutions, and no collapse or upsample step. `frameMs` is a **view** of the same events, chosen
per request. The old playground named a version folder `v<N>_f<frameMs>`: the version number meant
the music changed, the suffix meant you looked at it on a finer clock. Implementation 02, Phase 3
deleted the playground.

**5. The reader's answer beats the rule.** Every automatic choice (figure, beam group, hand, and the
old sheet's tuplet) has a manual override that is applied last and stays local. Any new automatic behaviour ships with
the same escape.

## Who names the figures (D-09, in three steps)

1. **The MVP (D-09, D-10).** Interval statistics fix a ladder only **up to a rational factor**: a
   beat and twice that beat explain the same gaps equally well (on one real piece's second half, two
   candidates scored within 0.1 % of each other). So the app presented the peaks of the gaps and the
   reader named one; naming one peak labelled every other at once.
2. **Implementation 02, Phase 2.** The sheet was drawn at once with the highest pile of gaps named a
   negra; the reader could still rename it.
3. **Implementation 03 (decided 2026-10-23; in the app since Phase 5, 2026-10-25).** D-09 is changed:
   the AI names the reference figure in a request of its own (the peaks of the gaps described in
   words), or the algorithm does from its pulse estimate (`proposal.beat`) when there is no AI. The
   result is `quarterMs` of `sheet.f1`. **Transpose figures** of the Sheet step is the reader's
   override (rule 5). Phase 10 (2026-10-27) removed the gap plot, the peaks and the ladder code.

## What is measured on raw times, and why it matters

The gaps between onsets are measured on the raw timestamps, **never on snapped columns** (D-07): the
old sheet's peak finding and ladder did so, and the AI's reference request still does.

Snapping splits every peak. A real 337 ms gap becomes 8 or 9 frames depending on phase, so it
appears as 320 ms about 57 % of the time and 360 ms the rest: one clean spike holding half the data
becomes two half-height spikes. Measured, not assumed.

Chord grouping runs on raw times for the same kind of reason (D-04): two notes 39 ms apart can
straddle a column boundary, so "same frame = same chord" would be phase-dependent.

## What a printed length is

**The old sheet (D-14):** the time from this onset to the next onset in the same hand, capped at one
redonda. **The new sheet (implementation 03, plan section 3.1):** the note's own length, relative to
the reference figure, capped at the next onset of the same hand. The figure does not grow to fill
the silence after it: a short chord stays a negra even when the next note of that hand comes much
later. Per hand, not per key, in both.

The accepted cost, stated plainly: a held note inside one hand is cut short when that hand plays
anything else. This is deliberate. The alternative fills the page with ties, rests and inner voices,
which is the ugliness being removed, and the player already knows the piece.

There are no ties (D-13) and no silencios (D-16). A blank space means the hand plays nothing.

## The closed vocabulary

`redonda`, `blanca`, `negra`, `corchea`, `semicorchea`, `fusa`, `semifusa` (D-12). The old sheet
also allowed dots on `blanca` and `negra` only: with dotted corcheas banned, a swing pair of 211 ms
and 125 ms both land on *corchea*, which is what a printed sheet of a shuffled piece shows. The new
sheet goes further and prints **no puntillos at all**: a dotted negra is written as the nearest plain
figure.

The old sheet marked three even notes dividing a beat as a tresillo (D-32). The new sheet has no
tuplets; its grace notes, trills, turns and mordents are written by the AI or the rules instead.

## What is dead and is not coming back on its own

- Choosing a granularity, and the collapse and upsample steps behind it
- Typing a BPM anywhere, including "recording tempo" and any beat arithmetic
- Editing a matrix cell by hand, and matrix JSON import and export
- Bar lines, time signatures, measures, and anything counted in beats
- The gap plot and the reader naming a peak (D-09 as first written): replaced by the AI's reference
  request and **Transpose figures** (implementation 03; the code removed in Phase 10, 2026-10-27)
- Text notation and matrix JSON as ways to create a piece: a sheet is written from recorded onsets
  and neither of those has any

If one of these should return on the wall-clock path, it is a new feature request with its own
reasoning, not unfinished work.

## Where to look deeper

- [`documentation/services/backend/events-to-sheet.md`](../../documentation/services/backend/events-to-sheet.md):
  from the notes to the hand split, step by step
- [`documentation/services/backend/time-matrix.md`](../../documentation/services/backend/time-matrix.md):
  the frame and the figure names that stayed of schema 2.0
- [`aitu-backend/src/aitu_backend/sheet/README.md`](../../aitu-backend/src/aitu_backend/sheet/README.md):
  the new sheet, sections 9 to 17
- [`documentation/services/backend/rhythm-and-annotations.md`](../../documentation/services/backend/rhythm-and-annotations.md):
  the old `sheet.json`, still read for its marks
- [`plan section 3`](../implementations/03-apply-poc-research/03-plan.md): the rules of the new sheet and what changed
- [`decisions.md`](../implementations/01-mvp/03-time-based-concept/decisions.md): D-01 … D-34, frozen
- [`CLOSURE.md`](../implementations/01-mvp/03-time-based-concept/CLOSURE.md): how the refactor closed
