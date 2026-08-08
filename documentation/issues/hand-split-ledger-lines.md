> Context: [transcription quality — the four layers](../../../context/music/transcription-quality.md),
> [the transcription pipeline](../services/backend/transcription-pipeline.md).

# A hand printing far outside its own staff

## The symptom

A stretch of the score where the **left hand** is written high above the bass staff under a
pile of ledger lines, and — usually in the same bar — the **right hand** is written low
below the treble staff under a pile of its own. The two staves have swapped territory for a
few onsets and then swapped back. The music is playable as written; it is just not what
anybody would engrave, and a reader has to count lines instead of reading notes.

The reference case is *Mr Blue Sky*, segment 00:05.00–04:57.37, frames **f1041–f1049**
(41.64–41.96 s):

```
f1041   Fa-5 -> LEFT     six ledger lines above the bass staff
f1044   Fa-2 -> RIGHT    six ledger lines below the treble staff
f1044   Mi-5 -> LEFT     five above the bass staff
f1049   Do-5 -> RIGHT    ...and the hands are back where they started
```

Fa-5 is the **top line of the treble staff**. Fa-2 sits comfortably inside the bass staff.
Neither note is remotely awkward — they were simply given to the wrong hands.

## Two separate causes, and how to tell them apart

### 1. The search: an impossible chord rewriting the music before it

This was the cause of the reference case, and it is the one to check first because it can
move a passage arbitrarily far.

`hands/beam.py` keeps a pool of surviving states per onset group, keyed by
`PairState.key()`. When **every** candidate partition is infeasible from **every** surviving
state — which happens whenever the transcription's sustains pin a hand under a chord no hand
could reach — the beam relaxes the group rather than dropping it, so an unplayable passage
appears in the output with a warning instead of vanishing.

That fallback used to write `pool[key] = ...` unconditionally. Two states differing only in
*history* — the same notes in the same hands, one reached cheaply and one ruinously —
collapse to the same key, so whichever parent happened to be enumerated last won, regardless
of cost. On the reference file that handed the path 15 objective units worse to the rest of
the piece, and the total cost of the whole split was **660.6 instead of 433.2**.

Fixed by taking the cheapest, exactly as the ordinary branch does. The fallback now also
emits a warning of its own (`no hand partition ... is reachable from any surviving hand
position`); `generate()` only ever warned about groups unplayable *in isolation*, so the
commoner kind — unplayable *from where the hands are* — was silent.

**How to recognise it.** The passage is far from anything difficult, the confidences around
it are 1.0, and there is an infeasible group **later** in the piece. Cut the window off
before that group and re-split: if the hands change, this is your cause.
`test_an_impossible_chord_does_not_rewrite_the_music_before_it` is that experiment as a test.

### 2. The cost model: nothing was charging for ledger lines

Seventeen of the eighteen cost terms ask what a pianist's hands can do. None of them asked
what the result would look like on paper, so two assignments that were ergonomically alike
were indistinguishable even when one of them printed four extra ledger lines. `pitch_prior`
looks like it should cover this and does not: it is linear from Do-4, weighted 0.10, and by
design "a nudge, never a decision".

`C_ledger` is the term that asks. See below.

## The `ledger` term

`hands/staff.py` + the block in `costs.transition` marked *what this assignment costs the
PAGE*.

The split decides which staff a note is drawn on — right on the treble, left on the bass
(`matrix/hands.py`) — so it is a typesetting decision as much as an ergonomic one. The term
counts the ledger lines the assignment forces onto the page and charges them **by
direction**:

| Direction | Meaning | Grace | Default |
|---|---|---|---|
| `outward` | left below the bass staff, right above the treble | `ledger_grace_outward` | 6 lines |
| `across` | left **above** the bass staff, right **below** the treble | `ledger_grace_across` | 2 lines |

Direction matters more than distance, and this is the whole design. La-0 and Fa-5 are both
six ledger lines off the bass staff; the first is the bottom note of the piano, which every
printed edition writes exactly there, and the second is the left hand standing in the right
hand's register. A single distance threshold cannot tell them apart, and one tuned to leave
the low octaves alone would never catch the case this term exists for.

