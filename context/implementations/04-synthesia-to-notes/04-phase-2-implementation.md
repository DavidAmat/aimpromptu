# Phase 2 — Evaluation: implementation report

Technical, for the agent that takes Phase 3. The plan is [`04-plan.md`](04-plan.md), the frozen
decisions [`04-decisions.md`](04-decisions.md), the status [`04-checklist.md`](04-checklist.md), and
what Phase 1 found is [`04-phase-1-implementation.md`](04-phase-1-implementation.md).

Phase 1 was a research spike that touched no application code. Phase 2 is the opposite: it puts the
detector Phase 1 measured into the app, builds the piano overlay both this phase and Phase 3 use, and
builds the page that says whether a change to the detector helped.

---

## 0. What this phase produced, in one table

| | Where | What it is |
|---|---|---|
| the overlay geometry | `aitu_backend/video/geometry.py` + `aitu-frontend/src/video/overlayGeometry.ts` | two rectangles become every key and its lane; one fixture keeps the two in step |
| the detector | `aitu_backend/video/detector.py` | the algorithm of section 8 of the plan, ported from `poc-synthesia-frames/scripts/detectors.py` |
| the plate | `aitu_backend/video/plate.py` | the 20th percentile plate, the single screenshot stand-in, the gradient channel |
| the momentum rule | `aitu_backend/video/momentum.py` | V-33 and V-34, ported and unit tested; **no caller yet — Phase 3 is its first** |
| the colour check | `aitu_backend/video/colour.py` | Task 2.3.4, measured and switched off |
| the example store | `aitu_backend/video/examples.py` | one record per screenshot under `data/frame-examples/` |
| the score board | `aitu_backend/video/scoring.py` | found, invented, missed, and what could not be scored |
| the HTTP surface | `aitu_backend/api/frame_examples.py` | `/frame-examples`, nine endpoints |
| the screens | `aitu-frontend/src/pages/video/`, `src/components/video/` | Video to Notes, four tabs, one of them built |

One new dependency, as the plan said: **pillow**. It was already installed transitively; it is now
declared, because the detector imports it directly. OpenCV is still not needed.

## 1. The score, which is the point of the phase

```text
example              d px   onsets f/i/m   sustains f/i/m
derulo                6.0        0/0/0          0/0/0
derulo               15.0        3/0/0          0/0/0
derulo               49.4        3/0/0          0/0/0
shut-up-and-dance    30.0        1/0/0          3/0/0
shut-up-and-dance    77.4        2/0/0          3/0/0
TOTAL                            9/0/0          6/0/0
```

Over the whole ground truth that exists: **every onset found, none invented, none missed, and the
same for sustains.** That is Phase 2's exit criterion, met on what can be measured.

**It is measured on two examples of twenty four, and that is the honest headline.** The other
twenty-one have a calibration and no hand reading, and `superestrella` has no roll to read at all.
Phase 1 said why: those two are the only examples where a human can read the picture without
guessing, because the other nineteen have a halo over the band where the answer is. Reading them is
what the annotation page was built for and it is the one thing this phase could not finish for
itself — see section 7.

### 1.1 The three windows read in this phase, and why they are not padding

Phase 1 left one reading per example. Three more were read here, chosen so that **a detector that
ignored the offset line would fail them**:

| reading | what it tests | the answer |
|---|---|---|
| `derulo` d = 15 px | a window of rows 147 to 161, which every tip falls inside and every rectangle higher up the roll falls outside | 3 onsets |
| `derulo` d = 6 px | a window of rows 156 to 161, which **no** tip falls inside — and the strike light lives in exactly those rows | nothing at all |
| `shut-up-and-dance` d = 30 px | a window of rows 346 to 375: G#4's tip is at 357 and inside it, C#5's is at 320 and outside | 1 onset, not 2 |

This is V-25 tested rather than asserted. The detector answers all three correctly, and in particular
it reports **nothing** at d = 6 where a rule that looked for "a rectangle near the line" would invent
three onsets off the strike light.

**How the truth was read, because it matters that it was not read from the detector.** Two
independent passes: a crop of the picture zoomed four to eight times with a red rule every five or
ten rows and the key midpoints drawn on it, read by eye; then the brightness down the middle third of
each key's own columns, thresholded halfway between the roll's floor and the rectangle's own level —
no lanes, no coverage, no gap closing, no splitting, no width gate. The two agree to a pixel or two,
and both agree with the readings Phase 1 made by hand on the two windows it read. The scripts are in
the report of this work, not in the repository; the numbers they produced are in each annotation's
own `note` field, so any of them can be argued with.

