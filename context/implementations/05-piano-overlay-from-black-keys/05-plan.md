# 05 — The piano overlay, found from the black keys: implementation plan

Read the prompt this plan answers first: [`05-prompt.md`](05-prompt.md). The status lookup is
[`05-checklist.md`](05-checklist.md). The frozen decisions are the V numbers of implementation 04,
[`../04-synthesia-to-notes/04-decisions.md`](../04-synthesia-to-notes/04-decisions.md): this plan
adds V-37 and V-38 there, and V-09 is superseded by V-37. Nothing else in that file changes.

This plan replaces **Story 2.1 of implementation 04 and nothing else**. The detector, the frame window
rule, the annotation page, the score board and Phases 3 to 5 of
[`../04-synthesia-to-notes/04-plan.md`](../04-synthesia-to-notes/04-plan.md) all stand, and all of
them read the overlay through the same `Calibration`.

## 1. What we are building and why

Implementation 04 fits the piano overlay from a grid: the user places one white key, and the app
repeats its width across the picture. That is wrong and it has to go. The cameras that record these
videos are not square to the keyboard, so perspective makes one white key wider than another, and
some pianos sit at a slight diagonal. No uniform grid fits either, and no amount of nudging will make
one. Phase 1 of 04 measured the octave period in the left, middle and right third of each picture
and found a spread of 3.4% at the median and 5.2% on `airplanes`; on a 52 white key piano that is a
drift of up to two and a half white keys from one end to the other, which is why the black keys of
`airplanes` never landed.

So the grid goes, and one rectangle replaces the whole of it. The user drags **one rectangle** over
the piano area — resizable and rotatable, so it can take whatever shape the picture needs — and the
piano is static for the whole video, so it is placed once. Everything inside it is found:

- the **black keys** first, because they are the strongest thing in the picture: dark, tall, and
  grouped in twos and threes;
- the **white keys** from them, or from the **thin dark line between two white keys**, whichever of
  the two routes scores better over the example set (V-20).

What comes out is a `Calibration` that carries **per-key borders** instead of one white key width for
the whole keyboard. Everything after it — the lanes, the detector, the annotation page, the score
board — reads that `Calibration` and needs to know nothing about how it was found.

## 2. Terminology

The words of the prompt, used with one meaning each. The words of implementation 04 keep their
meaning: rectangle, rectangle tip, upper line, offset line, piano overlay, vertical lane, sampled
frames, white key width. New work uses these and no synonyms.

- one rectangle: the single shape the user drags over the piano area. It has a position, a width, a
  height and an angle. In code it is `pianoRect`. It is never called a frame, because a frame is a
  sampled picture of the video.
- rectangle coordinates: distances measured along the top edge of the one rectangle (`u`) and down
  its side (`v`), from its top left corner, before any rotation. Picture coordinates are the pixels
  of the picture.
- black key group: two or three black keys standing together, with a wider gap on both sides.
- the pattern: the order of groups of two and three that fixes the pitch class of every key (V-10).
- occlusion: a hand, or anything else, covering keys so that the picture does not show them.
- extrapolated key: a key the finder did not see and placed from the pattern and its neighbours.
- confirmed key: an extrapolated key whose place was checked back against the pixels and found dark
  where a black key should be.
- route A: the white key borders derived from the black keys.
- route B: the white key borders read from the thin dark line between two white keys.
- family: one way of placing the five black keys of an octave against the white keys. Different
  renderings and different pianos use different families.
- per-key borders: the left and the right border of every key, one number each, instead of a left
  border, a width and a count.
- median white key width: the median of the white key widths of one calibration. It is what
  `whiteWidth` now means, and it is the unit of V-22 for every length that is not about one key.
- local white key width: the width of the white key being read, or, for a black key, the mean width
  of the two white keys it stands between. It is the unit for every length that is about one key.

## 3. What already exists and is reused

- `aitu_backend/video/geometry.py` and `aitu-frontend/src/video/overlayGeometry.ts` — the two
  twins of the overlay geometry, held together by
  `aitu-backend/tests/fixtures/video/geometry-fixture.json`, `tests/test_video_geometry.py` and
  `npm run check:geometry`. Both twins change here, and the check has to keep passing.
- `aitu_backend/schemas/video.py` — `Calibration`, `PianoKey`, `KeyLane`, `Geometry`. `Calibration`
  changes here; the other three do not.
