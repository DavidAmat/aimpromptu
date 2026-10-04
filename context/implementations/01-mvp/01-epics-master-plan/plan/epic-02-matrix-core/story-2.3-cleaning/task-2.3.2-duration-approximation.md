# Task 2.3.2 — Duration approximation

`matrix/approximation.py`: Appendix C of `01-matrix-notation-logic.md`. Real recordings never land on the grid; snap onsets and durations onto matrix columns sensibly.

## Subtask 2.3.2.1 — Onset snapping

Given note events `(start_s, duration_s)` from transcription, snap onset time to the nearest column boundary at the working granularity (fusa for the raw matrix).

## Subtask 2.3.2.2 — Duration fit

**Supervisor decision, 2026-07-27: the adjacency rule is binding.** The wording below replaces the
original draft, which was ambiguous and whose acceptance example contradicted it.

The algorithm is: **enumerate the durations that can be written legally, and pick the one closest
to what was played.**

Legal means either

1. a **single figure** — redonda, blanca, negra, corchea, … down to the working granularity; or
2. **two figures tied, adjacent in the hierarchy** — i.e. a dotted note (negra+corchea,
   corchea+semicorchea, blanca+negra).

Never more than two figures, and **never a non-adjacent pair**. `negra + semicorchea` skips
corchea, and is exactly the fussy extra ligature the rule exists to prevent, so it is not a
candidate at all.

At semicorchea granularity the legal column counts are therefore `1, 2, 3, 4, 6, 8, 12, 16, 24`.
Between two of them, take the nearer; on an exact tie take the **shorter** (a note that ends early
leaves a gap, one that ends late collides with the next). Temporal information is lost this way and
that is accepted — a readable page is the goal.

Output is the number of sustain columns to emit after the onset column.

## Subtask 2.3.2.3 — Tolerance to human timing

Expose a tolerance parameter (fraction of a column) so slightly-early/late onsets quantize stably; document that BPM choice is sensitive (General Note in the notation-logic doc).

## Acceptance

The Appendix C worked case: **1.23 s at 60 BPM / semicorchea granularity -> a plain negra**
(`1 -1 -1 -1`).

The comparison that produces it:

| Candidate | Columns | Lasts | Distance from 1.23 s |
|-----------|---------|-------|----------------------|
| corchea | 2 | 0.50 s | 0.73 s |
| **negra** | **4** | **1.00 s** | **0.23 s** ← closest |
| negra + corchea (dotted) | 6 | 1.50 s | 0.27 s |
| blanca | 8 | 2.00 s | 0.77 s |

`negra + semicorchea` (5 columns, 1.25 s) would have been nearer still, but it ties two figures two
steps apart and is never generated.

The appendix's other number falls out of the same comparison: 1.1 s is 0.10 s from a negra and
0.40 s from a dotted negra, so it is "counted as a 1 second".

> The earlier draft of this file named `negra + semicorchea` as the expected answer. That was the
> contradiction; it is resolved in favour of the adjacency rule.
