# The work after the plan closed — reported late

**Written 2026-09-13 by Task 14.1.1.3.** These reports are about work committed on the branch
`plan-resume` between **2026-08-10 and 2026-08-12**, immediately after the time-based concept plan
closed and before the remaining epics were rewritten for the wall clock.

None of it had a progress report. It belonged to no epic: the plan it would have been reported
under had closed the day before, and the epics it fed into had not yet been rewritten. That gap is
what Subtask 14.1.1.3 exists to fill, and it is why two documents written before this work —
[`user-reviews.md`](../../../03-time-based-concept/user-reviews.md) and
[`CLOSURE.md`](../../../03-time-based-concept/CLOSURE.md) — said that some of these features did not
exist. **Both have now been corrected.**

## Why the gap happened, said plainly

`CLOSURE.md` ends with "David plays a round of varied piano music through the app and collects what
is wrong or awkward. That list becomes a new implementation plan." What actually happened is that
the round of playing started immediately, produced findings immediately, and they were fixed
immediately — without a plan folder to report them in.

The work is good and it is all in the product. What was missing was the record of it.

## The reports

Each is reconstructed from its commit, which in this repository carries the reasoning as well as
the change. Where a commit recorded a browser measurement, that measurement is quoted rather than
summarised.

| # | Report | Commits | Date |
|---|---|---|---|
| 1 | [Piano Roll and Notes Falling, back on the wall clock](01-piano-roll-and-notes-falling.md) | `5cd4d77` | 2026-08-10 |
| 2 | [Picking notes, scrubbing, and a rectangle worth reading](02-selection-and-rectangles.md) | `db6673e` | 2026-08-10 |
| 3 | [A deleted note leaves the matrix, and Save decides it](03-deleting-a-note.md) | `f7a9f34` | 2026-08-10 |
| 4 | [One scrub bar for every page](04-one-scrub-bar.md) | `a6ae2b2`, `b806ed2` | 2026-08-10 |
| 5 | [Both ends of a marked stretch, and double-click to seek](05-range-handles-and-seek.md) | `c22a1ea`, `5644d56` | 2026-08-10 |
| 6 | [The left hand is printed in corcheas](06-left-hand-in-corcheas.md) | `937f480` | 2026-08-12 |

One more commit from the same window, `4da19a2` — the hand-inference second pass — **was** already
documented, in
[`documentation/services/backend/hand-inference-second-pass.md`](../../../../../documentation/services/backend/hand-inference-second-pass.md).
It is listed here only so the window is complete.

## What ties them together

Five of the six came from one person using the app on their own recordings, and each fixed
something that only shows up that way.

Three themes run through them:

**Position has one home.** Reports 2, 4 and 5 are all one argument worked out in public: a click on
a note must mean "this note" and nothing else, so seeking has to live somewhere a click means
nothing — the scrub bar, the playhead, and a double-click on blank ground.

**A decision about the page is not a decision about the music, except when it is.** Report 3 draws
that line: taking a note off the page changes what its neighbour is *called*, so it is a decision
about the piece and gets staged, reviewed and saved rather than applied.

**One real recording beats a fixture.** Report 6 is four changes, each measured against a printed
Chopin score rather than against an intuition, and one of them — the fixed 40 ms chord-grouping
window — closed a hole where the column length was silently changing the music.
