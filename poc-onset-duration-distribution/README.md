# PoC — onset-interval distributions as a way to find the grid

**Status:** research spike. Nothing here is wired into the app, imports the app, or
writes anywhere the app reads. It consumes stored artifacts and produces pictures.

---

## The problem this is circling

AImpromptu currently turns a transcription into a score like this:

1. the engine produces note events with real timestamps (`events.json`);
2. those events are snapped onto a **raw grid** — semifusa columns, sized by a
   **tempo the user typed in**;
3. the raw grid is collapsed to a display granularity (semicorchea) and the
   columns are read back out as figures — negra, corchea, semicorchea…

Step 2 is where the whole thing is decided, and the tempo it depends on is a
number a human guessed. Get it wrong by a few percent and the errors are not
uniform: a run of even notes beats against the grid, each note rounds to a
slightly different column, and what was eight identical semicorcheas prints as a
ragged mix of corcheas and semicorcheas. `matrix/isochrony.py` already exists to
patch that up after the fact — it detects runs that *should* be even and
re-spaces them, and refuses the ones it cannot fix without stealing duration
from the passage.

That is a repair. This PoC asks whether the tempo can be **measured** instead.

## The idea

Take one hand. Ignore which notes were played. Look only at the **gaps between
consecutive attacks** — the inter-onset intervals (IOI).

If a passage is all negras and a negra is 1000 ms, every gap is ≈1000 ms. If it
alternates negra / corchea / corchea / negra, the gaps are 1000, 500, 500. So a
histogram of the gaps should show **peaks at the figure durations**, with heights
proportional to how often each figure occurs. Humans are not metronomes, so each
peak is a small hill rather than a spike — hence buckets, not exact counts.

Two things follow, and they are the point of the whole exercise:

- **The peaks are the tempo.** Nothing else in the pipeline needs to be known to
  find them: not the BPM, not the key, not the note names, not the meter.
- **The shape is tempo-invariant.** A peak set of 1000 / 500 / 250 and a peak set
  of 1200 / 600 / 300 are the *same music* played at different speeds. Which peak
  gets called "negra" is a naming choice a human makes once; the machine only has
  to find the ladder and notice when it moves.

That second property is the prize. If a piece changes tempo halfway through, the
peaks all slide by the same factor while their *ratios* stay put. So a tempo
change is detectable as a shift of the whole comb — and once detected, the right
response is not to re-quantise the notes into different figures, it is to
**write a new BPM into the tempo map and keep the figures identical**. Same
notation, different clock. That is what `tempo-map.md` describes and what this
measurement would drive.

## Mr Blue Sky, and why this piece

David hears the rhythm change at **3:37**. The transcription for
`Mr Blue Sky — segment 00:05.00–05:10.37` is stored, the tempo entered for it was
178 BPM, and the isochrony work already flagged that some of its runs only come
out even at ~139 BPM. So it is a piece where the current pipeline is known to be
struggling and there is a specific, audible event to test against.

The two segments analysed are **0:00–3:37** and **3:37–end**, on the *segment*
clock (the stored audio starts 5 s into the original video).

## Method

| step | choice | why |
|---|---|---|
| hand split | join `events.json` against the stored `two-hands_semicorchea_{left,right}.npz` | the two matrices partition the transcription exactly (1432 R + 966 L = 2398 events, a verified bijection with zero unmatched), so this reproduces the app's own answer without re-running the beam-DP splitter. Note it inherits that answer: it checks the encoding round-trips, **not** that the split is musically correct |
| timing source | the **float seconds in `events.json`**, never the matrices | the matrices are consulted for identity only; using their columns would bake the very grid this PoC is trying to question |
| chords | onsets within **20 ms** of the group's first onset count as one attack | a three-note chord struck 8 ms apart is one rhythmic event; without this, 695 near-zero gaps swamp the low end |
| chord grouping rule | non-chaining — the window is measured from the group's **first** onset, not the previous one | single linkage would let a dense run swallow itself one 19 ms hop at a time |
| boundary | intervals are computed *within* each segment | the one gap that straddles 3:37 belongs to neither tempo |
| peaks | Gaussian KDE (12 ms bandwidth) → local maxima → basin between neighbouring minima | fixed bandwidth in **ms** because human jitter is roughly constant in absolute terms; the basin makes peak masses a real partition, so shares are comparable across segments |
| beat | search 250–1200 ms for the beat that puts the most **peak mass** on printable figure ratios | scores peaks, not raw intervals, so a peak carrying 44 % of the data counts 44 % |

The 250–1200 ms bound (50–240 BPM) is the only prior in the whole PoC, and it is
the honest place for one: from intervals alone, a beat and half that beat are
indistinguishable. See `RESULTS.md` — segment B lands in exactly that trap.

## Layout

```
data/     stored artifacts, copied verbatim (events.json, the three .npz grids)
scripts/  common.py   loading, hand labelling, chord collapse
          analysis.py KDE + peak finding, tatum fit, beat fit, swing, sliding scan
          run_poc.py  the whole run; writes everything in out/
out/      figures (png), tables (csv), results.json, run_log.txt
RESULTS.md  the findings and what they mean
```

Run it with `python3 scripts/run_poc.py` from the PoC root. Needs numpy, pandas,
matplotlib, seaborn — nothing from `aitu_backend`.

## What would come next if this holds up

1. Estimate the grid unit per window instead of asking the user for one BPM.
2. Segment the piece where the estimate steps, and emit a **tempo map** rather
   than re-quantising — figures stay, the clock changes.
3. Detect the *subdivision scheme* (binary vs. triplet vs. swung) per segment,
   because the raw grid is currently always a power of two and a swung beat has
   no representation on it at any resolution.