Past the grace the charge is quadratic in the excess over `ledger_reference` (2.5 lines):

```
cost = ((lines - grace) / 2.5) ** 2        weight 0.50
```

so three lines across is 0.08 — a whisper, which is right, because a right-hand chord
reaching down to Fa-3 is ordinary writing — and six is 1.28, which is a verdict.

Two properties worth knowing:

* **A chord pays for its extremes, not for every note.** A ledger line is drawn through the
  whole chord, so four notes six lines up cost the page what one does. Struck notes only;
  held ones were charged when they were struck.
* **It is a cost, not a veto.** Hard feasibility is a separate answer (`transition` returns
  `None`), and no weight on this term can overrule it. A crossing the hands are genuinely
  committed to still happens, and prints with its ledger lines — which is correct, and is
  why the term did not turn the package back into the pitch threshold it replaced.

Spelling: the term spells black keys as sharps, because the split runs before any key
signature is chosen. The disagreement with a flat spelling is at most one ledger line, well
inside either grace.

## What changed on the reference file

Whole piece, 2639 onsets, against the shipped behaviour before this work:

| | total cost | onsets across their staff | of those, > 2 lines | worst |
|---|---|---|---|---|
| before | 660.6 | 419 | 68 | 7 lines |
| beam fix only | 433.2 | 392 | 47 | 7 lines |
| beam fix + `ledger` | 441.9 | 388 | 42 | 6 lines |

27 onsets moved from the beam fix, 8 more from the term. The cost rises slightly in the last
row because a new term is being charged — the assignment is cheaper on every term that
existed before.

The strongest evidence is not the histogram. This piece has 14 saved `handOverrides` — notes
the reader moved to the other staff by hand, which is a human label for the same question.
The term agrees with **6 of the 14** without any override, all of them in the closing cadence
at f7184 and f7209. The old code agreed with none.

## The 8 corrections it still does not make, and why

f6692–f6778. The right hand is holding **seven** sounding keys spanning Fa-3 to Sol#-4 —
a pedalled chord whose sustains the transcription reports as held keys — so a new note
cannot go to the right hand (eight keys, five fingers) and cannot go to the left either
(span 33 semitones from its own held Do#-2). *Both* hands are hard-infeasible, the group is
relaxed, and no soft cost participates in that decision at all.

This is the known pedal limitation, not a tuning problem: the matrix carries no pedal data,
so a pedalled chord and a chord physically held down are the same thing to the model. Do not
try to fix it by raising the `ledger` weight — a soft term cannot and should not overrule a
hard constraint. It needs pedal detection, which is a different piece of work.

## Diagnostic recipe

```python
from aitu_backend.hands import DEFAULT_CONFIG, infer_hands
from aitu_backend.hands.staff import direction_of, ledger_lines

result = infer_hands(matrix, DEFAULT_CONFIG)
for item in result.assignments:
    lines = ledger_lines(item.midi, item.hand)
    if direction_of(item.midi, item.hand) == "across" and lines > 2:
        print(item.column, item.note, item.hand, lines, item.cost_breakdown, item.reasons)
```

* `reasons` names the offender directly: `left: 6 ledger lines across the bass staff — the
  other hand's register`.
* An empty `ledger` entry in `cost_breakdown` on an obviously off-staff note means the group
  was **relaxed** — check `result.warnings` and `diagnostics.infeasible_groups`, and read
  cause 1 above.
* To ablate: `DEFAULT_CONFIG.with_weights(ledger=0.0)`. If the passage is identical with the
  term off, the term is not what is deciding it.

## Where the reader still overrules everything

None of this replaces the note toolbox's *send to the other staff*, which writes a
`handOverride` into `rhythm.json`. The split is a proposal about music the algorithm cannot
see the player's hands for; the reader has the last word, and always did.

## Tests

`aitu-backend/tests/test_hands_staff.py`. Two fixtures are real windows of the reference
recording rather than constructions: `MR_BLUE_F1010` (the passage above, which fails on the
old fallback) and `MR_BLUE_F7140` (the closing cadence, which fails with `ledger` at zero —
the term's own ablation).
