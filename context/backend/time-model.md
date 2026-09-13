# The wall-clock model

What replaced tempo, why, and the rules everything downstream obeys. This is the single most
important idea in the project: almost every other design decision follows from it.

The reasoning at length is in
[`PRD.md`](../implementations/03-time-based-concept/PRD.md); the numbered decisions are
[`decisions.md`](../implementations/03-time-based-concept/decisions.md) (D-01 … D-34) and they stay
frozen and valid.

## The problem it solves

The app used to write music the way a metronome hears it. You told it a tempo and a note
resolution, it built a grid of *note figures*, and it fitted your playing into that grid.

Playing that was even came out ragged. A run of equal notes printed as a mix of sixteenths and
dotted eighths, **every time** — because no human plays exactly on a grid, and the grid was not
asking.

## The two numbers

A column used to be one thing doing two jobs. It is now two separate numbers.

**Where a note sits is measured wall-clock time.** A column is a fixed slice of real time, 40 ms by
default, and the column index of an onset is `round(onset_ms / frameMs)`. Nothing is fitted to
anything, and the same recording always gives the same columns.

**What a note is called is a label you choose.** You look at a picture of how the piece was actually
played — the distribution of gaps between one note and the next — click the gap that keeps
repeating, and give it a name: "that is a quarter note". Every other note takes its name from that
one choice, by proportion.

**Renaming moves nothing.** Changing your mind costs one click and no re-timing.

## The five rules

Every feature in the product obeys these.

**1. `events.json` is the piece.** The engine's output in seconds is the only thing stored; every
matrix, peak, ladder, figure and sheet is derived from it per request. A feature that changes the
music changes `events.json`. A feature that changes only how the music *reads* is stored beside it,
in `rhythm.json`.

**2. A column never moves.** Anything keyed by frame stays valid as long as the piece's wall-clock
length does not change. This is what makes editorial marks survive edits, and it is why a
re-recorded passage is scaled back into exactly the window it replaces.

**3. No BPM, no bar lines, no time signature, no metre.** A metronome is still allowed as a *sound
in the player's ears* — clicks every X milliseconds — but nothing derived from it is stored. The
only BPM number anywhere is printed text in a passage header, beside the millisecond value, because
some readers think in BPM.

**4. Granularity is gone as a concept.** There is no raw / collapsed / clean / two-hands ladder of
resolutions, and no collapse or upsample step. `frameMs` is a **view** of the same events, chosen
per request. A version folder is `v<N>_f<frameMs>`: the version number means the music changed, the
suffix means you looked at it on a finer clock.

**5. The reader's answer beats the rule.** Every automatic choice — figure, beam group, tuplet, hand
— has a manual override that is applied last and stays local. Any new automatic behaviour ships with
the same escape.

## Why the app never chooses the ladder

Interval statistics fix a ladder only **up to a rational factor**. A beat and twice that beat
explain the same gaps equally well. On one real piece's second half, two candidates scored within
0.1 % of each other.

So the app presents and the reader decides (D-09). Naming one peak labels every other peak
immediately, so the consequence of the choice is visible before it is committed (D-10).

Neither reading is more correct — the reader picks the one that is easier to read.

## What is measured on raw times, and why it matters

All peak finding and ladder fitting runs on the raw timestamps, **never on snapped columns** (D-07).

Snapping splits every peak. A real 337 ms gap becomes 8 or 9 frames depending on phase, so it
appears as 320 ms about 57 % of the time and 360 ms the rest — one clean spike holding half the data
becomes two half-height spikes. Measured, not assumed.

Chord grouping runs on raw times for the same kind of reason (D-04): two notes 39 ms apart can
straddle a column boundary, so "same frame = same chord" would be phase-dependent.

## What a printed length is

**The time from this onset to the next onset in the same hand** (D-14), capped at one redonda.
Per hand, not per key.

The accepted cost, stated plainly: a held note inside one hand is cut short when that hand plays
anything else. This is deliberate — the alternative fills the page with ties, rests and inner
voices, which is the ugliness being removed, and the player already knows the piece.

There are no ties (D-13) and no rest glyphs (D-16). Distance on the page is time, so a silence is
already the space it takes and the dashed lines crossing it.

## The closed vocabulary

`redonda`, `blanca`, `negra`, `corchea`, `semicorchea`, `fusa`, `semifusa`, plus dots on `blanca`
and `negra` **only** (D-12).

The dot restriction is deliberate. With dotted corcheas banned, a swing pair of 211 ms and 125 ms
both land on *corchea* — exactly what a printed sheet of a shuffled piece shows. Allowing the dot
pulls the long half to a dotted corchea and recreates the ragged mix.

One exception exists because a ladder of halves has no name for it: **three even notes dividing a
beat are marked as a tresillo, not rounded** (D-32). The rule is deliberately narrow, because a
wrong tresillo is worse than a missed one.

## What is dead and is not coming back on its own

- Choosing a granularity, and the collapse and upsample steps behind it
- Typing a BPM anywhere, including "recording tempo" and any beat arithmetic
- Editing a matrix cell by hand, and matrix JSON import and export
- Bar lines, time signatures, measures, and anything counted in beats
- Text notation and matrix JSON as ways to create a piece — a sheet is written from recorded onsets
  and neither of those has any

If one of these should return on the wall-clock path, it is a new feature request with its own
reasoning, not unfinished work.

## Where to look deeper

- [`documentation/services/backend/events-to-sheet.md`](../../documentation/services/backend/events-to-sheet.md)
  — the derivation path, step by step
- [`documentation/services/backend/time-matrix.md`](../../documentation/services/backend/time-matrix.md)
  — every schema 2.0 field
- [`documentation/services/backend/rhythm-and-annotations.md`](../../documentation/services/backend/rhythm-and-annotations.md)
  — what is stored beside `events.json`
- [`decisions.md`](../implementations/03-time-based-concept/decisions.md) — D-01 … D-34, frozen
- [`CLOSURE.md`](../implementations/03-time-based-concept/CLOSURE.md) — how the refactor closed