### 1.2 Task 2.3.4 — the colour check, measured, and it does not ship on

| setting | onsets f/i/m | sustains f/i/m | runs kept |
|---|---|---|---|
| plate — the chosen one | 5/0/0 | 3/0/0 | 31 |
| plate + the colour check | 5/0/0 | 3/0/0 | 29 |
| gradient edges alone | 0/0/5 | 0/0/3 | 0 |
| edges, hollow fallback on | 5/5/0 | 0/0/3 | 94 |
| plate and edges together | 5/0/0 | 3/0/0 | 31 |

(Measured on the two Phase 1 windows, before the three new readings were added, so the row for the
chosen setting reads 5/0/0 rather than 9/0/0.)

The colour check refuses two runs of thirty one and **changes no verdict**. V-20 says a rule ships
with its measured score or it does not ship, so it is a switch on the page that is off by default,
not a step of the detector.

The gradient channel is worse on these two: alone it finds nothing, because without the hollow
fallback a gradient's empty middle fails the centre test, and with the hollow fallback it invents
five onsets and loses every sustain. **That is not a verdict on the gradient**, because the examples
it was proposed for — the five outlined renderings — are exactly the ones with no hand reading yet.
It stays reachable as `channel=edges` and `channel=both` so the question can be answered the moment
those readings exist.

## 2. The piano overlay, built twice on purpose

Task 2.1.1 says one module owns the geometry and both services agree on its shape. They cannot share
the code: the calibration UI redraws the overlay on every drag of a handle, and a round trip per drag
is not a UI. So there are two implementations and one fixture:

```text
aitu-backend/tests/fixtures/video/geometry-fixture.json   one calibration, 88 keys, 88 lanes
  ├── aitu-backend/tests/test_video_geometry.py           asserts geometry.py against it
  └── aitu-frontend/scripts/check-geometry.ts             asserts overlayGeometry.ts against it
```

`npm run check:geometry` and `make test` both fail the moment the two disagree. It was tested by
breaking it: changing one black key offset from −0.13 to −0.12 makes the check say
`key 30 left: the frontend says 138.854…, the backend says 138.608…`. Regenerate the fixture with
`uv run python scripts/build_geometry_fixture.py` when the geometry changes on purpose.

There is also `POST /frame-examples/{slug}/geometry`, which answers with what the backend builds from
a calibration. It is the runtime form of the same check.

Two things about the geometry that Phase 3 should know:

- **`blackMode` defaults to `real`, not `boundary`.** Phase 1 measured that the boundary placement
  sits visibly left of where a photographed piano draws its black keys. The spike's own calibrations
  were measured with `boundary`; seeding them into the app switched them to `real`, and the score did
  not move — which says the difference does not reach the two plain Synthesia examples, not that it
  does not matter.
- **`blackNudge` is new**, in white key widths, applied to every black key after the mode. It is the
  "may nudge it" of Task 2.1.1, and it is the handle for `airplanes`, the one example photographed at
  a strong angle whose black keys the automatic finder put in the wrong place.

## 3. What changed against Phase 1, and why

Four things. Three are small and one is a genuine defect in the port.

### 3.1 `VOTE_FLOOR` is derived from the slack, not chosen

`momentum.vote_for_travel` never considers a travel below `VOTE_FLOOR`, because a shift of nothing is
where the lettering lives. Phase 1 used 15 px on three screenshots that were 51 and 68 px apart. A
video sampled at 10 frames per second travels about 17 px, so 15 is uncomfortably close to the answer
it has to find. The floor is now `2 × TOLERANCE + 1 = 11`, and the reason is a proof rather than a
preference: a run matches itself at any shift within `TOLERANCE` (5 px), so any floor at or below the
slack lets a letter vote for itself. This is tested — `test_the_travel_is_voted_for_by_the_runs_and_never_zero`
puts three letters and three falling rectangles in front of it and the vote answers the travel.

### 3.2 The vote answers the middle of its plateau, not its first shift

The 5 px slack makes the winning count a plateau, not a spike: every shift within the slack of the
real travel matches the same runs. Taking the first shift of the plateau — which `max()` does — biases
every travel low by the whole slack. It now takes the middle of the widest plateau. On Phase 1's own
synthetic case this is the difference between answering 46 and answering 51.