- `aitu_backend/video/detector.py` — reads keys and lanes through `geometry.keys()`. It changes in
  three lines, all about which white key width a length is measured in.
- `poc-synthesia-frames/scripts/find_keyboard.py` — Phase 1 of 04 already found the keyboard
  without the user, from the horizontal autocorrelation of the rows and the pattern of black keys.
  It is a grid finder, so it goes, but two of its findings are kept: the 75th percentile of a window
  is what separates a black key from a thin dark line, and the pitch class hypotheses have to be
  grouped by where they put the first C or the margin between them means nothing.
- `components/video/FrameCanvas.tsx` — the zooming, panning picture with the live scale. Reused
  whole. `DragRect.tsx` is the model for the one rectangle and is replaced by it.
- `components/video/PianoOverlay.tsx` — one element per key. It keeps its drawing and its press;
  it loses the two gestures that moved the grid.
- The example set: the 24 screenshots in
  [`../04-synthesia-to-notes/examples/`](../04-synthesia-to-notes/examples), served at 1280 px
  wide (V-35), the 21 seeded calibrations under `data/frame-examples/`, and the five hand readings
  on `derulo` and `shut-up-and-dance` that give the score board its 9/0/0 onsets and 6/0/0
  sustains. Those readings are keyed by offset line and MIDI pitch, not by geometry, so they survive
  the model change and are the regression check for it.

No new dependency. The finder is numpy and scipy, like the detector.

## 4. The shape of the work

```text
one rectangle (the user)  ──▶  rectified strip: the picture inside it, rotated straight
                                  │
                                  ├─▶ the black keys: dark, tall columns of the strip
                                  ├─▶ the pattern: groups of two and three → pitch class of every key
                                  ├─▶ extrapolation through the occlusion, then checked against the pixels
                                  ├─▶ the white key borders: route A (from the black keys) or route B (from the lines)
                                  └─▶ Calibration with per-key borders  ──▶  everything 04 already does
```

The finder is one function, `find_overlay(image, piano_rect) -> Calibration`, in
`aitu_backend/video/finder.py`. It reads one picture and one rectangle. It does not know whether the
picture is a screenshot or a sampled frame, and it does not read or write any file — the same shape
`detect()` has, for the same reason: Phase 3 of 04 calls it on a frame of a video without changing it.

## 5. The model change, and what it costs

This is the part the prompt asks to be said before it is changed. `Calibration` today is a grid: a
left border, a white key width, a count, and five black key offsets replicated across every octave.
It becomes per-key borders.

### 5.1 The new `Calibration`

```text
imageWidth, imageHeight        unchanged
pianoRect                      new: { x, y, width, height, angle } — the one rectangle, in picture
                               pixels and degrees. Kept so the rectangle comes back where it was left.
upperLine                      unchanged: one horizontal line (V-11). Its default is the top edge of
                               the found keys.
whiteBorders                   new: the u of every white key border along the top edge of the one
                               rectangle, left to right, one more than the white keys.
blackBorders                   new: { left, right } in u for every black key, in pitch order. Their
                               count is fixed by the pattern: one per pair of white keys two
                               semitones apart, and the model refuses any other count.
blackDepth                     new: how far down the rectangle the black keys reach, in v. Drawn,
                               never read by a detection rule. Replaces blackHeight.
whiteWidth                     kept, and its meaning changes: the median white key width, in
                               picture pixels along the upper line. Derived from the borders, never
                               set by hand. It is the unit of V-22 for every length that is not
                               about one key (section 5.4).
firstWhitePitchClass           unchanged, and now written by the finder from the pattern (V-10).
firstWhiteOctave               unchanged: the one thing the user says (V-10).
rollTop, guardBand, note       unchanged
found                          new: { route, confidence, extrapolated: [midi], confirmed: [midi],
                               corrected: [border index] } — what the finder said about its own
                               answer, so a weak answer is visible rather than silent, and which
                               white key borders the user dragged by hand afterwards.
gone                           leftBorder, whiteCount, whiteHeight, blackHeight, blackRatio,
                               blackMode, blackNudge, blackOffsets
```

