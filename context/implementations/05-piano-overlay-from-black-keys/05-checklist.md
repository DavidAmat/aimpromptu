# 05 — The piano overlay, found from the black keys: checklist

The status lookup for this implementation. The plan is [`05-plan.md`](05-plan.md); the frozen
decisions are the V numbers of
[`../04-synthesia-to-notes/04-decisions.md`](../04-synthesia-to-notes/04-decisions.md), with V-37
and V-38 added by this plan and V-09 superseded.

One phase is one epic. A story is ticked only when every task under it is done.

Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled, `[ ]` not started.

# [x] Phase 1 — Measure the pictures and decide the route
Read the white key borders of three octaves per picture by hand, find the families of black key
placement the 24 pictures use, check that the rectangles fall vertically on the tilted ones, build
both routes in `poc-piano-overlay/`, score them on the same truth, and choose. Nothing ships.

Done. The report is [`05-phase-1-implementation.md`](05-phase-1-implementation.md), the evidence is
[`../../../poc-piano-overlay/RESULTS.md`](../../../poc-piano-overlay/RESULTS.md). The truth is 901
white key borders on all 24 pictures, read by a line tool and checked by eye. The black keys were
found on every picture — 36 of 36 on the 21 full pianos, 23 and 30 on the two shorter ones — with
96.0% seen and the rest placed through the hands. Two families (V-40), the rectangles fall
vertically (V-39), and **route A ships**: 0.031 white key widths off at the mean and none over the
lane margin (V-41).

## [x] Story 1.1 — The truth and the claims
- [x] Task 1.1.1 **The truth**: the white key borders of three octaves on every picture, read by hand off ruled crops, with the borders a hand covers left out and counted. Read on the whole width rather than three octaves: 901 borders, 6 rejected by eye.
- [x] Task 1.1.2 **The families**: the five black key offsets per picture, clustered and named, with the residual of the best fit. Two families, and the black keys alone tell them apart.
- [x] Task 1.1.3 **Do the rectangles fall vertically?**: measured on all 24, not five. They do, within 0.4 degrees on 21 and 1.8 on the rest. V-13 stands.
- [x] Task 1.1.4 **The perspective**: white key width per third, the angle, and the taper, per picture. Up to 7% between thirds on `airplanes`; every keyboard level to under 1 degree.

## [x] Story 1.2 — The two routes
- [x] Task 1.2.1 **The black keys, and the extrapolation**: found, extrapolated, confirmed, the confidence and the pitch class, per picture, with the pictures. Pitch class right on all 24; three seeds of 04 were wrong, not the finder.
- [x] Task 1.2.2 **Route A**: the white keys from the black keys, fitting the family per picture, scored. 0.031 mean, 0.24 worst, 0 over the margin.
- [x] Task 1.2.3 **Route B**: the white keys from the thin dark lines, scored on the same truth. 0.024 at the top edge against A's 0.031; reads 73% of the borders and fills the rest with A's rule.
- [x] Task 1.2.4 **The decision**: route A. Section 6 of the plan updated; V-39, V-40, V-41 written.

# [x] Phase 2 — Per-key borders in both services
The model change with nothing found yet: the saved grids spelt out into borders, both geometry twins
rewritten and held by the fixture, the detector on local widths, and the score board unchanged at
9/0/0 onsets and 6/0/0 sustains.

Done 2026-09-14. The report is [`05-phase-2-implementation.md`](05-phase-2-implementation.md). The
score board reads **9/0/0 and 6/0/0** on the spelt-out grids, the fixture holds a straight and an
angled case and both twins pass it, the check fails on a tenth of a pixel, and the three screens
were driven in a real browser on `derulo`, `shut-up-and-dance` and `airplanes` with no error.

## [x] Story 2.1 — The model and the geometry
- [x] Task 2.1.1 **`Calibration` becomes per-key borders**: the new fields, the gone fields, the black border count refused when the pattern does not allow it; the frontend type mirrors it.
- [x] Task 2.1.2 **The two geometry twins**: borders read from the list, the local width, the rotated top edge, `overlayEdits.ts` gone, the fixture rebuilt with a straight and an angled calibration, the check proven by breaking it.
- [x] Task 2.1.3 **The upgrade of the saved records**: every grid calibration spelt out on load; the two hand-read examples keep their readings.

## [x] Story 2.2 — Everything that reads the overlay
- [x] Task 2.2.1 **The detector on local widths**: the pad, the extent window and the width gate read the local width; the score board still reads 9/0/0 and 6/0/0.
- [x] Task 2.2.2 **The overlay drawn from borders**: each key from its own borders inside the rotated group; the annotation page and the detection view unchanged to the eye.
- [x] Task 2.2.3 **The calibration editor, emptied**: every old button gone, the saved overlay, the upper line, the octave and Save; the page still opens on every example.

# [x] Phase 3 — The finder in the app, and the one rectangle on the screen
The chosen route ported into `video/finder.py`, an endpoint that finds the overlay inside the one
rectangle, all 24 examples found and scored in the app, and step 1 of `/video/examples` rebuilt
around the one rectangle.

Done 2026-09-14. The report is [`05-phase-3-implementation.md`](05-phase-3-implementation.md). All
24 examples have a found overlay with the key count the spike measured, the score board reads
**9/0/0 and 6/0/0** on them, and the screen was driven in a browser: the rectangle moved, the overlay
found again in 567 ms, a border corrected by hand, saved. **Implementation 05 is complete.**

## [x] Story 3.1 — The finder
- [x] Task 3.1.1 **`video/finder.py`**: one function, one picture and one rectangle in, a calibration out; `FinderSettings` with every threshold measured; unit tests on a drawn keyboard, straight, rotated, occluded, and overreaching. Seven tests.
- [x] Task 3.1.2 **`POST /frame-examples/{slug}/find`**: the rectangle in, the found calibration out, with the route, the confidence and the extrapolated and confirmed keys. 422 with the finder's words when there is no keyboard.
- [x] Task 3.1.3 **Every example found**: all 24 found and saved, the same key count as the spike on all 24 and the same borders to 2.5 px at the worst, the seed rewritten, the score board still 9/0/0 and 6/0/0.

## [x] Story 3.2 — The screen
- [x] Task 3.2.1 **The one rectangle**: `PianoRect.tsx` — dragged, resized and rotated on the picture, sized by the live scale.
- [x] Task 3.2.2 **Step 1, rebuilt**: the rectangle, the overlay found when it settles, the upper line, the octave, the confidence, Save; extrapolated and confirmed keys drawn apart.
- [x] Task 3.2.3 **A border dragged by hand**: any white key border taken and dragged along the top edge when the found overlay misses, stored as the user's, drawn apart.
- [x] Task 3.2.4 **Timed**: driven in a browser, not by a person — 567 ms from the rectangle settling to the overlay found; one drag and one dropdown. A stopwatch on a person was not taken, and the report says so.

## [x] Story 3.3 — The plan of 04 brought up to date
- [x] Task 3.3.1 **Write it down**: the 04 plan's Calibration tab, threshold table, "does not handle" list and Task 3.3.2; the 04 checklist's Story 2.1; this folder's README, the implementations table and the index.
