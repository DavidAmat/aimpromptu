> Context: [context/music/transcription-quality.md](../../context/music/transcription-quality.md)

# An evenly played passage prints as a mix of corcheas and semicorcheas

The most common "the transcription is wrong" report that is **not** a transcription problem.
Diagnosed twice on 2026-08-02, on two different engines, on the same song — once on
ByteDance and once on Transkun, with the same root cause both times.

---

## Symptom

A fast passage the player clearly played evenly comes out on the score as an irregular mix
of figures — three semicorcheas, a corchea, three semicorcheas, a corchea. Often with a
`1,1,1,2` periodicity if you count them.

## The arithmetic, in one paragraph

Take the real numbers. Right hand, f3079–f3094, thirteen notes, gaps of 106.7 ms. One
semicorchea at 178 BPM is 84.27 ms, so each gap is **1.27 columns**. Twelve gaps is 15.2
columns of real time. But a gap can only be a whole number of columns, so twelve gaps must
be written as **nine 1s and three 2s** — nine semicorcheas and three corcheas. There is no
other way to add twelve whole numbers to 15. Nobody chose the corcheas; they are the change
left over.

Where they land is the drift wrapping:

```text
column:      3079 3080 3081 3082 3083 3084 3085 3086 3087 3088 3089 3090 3091 …
played:        ●         ●    ●    ●    ●         ●    ●    ●    ●         ●
gap:              2    1    1    1    2    1    1    1    2    1    1    1
                  ↑                   ↑                   ↑
```

Columns 3080, 3085 and 3090 hold no note at all. The exact position climbs by 1.27 each
time — 3079.00, 3080.29, 3081.52, 3082.81, 3084.11 — and every fourth note the fraction
wraps past the halfway mark and lands two lines further on.

**At the right tempo the whole thing disappears.** At 140 BPM a column is 107.1 ms against a
gap of 106.7: ratio 1.00, twelve 1s, zero debt.

---

## Diagnostic recipe

1. **Open Notes Falling (raw)** and click through the passage. If the rectangles are the same
   length and the gaps are the same, the engine is fine and the problem is downstream. The
   dialog reports `IOI ÷ column` directly — that number *is* the diagnosis.
2. **Check the run report** — `GET /matrix/{uuid}/runs`, surfaced as a banner on that tab.
   A refused run says exactly what tempo it wants.
3. **Read `playedSpan`.** Close to a whole number → the run was evened out and something else
   is wrong. Far from one (0.15+) → it was refused on purpose and the tempo is the story.

Useful one-liner for a whole file — fit a 16th grid across BPM and take the best alignment:

```python
import numpy as np
r = lambda seg, b: abs(np.exp(2j*np.pi*((seg/(60.0/b/4))%1.0)).mean())
best = sorted(((r(onsets, b), b) for b in np.arange(80, 220, 0.05)), reverse=True)[:5]
```

Alignment above ~0.9 is a confident answer; ~0.3 means the region does not have one tempo
(usually because it mixes sixteenths and triplets).

---

## The three causes, and how to tell them apart

### 1. The stated BPM is wrong

Most common. The run report's `suggestedBpm` names the right one. On the reference file the
refusals cluster at **139.4** against a stated 178.

Note `133.5 × 4 = 178 × 3` — a "tempo error" of exactly ¾ or 4⁄3 usually means the passage is
in a triplet feel rather than at a different tempo.

### 2. The piece changes tempo

Fit either side of the suspected boundary. On the reference file, around 218 s: **133.5 BPM
before (alignment 0.94), 127.9 after**. No single number serves both.

Fix is per-region tempo. The clock is built (`matrix/tempo_map.py`) but not wired.

### 3. The passage is a tuplet

Ratios near **1.5 or 1.69 columns** that no tempo resolves. At 140 BPM a sixteenth is 107.2 ms
and an eighth-triplet is 142.9 ms — a passage containing both cannot be printed on a binary
grid **at any tempo**. Frames f3064–f3075 of the reference file are exactly this.

Fix is triplet subdivision in `Granularity`. Not started.

---

## What was measured, for comparison

Reference artifact `a1689618` (Transkun, `Mr Blue Sky — segment 00:05.00–05:10.37`,
305.3695 s, stated 178 BPM, 3624 semicorchea columns).

| Passage | Gap | ÷ column | Verdict |
|---|---|---|---|
| f3067–f3075 | 142.7 ms | 1.69 | refused → 211.0 BPM (a triplet, not a tempo) |
| f3079–f3094 | 106.7 ms | 1.27 | refused → 139.6 BPM, 21 onsets |
| f3120 | 106.7 ms | 1.27 | refused → 140.1 BPM, 13 onsets |
| whole piece | | | `suggestedBpm` 139.4 |

Setting a **140** override over the second half gives twelve uniform semicorcheas for
f3079–f3094. **128 does not** — ratio 0.91, and two attacks collide into one column.

Two outliers in that window (287.3 ms and 215.7 ms, both ≈ double their neighbours) are
notes Transkun dropped — a genuine layer-1 miss, and they fragment the run detection.

---

## What this is *not*

- **Not a sampling problem.** The gaps in that passage vary by ±3 ms across 25 notes.
- **Not cross-hand contamination.** Checked: the whole run is in the right hand, and the
  right hand's own onset columns alternate identically. The per-hand sustain rule already
  works — the left hand's held `Eb2` survives 23 right-hand attacks over the top of it.
- **Not fixable with a finer raw grid.** Moving raw from fusa to semifusa changed the spans
  from `{1:17, 2:7}` to `{1:18, 2:6}`. It is aliasing, not resolution.