A border is stored in rectangle coordinates and not in picture pixels because that is where it was
measured and where it is drawn. The geometry turns a border into a picture x with one line:
`x = pianoRect.x + u · cos(angle)`. The rectangles of the roll fall straight down the picture whatever
the camera did to the piano — the roll is drawn by the software over the video, in screen space — so
the lane of a key is the vertical strip under the point where that key's top edge sits. Phase 1
measures that claim on the tilted pictures before anything is built on it (Task 1.1.3).

### 5.2 What it costs `video/geometry.py`

- `white_borders()` stops being a formula and reads the list.
- `keys()` loses the grid loop and the whole of the black key placement: `black_offset()`,
  `REAL_BLACK_OFFSETS`, the two modes and the nudge go. A black key is read from `blackBorders` in
  order, and the pattern only says which pitch it has.
- `lanes()` pads each key by the margin times the **local** white key width, not one width for all.
- new: `top_edge_x(cal, u)`, the one line above, and `local_white_width(cal, key)`.
- `guard_band_px()` and `default_octave_for()` are unchanged.
- `tests/test_video_geometry.py`: 5 of its 13 tests are about the grid, the modes, the nudge and the
  replicated octave, and go. Their replacements test borders that are not evenly spaced, a rotated
  rectangle, the local width, and a wrong count of black borders being refused.
- `scripts/build_geometry_fixture.py`: the fixture calibration is written from the same 88 key
  numbers Phase 1 of 04 measured, spelt out as borders, plus a second calibration with an angle of
  4 degrees and borders that widen from left to right, so the check covers what the grid could not.

About 60 lines go and 40 come.

### 5.3 What it costs `overlayGeometry.ts`

- The same as the backend: `whiteBorders()`, `blackOffset()`, `defaultBlackOffsets()`,
  `REAL_BLACK_OFFSETS`, `guessFirstPitchClass()` go; `buildKeys()` reads the two lists;
  `buildLanes()` pads by the local width; `topEdgeX()` and `localWhiteWidth()` come.
- `components/video/overlayEdits.ts` goes whole: `shiftStart` moved the grid.
- `scripts/check-geometry.ts` compares both fixture calibrations and does not otherwise change.
- Readers of `whiteWidth` outside the geometry keep working with no change, because they want the
  median: the default offset line of two white keys in `ExamplesPage`, `AnnotationEditor` and
  `DetectionView`, and the label of `OffsetLine`.
- `PianoOverlay.tsx` loses `onMove` and `onBlackKeyMove`, and draws the keys inside a group rotated
  by the rectangle's angle, each key from its top border down to `blackDepth` or to the bottom of
  the rectangle. Its press, its hover names and its marks are unchanged, so the annotation page and
  the detection view do not change.

### 5.4 What it costs the lanes of V-13 and the unit of V-22

V-13 says a lane is the strip between the left border and the right border of one key, widened by a
margin. That stays word for word. What changes is where the two borders come from: the key's own
borders, from the list, instead of `leftBorder + k · whiteWidth`. The lane is still a vertical strip
of the picture, because the rectangles fall vertically (section 5.1). The margin, which V-13 gives
in white key widths, is measured in the **local** white key width: a key that perspective made 22 px
wide gets a smaller margin than one it made 28 px wide, and attribution keeps its 0.33 margin on both.

V-22 says every geometric threshold is in white key widths, and that the white key width is the one
length the calibration always knows. There are now two such lengths, and V-38 says which threshold
uses which:

| threshold | unit | why |
|---|---|---|
| lane `margin` | local | it is about this key |
| `extentWindow` | local | the search for this rectangle's own edges |
| `minWidth`, `maxWidth` | local | the width gate compares a rectangle against the key it is on |
| `minHeight`, `clipTolerance` | median | vertical lengths; perspective across the keyboard does not change them |
| halo guard band default | median | one band for the whole picture (V-24) |
| the offset line defaults | median | one window for the whole picture |

On 23 of the 24 pictures the two differ by under 5%, which is inside the noise every one of those
thresholds was measured with. On the tilted pictures they differ by more, and that is the point.

In `detector.py` this is three lines in `runs_for_key`: the pad, the extent window and the width gate
read `key["white"]` — the local width handed in by `detect()` — and `min_height`,
`clip_tolerance` and the guard band keep reading `cal.white_width`.

### 5.5 What it costs the saved records

The 21 seeded calibrations and the two examples with hand readings are grids. `examples.load()`
spells a grid out into borders on the way in — the same borders `geometry.white_borders()` computed
from it — and the record is written back in the new shape the first time it is saved. Nothing saved
is lost, the five hand readings never notice, and the score board has to read the same
**9/0/0 onsets and 6/0/0 sustains** before and after the change. That number is the regression check
of Phase 2 and it is quoted in the report.

