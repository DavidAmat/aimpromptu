# 5 — Matrix core (Epic 2)

**What this epic did:** the musical rules. No UI at all — this is the engine every other epic uses.
Its 200-odd tests already cover it, so this guide exists so you can *see* the rules behave rather
than take my word for it.

About 10 minutes, all in a terminal. Run everything from `aitu-backend/`.

---

## 5.1 — Timing: how a square becomes a note length

```bash
uv run python -c "
from aitu_backend.matrix.model import PianoMatrix
m = PianoMatrix.empty(8, granularity='corchea', tempo_bpm=60)
print('one column lasts', m.time_step_seconds, 'seconds')
print('one column is', m.beats_per_column, 'beats')
print('8 columns =', m.duration_seconds, 'seconds')
"
```

Expected: `0.5 seconds`, `0.5 beats`, `4.0 seconds`.

> A beat is a **negra** (quarter note). At 60 BPM one negra is one second, so a corchea (eighth)
> column is half a second. This is the "60 BPM, 0.5 s per column" default from the notation
> documents — worth confirming it matches how you think about tempo.

---

## 5.2 — Collapsing: making the page less cluttered ⭐

This is the central idea of the project.

```bash
uv run python -c "
from aitu_backend.matrix.granularity import collapse_to
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.text_notation import sequence_to_sparse_payload

raw = PianoMatrix.from_coo_payload(
    sequence_to_sparse_payload(['*Do-4','Do-4','*Re-4','Re-4','*Mi-4','Mi-4','*Fa-4','Fa-4']),
    granularity='fusa', tempo_bpm=60)
c = collapse_to(raw, 'semicorchea')

print('columns:', raw.frame_count, '->', c.frame_count)
print('duration:', raw.duration_seconds, '->', c.duration_seconds)
print('notes still there:', [c.cell(r, i) for i, r in enumerate([39, 41, 43, 44])])
"
```

Expected: `8 -> 4` columns, `1.0 -> 1.0` seconds, `[1, 1, 1, 1]`.

> **What just happened.** Four notes were written as pairs of fine squares. Collapsing merged each
> pair into one — half as many squares, **the same music, the same total length**. Fewer squares
> means fewer symbols on the printed page. The rule when merging a pair is simply: *if either
> square is a struck note, the merged one is a struck note; otherwise if either is a held note, it
> is held; otherwise silence.*

**And it only goes one way:**

```bash
uv run python -c "
from aitu_backend.matrix.granularity import collapse_to, upsample_to
from aitu_backend.matrix.model import PianoMatrix
import numpy as np
g = np.zeros((88, 4), dtype=np.int8); g[39] = [1, 0, 1, 0]
m = PianoMatrix.from_dense(g, granularity='semifusa', tempo_bpm=60)
back = upsample_to(collapse_to(m, 'fusa'), 'semifusa')
print('before:', m.grid[39].tolist())
print('after :', back.grid[39].tolist())
"
```

Expected: `[1, 0, 1, 0]` before, `[1, -1, 1, -1]` after — the silences became held notes.

> **This is why the fine grid is kept forever.** Collapsing throws information away. Going back to
> a *different* resolution always starts again from the original fine version, never from an
> already-collapsed one. That is the rule you checked the speed of in guide 3.

---

## 5.3 — Cleaning: the readability rule

```bash
uv run python -c "
import numpy as np
from aitu_backend.matrix.cleaning import clean_sustains
from aitu_backend.matrix.model import PianoMatrix
g = np.zeros((88, 4), dtype=np.int8)
g[27] = [1, -1, -1, -1]   # a low Do held for four beats
g[39] = [0,  1,  0,  0]   # Do an octave up, struck on beat 2
g[41] = [0,  0,  1,  0]   # Re, struck on beat 3
m = PianoMatrix.from_dense(g)
print('before:', m.grid[27].tolist())
print('after :', clean_sustains(m).grid[27].tolist())
"
```

Expected: `[1, -1, -1, -1]` before, `[1, 0, 0, 0]` after.

> **The rule:** a held note stops being held the moment *anything else* is struck. The low Do was
> genuinely still ringing — but printing it as a four-beat note tied under a moving melody makes a
> page that is hard to read. So the score records the strike and drops the tail.
>
> **Does this match how you want your sheets to look?** It is the most opinionated rule in the
> project and it comes straight from your notation document. If you disagree with it once you see
> real scores in Epic 9, this is the one place to change.

**The exception:** re-striking the *same* key is untouched — a chord held while nothing else
happens keeps ringing. That is what makes held chords still work.

---

## 5.4 — Rounding real timings

```bash
uv run python -c "
from aitu_backend.matrix.approximation import approximate_duration, expressible_columns
print('writable lengths:', sorted(expressible_columns('semicorchea')))
for d in (1.10, 1.23, 1.40, 1.50, 0.98):
    print(f'{d:.2f}s ->', approximate_duration(d, 'semicorchea', 60).describe())
"
```

Expected:

```
writable lengths: [1, 2, 3, 4, 6, 8, 12, 16, 24]
1.10s -> negra (4 columns, -0.100 s)
1.23s -> negra (4 columns, -0.230 s)
1.40s -> negra + corchea (6 columns, +0.100 s)
1.50s -> negra + corchea (6 columns, +0.000 s)
0.98s -> negra (4 columns, +0.020 s)
```

> **The rule, in one sentence:** list the durations that can be *written* legally, and pick the one
> closest to what was played.
>
> Legal means a **single figure** (negra, corchea, …) or **two adjacent figures tied** — which is
> just a dotted note. Never a pair that skips a step.
>
> **The worked example, 1.23 s.** The candidates either side are:
>
> | Candidate | Lasts | Distance from 1.23 s |
> |---|---|---|
> | **negra** | **1.00 s** | **0.23 s** ← closest |
> | negra + corchea (dotted) | 1.50 s | 0.27 s |
>
> So it becomes a plain **negra**. `negra + semicorchea` (1.25 s) would have been nearer — but it
> ties figures two steps apart, so it is never even considered. That is the whole point of the
> rule: no fussy extra ligatures, even when they would be marginally more accurate.
>
> Some timing is lost this way, and that is accepted. A readable page beats a perfect stopwatch.

---

## 5.5 — Splitting the hands

```bash
uv run python -c "
from aitu_backend.matrix.hands import split_hands
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.text_notation import sequence_to_sparse_payload
m = PianoMatrix.from_coo_payload(sequence_to_sparse_payload(['*Do-3 || *Do-5','*Do-3 || *Re-5']))
h = split_hands(m)
print('left hand rows :', h.left.active_rows())
print('right hand rows:', h.right.active_rows())
print('same shape as the original:', h.right.shape == h.left.shape == m.shape)
"
```

Expected: left `[27]`, right `[51, 53]`, `True`.

> **Middle C is the dividing line** — that key and above is the right hand, below is the left.
> A deliberately simple rule for now; working out which hand actually played a note is a hard
> problem of its own.
>
> Note the last line: both hands keep the **full size** of the original. Splitting never cuts
> anything — it just blanks out the other hand's keys — which is what keeps the two staves lined
> up when they are printed one above the other.

---

## What "working" looks like

Every number above matches. If any does not, that is a real bug in the engine and worth telling me
about immediately — every later epic sits on top of this.

## The full test suite

```bash
make test
```

~450 tests, about two seconds. The matrix ones reproduce every worked example from your notation
documents by name — `test_appendix_b_first_example`, `test_appendix_c_worked_case`, and so on. If
you ever change a rule in the documents, those tests are where the change has to land first.

Next (optional): [6 — Artifacts and versioning](epic-05-artifacts.md)
