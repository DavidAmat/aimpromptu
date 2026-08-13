# Task 9.7.2 — Trills · progress

Status: **done** on 2026-08-13. Chord grouping was already shipped; this is the remaining half.

## What was implemented

Detection runs on raw event times, not on snapped columns. A run qualifies only when it is one
hand, exactly two pitches a whole tone or closer, strictly alternating, at least six pitch changes
(seven notes), with even gaps each between 25 ms and 160 ms. The rule is narrow on purpose: a
wrong trill hides real notes, a missed one costs nothing.

The score payload carries `trillSuggestions`. The Rhythm tab offers **Mark tr** / **Not a trill**.
Accepting stores the mark in `rhythm.json` over a frame range. The backend then collapses a *copy*
of the hand matrices: the storm of notes is silenced and one onset of the lower pitch is left,
held for the length of the run. Italic `tr` is drawn above that note. Playback still uses
`events.json` (D-29). Removing the mark, or wiping the reading, prints the notes again.

Other ornaments stay ignored by design.

## Errors found

None that changed the approach. An existing payload test
(`test_the_worked_example_at_00_46_prints_three_equal_corcheas`) already fails on `master` and
was left alone.

## Deviations

The drawing package already carries a `trill` passage kind losslessly but does not draw it. Rather
than changing `@aimpromptu/grid-notation` in a sibling repo, accepted marks use the existing free-text
annotation (`tr` in italic above the staff). Same visual, no package bump.

Ignored suggestions are stored in `rhythm.json` as `ignoredTrills` so they are not offered again
after a reload. The task did not ask for this; without it the chip would return every visit.

## Manual trial

1. Record a fast trill of at least seven notes, two neighbouring keys (a semitone or a whole
   tone), one hand, then a different note after it.
2. Open the Rhythm tab, name a gap, wait for the sheet.
3. A line should appear: **Possible trill at …** with **Mark tr** and **Not a trill**.
4. **Mark tr**: the storm becomes one held lower note with `tr` over it. Play: every
   alternation still sounds.
5. **Remove mark**: the notes print again.
6. Save, reload: the mark is still there. Wipe the reading: it is gone.

## For the next worker

Epic 9 is complete. Epic 10 (Piano Library) is next. The performance view (Task 10.2.1) already
lists trill marks among the overlay toggles; they will need to read `rhythm.json` the same way
the Rhythm tab does.
