# Hand inference: the page-level second pass

The default split method is now `refine`: the beam dynamic program followed by a second
pass that repairs two defects the search structurally cannot see. This note records what
changed, why, and what it is worth, so the numbers are not folded away into commit
messages.

Everything here was measured on the 209-scenario benchmark that lives in the
`poc-piano-hand-prediction` repo. `scripts/benchmark_hands.py` is the bridge; run it after
any change to the cost model, the gate, the detector or the pass.

```bash
cd aitu-backend
PYTHONPATH=src:../../poc-piano-hand-prediction/backend/src \
  python3 scripts/benchmark_hands.py --methods beam,refine
```

## What changed

| | before | after |
|---|---|---|
| default method | `beam` | `refine` (`beam-refine-v1` in metadata) |
| `CostWeights.ledger` | 0.50, inside the search | 0.0 — the term moved to the pass |
| ledger weight in the pass | — | `RefineConfig.ledger_weight = 6.25` |
| gate on the `across` charge | none | `reach_gate`, on the other hand's availability |
| figuration | not modelled | `figuration.py`, `C_pattern`, and ledger relief |

## What it is worth

On the benchmark, 209 scenarios and 3 701 labelled onsets:

| configuration | accuracy | exact | invariants | severe | → correct | → wrong |
|---|---:|---:|---:|---:|---:|---:|
| no ledger term at all | 0.9546 | 168 | 0 | 64 | – | – |
| **what shipped before** (in-search 0.50, ungated) | **0.9506** | 165 | 0 | 37 | 34 | **49** |
| in-search 0.50, gated | 0.9554 | 168 | 0 | 52 | 34 | 31 |
| **`refine`, the new default** | **0.9641** | 170 | 1 | 45 | 36 | **1** |
| `refine`, gate off | 0.9551 | 164 | 1 | 19 | 36 | 34 |
| `refine`, register term off | 0.9546 | 168 | 0 | 64 | 0 | 0 |
| `refine`, figuration term off | 0.9649 | 171 | 1 | 42 | 39 | 1 |

*severe* counts onsets printed more than three ledger lines onto the other staff.
*→ correct* / *→ wrong* count onsets moved towards or away from the human labels,
against the plain beam.

Three things to read out of that table.

**The term as it shipped was a regression.** 0.9506 against 0.9546 for having no term at
all, and 49 onsets moved away from the labels. The geometry was never the problem; the
placement was. A group-by-group search that cares about the page rewrites whole textures
to tidy one chord — on an alternating-triad toccata it swapped the upper voice as readily
as the lower one.

**The gate is what makes the term pay.** Without it the pass still cleans the page —
severe onsets drop to 19, the lowest number in the table — and costs accuracy doing it,
34 regressions against 1. Fewest ledger lines is the wrong target. Human engravers write
129 onsets three or more lines across on this benchmark; 116 of them are while the other
hand is busy. What they essentially never write is a hand four lines across while the
other staff is *empty*: zero cases, against fourteen the ungated search produces. The gate
encodes that difference and nothing else.

**The figuration term costs three onsets here and is still worth having.** This benchmark
contains no broken figurations — the golden labels have 32 figures and 0 broken, the beam
27 and 0 broken — so the term has nothing to gain and only the relief to pay for. Its
value is on figuration-heavy material the benchmark does not contain: on the 18-scenario
suite built for it, exact matches go from 0.72 to 0.89 and broken figures from 3 to 0.
Turn it off with `DEFAULT_CONFIG.with_refine(pattern_weight=0.0)` if a piece is all block
chords and the three onsets matter more.

## The Mr Blue Sky cadence, and why the gate needed a second thought

`test_hands_staff.py` pins a real case: the closing cadence, where giving the first triad
entirely to the right hand pins it under its own sustains, so the ascent an octave higher
lands on the bass staff under five, six and seven ledger lines.

An honest gate breaks this case. At the moment the ascent arrives, the right hand really
cannot take it — it is holding four keys — so the gate reports "nothing to decide" and
charges nothing. The cause is two groups earlier, and neither the search nor a local move
can see that.

The fix is to distinguish **struck** blockers from **sustained** ones
(`HandModel.ledger_gate_sustained`). A hand blocked by keys it is striking now is forced;
a hand blocked only by what it is holding may have been handed that chord by a decision
that could have gone the other way. Sustained blockers are therefore charged in full, the
windowed re-solve is given something to improve, and it finds the split that keeps the
right hand free. A genuine crossing over a chord the other hand really is holding is still
safe, because moving into that hand is infeasible and the pass rejects infeasible moves.

This costs nothing on the benchmark — 0.9641 either way — and recovers the case.

## Cost

Roughly 1.7x the beam alone: 3.6 s to 6.0 s over the whole benchmark. The pass is bounded
by `RefineConfig.max_rounds` and `time_budget_s`, and by an incremental replay that
re-evaluates only the groups a move can affect and stops as soon as the joint hand state
reconverges with the reference. Without that shortcut it is roughly 16x on a four-minute
piece rather than 2x.

To trade quality for latency: `window_resolve=False` saves about a fifth and gives up the
only move that can restructure rather than relocate; `max_rounds=1` saves more.

## Known limits

* **A deliberate hand crossing is invisible in the matrix.** The pass's single regression
  on the benchmark is exactly that — a right-hand ostinato with one note a human gave to
  the left hand, reaching over. One onset in 3 701, and unfixable without a signal the
  matrix does not carry.
* **A figure split evenly between the hands is not detected.** It is a minority of both
  streams. `FigureModel.merged_stream` lifts this and immediately invents a figure inside
  a two-voice invention, so it is off.
* **The gate cannot express a swap.** It asks whether the other hand could *also* take a
  note, not whether the two should trade. Wide inversions are caught by the crossing and
  collision terms instead.
* **Figuration confidence is uncalibrated**, like the existing per-onset `confidence`.
