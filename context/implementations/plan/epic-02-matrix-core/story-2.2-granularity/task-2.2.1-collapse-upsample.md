# Task 2.2.1 — Collapse and upsample

`matrix/granularity.py`: move a matrix between temporal granularities.

## Subtask 2.2.1.1 — One-step merge

Merging goes exactly one hierarchy step at a time (e.g. semifusa -> fusa). Column count halves (`X -> X//2`), `time_step_seconds` doubles, BPM unchanged. Pair-merge rules per row:

```text
[1, 1] -> 1     [0, 1]  -> 1     [-1, 0]  -> -1
[1, 0] -> 1     [0, 0]  -> 0     [-1, 1]  -> 1
[1,-1] -> 1     [0,-1]  -> impossible (validator catches upstream)
                [-1,-1] -> -1
```

Odd column counts: pad the tail with a silence column before pairing.

## Subtask 2.2.1.2 — Multi-step collapse

`collapse_to(matrix, target_granularity)` chains one-step merges (7th -> 6th -> 5th …). Never skip steps. Collapsing loses information; document that reversal is impossible — always recompute coarser targets from the stored raw fusa matrix, never from an intermediate.

## Subtask 2.2.1.3 — Upsample

Going finer (e.g. negra -> corchea) uses the simple expansion rules, one step at a time:

```text
0 -> [0, 0]    1 -> [1, -1]    -1 -> [-1, -1]
```

## Subtask 2.2.1.4 — Performance

Vectorized numpy implementation over the dense int8 form (reshape to pairs, lookup table), then back to sparse. Target: full collapse chain for a 5-minute piece at fusa granularity well under a second (keeps the in-situ BPM/granularity switching in the Matrix tab instant).

## Acceptance

Tests reproduce every worked example in `project-features.md` (single note, consecutive notes, silences, the X//2 -> X//4 -> X//8 chain).
