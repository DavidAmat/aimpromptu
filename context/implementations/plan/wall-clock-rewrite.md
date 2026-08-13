# The remaining epics, rewritten for the wall clock

**Written 2026-08-12.** Epics 1 to 9 were planned and mostly built on a model the app no longer
has. The time-based concept refactor replaced it, closed on 2026-08-10, and deleted the code the
old model needed. This file says what changed, what that means for the work still to do, and which
rules every remaining task file now obeys. Each rewritten task file links here instead of repeating
it.

Model documents, all still valid: the reasoning in
[`../time-based-concept/PRD.md`](../time-based-concept/PRD.md), the frozen decisions in
[`../time-based-concept/decisions.md`](../time-based-concept/decisions.md) (D-01 … D-34), the data
shapes in [`../time-based-concept/contract.md`](../time-based-concept/contract.md), and what
shipped in [`../time-based-concept/CLOSURE.md`](../time-based-concept/CLOSURE.md).

---

## 1. What changed, in one paragraph

A matrix column used to do two jobs: it was where a note sits on the page **and** it was the
rhythmic value of that note. Because it was both, its width came from a tempo somebody typed in,
and a grid that could not express the playing produced the same wrong figure every time. The two
jobs are now separate. **Position is measured wall-clock time** — one column is a fixed number of
milliseconds, 40 by default (D-01). **The figure is a name the reader chooses** — you click the gap
that repeats in your own playing, say what it is called, and every other note takes its name from
that one choice (D-09, D-10). There is no BPM anywhere in the product.

## 2. The five rules a remaining task has to respect

1. **`events.json` is the piece.** The engine's output in seconds is the only thing stored; every
   matrix, peak, ladder, figure and sheet is derived from it per request (contract §8). A feature
   that changes the music changes `events.json`. A feature that changes only how the music reads
   is stored beside it, in `rhythm.json`.
2. **A column never moves.** Column index is `round(onset_ms / frameMs)` (D-02). Anything keyed by
   frame stays valid as long as the piece's wall-clock length does not change. This is what makes
   editorial marks survive edits, and it is the reason the range splice in Epic 11 preserves
   duration.
3. **No BPM, no bar lines, no time signature, no metre** (D-01, D-28). A metronome is still allowed
   as a sound in the player's ears — clicks every X milliseconds — but nothing derived from it is
   stored.
4. **Granularity is gone as a concept.** There is no raw / collapsed / clean / two-hands ladder of
   resolutions any more, and no collapse or upsample step. `frameMs` is a **view** of the same
   events, chosen per request. A version folder is `v<N>_f<frameMs>`, for example `v2_f40`: the
   version number means the music changed, the suffix means you looked at it on a finer clock.
5. **The reader's answer beats the rule.** Every automatic choice — figure, beam group, tuplet,
   hand — has a manual override that is applied last and stays local (D-17, D-34). Any new
   automatic behaviour in these epics ships with the same escape.

## 3. The splice rule for range editing

David's rule, and the reason for it. **A re-recorded passage is written back into exactly the
window it replaces.** You mark 3 seconds of the sheet, you may play the passage as slowly as you
like — 6 seconds, 12 seconds — and the take is scaled back into those same 3 seconds on accept.

The column count therefore never changes, and that single property buys everything else: the
recording still lines up with the page, the playhead still lands where it did, and every passage
boundary, key change, override, beam break and fingering **after** the edited window keeps working
without renumbering. It is the same property D-21 gives a ladder change — an edit at the end of a
piece must never make a reader re-read the beginning.

The underlying operation is a plain splice of a submatrix of columns and it does not care about
length: fewer columns and more columns are both possible. Range editing does not offer them,
deliberately. Where a length change is the point — appending a new passage to a piece being
composed — it belongs to Epic 13, which is allowed to move everything after the insertion point
because there is nothing there yet.

## 4. Verdict per remaining epic

| | Verdict | Why |
|---|---|---|
| Story 9.7 — tuplets, trills, chords | **Partly shipped, rest rewritten** | Chord grouping and tresillos already exist (D-04, D-32). What remains is manual N-tuplets and trill detection. |
| Epic 10 — Piano Library | **Alive, small changes** | Reads the time score payload and the saved rhythm; version names carry `frameMs`; PDF is now a real deliverable. |
| Epic 11 — Range editing | **Alive, rewritten** | The splice rule above replaces every BPM and beat calculation in the old text. |
| Epic 12 — Annotations | **Partly shipped, rest alive** | Fingering shipped in P8.1. Lyrics and cue-size notes are unchanged in intent and change home. |
| Epic 13 — Composing live | **Alive, rewritten** | An empty piece is an empty `events.json` and a `frameMs`, not an empty matrix at a BPM. |
| Epic 14 — Final documentation | **Alive, larger** | It also has to cover the wall-clock model and the work done after the plan closed. |

## 5. What is dead and is not coming back through these epics

- **Choosing a granularity**, and the collapse and upsample steps behind it.
- **Typing a BPM** anywhere, including "recording tempo", "track tempo" and any beat arithmetic.
- **Editing a matrix cell by hand**, and matrix JSON import and export. The Matrix tab is gone.
- **Bar lines, time signatures, measures** and anything counted in beats, such as "trim the take to
  the expected number of beats".
- **Text notation and Matrix JSON as ways to create a piece.** A sheet is written from recorded
  onsets and neither of those has any.

If one of these should return on the wall-clock path, it is a new feature request with its own
reasoning, not unfinished work from the old plan.

## 6. What already came back after the plan closed

Recorded here because `user-reviews.md` and `CLOSURE.md` were written before it and say these do
not exist. On the branch `plan-resume`, 2026-08-10: **Piano Roll** and **Notes Falling** are back,
drawn from `GET /matrix/{id}/events` on the wall clock; a note can be taken off the recording and
put back; notes can be picked singly or with a rubber band; the scrub bar, the draggable playhead
and double-click to seek work on every page that plays. **Matrix**, **Notes Falling (raw)** and
**Music Notation** stay retired.