## 6. The finder

### 6.1 The black keys

1. Rectify: the picture inside the one rectangle is rotated straight, so the rest reads a strip whose
   columns are `u` and whose rows are `v`. Grey, at the working resolution (V-35).
2. Column darkness: the black keys are the dark, tall columns of the top part of the strip. For each
   column, how much of the top half of the strip is darker than the strip's own light level. A hand
   is dark in some columns too, but it is not tall and thin, and it is not spaced like keys; this
   is what the pattern step is for.
3. Runs of dark columns are black key candidates. Width, depth and spacing are measured for each,
   and the median black key width and depth over the candidates are the picture's own numbers.
4. The pattern: the gaps between consecutive candidates are either "inside a group" or "between two
   groups"; the sequence of group sizes must read 2, 3, 2, 3 … Every start of that sequence is one
   hypothesis for the pitch class of the leftmost black key, and the hypotheses are grouped by where
   they put the first C (Phase 1 of 04 measured why: without that, the runner up is the winner
   wearing a different label). The margin between the best and the second best is the finder's
   confidence, and it is reported.
5. Extrapolation through the occlusion: a hand hides some keys in 17 of the 24 pictures. The found
   candidates fix the pattern and a smooth position function — the u of black key number k, fitted
   over the found ones with a low order polynomial, because perspective changes the period smoothly
   and never in steps. Every black key the pattern says should exist and the strip did not show is
   placed from that function, and flagged **extrapolated**.
6. Check back against the pixels: an extrapolated key is **confirmed** when the strip is dark where
   it was placed, and left flagged when it is not — a hand is lighter than a black key, so an
   unconfirmed key is one that a hand covers, and the user sees which keys those are.
7. The user's rectangle may reach past the keyboard at either end. A hypothesis that needs a black
   key where the strip is light and unoccluded is refused; the keyboard is what the pattern accounts
   for.

### 6.2 The white keys: route A, from the black keys — **this is what ships (V-41)**

The white key borders are derived from the black keys. It is not one rule. On some pianos a white key
border sits at the midpoint between two black keys and on others it does not: in the picture the
prompt supplies, F# sits well off the midpoint between F and G. **Phase 1 measured the families these
24 pictures actually use (V-40): two.** The real piano family on 23 of them — C# at −0.095, D# at
+0.100, F# at −0.131, G# at +0.009, A# at +0.137 white key widths from the border each stands on —
and the boundary family on `derulo`, where all five are zero. The twelve equal slots family below is
not used by any of them and is not fitted. The two are told apart from the black keys alone: the gap
between two groups over the gap inside a group is 1.98 on `derulo` and 1.49 to 1.56 on the rest.
The three candidates that were named before measuring, for the record:

- **twelve equal slots**: the octave is cut into twelve equal semitone slots at the back, and a black
  key sits on its slot. C# is then 0.125 white key widths left of the C|D border, D# is 0.04 right of
  D|E, F# is 0.21 left of F|G, G# is 0.04 left of G|A, A# is 0.125 right of A|B. This is what a
  drawn keyboard does, and it is the family whose F# is well off the midpoint.
- **symmetric groups**: the two black keys of a group sit symmetric about the middle white key of
  the group (D), and the three about G#. The offsets of 04's `REAL_BLACK_OFFSETS` were this family.
- **the real acoustic layout**, where D, E and the other white keys have different widths at the
  back so that the front widths come out equal.

Route A as built: the family from the gap ratio; the local white key width at each black key from
the octave period around it over seven; one border per black key, its centre minus the family's
offset times the local width; E|F and B|C as the midpoints of the borders on each side; and past the
outermost black keys, borders at the local width while the key's midpoint is still inside the
rectangle. Measured: 0.031 white key widths from the truth at the mean over 901 borders, 0.24 at the
worst, none over the lane margin. The borders are in u, along the top edge.

### 6.3 The white keys: route B, from the thin dark lines

The thin dark line between two white keys is narrow but it is there. It is visible only in the front
part of the keys, below the black keys, because in the back part it runs under a black key. Route B:

