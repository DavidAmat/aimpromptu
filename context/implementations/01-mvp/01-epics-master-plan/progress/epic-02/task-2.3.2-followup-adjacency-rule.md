# Task 2.3.2 — follow-up: the adjacency rule is binding

Date: 2026-07-27. Supervisor decision. Supersedes the "open question" section of
[`task-2.3.2-progress.md`](task-2.3.2-progress.md).

## The decision

> *"The rule is there to avoid extra ligatures like the example you are showing. The rule must be
> followed. The options to explore are to either have only 4 negra (1 second) or have 4 negras + 1
> corchea (the adjacent figure next to negra) (1.5 s). Since 1 s is closer to 1.23 s than 1.5 s is,
> the resolution here is to simply produce 4 negras."*

Non-adjacent ligatures are **never generated**. The contradiction in Appendix C is resolved in
favour of the rule, and against its own worked example's answer.

## What it made simpler

The supervisor's framing is a cleaner algorithm than the one I had:

> **List the durations that can be written legally, and pick the one closest to what was played.**

That is the whole thing. Legal means a single figure, or two **adjacent** figures tied — which is
just a dotted note. My previous version rounded to the nearest column *first* and then searched for
something writable, which was a step of indirection with no purpose once the candidate list is this
short.

### The worked example, as documented

*1.23 s at 60 BPM, semicorchea grid (0.25 s per column):*

| Candidate | Columns | Lasts | Distance from 1.23 s |
|-----------|---------|-------|----------------------|
| corchea | 2 | 0.50 s | 0.73 s |
| **negra** | **4** | **1.00 s** | **0.23 s** ← closest |
| negra + corchea (dotted) | 6 | 1.50 s | 0.27 s |
| blanca | 8 | 2.00 s | 0.77 s |

Result: a plain **negra**, `1 -1 -1 -1`. `negra + semicorchea` (1.25 s) would have been nearer, but
skips corchea, so it is not a candidate.

The appendix's other number needs no special case: 1.1 s is 0.10 s from a negra and 0.40 s from a
dotted negra, so it is "counted as a 1 second" by the same comparison.

## Changes

| Where | Change |
|-------|--------|
| `expressible_columns` | adjacent pairs only. The old `strict_adjacent=False` default is gone; the escape hatch is now `allow_non_adjacent=True`, which exists **only** so a test can demonstrate what the rule excludes |
| `approximate_duration` | compares against the **unrounded** duration (`duration / column_seconds`) rather than a pre-rounded column count — that is what makes "closest" mean closest to what was actually played |
| `_nearest_expressible` | renamed `_closest_writable`; same tie-break (shorter wins) |
| `snap_note` | parameter renamed to match |

Legal column counts at semicorchea granularity are now `1, 2, 3, 4, 6, 8, 12, 16, 24` — singles and
dotted notes, nothing else.

### Why comparing against the unrounded duration matters

Rounding first loses the information the comparison needs. A note lasting 5.4 columns rounds to 5;
5 is unwritable, and 4 and 6 are then equidistant from it, so the tie-break would pick 4 — even
though 6 is plainly nearer to 5.4. Comparing against 5.4 directly gives 6. One line, and it only
shows up in cases like this.

## Knock-on effects

Two existing tests changed answer, both correctly:

- **`test_snap_note_places_a_transcription_event`**: 1.23 s is now 4 columns, so a note starting at
  column 4 ends at column 8 rather than 9.
- **`test_the_project_features_rounding_example`** (Epic 4). At **fusa** granularity the legal
  counts are `1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48`, so the features doc's example resolves as:
  - `1.1 s` = 8.8 columns -> **8** (a negra, 1.00 s); 12 would be 1.50 s.
  - `0.6 s` = 4.8 columns -> **4** (a corchea, 0.50 s); 6 would be 0.75 s.

Both were previously 9 and 5 — counts only reachable through non-adjacent ties.

## Verification

```
pytest        # 452 passed
mypy, flake8, black   # clean
```

New tests: the worked case with its exact figures and error; the candidate comparison spelled out;
`5 not in expressible_columns(SC)` and its appearance only under `allow_non_adjacent=True`; the
complete legal set `[1, 2, 3, 4, 6, 8, 12, 16, 24]`; and a structural test asserting **every**
two-figure entry is a dotted note (the second figure is exactly half the first).

## Documentation

The rule is now written down in three places, at three levels of detail:

- `matrix/approximation.py` module docstring — the algorithm and the candidate table.
- `plan/epic-02-matrix-core/.../task-2.3.2-duration-approximation.md` — the task file's subtask and
  acceptance criterion rewritten, with a note that the earlier draft's expected answer was the
  contradiction.
- `progress/user_review/epic-02-matrix-core.md` §5.4 — the same table for a non-developer, runnable.
