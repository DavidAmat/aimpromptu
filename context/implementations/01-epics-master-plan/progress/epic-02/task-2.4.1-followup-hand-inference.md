# Task 2.4.1 follow-up — the two-hands split is inferred, not thresholded

> Context: [checklist](../../plan/checklist.md) · research prompt:
> [`02-system-prompt-hand-inference-poc.md`](../../plan/research-01-hand-inference/02-system-prompt-hand-inference-poc.md)

**Date:** 2026-07-28. **Status:** implemented, tests green, awaiting the supervisor's
musical trial on real transcriptions.

## What changed

Task 2.4.1 shipped Appendix D as written: `Do-4` (MIDI 60) and above is the right hand,
everything below is the left. That produced a readable grand staff and was always meant to
be replaced. The `poc-piano-hand-prediction` research repository was built to find the
replacement; its **v3 beam dynamic program** is now the default here.

`split_hands()` no longer takes a `threshold`. It runs inference and returns the same
`TwoHands` shape plus the evidence behind the decision. The old rule is still available two
ways, deliberately:

| Call | What it does |
|------|--------------|
| `split_hands(matrix)` | beam DP over onset groups — the default |
| `split_hands(matrix, method="threshold")` | the C4 rule, *scored by the same cost model* so it stays comparable |
| `split_hands_at_row(matrix, threshold="Mi-4")` | pure row arithmetic, no cost model |

## Why the threshold had to go

Not because it was slightly less accurate. On the research benchmark (209 scenarios,
3,674 labelled onsets) the numbers were:

| | threshold | **beam v3** |
|---|---:|---:|
| onset accuracy | 0.848 | **0.955** |
| exact scenario match | 0.583 | **0.844** |
| invariant violations | 21 | **0** |
| physically impossible hand spans | 21 | **0** |

The last row is the argument. A fixed pitch boundary treats a note's register as a
*decision* when it is only *evidence*, so it cannot express things that are ordinary piano
writing:

- an exact octave (`Do-3` + `Do-4`) is fingers 1 and 5 — the threshold split it every time;
- a scale from `Sol-3` to `Sol-4` is one gesture — the threshold cut it in three;
- a left hand jumping from a bass note into middle-register chords under a stable melody;
- a hand crossing;
- a melody dipping below middle C without changing hands.

The replacement models the split as what it is: a temporally coupled allocation of two
moving hands, minimising a named objective over onset groups.

## The objective

Eighteen named, separately weighted, individually ablatable terms — span, capacity,
movement, acceleration, crossing, crossing-duration, interleaving, voice continuity, role
stability, pitch prior, octave, split, balance, dominance, polyphony, engagement, handoff,
future. Definitions and units are in the module docstring of
`aitu_backend/hands/costs.py`; the tuned defaults are in `config.py`.

Two things worth knowing:

1. **Hard feasibility is not a big penalty.** Five fingers and the absolute span limit make
   `transition()` return `None`, so the search never visits that state. Pricing them as
   costs is how a model ends up recommending something unplayable because it was cheap
   overall.
2. **The C4 rule survives as `pitch_prior`, weight 0.10.** It is a nudge worth about a
   twelfth of a movement unit per octave of deviation, routinely overruled by context.

## Where hands are decided, and where they are read

Once, at the **clean** stage of the pipeline — `transcription/pipeline.py::derive`. Every
view reads that one result rather than deciding again, so the notation, the piano roll and
the falling notes cannot disagree about who plays a note.

| Artifact | Holds |
|---|---|
| `two-hands_<gran>_{right,left}.npz` | the two aligned matrices (unchanged) |
| `hands_<gran>.json` | the compact map, for a working artifact |
| `metadata.json` → `handAssignments` | the compact map, for a saved version |
| `GET /matrix/{uuid}/hands` | the same block, for any consumer |

## The compact hand map

One character per onset — `"l"` or `"r"` — in the matrix's canonical `(column, row)` order,
which is exactly the order the sparse COO payload lists its onsets in:

```json
"handAssignments": {
  "method": "beam-dp-v3",
  "handMap": "lrrrrrrrlrrrrrrr",
  "onsetCount": 16,
  "granularity": "fusa",
  "frameCount": 24,
  "ambiguousOnsets": 1,
  "infeasibleGroups": 0,
  "warnings": []
}
```

Reading it is one counter: walk `rows`/`cols`/`onset`, skip sustains (`onset[i] === -1`),
and take the character at the running onset index. Sustains carry no character because a
note is played by one hand from strike to release — a per-sustain character would be
redundant data that could go out of sync. TypeScript reader:
`aitu-frontend/src/music/handMap.ts`.

At one byte per note a four-minute piece costs a few kilobytes; an array of
`{col, row, hand}` objects would have cost roughly thirty times that and restated `rows`
and `cols` which the payload already carries.

`onsetCount`, `frameCount` and `granularity` travel with the map so a consumer can check it
still describes the matrix in hand. A mismatch means the matrix was edited after the split;
the readers on both sides refuse rather than guess, because a map off by one note would
mis-colour a whole passage while looking authoritative.

## Performance

The threshold was a numpy row mask — effectively free. A search is not, and the pipeline
test that guarded "sub-second recompute" now measures the two separately, with the reason
written into the test.

| Input | Time |
|---|---:|
| 1-minute piece | 0.24 s |
| 3-minute piece | 0.88 s |
| 4-minute piece (960 frames) | 1.27 s |
| 5-minute grid of random noise (40+ simultaneous keys) | 1.6 s |

Three optimisations found while getting there, all algorithmic rather than tuning — the
first pass took **34 s** on the noise case:

1. **Overloaded groups are flagged, not searched.** Past ten distinct simultaneous keys no
   two-hand assignment exists, so there is no question to optimise. It warns and moves on.
2. **Voice memory is built once per transition, not once per note**, and looked up by
   binary search. This was the single largest win; it was the hottest path by far.
3. **Two O(k²) loops** (interleaving inversions, closest hand inversion) reduced to O(k)
   and O(k log k), and the per-term `dataclasses.replace` chain replaced by one
   accumulator.

Runtime tracks **onset groups × beam width × candidates**, so polyphony is the risk, not
matrix resolution. A finer granularity is cheap; a wall of chords is not.

## What is still weak

Carried over from the research repository's own failure ledger — these are known, not
newly discovered:

- **Hand crossings.** A one-frame crossover and a permanent role swap are priced almost the
  same. `crossing-duration` scored 0.400 acceptable-match against 1.000 for most families.
- **Delayed voice splits.** When diverging voices still fit one hand the objective keeps
  them there until forced apart; a human splits earlier.
- **Long runs.** Nothing models cumulative lateral travel, so a three-octave run may stay in
  one hand where a player would hand it over.
- **Octave doubling** is genuinely undecidable from the matrix — one-hand octaves and
  two-hand unison look identical.

## Do not trust `confidence` as a probability

It is `1 − exp(−margin / 0.5)`, where `margin` is how much more the cheapest *local*
alternative that flips this note would cost. It ignores downstream consequences and has
never been calibrated. Fine for ordering a review queue or highlighting close calls; not
for automatic acceptance, not for showing a user a percentage, not for comparing pieces.

## Open question for the supervisor

`relocation_mode` defaults to `release_aware`: a hand cannot move while its assigned keys
are still sounding. The matrix carries no pedal data, so this is unprovable either way —
the research benchmarked it as better, but pedal-heavy real material may want
`onset_gap`. Worth a listen once real transcriptions go through.