1. In the front part of the strip, the columns that are darker than both neighbours by a small,
   consistent amount are line candidates; the same 75th percentile trick of Phase 1 of 04 keeps a
   black key from looking like a line.
2. Each candidate is a short line segment, fitted over the rows it is visible in. Perspective makes
   the segments lean, so each is a line with a direction, not a column.
3. The segment is extended up to the top edge of the rectangle, and its crossing is the border in u.
4. A hand hides lines too. The pattern from 6.1 says how many white keys sit between two black key
   groups, so a missing line is placed from its neighbours and flagged, the same way an extrapolated
   black key is.

Route B gives the white key borders directly instead of inferring them, which is why it is worth
measuring against route A. Its weakness is known before measuring: the lines are one or two pixels
wide at 1280 px, and on the dim pictures (`more-examples-1`, `more-examples-10`) they may not be
there at all. **Measured: it does not ship.** On the borders both routes can be scored on
independently it is 0.024 white key widths off against route A's 0.031, a fifth of a pixel apart;
but it could read only 73% of the borders, against the 96.0% of black keys route A rests on, and
fills the rest with route A's rule. It stays in the spike as the tool the truth is read with.

### 6.4 The score, which decides

Both routes are measured over the example set on the same truth and the one that scores better ships,
with the number beside it (V-20). The truth is read by hand in Phase 1: for every one of the 24
pictures, the u of every white key border of three octaves — one at the left, one in the middle,
one at the right, away from the hands where possible — read off a crop zoomed four to eight times
with a rule every five pixels, the way Phase 2 of 04 read its ground truth. That is about 21 borders
per picture, about 500 in all. The score of a route is:

- the mean and the worst absolute error of its borders against the truth, in local white key widths;
- the count of pictures on which it found the right number of keys and the right pitch class;
- the count of pictures on which its worst error exceeds 0.25 white key widths, which is the lane
  margin: past that, a lane no longer holds its own rectangle.

Two more numbers are quoted whichever route wins, because they are what the overlay is for:

- the score board of 04 on the five hand readings must still read 9/0/0 and 6/0/0 with the found
  overlay in place of the seeded grid on `derulo` and `shut-up-and-dance`;
- the time a person takes to place the one rectangle on an unseen screenshot, measured, against the
  minute Task 2.1.2 of 04 allowed for the grid.

## 7. The HTTP surface

One endpoint is added and one changes its shape.

- `POST /frame-examples/{slug}/find` — the one rectangle in, the found `Calibration` out. Nothing is
  saved; the UI shows it and the user saves it through the endpoint below.
- `PUT /frame-examples/{slug}/calibration` — unchanged in name, and its body is the new
  `Calibration`.
- `POST /frame-examples/{slug}/geometry` — unchanged; it is the runtime form of the geometry check.
- Phase 3 of 04 adds `POST /video/{uuid}/find` beside it when it exists; nothing here presumes it.

## 8. The screens

`/video/examples` keeps its three steps: **1 Fit the piano, 2 Read it by hand, 3 What the detector
saw.** Steps 2 and 3 do not change. Step 1 becomes the one rectangle and the overlay that was found
from it.

Every button of the old flow goes: place the white key, place the black key, render one octave,
render the piano, move the piano, + key left, + key right, and the backspace trim with it. What
stays on the screen:

- the picture, zoomed and panned as before;
- **the one rectangle**, dragged by its body, resized from its edges and corners, and rotated from
  one handle above its top edge. It is drawn on the picture the moment the step opens — at the
  saved `pianoRect` when there is one, and across the bottom third of the picture when there is not;
- **the overlay found from it**, drawn the moment the rectangle settles, without a button: the
  answer is what the screen is about, so the finder runs when the rectangle has stopped moving for
  a moment, the way the detector re-reads when the offset line moves. Extrapolated keys are drawn
  with a dashed border, confirmed ones with a dotted one, so a hand's cost is visible;
- **the upper line**, one horizontal line, dragged up and down, defaulting to the top edge of the
  found keys (V-11);
- the **octave** dropdown, defaulting from how many keys were found (V-10). The leftmost key
  dropdown goes: the pattern fixes the pitch class, and the names on hover show it;
- the finder's confidence and its route, one line of text, and the count of extrapolated keys;
- **Save**.

