# Task 9.7.1 — Tuplets the app did not find (nice to have)

> **Rewritten 2026-08-12 for the wall-clock model.** Part of this task shipped in the refactor. See
> [`../../wall-clock-rewrite.md`](../../wall-clock-rewrite.md).

**Already done.** Three even notes dividing a beat are found automatically, before figures are
chosen, and drawn with a bracket and a 3 (D-32, tasks P3.9 and P6.10). The plot names such a pile
"corchea de tresillo" instead of calling it a badly fitting corchea.

**What is left** is everything that is not a triplet, and every triplet the rule deliberately misses
— D-32 is narrow on purpose, because a wrong tuplet is worse than a missing one.

## Subtask 9.7.1.1 — Mark a group by hand

Pick the notes with the selection the sheet already has (Command-pick for a set of notes, or a
marked stretch of columns for a whole passage), choose N — 3, 5, 6, 7 — and the group prints with a
bracket and the numeral. One hand at a time; a tuplet across two hands is not a tuplet.

## Subtask 9.7.1.2 — Where it is stored and when it is applied

Beside the figure overrides in `rhythm.json`, keyed by hand and the first note's frame, exactly like
a beam break (D-34). It is applied **after** automatic detection, so a manual group replaces an
automatic one over the same notes rather than competing with it. It changes how the notes are named
and grouped, never where they sit: no column moves, and every note outside the group is untouched
(D-17).

The old text spoke about "dropping the artificial rests" the tuplet range rendered. There are no
rests to drop — the sheet has no rest glyphs at all (D-16).

## Subtask 9.7.1.3 — Removing it

Deleting the mark restores whatever the automatic path produced, including an automatic tresillo if
the notes qualify for one.

## Acceptance

Manual trial: a five-note run in the right hand that prints as a ragged mix is marked as a
quintuplet and prints as five even notes under a bracketed 5; the left hand under it does not move;
**Remove all** clears the mark.