### 3.3 The offset line is stored in pixels, not in white key widths

Phase 1's `ground_truth.json` stored `d_in_white_keys: 2.0`. An `Annotation` stores `offsetPx`,
because on a video the offset line is `scrollSpeed × sampleMs` and that is a length in pixels (V-25).
The seed multiplies by the white key width once, at the boundary. Nothing downstream has to know.

### 3.4 A picture is read at one resolution, and it is served at that resolution

The example screenshots are 3600 px wide and a video is 1280. `video/images.py` resizes every picture
to `WORK_WIDTH = 1280` before anything reads it, **and the browser is served that same copy** from
`GET /frame-examples/{slug}/image`. So a coordinate the user places in the calibration UI is the
coordinate the detector reads, with no scaling anywhere between them. This is the twin of V-22 for
coordinates: V-22 puts every length in white key widths, this puts every coordinate in one picture's
pixels at one width.

The derived copy lives at `data/frame-examples/cache/<slug>.jpg`, is rewritten when the screenshot is
newer, and is gitignored. The records beside it are not: a hand reading cannot be reproduced.

## 4. The shape of the code, for the agent that extends it

### 4.1 The detector is parameterised, and that is how a change gets measured

`DetectorSettings` is a frozen dataclass carrying every named threshold with the measurement behind
it in its own comment. `detect()` takes one. `scoring.board()` takes one. So a proposed change is
`board(settings=DetectorSettings(gap_close=3))` and a number, not an argument. **Do not turn these
back into module constants.**

```python
from aitu_backend.video import detector, scoring
from aitu_backend.video.detector import DetectorSettings

scoring.board(settings=DetectorSettings(split_prominence=0.30))   # what does it cost?
scoring.board(channel="both", colour_check=True)                   # what do the extras cost?
```

### 4.2 `detect()` is deliberately ignorant

It takes a picture, a calibration, one offset line and optionally a real plate. It does not know
whether the picture is a screenshot or a sampled frame, it does not read or write any file, and it
does not know what a video is. Phase 3 hands it `plate=` built by `plate.build_plate(frames)` and
loops; nothing in it needs to change for that.

The one thing it does **not** yet do is apply the momentum rule, because a single screenshot has no
neighbouring frame to ask. `momentum.apply(runs, before, before_travel, after, after_travel)` returns
`(kept, refused)` and stamps every run, and `Detection.refused` and the `momentum` field on a run are
already on the wire and already drawn by the UI. **Wiring it is Phase 3's job and it is the first
real test the rule gets**, because Phase 1 could only try it on three screenshots that had to be
registered onto each other first.

### 4.3 The lane is read once, for its own key

`runs_for_key` is the whole of V-27 and it is the part most likely to be broken by a well meant
refactor. Reading every lane and then sorting runs by nearest midpoint looks like V-13 and V-14 and
is wrong — Phase 1 measured 23 overlapping runs on one key from it. The filter form is one line:

```python
if midis[int(np.argmin(np.abs(mids - mid)))] != key["midi"]:
    continue    # this rectangle is centred nearer another key; its own lane will find it
```

### 4.4 What the UI needs from a detection, and why it is JSON and not a picture

Task 2.3.2 asks for an overlay drawn on the picture. It is drawn in the browser, in SVG, over the
same JPEG the detector read — not rendered server side. That is what makes it pannable, zoomable and
clickable, and it is why `DetectedRun` carries `x0`, `x1`, `yTop`, `yBottom` in picture pixels rather
than anything pre-drawn. Phase 3's detection tab should reuse `components/video/DetectionView.tsx`
whole.

## 5. The screens

A new top section, **Video to Notes**, with four tabs in `layout/routes.ts`: Video, Calibration,
Detection, Examples. Phase 2 built Examples; the first three are `Placeholder`s naming Phase 3.

```text
/video/player        Phase 3 — the sampled frames, spacebar, arrows, progress bar
/video/calibration   Phase 3 — CalibrationEditor on a frame of the video
/video/detection     Phase 3 — the detector over every sampled frame
/video/examples      built
/video/examples/:slug
```

Inside one example the work is three numbered steps: **1 Fit the piano, 2 Read it by hand, 3 What the
detector saw.**

The components are written to be reused by Phase 3 and none of them knows about examples:

| Component | What it is |
|---|---|
| `FrameCanvas` | the picture in an SVG `viewBox`, wheel zoom, drag pan, a `focus` prop that jumps the view |
| `DragRect` | one horizontal rectangle, eight handles, never rotates |
| `PianoOverlay` | one element per key, marks, names on hover |
| `CalibrationEditor` | the four steps: place, place, render, move — and the trim |
| `OffsetLine` | the window, dragged up and down the picture |
| `AnnotationEditor` | the cycle, the dragged offset line, the saved readings |
| `DetectionView` | the runs drawn on the pixels, thrown out or corrected in place |
| `ScoreBoardTable` | the board, and what could not be scored |

### 5.1 The screens were rebuilt once, and what the rebuild was about

The first version of all three screens put every control on the screen at once: two pairs of cut
buttons and a slider for the upper line on the calibration step, a strip sheet and a view toggle and
an offset slider on the reading step, a channel picker and a colour switch and a run button on the
detection step. The user rejected all of it, and the correction is worth more than the code: **the
picture is the control, and a screen should only offer the step you are on.**

| step | what it is now |
|---|---|
| 1 · fit the piano | five steps, one at a time: place the white key → accept, place the black key → accept, **render one octave** → align its five black keys, render the piano, move the piano. Nothing else is on the screen while a rectangle is being placed, and **no overlay is drawn until it is rendered** — not even for an example that was calibrated before. *Move the piano* brings a saved one back |
| 2 · read it by hand | one picture, the piano accepted on step 1, one line dragged up and down. Press a key to cycle it. The rule of V-18 is folded away under one line |
| 3 · what the detector saw | the same picture with what the detector found drawn on it. Press a rectangle to throw it out, press a key to say what it should have been. The detector re-reads as the line moves; there is no run button |

Three things this settled that are worth keeping:

- **Taking a key off trims the grid; it does not punch a hole in it.** The overlay is a left border,
  a white key width and a count, so what is kept is the longest unbroken run of white keys holding
  none of the picked ones. That is the right answer for the case it exists for — the overlay reaching
  past the keyboard at one end or both. The pitch class and the octave move with a trim from the
  left, because it is the same keyboard read from a different key: trimming six white keys off
  `derulo` takes it from `A0 to B7` to `G1 to B7`, and that shift is V-10 staying true.
- **A press and a drag on a key are told apart by travel, not by a mode.** On the calibration step a
  drag moves the whole overlay and a press picks the key out; the user never has to say which they
  meant. A box swept over the roll above the keys picks several, and `FrameCanvas` lets a screen
  claim a press (`onPictureMouseDown` returns `true`) so panning keeps working everywhere the box
  does not claim.
- **The reading and the judging are the same act.** Correcting the detector on step 3 produces the
  hand reading for that window, so the fastest way to read an example is to let the detector read it
  first. That is only sound because every box is drawn on the rectangle it claims to be — accepting
  one is looking at it, not trusting it. It is also why the channel picker and the colour switch are
  **not** on that screen: they belong on the score board, where a change gets measured.

**The octave is aligned before the keyboard is built from it, and that changed the calibration.**
`blackMode` + `blackNudge` said one of two fixed patterns moved as a block; every rendering puts its
black keys somewhere slightly different and not all of them by the same amount, so that was never
going to be enough. A calibration now carries `blackOffsets` — five numbers, one per black key of an
octave, each in white key widths from the boundary between the two white keys it stands between,
in the order C#, D#, F#, G#, A#. The user drags the five black keys of one octave onto the picture
and `geometry.keys` replicates that octave across the whole keyboard, which is measured: with one
black key moved, every key of that pitch class across the keyboard moves with it and they stay one
octave apart.

`blackMode` and `blackNudge` stay in the model as what `blackOffsets` starts at and as what a
calibration saved before the octave step still means — `black_offset()` falls back to them when the
list is absent, and a test asserts the fallback equals spelling the same offsets out. That is what
keeps the 21 seeded calibrations valid, and why the geometry fixture did not have to change.

**The octave preview is eight white keys, not seven.** Seven is an octave only when it starts on a C:
from a D it holds four black keys and the fifth never appears to be aligned. Any eight consecutive
white keys have seven gaps between them and exactly two of those are semitones, so they always hold
all five.

**A placed rectangle comes back where it was left.** Pressing *place the white key* again used to drop
a fresh rectangle at the middle of the picture, throwing away the placement that had just been
accepted. Coming back to a key to check it or move it two pixels is the ordinary case.