The user corrects a wrong overlay by reshaping the rectangle: everything inside the rectangle is
found. When the found overlay misses completely, the fallback is on the picture too (the user's
decision, 2026-09-14): **any white key border can be taken and dragged** sideways along the top edge,
one at a time, for the whole piano. A dragged border is stored as the border it made, the key on each
side of it follows, and it is marked as the user's so the finder's own answer is never mistaken for a
hand one. A picture that needs hand corrections is still a finder defect and is named on the score
board with the reason: the finder is what has to be right, and the drag is what lets the work go on
while it is not.

Doing this on an unseen screenshot is measured (Task 3.2.3), and the bar is under thirty seconds:
one gesture and one dropdown, against the four gestures and two dropdowns of the grid.

## 9. Risks, named now

- **Route B may not exist on the dim pictures.** Then route A ships, and the report says on which
  pictures the lines could not be read.
- **A family that none of the three candidates fit.** Route A reports the residual of the best fit
  per picture; a picture whose residual is far above the rest is a fourth family or a finder defect,
  and either is named.
- **Both hands over the middle of the keyboard** hide up to two octaves in a row. The position
  function is fitted on the found keys on both sides of the gap, so it interpolates rather than
  extrapolates there, which is the easier case. A hand at the very end of the keyboard is the hard
  one, and `more-examples-14` has one.
- **Perspective that is not a rotation.** The one rectangle rotates; it does not skew. On `ode1` and
  `superestrella` the keys taper towards the top, so the front part of a key does not sit under its
  top edge. Everything that matters is read at the top edge — the lanes, the borders of route A, and
  the crossing in route B — so the taper costs nothing there. Phase 1 measures how far the front
  part sits from the top edge on those pictures, so the number is known.
- **The rectangles may not fall vertically on a tilted picture.** If Task 1.1.3 finds that they lean
  with the piano, the lane is a leaning strip and the detector has to rectify the roll too. That
  would be a change to V-13 and stops the plan at Phase 1 until it is raised.
- **`airplanes`.** It is the reason for this plan and it is the hardest picture. It is scored like
  the others and it is not allowed to be the one that is left out.

---

# Phase 1 — Measure the pictures and decide the route  ·  done

What it found is [`05-phase-1-implementation.md`](05-phase-1-implementation.md) and the evidence is
[`../../../poc-piano-overlay/RESULTS.md`](../../../poc-piano-overlay/RESULTS.md). V-39, V-40 and
V-41 were added. The tasks below are left as they were written, so a reader can see what was asked
as well as what came back.

Nothing in this phase ships to a user. Its work lives in `poc-piano-overlay/` at the repository
root, beside `poc-synthesia-frames/`; when the route is accepted, Phase 3 ports it into the backend
and the frontend as appropriate and the spike stays as the evidence. Its conclusions go into
[`../04-synthesia-to-notes/04-decisions.md`](../04-synthesia-to-notes/04-decisions.md) as new V
numbers, each with the measurement behind it.

## Story 1.1 — The truth and the claims

### Task 1.1.1 — The truth: white key borders read by hand

For every one of the 24 pictures, the u of every white key border of three octaves, read by hand off
zoomed, ruled crops as section 6.4 says, plus the angle of the keyboard and the one rectangle used,
in `poc-piano-overlay/data/truth.json`. A border a hand covers is left out and counted; nothing is
guessed into the truth.

### Task 1.1.2 — The families

Measure, on every picture where an octave is fully visible, where each of the five black keys sits
against the white key borders of the truth, in local white key widths. Cluster the 24 answers and
name the families found. The report has one row per picture: the five offsets, the family, and the
residual of the best fit. This is the table route A is built from.

### Task 1.1.3 — Do the rectangles fall vertically?

On `airplanes`, `ode1`, `ode2`, `ode3` and `superestrella`, measure the lean of the falling
rectangles and of the light beams against the lean of the keyboard. If the rectangles are vertical
in the picture while the keyboard is not, V-13 stands and the lanes stay vertical strips. If they
lean with the keyboard, stop and raise it: the lanes would have to lean too.

### Task 1.1.4 — The perspective

On every picture: the white key width in the left, middle and right third, the angle of the
keyboard, and on the tapering pictures how far the front of a key sits from its top edge. This is
the number that says how wrong the grid was per picture, and it goes in the report beside the
family table.

## Story 1.2 — The two routes

### Task 1.2.1 — The black keys, and the extrapolation

