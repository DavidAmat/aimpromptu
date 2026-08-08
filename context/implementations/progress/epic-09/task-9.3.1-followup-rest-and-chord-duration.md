# Task 9.3.1 follow-up — onset-led rests and chord durations

Status: **implemented and regression-tested** on 2026-07-27 at the supervisor's request.

## Rule

- A measure may begin with rests before its first entrance.
- Once sounding begins, no visible rest is placed before another onset.
- The preceding note/chord fills the onset-to-onset span.
- Every member of a chord shares that span even when recorded releases differ.
- The final event expands toward the barline; only an unwritable tail becomes a visible rest.
- An unwritable interior residue is an invisible timing spacer, preserving alignment without
  drawing silence or repeating the note.
- No tie is emitted across a barline; any gap before the next onset becomes a leading rest.

## Implementation

`notation/score_builder.py` now builds the hand timeline from onset groups instead of recorded
release gaps. `ScoreEntry.isSpacer` crosses the API only for a mathematical interior remainder;
the thin VexFlow adapter gives that rest transparent fill/stroke while retaining its ticks.

The cut-measure UI copy was updated: inserted timeline columns push the following note into a new
measure, while the preceding event expands to the old barline when readable.

## Verification

Regression tests cover a delayed entrance, interior gaps, unequal chord releases, seven corcheas
whose final Si expands to a negra, invisible odd interior residue, visible odd trailing residue,
and the Do-Re-Mi-Fa cut-measure example. Golden score documents were deliberately regenerated.
