# Phase 1 — Measure the pictures and decide the route: implementation report

Technical, for the agent that takes Phase 2. The plan is [`05-plan.md`](05-plan.md), the status is
[`05-checklist.md`](05-checklist.md), the decisions are the V numbers of
[`../04-synthesia-to-notes/04-decisions.md`](../04-synthesia-to-notes/04-decisions.md) — this phase
added V-39, V-40 and V-41 — and the evidence is
[`../../../poc-piano-overlay/RESULTS.md`](../../../poc-piano-overlay/RESULTS.md). Nothing in this
phase touched application code.

## 0. What this phase produced, in one table

| | Where | What it is |
|---|---|---|
| the black key finder | `poc-piano-overlay/scripts/blackkeys.py` | the band, the candidates, the alignment, the extrapolation, the check. **This is what Phase 3 ports.** |
| route A | `poc-piano-overlay/scripts/routes.py` `route_a()` | the white key borders from the black keys. **Ships.** |
| route B | `poc-piano-overlay/scripts/routes.py` `route_b()`, `lines.py` | the borders from the thin dark lines. Measured, does not ship, stays as the truth's tool |
| the truth | `poc-piano-overlay/data/truth.json` | 901 white key borders on all 24 pictures, read by the line tool on two rows and checked by eye |
| the rectifier | `poc-piano-overlay/scripts/common.py` `rectify()` | the strip inside the one rectangle, rotated straight |
| the tables | `poc-piano-overlay/RESULTS.md` | black keys, truth, families, perspective, fall, routes — one row per picture |

## 1. The decision, and the numbers behind it

**Route A ships (V-41).** Over 901 truth borders it is 0.031 local white key widths off at the mean
— 0.8 px on a 25 px key — 0.24 at the worst, and no border is over the lane margin of 0.25. On the
265 top edge borders, the only place both routes can be measured on the same footing, route A is
0.031 and route B 0.024: a fifth of a pixel apart. What decides it is what each route rests on: the
black keys were seen on 811 of 845 (96.0%), the front lines were readable on 901 of about 1220
(74%), and every border route B has to fill, it fills with route A's rule.

**Two families, not three (V-40).** 23 of 24 pictures place their black keys the way a real piano
does — C# −0.095, D# +0.100, F# −0.131, G# +0.009, A# +0.137 white key widths from the border each
stands on, no picture more than 0.05 off on any key — and `derulo` puts them on the boundaries. The
twelve equal slots family is used by nobody. The gap ratio between and inside the groups tells the two
apart from the black keys alone: 1.98 against 1.49 to 1.56.

**The rectangles fall vertically (V-39).** Within 0.4 degrees on 21 pictures, 1.8 on the three whose
strong edges are scrollwork. The keyboards are level to under a degree, all 24, so the one
rectangle's angle was zero everywhere and the lanes stay vertical strips: V-13 stands.

**The black keys are found on every picture.** 36 of 36 on the 22 whole pianos, 23 on
`shut-up-and-dance`, 30 on `superestrella`; 34 keys placed through a hand or a pressed key, 26 of
them confirmed dark by the pixels; the pattern right on all 24, which corrected three seeds of 04.

## 2. How the finder works, for the port

`find_black_keys(strip)` takes the rectified grey strip and answers a `BlackKeyResult`. In order:

1. **`otsu()` over rows 3 to 40** gives the threshold: black keys and the tops of white keys make
   two clear modes there. Do not take the light level from the whole strip — the glow at the top
   edge is 255 on the photos and it made the grey front of a white key count as dark.
2. **`black_band()`** reads the depth down the black key columns themselves: the columns that are
   dark in rows 3 to 20 are averaged into one vertical profile, and the depth is the first row where
   it has risen halfway from its dark level to its level below the keys. A row share failed on 15 of
   24 for the reason above.
3. **`candidates()`**: runs of columns whose share of dark rows in the band is at least 0.6, kept
   when their width is 0.5 to 1.6 of the median width of the runs at least 4 px wide. A thin line is
   1 to 3 px, a hand is wider than 1.6 keys.