Build section 6.1 as a script over the 24 pictures. Report per picture: black keys found, black keys
extrapolated, extrapolated keys confirmed, the pattern's confidence, and whether the pitch class is
right. Save the picture of what it found with the truth drawn beside it. A picture on which the
pattern is wrong is a result and is named.

### Task 1.2.2 — Route A

Build section 6.2 on top of 1.2.1, fitting the family per picture. Score it as section 6.4 says.

### Task 1.2.3 — Route B

Build section 6.3. Score it the same way, on the same truth. Say on which pictures the lines could
not be read at all.

### Task 1.2.4 — The decision

One table, both routes, every picture, and the totals. The route that scores better ships; if they
tie, route A ships because it has fewer things to go wrong on a dim picture. Section 6 of this plan
is updated to match, and the decision goes into the decisions file as a V number with the table
behind it.

Exit criteria: a reader can build the finder from the report alone, every number in it has a
measurement beside it, and the route is chosen.

---

# Phase 2 — Per-key borders in both services  ·  done

The report is [`05-phase-2-implementation.md`](05-phase-2-implementation.md).

The model change of section 5, with nothing found yet: the saved grids are spelt out into borders,
and every screen and every test that reads the overlay keeps working. This phase is done before the
finder so that the finder lands on a model that is already proven against the score board.

## Story 2.1 — The model and the geometry

### Task 2.1.1 — `Calibration` becomes per-key borders

`schemas/video.py` as section 5.1: the new fields, the gone fields, and a validator that refuses a
count of black borders the pattern does not allow. `api/frameExamples.ts` mirrors it.

### Task 2.1.2 — The two geometry twins

`video/geometry.py` and `overlayGeometry.ts` as sections 5.2 and 5.3. `overlayEdits.ts` goes. The
fixture is rebuilt with two calibrations, one straight and one at an angle with borders that widen,
and `make test` and `npm run check:geometry` both pass against it. It is tested by breaking it: one
border moved by a tenth of a pixel in one twin makes the check fail, and the report quotes the
message.

### Task 2.1.3 — The upgrade of the saved records

`examples.load()` spells a grid calibration out into borders, as section 5.5. All 21 records load,
the two with hand readings keep them, and `superestrella` keeps its no-roll mark.

## Story 2.2 — Everything that reads the overlay

### Task 2.2.1 — The detector on local widths

The three lines of section 5.4 in `runs_for_key`, and `detect()` handing each key its local width.
The score board reads **9/0/0 onsets and 6/0/0 sustains** after the change, and the report quotes
it. If it does not, the change is wrong and the phase stops there.

### Task 2.2.2 — The overlay drawn from borders

`PianoOverlay.tsx` draws each key from its own borders inside the rotated group, and loses the two
grid gestures. The annotation page and the detection view render the seeded examples exactly as
before, checked in a browser on `derulo`, `shut-up-and-dance` and `airplanes`.

### Task 2.2.3 — The calibration editor, emptied

`CalibrationEditor.tsx` loses every button of the old flow and, for this phase, shows the saved
overlay with the upper line and the octave dropdown, and Save. The one rectangle and the finder come
in Phase 3; this phase must not leave the page unable to open. `DragRect.tsx` stays until Phase 3
replaces it.

Exit criteria: `make test`, `make lint` (the pre-existing counts and no more), `npm run lint`,
`npm run check:geometry` and `npm run check:render` all pass; the score board is unchanged; the
three screens open on every seeded example.

---

# Phase 3 — The finder in the app, and the one rectangle on the screen  ·  done

The report is [`05-phase-3-implementation.md`](05-phase-3-implementation.md). Implementation 05 is complete.

## Story 3.1 — The finder

### Task 3.1.1 — `video/finder.py`

The chosen route of Phase 1, ported from the spike into the app as one function,
`find_overlay(image, piano_rect) -> Calibration`, with a frozen `FinderSettings` dataclass carrying
every threshold and the measurement behind it, the way `DetectorSettings` does. Unit tests on a
drawn keyboard: straight, rotated, with a block of keys painted over as a hand, with the rectangle
reaching past both ends.

### Task 3.1.2 — `POST /frame-examples/{slug}/find`

The endpoint of section 7. The found calibration carries `found.route`, `found.confidence` and the
extrapolated and confirmed keys.

### Task 3.1.3 — Every example found

