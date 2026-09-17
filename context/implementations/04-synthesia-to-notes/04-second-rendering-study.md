# The second rendering: a roll over a photograph — study report

Technical, for the agent that rebuilds the detector after the decisions below are taken. The plan
is [`04-plan.md`](04-plan.md), the frozen decisions are [`04-decisions.md`](04-decisions.md), and the
report before this one is [`04-phase-4-implementation.md`](04-phase-4-implementation.md). The
scripts behind every number are in
[`../../../poc-synthesia-frames/scripts/photo/`](../../../poc-synthesia-frames/scripts/photo/).

Every rule below was first measured by patching the shipping modules from outside, on the two videos
on this machine, and raised for a decision. **The recommended rules were then built on 2026-09-16**:
V-44 to V-46 in [`04-decisions.md`](04-decisions.md), section 7 says where.

---

## 0. The two videos, and what the study found in one table

| | AITANA — SUPERESTRELLA (the photograph) | Elektronomia — The Other Side (Phase 3 and 4's video) |
|---|---|---|
| uuid | `b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7` | `ddd8bce8-3e3f-4262-9595-46aaf66de54b` |
| frames | 1892 at 100 ms, 72 keys C2 to B7, white key 30.7 px | 2728 at 100 ms, 88 keys, white key 24.6 px |
| the roll | drawn over a photograph and a fixed title; rectangles are rounded, rimmed, semi-transparent, blue and magenta | a flat dark roll; opaque rectangles |
| strikes the keyboard shows | 1356 (7.2 a second) | 3299 with this study's tool |
| **shipped reading** | 4967 notes, 91% of strikes found, **68% of notes not shown** | 4295 notes, 91% found, 28% not shown |
| **proposed reading** | **1492 notes, 98.7% found, 6.5% not shown** | 4398 notes, 90.8% found, 28.4% not shown |

The 68% was five lanes. 3174 of the 3395 invented notes sit on three keys — F#4, C#5 and A#4 — the
keys this piece plays most, lit in 35%, 26% and 21% of the frames. Every other key was read almost
right from the start. Section 2 says why those five lanes broke, and it is the plate.

## 1. The score: the rendering's own keyboard, as Phase 4 did

There is no hand reading of a whole video. But this rendering, like Synthesia, lights the key on its
keyboard while a note sounds, below the upper line where the detector never looks. A key going from
unlit to lit is a strike, and it is evidence no rule can have been fitted to.

`lit_keys2.py` reads it. A lit key here is **coloured** — magenta or blue on a grey, white or black
key — so the tool is the saturation of a patch of the key: the median over the patch of
`max(r,g,b) - min(r,g,b)`. Unlit keys read 3 to 5; lit ones 105 to 156; the threshold is 60 and nothing
sits near it. Two things about where the patch is, both learnt the hard way:

- **The white key patch is at the top of the key, just under the black keys.** This rendering lights
  a white key from the top down over two or three frames. A patch at the front of the key read every
  strike up to 200 ms late, and the first version of this report blamed the reading for it.
- **The black key patch stays away from the top of the keyboard.** The strike glow at the upper line
  pulses in magenta over the middle black keys; a patch in it invented a strike on every beat.

**The tool cannot see a legato repeat.** A key struck again while it is still lit stays lit, and at
10 frames a second a gap under 100 ms is never sampled. So "not shown" is a ceiling on invented notes,
not a count of them, and the report splits it into *within 250 ms of another note on the same key*
and *isolated*. Both traces in section 6 that were followed frame by frame turned out to be legato
repeats the keyboard cannot show.

The timing: the onsets of the proposed reading sit **69 ms before** the strike at the median (p10
−109, p90 −21). The strike is the first sampled frame in which the key is lit, so it is 0 to 100 ms
late by construction and −50 ms of that is the tool's own; the rest is the soft glow under every
rectangle tip in this rendering, about 4 px.

On the first video the same tool, with the plate difference instead of saturation (its keys light in
a colour close to the roll), reads 3299 strikes and finds 91% of them whole-piece with the shipped
reading; Phase 4's tool read 97% on frames 400 to 1000. The two tools read different patches; every
comparison below is against the same tool, so the *changes* are what count there.

## 2. Why the plate broke: V-29's assumption, not the photograph

The plate is the per-pixel 20th percentile of 100 frames, **per channel**, and V-29 says plainly what
that assumes: *the rectangles are lighter than the roll behind them*. On a dark roll every colour is
lighter in every channel. On a mid-grey photograph a blue rectangle is not:

```text
blue rectangle   (27, 50, 160)      grey photo behind it   (99, 94, 101)
```

Red and green *drop* under the rectangle. Once a lane holds a rectangle in more than 20% of the
frames, the 20th percentile of R and G is the rectangle's, B stays the photo's, and the plate holds a
colour that is neither: a dark-blue band down the whole lane. The difference against it is then large
in the *empty* lane and small under a real rectangle — the lane inverts, and the whole column becomes
one tall foreground shape that the split rule chops every 94 ms. That is the thin box spanning the
whole roll in the screenshot, and the 4967 notes.

Measured (`eval_plates.py`): the occupancy of the F#4 lane — the share of lane pixels that read as
foreground, over 40 spread frames — is **0.92 under the shipped plate** and 0.39 under any plate that
does not assume a colour, while the keyboard says the key is lit in 0.35 of frames. Going lower makes
it worse: the 5th percentile puts the worst lane at 0.95, because a lower percentile takes the
rectangle in a dropped channel sooner.

The photograph itself is not the problem. The title is static, it is in every plate, and its residual
against the plate is 4 levels at the median; the box drawn over "SUPERESTRELLA" in the screenshot is on
a real blue note. The lane coverage and the width gate did not fail either — they did what they were
told on an inverted foreground.

### 2.1 What was tried, and what it cost

Four plates, all scored against the keyboard with the rest of the pipeline unchanged unless stated.

| plate | photograph: notes · found · not shown | first video: notes · found | verdict |
|---|---|---|---|
| p20, shipped | 4967 · 91% · 68% | 4295 · 91% | assumes lighter notes (V-29) |
| p05 | worst lane occupancy 0.95 | — | worse, same reason |
| plain median of 100 frames | occupancy right (0.42 worst) | — | fails a lane occupied over half the time (V-29's own finding) |
| long-still mean, L = roll height ÷ travel | 1559 · 98% · 14% | **5711 · 55%** | see below |
| long-still, still-roll frames left out by the speed series | 1559 · 98% · 14% | 4293 · 91% | luck, see below |
| long-still, still-roll frames left out by raw change < 0.2% | 1491 · 98.7% · 6.4% ¹ | **3821 · 87%** | fails a held chord |
| **still-median** (section 2.2) | **1492 · 98.7% · 6.5%** ¹ | **4295 · 90.8%** | equals the shipped plate where it was right |

¹ with the other rules of section 4 in place.

The long-still plate — "the background is what stays still longer than a rectangle can, and nothing
can fall for longer than the roll is tall" — was the first principled idea and it looked right on the
photograph. It fails on the first video twice, and both failures are one lesson: **in a busy lane the
background is never still for that long, so whatever else stays still wins.** First the YouTube end
screen, a second static picture that holds the last 20 s: with it in, the G2, C3 and G3 lanes read the
end screen. With the still-roll frames taken out, the same lanes read the **held chord at 248 s**,
which is longer than the roll is tall and is the only long stillness those lanes ever have: the plate
there is `(123, 153, 180)`, the chord's light blue, on 96% of the lane. The run that "passed" with the
speed series' near-zero pairs left out passed because those pairs happened to cover the chord.

### 2.2 The plate proposed: the median of what stands still

`still_median.py`. About 150 frames spread over the video, and for each of them the two frames either
side. A pixel of a frame counts only when it **did not change** — by fewer than 12 levels in any
channel — across those neighbouring frames, so no moving edge is on it; and a frame whose roll changed
on **fewer than 0.2% of its pixels** is a rest or a card, not a picture of the roll's background, and
is left out whole. The plate is the per-pixel median of what counts, and the plain median fills a
pixel that never stood still (none on either video).

Why each part is there:

- **The median, not a percentile**: no assumption about which way a rectangle differs from the roll.
  This is what fixes the photograph.
- **Only still pixels**: the moving edges of rectangles — which are what the sampling sees most of on
  a short note — never enter the vote. It is V-33's fact, *a rectangle falls*, used on the plate.
- **Short stillness, two frames each side**: long enough to drop an edge, short enough that a busy
  lane still has hundreds of background votes. Measured: the roll pixels have 74 still frames at the
  10th percentile and 130 at the median on the photograph, 97 and 133 on the first video.
- **Still-roll frames out**: an end screen, a title card, a paused roll. The raw change tells them:
  on the first video 170 pairs change on under 0.2% of the roll and the moving pairs' 1st percentile
  is 0.34%; on the photograph 27 intro pairs against 4.6%. It needs no plate and no speed, so the
  plate can be built first, as it is today.

What it still cannot do, said plainly: **a pixel covered by still rectangle interiors more than half
the time** — a drone held for most of a piece on one key — would put that drone in the plate. Neither
video has one. The rebuild should report the lane occupancy per key (already computed for this study)
so a lane over about 0.6 is named in the report rather than trusted.

Cost: 750 JPEG reads — 150 picks × 5 frames — 23 s on eight workers for the photograph and 19 s for
the first video. The shipped plate reads 100 frames on one process in about 4 s.

## 3. The measurements that failed on a photograph

### 3.1 The roll bounds (V-28) were computed on raw grey

`motion.roll_bounds` scores every row by *did the next frame look like this row moved down by one
travel, or like it did not move* — a difference of two correlations — **on the raw grey rows**. On a
flat roll a row's content is its rectangles, so the moved correlation wins. On a photograph the row's
content is the photograph, which does not move, so "did not move" wins on every row: the score is
negative in every 50-row band (−0.01 to −0.20), the longest moved stretch is empty, and the answer was
**roll top 0, guard band 515 rows** — the whole roll untrusted. Two consequences downstream: the head
of the stitched roll had zero rows, and `tip_trusted` was false on every run.

On the plate difference (`study_bounds.py`, 60 pairs, every row scored — the shipped loop stops
`travel + 1` rows short of the line, which left the rows that matter unscored), the score by 10-row
band from row 400 reads `0.06, 0.02, 0.02, 0.01, 0.01, 0.01, −0.02, −0.04, −0.14, −0.48, −0.60, −0.49`.
Two readings of it:

- the band where "did not move" wins (score < −0.05): rows 478 to the line, **37 rows = 1.21 white
  keys**;
- the band where the score is not positive: rows 459 to the line, **56 rows = 1.82 white keys**.

The rectangles' own strength says the glow starts about row 440 to 460: their mean strength falls
from 71 at row 440 to 30 at the line while the foreground share doubles. The second reading is the
one to build — *the guard band is the rows above the line, scanning upward, until the roll is seen to
move* — and it lands on V-24's 1.75 by a different route. The roll top by the same rule from the top
is 0 on this video, which is right: the rectangles enter at the picture's edge.

The "longest moved stretch" the shipped code takes is fragile on a sparse piece even with the right
picture: 0 to 159 with 15 pairs and 0 to 407 with 60, because most rows have nothing falling in most
pairs. The upward scan from the line does not have that problem.

### 3.2 The scroll speed (V-06) is biased by whatever does not fall with the roll

The correlation of row profiles answered **6 usable pairs of 1891** with the shipped plate — the
measurement that gave 20.16 px per frame — and 15 with a right plate. On a photograph the profile is
shared with things that move at other speeds: the light swirls the rendering animates across the roll
and the glow band at the bottom. Four profiles were tried (`study_profiles.py`, `study_blocks.py`) and
they disagree by 4%:

```text
profile                              usable pairs   median px/frame
plain mean (shipped)                        15          19.95
binary (share > tau)                         8          20.36
edge (vertical gradient)                     0            —
strong (mean of max(0, d − tau))            86          20.10
sum of 16 column-block correlations          1          19.38     (1650 of 1891 pairs land in 18..22)
```

V-33 already says why: *the travel is voted for by the runs, never taken from a correlation of the
pictures*. Applied to the speed (`study_vote.py`): the runs of every frame linked one to one to the
next frame with `momentum.link`, and the fall of every free edge collected:

```text
48 396 linked edges over 1815 pairs
mean fall 20.22 px/frame     thirds of the piece: 20.21 · 20.22 · 20.18
per-pair means: quartiles 20.03 to 20.40
```

That is the speed the study uses: **202.2 px/s**. The shipped 20.16 from six pairs was within 0.3% of
it by luck; 19.95 is 1.3% off, and 1% of speed is 2 s of drift over this piece in the boxes drawn back
on the frame — which is the *boxes not fitting* in the screenshot, together with the plate. The times
of the stitched roll do not drift with the speed at all: the strips are placed with the same number
that turns rows into seconds, so an error cancels; it shows only in how the notes are drawn back.

The runs' vote costs one detection per frame, which the reading already pays. It also answers, per
pair, how many rectangles agreed, which is a sharper "usable" than a correlation peak ratio.

### 3.3 Two defects the study met on the way

**The extent measures the rim, not the rectangle.** `_full_extent` takes the brightest column in a
window as the reference and keeps columns above half of it. This rendering draws a light rim around a
darker fill: on frame 0 the F#3 rectangle's rim reads 170 and its fill 90, so at half the peak only the
rim passes, the run is 0.29 keys wide and the width gate refuses it — the piece's second note, at
0.78 s, lost. Against the **median of the columns within a quarter key of the key's centre** instead
(`extent_core.py`) the rim no longer sets the bar: found 1327 → 1337 on the photograph, and 4292 for
4295 notes on the first video with the same score.

**The split rule does not measure what V-26 says.** `valleys()` takes the prominence of a dip against
the *maximum of the whole run* on each side, not against the plateau beside it. Section 4 is about that.

## 4. The split rule cuts at the seams of the strips

With the plate right, 190 of 1591 notes were still not shown, and the *isolated* ones were few; the
rest were "within 250 ms of another note on the same key". Counting consecutive same-key notes by the
rows between them settles what they are: a real border between two touching rectangles leaves 3 to 8
rows; a cut by `split_run` leaves **exactly 0**, because the cut row is kept in the first piece.

```text
photograph, shipped split:   270 pairs at 0 rows      53 at 3 to 8 rows
```

Mapping every cut back to the frame row its stitched row came from (`seams.py`):

```text
frame row   15  16  17  18  19  20  21  22  23  24  25  26  27  28  29  30  31  32  33  34  35
cuts        53  11   6   5   6   9  10  12  16   9   5   8  11  12  13  10  12  12  19  20  11
```

The strip is frame rows 15 to 35. **92 of the 270 cuts are on its first or last two rows**, against
39 if they were spread evenly. The strength profile across a seam shows why: the same content reads
4 to 9 levels different in the frame after — `117, 117 | 111, 112` and `96 | 87` are typical — so the
stitched roll carries a saw-tooth with the strip's period. Where it comes from: not the photograph
(the per-row gain of foreground across the strip rows is flat to 0.7% on both videos), but the
rectangle's own brightness changing between one sampled frame and the next, which this rendering does
as a note approaches the keyboard. A step of 8% is nowhere near the 0.40 prominence — **against the
plateau beside it**. Against the brightest row of a run that brightens by 25% over three strips, it is.

`local_valleys.py` measures the plateau within **14 rows** (0.46 white keys) either side of the dip,
which is what the rule was written to do: a real border is 3 to 7 rows and its plateaus are right
there; a seam step is 8%. Swept against both keyboards (`sweep_prominence.py`):

```text
split_prominence      photograph: notes · found · not shown       first video: notes · found
   0.15               1583 · 99.1% · 9.0%                          4638 · 91.1%
   0.20               1526 · 98.9% · 7.3%                          4470 · 91.0%
   0.25               1506 · 98.8% · 6.8%                          4411 · 91.0%
   0.30  ←            1491 · 98.7% · 6.4%                          4401 · 91.0%
   0.40               1482 · 98.3% · 6.3%                          4292 · 90.9%
   whole-run, 0.40 (shipped)   1591 · 98.6% · 11.9%                4295 · 90.9%
```

0.30 sits on the plateau of both. At 0.40 under the local measure four real strikes go: a run of five
short repeats on A#5 becomes one 2.44 s note, because its borders are shallow and were only ever cut
against the run's brightest row. Phase 4's 0.40 was measured under the inflated rule and is not
comparable.

**Phase 4's count on the first video stands.** Its cuts cluster too — at rows 75, 78, 79, 82, 86 and
90 of a strip 74 to 90 — but that is a comb at the beat: the repeated eighth notes of that piece are
37 px apart and 37 mod 16.89 is 3.2 rows, so real borders land every three or four rows of strip
phase. The local rule leaves them: 4292 for 4295 notes at 0.40. Only the seam cuts of the photograph
were false.

A per-pixel gain that flattens the strength across the strip (`flatfield.py`) was measured and is
rejected: it took the strikes found from 98.6% to 82.2%, because a gain from the 90th percentile of
foreground is set by rims and glow and starves the fill.

Moving the strip lower does not help either: at row 60 the reading has 1604 notes and 13% not shown,
at row 120 1674 and 15%, because lower in the roll the strip crosses the light swirls. Row 15 stays.

## 5. What is left, named honestly

The proposed reading: **1492 notes, 1339 of 1356 strikes found (98.7%), 96 notes not shown (6.5%)**,
of which 63 are within 250 ms of another note on their key and 33 are isolated. Of the 17 strikes not
found and the 33 isolated notes, the ones traced frame by frame through the per-frame runs
(`runs_static.json`, section 6) are:

- **legato repeats** the keyboard cannot show — C#4 at 16.37 s and F#3 at 40.06 s are second notes of
  a key that stays lit through touching rectangles;
- **wide white-key rectangles spilling into a black key's lane**: the B2 and B3 rectangles here are
  1.19 to 1.28 white keys wide, and their rims read as short notes on A#2 and A#3 at 64.14 s. V-27
  drops a run centred nearer another key, but the extent measured from the black key's lane is the rim
  only, so its midpoint lands on the black key. A cross-lane rule — two runs on adjacent keys that
  overlap in rows and in x are one rectangle — would take these; it was not built or measured;
- **light swirls**: the rendering animates curved light streaks across the roll; a few pass the width
  gate in the strip. The stitched roll has no momentum rule (V-33), which is the plan's own open item.

The per-frame reading, which is what the Detection tab shows, is worse on this rendering than the
piece is: **frame to frame agreement (V-31) 0.72** with every fix, against 0.97 on the first video,
and the momentum rule refuses 3710 of 49 394 runs — the swirls, mostly. The tips of the wide white-key
rectangles read erratically in the lower roll (a trace on B2 has the tip at 306, 367, 388 in three
consecutive frames while the top moves 20, 20, 21) because their lower part is darker and the glow
band eats it. None of this reaches the stitched roll, which reads the strip at rows 15 to 35. It is
written down so nobody reads 0.72 as a defect of the piece.

Two things this rendering does that the plan's vocabulary has no word for:

- **semi-transparent rectangles**: the same magenta reads `(155, 68, 175)` over white and
  `(102, 17, 116)` over dark hair, so the plate difference inside one rectangle runs from 95 to 145
  with the photograph behind it. Nothing built here depends on the fill being one value, but the
  colour check of V-36 would, if it were ever turned on;
- **a brightness that changes with time**: the saw-tooth of section 4.

## 6. Where the evidence is

`poc-synthesia-frames/scripts/photo/`, one script per measurement, run as its README says. The
intermediate files — the plates, the strike lists, the per-frame runs, every reading as JSON — were in
the session's scratch folder and are not kept; every one is rebuilt by its script in under a minute.

The readings that matter were drawn back on frame 65 the way the Notes tab draws them: with the
shipped reading, 70 boxes, the five inverted lanes stacked with boxes and every true rectangle boxed
right; with the proposed reading, 24 boxes and every one on a rectangle.

## 7. What the rebuild changed

| where | what | decision it touches |
|---|---|---|
| `video/plate.py` | `build_plate` becomes the still-median of section 2.2; `reading.build_plate` reads 150 picks and their neighbours over workers | replaces V-29 |
| `video/motion.py` | `roll_bounds` scores the plate difference, every row, and reads the guard band upward from the line; `scroll_speed` takes the runs' vote, with the per-pair agreement as "usable" | V-28 stands; V-06's method changes |
| `video/detector.py` | `valleys` measures the plateau within 0.5 white keys; `split_prominence` 0.30; `_full_extent` against the core median | V-26 as written; the threshold table |
| `video/reading.py`, `notes.py` | the lane occupancy per key in the report, and a named warning over 0.6 | V-20 |
| `04-plan.md` section 8 and the threshold table, `04-decisions.md` | V-29 replaced, V-06 amended, two new V numbers, and the numbers of this report | — |

Nothing on the frontend changes. The Notes tab draws the boxes from `scrollSpeed` and they fit once
the speed is the rectangles' own.
