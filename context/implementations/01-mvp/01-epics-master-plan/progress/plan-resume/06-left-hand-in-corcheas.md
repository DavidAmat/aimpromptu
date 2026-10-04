# The left hand is printed in corcheas: four changes, each with its measurement

**Commit `937f480`, 2026-08-12.** Reported 2026-09-13 by Task 14.1.1.3.

## The case

Chopin's Nocturne Op. 9 no. 1 printed a bass note held 397 ms as a **negra** where the score has a
**corchea**.

Diagnosed in `poc-piano-hand-prediction/notes-duration` against the printed score for bars 1–3. This
report is the product half of that work.

Four changes, and each one is here because it was measured on that recording rather than reasoned
about.

## 1. The line between two figures leans towards the commoner one

`matrix/bands.py`, wired into `to_score_payload` behind `weighted_figure_lines=True`.

The line used to sit at the halfway point between two figures. It now leans towards whichever of
them the passage plays more of:

```text
line between A and B  =  A * (B/A) ** ( pileA / (pileA + pileB) )
```

**With even piles the exponent is ½ and this IS the geometric mean, to the decimal**, so a passage
with balanced piles is drawn exactly as before. That equivalence is what makes this a refinement of
D-11 rather than a departure from it, and there is a test pinning it.

Three details that are load-bearing:

- **Piles are counted once, inside the halfway bands.** Recounting inside the new lines ratchets:
  447 ms, then 466, then the clamp.
- **Per passage, both hands pooled.** The lines have to be drawn from the whole passage before any
  note is judged against them.
- **Clamped to 80/20**, so a rare figure keeps a fifth of the room on each side.

## 2. ByteDance's onset threshold: 0.3 → 0.5

`transcription/engine.py`.

The package's post-processor opens a note at **any** onset peak above the threshold, without
checking that the key is already inside a note it just opened. That is where phantom re-onsets come
from.

Swept over the whole recording: **0.5 removes three of the four phantoms and still finds all 38
notes of the printed bars.** 0.6 takes the fourth but starts deleting a real one.

## 3. The leakage filter, corrected in two places

`transcription/leakage.py`.

**The lag test becomes two-sided.** Chopin's phantoms arrive **1–12 ms ahead** of the cluster, not
behind it, and all four walked through a rule fitted to one earlier file where the phantom arrived
+6.7 ms behind. Which side of an attack a secondary detection lands on is a property of the model's
receptive field, not of the playing, so demanding one sign was over-fitting.

**The asymmetry test compares company instead of demanding zero.** Counting alone was not enough,
and **a fixture caught it**: a genuine chord re-strike also gains neighbours. What separates them is
*which* keys those are — the same chord shares its pitches, a phantom's are disjoint.

With change 2 this leaves **0 of 4 phantoms and all 38 notes**. On its own at threshold 0.3 it
deletes a real `Fa4`, **so the two ship together** and must not be separated.

## 4. The chord-grouping window no longer follows `frameMs`

`transcription/events_to_matrix.py`. It is a fixed **40 ms**.

This is the most important of the four, because it was a hole in a promise rather than a tuning
error. Letting the grouping window follow the frame length meant **the column length was changing
the music**: at 10 ms it conjured **22 semifusas that do not exist at 40 ms**.

`frameMs` is supposed to be layout and nothing else. It is again.

The last note of a hand keeps the halfway rule for the same reason — it has no gap, its length runs
to where the sheet ends, and that is a whole number of columns.

## Tests

11 new: the geometric-mean equivalence, the clamp, no iteration, the two-sided lag, the chord
re-strike refusal, and the grouping window.

Full suite green. `test_api_smoke`'s 404 was already failing before these changes.

## For the next worker

- **Changes 2 and 3 are one change.** Reverting the threshold without reverting the leakage rule
  deletes a real note.
- **The fixed 40 ms grouping window is a promise, not a default.** If it ever has to follow
  `frameMs` again, that is a change to what `frameMs` means.