Run the finder over all 24 with a rectangle placed by hand, save the calibrations, and score them
against the truth of Phase 1 in the app rather than in the spike: same numbers, or the port is wrong.
The seed script learns to write the found calibrations, so a fresh checkout starts from them. The
score board of 04 still reads 9/0/0 and 6/0/0 on the found overlays of `derulo` and
`shut-up-and-dance`.

## Story 3.2 — The screen

### Task 3.2.1 — The one rectangle

`PianoRect.tsx` replaces `DragRect.tsx`: one rectangle, dragged, resized and rotated on the picture,
in picture pixels, with the live scale for its handles. The angle handle sits above the top edge and
the angle is shown while it is dragged.

### Task 3.2.2 — Step 1, rebuilt

`CalibrationEditor.tsx` as section 8: the rectangle, the overlay found when it settles, the upper
line, the octave, the finder's confidence, Save. The saved rectangle comes back where it was left.
Extrapolated and confirmed keys are drawn as section 8 says.

### Task 3.2.3 — A border dragged by hand

`PianoOverlay` lets a white key border be taken and dragged sideways along the top edge, one at a
time, when the found overlay misses. The border moves in `whiteBorders`, the keys on both sides of it
follow, the black key between them keeps its own found borders, and the index goes into
`found.corrected`. Corrected borders are drawn in the user's colour. No other key gesture exists.

### Task 3.2.4 — Timed

A person places the rectangle on an unseen screenshot and saves. The time is written in the report
against the thirty second bar.

## Story 3.3 — The plan of 04 brought up to date

### Task 3.3.1 — Write it down

In [`../04-synthesia-to-notes/04-plan.md`](../04-synthesia-to-notes/04-plan.md): section 7's
Calibration tab, section 8's threshold table (the black key width of 0.58 is now measured per
picture), the "what this does not handle" list (`airplanes` comes off it or stays with its measured
reason), and Task 3.3.2, which opens the calibration UI of this plan on a frame. In
[`../04-synthesia-to-notes/04-checklist.md`](../04-synthesia-to-notes/04-checklist.md), Story 2.1
points here. The README of this folder, the table in
[`../README.md`](../README.md) and [`../../00-index.md`](../../00-index.md) say the state.

Exit criteria: an unseen screenshot is calibrated with one gesture and one dropdown in under thirty
seconds; every one of the 24 examples has a found overlay; the two routes' scores are in the report
with the winner named; both geometry checks pass; the score board is unchanged.

---

# 10. How a phase is handed off

The same as implementation 04. One agent per phase, with the phase's whole context in one session. At
the end of a phase the agent writes `05-phase-X-implementation.md` in this folder — technical, for
the next agent — updates [`05-checklist.md`](05-checklist.md), and writes the walkthrough message in
the structure of
[`../../language/communication-implementation-plans.md`](../../language/communication-implementation-plans.md).
The handoff sentence for the next agent:

```text
You are working on an implementation plan. Read @context/implementations/05-piano-overlay-from-black-keys/05-plan.md,
@context/implementations/04-synthesia-to-notes/04-decisions.md,
@context/language/communication-implementation-plans.md,
@context/implementations/04-synthesia-to-notes/04-phase-2-implementation.md and
@context/implementations/05-piano-overlay-from-black-keys/05-phase-X-implementation.md. Start Phase X+1.
```

Every worker, every phase:

- Reads the V numbers and does not reinterpret one. V-09 is superseded by V-37; V-13 and V-22 are
  read with V-38 beside them. A decision that looks wrong is raised and the work stops there.
- Reads the five rules in
  [`../01-epics-master-plan/plan/wall-clock-rewrite.md`](../01-epics-master-plan/plan/wall-clock-rewrite.md)
  and D-01 to D-34. They are still binding.
- Follows [`../../09-coding-conventions.md`](../../09-coding-conventions.md), keeps paths in
  `storage/paths.py` and routes in `layout/routes.ts`, and remembers the three ESLint rules Phase 2
  of 04 wrote down in its section 5.3.
- Runs `make test` and `make lint` in `aitu-backend`, and `npm run lint`, `npm run check:geometry`
  and `npm run check:render` in `aitu-frontend`, before reporting done, and states the counts. The
  baseline is Phase 2 of 04: one known test failure, four flake8 errors and thirty mypy errors, all
  pre-existing; one more of any of them is this plan's.
- Quotes numbers, not impressions. A rule with no measurement beside it does not ship (V-20).
