# Task 9.3.1 — Stems, beams and ties · progress

Status: **done, including the supervisor's rest/chord-duration follow-up** on 2026-07-27.

All three rules live in `notation/score_builder.py` and travel to the frontend as decided values
(`stemDirection`, `beamGroup`, `tieToNext`). `tests/test_notation_engraving.py` pins each one.

## Stem direction

Staff position is diatonic (`octave * 7 + letter`), not MIDI, so an accidental never moves a note to
a different line. Treble's middle line is Si-4, bass's is Re-3. Below it the stem goes up, otherwise
down; a chord or a beamed group uses the mean position — the group's centre of gravity, as the
feature doc asks.

The score deliberately stays one readable voice per hand. Simultaneous notes are one chord and
share the duration to the next onset, so partial recorded releases never split the chord into
multiple voices.

## Beaming

Maximal runs of consecutive same-figure beamable notes (corchea and shorter, undotted), broken at
measure boundaries. A lone corchea keeps its flag. Then the arpeggio break.

**The arpeggio rule needed narrowing.** Taken literally — "a note whose previous *and* following notes
are higher" — the rule also fires on the Mi of a Do-Sol-Mi-Sol Alberti figure, which would chop the
accompaniment into pairs and defeat the purpose. The doc's own phrasing is *the lowest note of the
pattern*, so a break now additionally requires the note to be no higher than anything within
`ARPEGGIO_WINDOW` (3 entries) either side. Do-Sol-Mi-Sol-Do-Sol-Mi-Sol breaks only at each Do.

The window is deliberately local rather than global, because the doc says the pattern's lowest note
"may change over time" — a walking bass finds its new low point without help.

## No-tie policy

The policy is a refusal, not a feature: **no ties, ever.** There are also no visible
rests between sounding events. A span that is not writable takes the longest legal figure that
fits; an interior residue becomes an invisible `isSpacer` timing slot, while a measure-ending
residue may become a visible rest. At a barline, the preceding event fills to the barline and any
gap before the next onset becomes a leading rest in the following measure.

The measure grid from Task 9.1.1 is what decides this, which is why the barlines had to exist before
the policy could.

## Errors found

The first draft of `_beam_runs` split at every strict local minimum; the Alberti test caught it
immediately. That test is the one to keep an eye on if the rule is ever tuned again.

## Manual trial

[`user_review/epic-09-notation.md`](../user_review/epic-09-notation.md) step 9.4 — play an
Alberti-style accompaniment (Do Sol Mi Sol, twice) as corcheas and check the beams break at each Do,
not at each Mi.

## For the next worker

`BEAMABLE_TOKENS` lives in `notation/durations.py`; dotted figures are excluded from beams on
purpose (same-duration rule). If tuplets (Task 9.7.1) ever beam, they will need their own grouping —
`beamGroup` is just an integer id, so a tuplet can reuse it.