**Adding a key back is two buttons, + key left and + key right.** Backspace takes keys off and had no
mirror, which is a gap in two ordinary cases: moving the overlay across leaves a gap at the end it
came from, and trimming one key too many should not need the piano rendered again. Dragging the two
ends of the keyboard as handles was tried first and rejected by the user as useless; the buttons are
what shipped. Adding on the left goes through the same `shiftStart` the trim uses, so the pitch class
and the octave of the leftmost key can never follow one of them and not the other.

**An example always opens on step 1.** The first version jumped an example that already had a
calibration straight to reading it, to save a click. It saved a click and hid where the work starts:
the piano is the first thing to check on a picture you have not seen before, and an example arriving
already on step 2 with an overlay drawn on it says both of those questions are settled.

What was thrown away and should not come back: the strip sheet. Phase 1's own ground truth was read
off a label sheet — the band cut into pieces, piled up and zoomed — and copying it into the app was
the obvious move. It was wrong here: a strip stretches the picture much more across than down, so
anything drawn in it is distorted, and the user has just fitted a piano they can press directly.

**Not built: the timeline in step 3.** The user asked to pick the frame from a timeline and judge the
detector on it. An example screenshot is one frame, so there is no timeline to draw; this is Phase 3's,
where the sampled frames of a video are what the same screen steps through.

### 5.2 The live scale, and the two bugs a guessed one caused

Everything drawn on the picture — a handle, a stroke, a label — has to keep its size **on screen**
while the picture under it zooms. The first version sized them against `imageWidth / 1000`, a guess
at the canvas's width, and it was wrong in two ways that both showed up the moment anyone zoomed in:

- the handles of the placed rectangle grew with the zoom until they covered the whole key they were
  there to size;
- a drag converted the mouse's travel into picture pixels with that same wrong factor, so the shape
  slid away from the pointer instead of staying under it.

`FrameCanvas` now measures itself with `useElementSize` and hands the live scale to its children:
`children` may be a function of it. Measured in a browser: a handle is **9.0 screen pixels at 1.0x
and 9.0 at 10.5x**, and a drag asked to travel 90 × 40 screen pixels moves the shape 90 × 40.

The same fix corrected a third thing nobody had noticed. The canvas draws with
`preserveAspectRatio="xMidYMid meet"` and has a fixed height, so the picture is **letterboxed** more
often than not — and the old mapping from a mouse position to a picture coordinate assumed the
content filled the element. Clicks landed on the wrong row and vertical pans travelled the wrong
distance. There is now one `layout()` helper that both the mapping and the scale come from.

### 5.3 This codebase's ESLint refuses two patterns you will reach for

**`react-hooks/set-state-in-effect`** `react-hooks/set-state-in-effect`
rejects `setState` called synchronously in an effect body, and the React Compiler rules reject
reading a ref during render. So:

- to reset state when a prop changes, keep the previous prop **in state** and compare during render —
  `const [seen, setSeen] = useState(url); if (seen !== url) { setSeen(url); … }`. A ref there lints.
- to load data in an effect, use a promise chain — `api.thing().then(setThing).catch(…)` — not
  `setThing(await api.thing())`. The second reads as a synchronous `setState` to the rule.
- a file that exports a component may not also export a constant (`react-refresh/only-export-components`),
  which is why the palette of these overlays lives in `components/video/overlayColours.ts`.

## 6. The checks, and the baseline for Phase 3

```text
cd aitu-backend
  make test          1 failed, 812 passed        (769 before this phase: 43 new tests)
      the one failure is the known pre-existing
      tests/test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas
  flake8             4 errors, all pre-existing and the same four Phase 1 listed
  mypy              30 errors, all pre-existing, none in anything this phase wrote

cd aitu-frontend
  npx tsc -b         clean
  npm run lint       clean
  npm run check:render     26 passed, 0 failed
  npm run check:geometry   the two services build the same overlay
```

**A note on `make lint`, which Phase 1 could not have seen.** It runs flake8 and then mypy, and
flake8 has failed on four pre-existing errors since before this plan started — so mypy has never run
under it and its **30 pre-existing errors were invisible**. None of them is in `video/`,
`schemas/video.py`, `api/frame_examples.py` or the new tests: those are clean, and they were kept
clean on purpose so the count is a usable baseline. A thirty-first is Phase 3's.

New tests, 43 of them:

```text
tests/test_video_geometry.py    10   the overlay, and the fixture both services assert against
tests/test_video_detector.py    17   the window rule, and the pixels: gaps, splits, width, roll top,
                                     the guard band flag, and the single row watcher losing
tests/test_video_momentum.py     5   fell, static, no neighbour, the aliasing case, the travel vote
tests/test_video_examples.py    11   the store, the router, the score, and V-25
```

Everything that touches the example screenshots is skipped rather than failed when they are missing,
and everything that needs a calibration is skipped rather than failed when the seed has not been run.

## 7. What Phase 2 did not finish, named plainly

**Twenty-one examples have no hand reading.** This is not an oversight and it is not something the
next phase should paper over: the page exists so that a person can read them, and the score board
names each one with the reason instead of counting it. Until they are read, every number in section 1
is a number about two pictures, both of them plain Synthesia with solid rectangles and no halo — the
easiest two of the twenty four.

What that leaves unmeasured, specifically:

- **the five outlined renderings**, which is the only reason the gradient channel exists;
- **the twenty examples with a halo at the upper line**, which is what V-08, V-23 and V-24 are for;
- **`more-examples-3`**, where 34 of 49 runs are lettering — the case the momentum rule was invented
  for, and which one screenshot cannot answer anyway;
- **`airplanes`**, photographed at an angle, where the black keys need the nudge and nobody has yet
  tried to place them by hand;
- **`more-examples-9`**, whose rectangles change colour with their height, which is the case the
  colour check would most likely get wrong.

**Nothing calls the momentum rule yet.** It is ported, tested and on the wire; Phase 3 is its first
caller and its first real test.

**The seeded calibrations are the spike's, not a person's.** Twenty-one of them came from
`find_keyboard.py`, which Phase 1 checked by eye on twenty of twenty one and found wrong on
`airplanes`. They are a starting point that saves the user twenty-one calibrations from nothing, and
every one of them can be replaced in the UI. Re-run the seed with `--force` to go back to them.

**The calibration UI was not timed on an unseen screenshot.** Task 2.1.2 sets a bar of under a
minute. The flow is four gestures and two dropdowns and it was driven end to end in a browser, but a
person has not been timed doing it, because every example already had a calibration to start from.

## 8. How to run it

```bash
cd aitu-backend
uv sync --extra transcription --extra transkun     # pillow is new in the base dependencies
uv run python scripts/seed_frame_examples.py       # Phase 1's calibrations and its two readings
cd .. && make serve                                # http://localhost:5173/video/examples
```

The seed never overwrites work: an example that already has a calibration keeps it, and a reading
already saved at that offset line position is left alone. `--force` replaces both.

```bash
# the score, from the terminal
cd aitu-backend && uv run python -c "
from aitu_backend.video import scoring
b = scoring.board(); print(b.total.model_dump()); print(b.skipped)"
```

## 9. What Phase 3 should know before it starts

1. **Reuse, do not rebuild.** `CalibrationEditor` is Task 3.3.2 whole; `DetectionView` is what the
   detection tab should draw; `FrameCanvas` is the player's surface. All three take a picture URL, a
   width and a height, and nothing else about where the picture came from.
2. **Add the paths to `storage/paths.py` and nowhere else**, beside `frame_examples_root()` which
   shows the shape. The plan's section 5 has the tree.
3. **`sampleMs` is never `frameMs`** (V-04). Nothing in this phase has either; do not introduce a
   name that blurs them.
4. **The plate is `plate.build_plate(frames)`** — the 20th percentile of about 100 frames spread over
   the video (V-29). Pass it to `detect(plate=…)` and the stand-in is not used.
5. **`rollTop` and `guardBand` are fields on the calibration that a screenshot leaves at zero.** A
   video measures both from motion (V-28); `geometry.guard_band_px` falls back to 1.75 white key
   widths when the guard band is zero, and `detect` reads the roll from `rollTop` down. The UI
   already draws both, so a wrong measurement is visible rather than silent.
6. **Wire the momentum rule** as described in 4.2, and report what it drops on a real video — Phase 1
   only ever ran it on three registered screenshots.
7. **Frame to frame agreement (V-31) is the score once there is a video**, and it needs no labelling.
   `poc-synthesia-frames/scripts/continuity.py` is the measurement; it is the thing that found four
   of the five defects in Phase 1's section 11.
8. **Do not score anything at the upper line without saying so.** The numbers there are dominated by
   the halo; the detector's real job is read high in the roll (V-23).