4. **`align()`** is a dynamic programme over the candidates in order. State: the last kept
   candidate and its position in the pattern (C#, D#, F#, G#, A#). A transition throws out the
   candidates between (1.5 each), walks the pattern over `m` keys (0.6 per hidden key) and pays 12
   times the relative error between the measured gap and the expected one. The expected gap is built
   from the two gaps the picture shows — the 30th percentile of the gaps is the gap inside a group,
   the median of the gaps 1.3 to 2.6 times that is the gap between groups — **never from a family**.
   Only the last 8 candidates are considered as the predecessor. The chain carries, on each kept
   candidate, the number of keys walked into it from the one before; an off-by-one there shifted
   every index and invented a key, which is worth a test.
5. **The runner up** is the best alignment with the first kept candidate pinned to each other
   position, and the confidence is the cost margin over the winner as a share of the winner's cost.
   Pinning is what makes it a different keyboard and not the same one relabelled (Phase 1 of 04 fell
   into that trap with its grid finder).
6. **The position function** is a quadratic in the pattern's own coordinate — the gaps of step 4
   walked from the first seen key — fitted over the seen keys. Fitting on a per-octave semitone
   coordinate against a relative index was the source of a stray key at index 0; the walked
   coordinate has no octave arithmetic in it.
7. **Inside the seen span** every key the pattern needs is placed from the function and flagged
   extrapolated; **past the ends** the walk goes on only while `dark_at()` confirms a key (share of
   dark pixels at least 0.6 in the middle 60% of the key's width). Confirmation is checked on the
   inner keys too and reported, never used to delete: a pressed black key is lit.

The whole thing is 0.07 to 0.10 s per picture in numpy with a Python loop for the alignment; the
alignment is about 40 candidates × 8 × 5 × 13 steps.

`route_a(keys, width)`:

1. `family_of()`: the gap ratio; `boundary` above 1.75, else `real`.
2. The local white key width at each black key is the mean distance to its same-name neighbours an
   octave away, over 7; a key with none takes its nearest neighbour's.
3. Each black key gives the border it stands on: its centre minus the family's offset times the local
   width. Borders are kept by slot — C|D = 0, D|E = 1, E|F = 2, F|G = 3, G|A = 4, A|B = 5, B|C = 6,
   plus 7 per octave — anchored on the first C# in the strip.
4. E|F and B|C are the midpoints of the borders on each side. Any slot still empty between the ends
   is interpolated.
5. Past the outermost black keys the borders continue at the local width while the key's midpoint
   is inside the rectangle — at least half of it shows.

## 3. What changed against the plan, and why

- **The truth was read on the whole width, not on three octaves per picture**, and by a tool checked
  by eye rather than by eye alone. The tool reads two rows in the front of the keys; a line is truth
  when it was found on both rows, its lean agrees with its neighbours', and it is not a duplicate.
  Every picture was then looked at on a 2.5x ruled crop, and six lines that passed the three checks
  but sat on a hand's edge or the scrollwork were taken out by eye (`data/eye-rejections.json`). The
  first version of the pairing marked a perfectly vertical line as found on one row only, because it
  compared the two rows' positions for inequality; that threw out half of `derulo` and all of
  `shut-up-and-dance`, and the fix is a `paired` flag set by the pairing itself.
- **Route B cannot be scored on the front truth**, because it is the front truth's own reading
  without the eye. That was known when the truth was designed and it is why the top edge borders —
  E|F and B|C, visible between two white keys with no black key over them — were read as a second,
  independent truth. Both routes are compared there, and what decides between them is coverage
  rather than a fifth of a pixel.
- **The rectangles fall vertically on all 24**, not only on the five tilted ones, because the
  measurement costs nothing per picture.
- **No family had to be fitted per picture.** The plan asked for the family that fits the black keys
  best on each picture; two families and a gap ratio with 0.2 of room on both sides made that a
  threshold, not a fit.
- **The one rectangle's angle was zero on every picture**: the keyboards are level to under a degree.
  The rectifier exists and Phase 3 tests it on a drawn keyboard at an angle; the set does not.

## 4. What Phase 2 and Phase 3 should know

1. **The `Calibration` model of section 5 of the plan stands as written.** `whiteBorders` are the
   route A borders in u along the top edge; `blackBorders` are each key's `centre ± width / 2`;
   `blackDepth` is the band depth; `whiteWidth` is the median of the diffs of `whiteBorders`.
   `found.route` is `"A"`, `found.confidence` is the alignment margin, `found.extrapolated` and
   `found.confirmed` are the keys with `seen == False`.
2. **Pitch class:** the first white key of the rectangle is the white key below the first border,
   and its pitch class follows from the first black key's name and how many borders precede it.
   `superestrella` starts on C; everything else on A. This is the octave dropdown's default.
3. **The seeds of 04 disagree with the finder on three pictures and the finder is right** —
   `airplanes`, `more-examples-4`, `more-examples-11` all show A#0 at the left edge. The upgrade of
   Task 2.1.3 spells the seeds out as they are; Phase 3's Task 3.1.3 replaces them with the found
   overlays, and the two examples with hand readings (`derulo`, `shut-up-and-dance`) have the same
   pitch class either way, so the score board's 9/0/0 and 6/0/0 is not at risk from this.
4. **The lane margin is safe.** The worst border error is 0.24 white key widths on `feather` and the
   next is 0.185; the margin is 0.25 and attribution has 0.33. Nothing needs re-measuring in the
   detector.
5. **The end rule** keeps a key whose midpoint is inside the rectangle. On eleven pictures that is one
   white key fewer than the seed counted; the difference is the key the picture's edge cuts in two.
6. **`rects.json` is the placement a user would make**: the full width, the top edge on the upper
   line, the bottom at the bottom of the picture. Nothing in the finder needs the rectangle to end
   at the front edge of the keyboard; `keyboard_bottom()` finds that itself and it is only used by the
   line reader.

## 5. The checks

No application code changed, so the baseline of Phase 2 of 04 stands unchanged: `make test` 1 failed
and 812 passed, flake8 4 pre-existing, mypy 30 pre-existing, `npm run lint` clean, the two geometry
checks passing. The spike's own scripts run end to end in about 40 s for all 24 pictures.
