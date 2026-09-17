# Phase 1 — Research: implementation report

Technical, for the agent that takes Phase 2. The plan is [`04-plan.md`](04-plan.md),
the frozen decisions [`04-decisions.md`](04-decisions.md), the status
[`04-checklist.md`](04-checklist.md).

The work lives in [`../../../poc-synthesia-frames/`](../../../poc-synthesia-frames)
at the repository root. Its [`RESULTS.md`](../../../poc-synthesia-frames/RESULTS.md)
holds every table in full and `out/run_log.txt` is one run of every script. This
report is the argument; that file is the evidence.

Nothing in the spike imports the app, is imported by the app, or writes anywhere
the app reads. No new dependency was needed: numpy, scipy and pillow are already
installed, and ffmpeg and yt-dlp are already required by the project. **OpenCV
did not turn out to be necessary and is not proposed.**

---

## 0. What changed in the plan

Phase 1's job was to challenge section 8 of the plan. Five things changed:

| | plan before | after Phase 1 | why |
|---|---|---|---|
| halo guard band | 12 rows | **1.75 white key widths**, per video | measured 1.73 at the median, 4.14 at the worst; 12 rows is 0.48 |
| thresholds | pixels | **white key widths** | the white key width sets the scale of everything and it is known from the overlay |
| where the tip is read | at the upper line | **high in the roll** | 2.5× more runs per unit height near the line, all of them noise |
| width of a run | not mentioned | **0.35 to 1.40 white key widths** | halves the invented onsets |
| edge of a run | fixed threshold | **0.50 of the run's own peak**, over a local window | finds a third more rectangles; separates a rectangle from its glow |
| lanes | every lane read, then sorted by midpoint | **one key, one lane, one answer** | three lanes see one rectangle and cut it three ways; 23 overlapping runs on one frame |
| the roll | rows 0 to the upper line | **bounded above too, found from motion** | this video has a toolbar and a moving progress bar over the top 58 rows |
| the plate | median of 50 frames | **20th percentile of 100** | the median goes bright where a lane holds a long note, and lays false borders across it |
| splitting a run | not mentioned | **prominence 0.40** | texture reaches 0.13, a real border is 0.75 to 0.80 |
| gapClose | 3 rows, closing six | **2 rows, closing two** | the border between two stacked rectangles is 3 to 7 rows |
| the guard band | deleted the run | **flags the run** | it deleted a legitimate 43 row rectangle and lost a real onset |

Section 11 was written after the user reviewed the first version on a video of
their own, and it rebuilt the detector: five more defects, four of them
structural, all measured. The table above is what Phase 1 changed on the
screenshots; the table in section 11.1 is what section 11 changed on a video.

Nothing in V-01 to V-20 was contradicted except V-15, which asked for the median
of about 50 frames and had to become the 20th percentile of about 100 — the
reason is in section 11.6 and the replacement is V-29. V-05, V-06, V-07 and V-14
were confirmed with numbers. Eleven new decisions, V-21 to V-31, were added.

One thing is **raised, not decided**: whether Phase 4 should follow a rectangle
from frame to frame (Task 4.1.1 as written, and V-07 as written) or stitch the
sampled frames into one long roll and label it once. Section 7 has the
measurement and the picture. It is in front of the user because it touches V-07.

---

## 1. Task 1.1.1 — the survey

### Projects that read a piano roll video

Six were found; the source of the two that document their method was read.

| project | how it reads the notes | why it is or is not usable for us |
|---|---|---|
| [41pha1/MIDI-Converter](https://github.com/41pha1/MIDI-Converter) | one horizontal row of pixels **inside the keyboard**, at 0.85 of the frame height; key centres from bright and dark runs along that row; a key is on when its pixel differs from its own unpressed colour by more than 30 | the single row watcher, on the keys. Dies on every video with hands over the keyboard, which is 17 of our 21 examples. Onsets are quantised to the video frame. |
| [Adelost/piano-video-2-midi](https://github.com/Adelost/piano-video-2-midi) | the same idea with a GUI: the user types the white key row, the black key row, the first C, the octave count, five black key offsets and two activation thresholds, and it samples a small disc at each key centre | same weakness. Confirms V-09 from a different direction: every project that works asks the user to calibrate. |
| [mattstaib/pianoroll_to_midi](https://github.com/mattstaib/pianoroll_to_midi) | per-pixel **median background plate**; per-frame vertical **offset by brute force search**; the top `offset` rows of every frame **concatenated into one long roll**; `skimage.label` + `regionprops` on that; Gaussian mixture colour clustering to drop blobs whose colour is not a note colour | the closest to our plan, and the source of the stitched roll idea in section 7. Its weakness is that it assumes the keyboard is exactly 52 white keys spanning the full frame width, which V-09 replaces. |
| [alborrajo/sheetesia](https://github.com/alborrajo/sheetesia) | Rust + OpenCV, method not documented in the README | not read further |
| [edvein-rin/synthesia-video-converter](https://github.com/edvein-rin/synthesia-video-converter), [minyor/syn2midi](https://github.com/minyor/syn2midi) | listed, not read | |

### The papers

The academic field is called **visual piano transcription**, and it is a
different problem from ours. It reads a **real keyboard** from a top-down video
of a human playing — the key itself tilts and shades when struck — and it needs
a learned model to do it. [Multi-Task Multi-Frame Visual Piano Transcription
(V2N)](https://arxiv.org/html/2608.03419) and [Pay Attention to the Keys: Visual
Piano Transcription Using Transformers](https://arxiv.org/pdf/2411.09037) are
the state of the art; [Automatic Piano Music Transcription Using Audio-Visual
Features](https://cje.ejournal.org.cn/en/article/doi/10.1049/cje.2015.07.027)
tracks the pianist's hands to help an audio model.

None of it applies. They are reading a physical object that barely moves. We are
reading a drawing made on purpose to be read, whose geometry we are given by the
calibration. The problem is far easier and does not need a model.

### The classical toolbox, and what happened to each

| primitive | what it does | verdict |
|---|---|---|
| background subtraction (median plate) | removes everything that does not move | **chosen.** The one thing that removes static decoration. Section 6. |
| connected components / labelling | one shape, one note | **chosen**, in the stitched roll of section 7 |
| span fill per row | makes an outlined rectangle count as filled | **chosen.** Needed by 5 of 21 examples |
| gradient (Sobel) | finds a drawn border, ignores a smooth glow | **kept as a second channel.** The only one that reads an outlined rectangle where the fill is the background colour |
| colour clustering | the biggest cluster is the background | **dropped as a primary.** The slowest, and 4 of 21 examples are grey so it has nothing to cluster. Keep for Task 2.3.4. |
| absolute threshold | brighter than a floor | **dropped.** Works only where the background is one flat colour |
| the single row watcher | read one row above the upper line | **dropped.** Section 4. |
| Canny + Hough, template matching, adaptive threshold | | not tried. Hough finds lines, and the rectangles are found by the lane grid already; template matching needs a template and the whole problem is that there is no one template. |

## 2. Task 1.2.1 — the casuistry catalogue

The measurable half is in
[`RESULTS.md` section 1](../../../poc-synthesia-frames/RESULTS.md). The half a
human has to read is here. All 21 were looked at; the thumbnails are in
`out/thumbs/`.

| example | rectangle | halo | sparkles | decoration in the roll | keyboard | hands |
|---|---|---|---|---|---|---|
| 7years | solid white, rounded | very strong, plus a tall light beam per sustained note | heavy | watermark text | photo, 88 | yes |
| airplanes | soft blue, gradient | glow line across the whole width, plus light beams | at the strike | title text, top right | photo, 88, **at an angle** | yes |
| derulo | solid blue and green | **none** | small burst at the strike | octave guide lines, Synthesia chrome, watermark | drawn, 88 | no |
| feather | gradient, textured | strong bloom, saturates | heavy | watermark text | photo, 88 | yes |
| more-examples-1 | solid orange, rounded | glow line | few | **big title text across the roll**, moon, guide lines | photo, 88 | yes |
| more-examples-2 | solid orange | glow line | heavy | moon, guide lines (the title of -1 is gone: it is animated) | photo, 88 | yes |
| more-examples-3 | solid blue | glow line | few | **title text and white decorative scrolls over roll and keys** | photo, 88 | yes |
| more-examples-4 | **outlined** red | wavy glow line | heavy, comet trails | guide lines | photo, 88 | yes |
| more-examples-5 | gradient orange | glow line | few | title text, scrolls, moon | photo, 88 | yes |
| more-examples-6 | solid gold, gradient | glow line | heavy, comet trails | moon, guide lines | photo, 88 | yes |
| more-examples-7 | **outlined** white | very strong, thick white band | very heavy | moon, guide lines | photo, 88 | yes |
| more-examples-8 | **outlined** blue | glow line | moderate | moon, guide lines; **rectangles cross the upper line and continue over the key** | photo, 88 | yes |
| more-examples-9 | solid, **colour changes with height** (magenta at the top, red at the line) | wavy glow line | heavy | moon, guide lines | photo, 88 | yes |
| more-examples-10 | **shallow**, dim beige, blurred far away | glow line | few | moon, guide lines | photo, 88 | yes |
| more-examples-11 | solid white | almost none across the width, but tall light beams | few | moon | photo, 88 | yes |
| more-examples-12 | **outlined, two colours** (red and cyan: the hands) | wavy glow line | heavy | moon, guide lines | photo, 88 | yes |
| more-examples-13 | solid beige, textured | glow line | moderate | moon, guide lines | photo, 88 | yes |
| more-examples-14 | **outlined** gold, very dense | wavy glow line | very heavy, comet trails | moon, guide lines | photo, 88 | yes |
| not-immediate-strokes | **outlined** white | strong | very heavy, comet trails | faint guide lines | photo, 88 | yes |
| shut-up-and-dance | solid blue and green, two shades | thin red line only | burst at the strike | octave guide lines | drawn, 88 | no |
| superestrella | **not visible** | n/a | n/a | n/a | photo, 72 keys, **no roll at all** | no |

What this table decides:

- **Five of 21 are outlined**, so the span fill of the plan's step 4 is not
  optional.
- **Twenty of 21 have a glow at the upper line.** The one that does not is
  `derulo`, plain Synthesia. This is the whole reason the single row watcher
  fails and the reason for V-23.
- **Seventeen of 21 have hands over the keys.** Any method that reads the
  keyboard instead of the roll is dead on arrival, which rules out three of the
  four projects surveyed.
- **Two of 21 colour the rectangles by hand** (`more-examples-12` and the two
  plain Synthesia ones). V-17 says we never use that, and it stays.
- **One of 21 changes the rectangle's colour with its height** in the roll
  (`more-examples-9`), so the second check of Task 2.3.4 cannot compare a run's
  colour against one fixed palette.
- **`superestrella` cannot be used.** It is a crop of the keyboard with a roll
  0.5 white key widths tall. It should be annotated as "no roll" in Phase 2 and
  left out of the score, not counted as a failure.
- **`airplanes` is the hard one.** The keyboard is photographed at a strong
  angle. The white key grid still fits to 5% (section 3), but the automatic
  finder put the black keys in the wrong place. A user placing the black key by
  hand may well fix it; Phase 2 finds out.

## 3. The piano overlay, and finding it without the user

`find_keyboard.py` was written for the spike's own use — 21 examples had to be
calibrated before any detector could run. It is **not** proposed for the app;
V-09 stands. But what it does and how well it does it is worth knowing, because
Task 2.1.2 has to be fast and the same three steps would make a good suggest
button later.

1. **The keyboard is the only part of the picture that repeats with the
   octave.** Score every row by the strength of its horizontal autocorrelation
   peak; the longest run of high scoring rows is the keyboard, and its first row
   is the upper line. Worked on 21 of 21. The autocorrelation peak is 0.49 to
   0.79.
2. **The octave period divided by seven is the white key width.**
3. **The phase and the pitch class of the leftmost white key come from matching
   the pattern of two and three black keys** against a strip 0.35 to 2.0 white
   key widths below the top of the keyboard — above where the hands are.

Two traps worth writing down, because both cost time:

- **Sliding the overlay right by one white key and naming the next pitch class
  describes the same keyboard.** Searching the offset over a range two white
  keys wide therefore makes all seven pitch class hypotheses equivalent, and the
  margin between the best and the second best comes out at 0.1%, which means
  nothing. Restricting the offset to one white key and grouping hypotheses by
  where they put the first C fixes it: the margin is then **25% to 68%**, on all
  21 examples. That is V-10 measured — the black key pattern really does fix the
  pitch class with no ambiguity.
- **Two white keys are separated by a thin dark line**, so the mean over a
  window at a boundary with no black key is dragged down by it and starts to
  look like a black key. Taking the 75th percentile of the window instead of its
  mean is what makes the pattern score work.

Result: 19 of 21 came out as a whole 88 key piano, A0 to B7 with the top C
cropped off by the screenshot. 20 of 21 look right when the overlay is drawn on
the picture (`out/calibration/`). **`airplanes` has its black keys in the wrong
place**; its autocorrelation peak, 0.49, is the lowest of the 21, so the picture
itself says the answer is weak. A suggest button should report that number and
not offer a suggestion below some floor.

**Is the white key width the same across the picture?** Yes. The octave period
measured separately in the left, middle and right third agrees to within **4% at
the median and 5.2% at the worst**. A plain rectangle grid is enough; Task 2.1.1
needs no perspective. Some of that 3.4% floor is the measurement's own noise.

**Black key mode.** The `boundary` mode — the black key centred on the boundary
between two white keys — is visibly a little left of where a photographed piano
draws it, on `derulo` and `more-examples-14` both. Task 2.1.1's second mode,
the real piano offsets, is needed and its default should be the real one.

## 4. Task 1.2.2 — the five detectors

Full tables in [`RESULTS.md` section 4](../../../poc-synthesia-frames/RESULTS.md).
The short version:

- **The single row watcher, the baseline the plan asked to beat, loses badly.**
  On `derulo` — the only example with no glow — it finds all three onsets and
  invents three, because it has no midpoint attribution and calls the
  neighbouring black key too. On the other eight it calls **every one of the 88
  keys on**, because the row it reads is the row the animation lights. Over the
  two scored examples: 5 onsets found, **56 invented**.
- **Every other candidate finds every onset that is there.** They separate on
  what they invent and on whether they survive a glow.
- **The background plate difference is the one to build on.** It is the only
  mask whose behaviour does not depend on how the rectangle is filled, because
  it does not look at the rectangle — it looks at what changed.
- **The gradient is worth keeping as a second channel** for the outlined styles:
  22 runs on `not-immediate-strokes` against 15 for the plate, and it is the only
  one that boxed the rectangles on `feather` before the relative edge rule.
- **Colour clustering is not worth its cost as a primary** — it is by far the
  slowest, and 4 of 21 examples are grey, so it has nothing to cluster. The idea
  belongs where the plan already puts it, in Task 2.3.4.

Two rules were added, and both are measured:

- **The width gate.** A run whose whole rectangle is narrower than 0.35 or wider
  than 1.40 white key widths is not a note. It halved the invented onsets and
  took the invented sustains to zero. It kills the strike sparkles, which spread
  over two or three keys and are short.
- **The relative edge, `tauEdge`.** The rectangle is the bright part and the
  glow around it is the dim part, so a column belongs to the rectangle when it
  reaches half the strongest column of that run, rather than a fixed threshold.
  Finds **a third more rectangles** (104 → 142) at no cost in attribution. This
  is what made the plate difference able to read `feather` (2 runs → 15) and
  `not-immediate-strokes` (6 → 15).

There is a trap in the run extraction that is easy to get wrong and expensive to
find: **a lane only shows the part of the rectangle that falls inside it.** V-14
attributes by the midpoint of the rectangle, so the rectangle has to be measured
whole, across the lane borders, before the midpoint is taken. Attributing by the
midpoint of what the lane saw puts the same rectangle on three different keys
and invents two onsets per note. Fixing that alone took `derulo` from 10 onsets
to 6, against a truth of 3.

### The finding that matters most

The band right above the upper line is **the wrong place to look**. Counting the
runs the plate detector finds per white key width of band height, on the same
nine examples and the same music:

```text
high in the roll (3 to 8 white keys above the line)   28 runs per key of height
at the upper line (0 to 3.2 white keys)               69 runs per key of height
```

Two and a half times as many, and the extra ones are the halo, the strike light
and the sparkles. Three of the nine examples cannot be read at the upper line at
all — on `feather` the whole band is bloom, and the only run the plate detector
kept there was the channel's watermark.

This does not contradict V-08; it is V-08's constructive form, and it is now
V-23. A rectangle is on the screen for 3.3 s before it reaches the upper line
(section 5), so there is no reason to read it in the one place where it cannot
be read.

### The ground truth, and its limit

`data/ground_truth.json` holds onsets and sustains read by hand off
`out/labels/<slug>.jpg` for `derulo` and `shut-up-and-dance`, applying V-18 word
for word, with the offset line two white key widths above the upper line. Those
two are the only examples where a human can read the picture without guessing.

The label sheet that made it readable is worth copying into Task 2.2.2: the band
between the offset line and the upper line, cut to the part of the width that
has anything in it, zoomed 4×, cut into strips and piled up, with every key's
MIDI number printed — white keys below the line, black keys above it. A human
reading forty empty lanes is a human making mistakes.

One entry in the ground truth is `skip`, and Phase 2 needs the same idea: key 65
of `shut-up-and-dance` has its rectangle entirely past the upper line with the
strike light over what is left, and the picture simply cannot say whether any of
it is still above the line. **An annotation page needs a third answer that means
"the picture cannot say", and those keys have to come out of the score on both
sides** rather than being guessed.

## 5. Task 1.2.3 — the scroll speed. V-05 and V-06 hold

One video downloaded by hand: *Shut Up and Dance*, `Zil8XOMgBQU`, which the
audio library already has and which example `shut-up-and-dance` was
screenshotted from. 1280×720, 60 frames per second, 213.7 s, 9.6 MB, sampled at
10 frames per second into 2136 frames.

```text
usable frame pairs: 1457 of 2135
shift per sampled frame: median 15.84 px, quartiles 15.73..15.91, spread 0.17 px
scroll speed: 158.4 px/s
```

Over ten equal parts of the piece: 15.385, 15.826, 15.841, 15.822, 15.820,
15.847, 15.801, 15.852, 15.851, 15.791.

- **The scroll speed is constant to 0.3% over nine tenths of the piece.** The
  first tenth reads low because it is the intro, where little is falling. The
  median over the whole series outvotes it, so V-06's "the series is stored and
  smoothed" is enough and no special handling of the intro is needed — but a
  Phase 3 that reports the spread must report the median too, or the intro will
  look like instability.
- **It can be measured from a pair of frames.** 1457 of 2135 answered sharply;
  the rest are the quiet stretches, which have nothing to align. Method: the row
  profile of the roll band against the plate, cross correlated by FFT, with a
  parabola fitted to the peak for the part of a pixel. The brute force search
  `pianoroll_to_midi` uses is O(height) full-frame differences per pair and is
  not needed.
- **What the spread costs**: a tip half the roll up, timed with the median speed
  instead of the true one, is 6.4 ms off at the upper quartile and 13.5 ms at
  the 95th percentile. At the very top of the roll, 12.7 and 27.0 ms.
- **One pixel is 6.3 ms.** Placing an onset by the frame it happened in, which
  is what every project surveyed does, costs ±50 ms at 10 frames per second.
  Reading it from the distance costs 6.3 ms per vote. **V-05 is worth an eight
  fold improvement, measured.**
- **A rectangle is on the screen for 3.3 s before it reaches the upper line —
  33 sampled frames.** V-07's "twenty or thirty independent estimates" is right.

### Disk, for Phase 3

```text
video                      9.6 MB      (213.7 s, 720p)
frames at 10 per second   118   MB     (2136 frames, JPEG quality 3)
```

**The frames cost twelve times the video**, 33 MB per minute of music. Sampling
took 3.8 s of wall clock for 3.6 minutes of video. Downloading took 3.6 s. This
is the number behind V-01.

### yt-dlp, for Phase 3

The format that came down was **AV1** (format 398 + audio 140), not H.264. Ask
for `bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]` and
that is what YouTube serves. ffmpeg decoded it without complaint.

yt-dlp printed three warnings about a JavaScript challenge it could not solve
and about formats that may be missing. The download worked anyway. Phase 3's
"errors are surfaced word for word" has to not treat these warnings as errors.

## 6. The background plate. V-15 holds

The plate is the per-pixel median of 50 frames spread over the video. In it, the
octave guide lines of *Shut Up and Dance* show at x = 76, 348, 619, 890, 1162 —
five lines, 271 px apart, which is seven white keys, exactly one octave. The
plate finds them without being told they exist.

Over 300 sampled frames in the middle of the piece, with the offset line set to
one sampled frame of travel:

```text
stand-in (the per-row median of one screenshot)   11.8 onsets per second
real plate (the median of 50 frames)               8.6 onsets per second
```

**The real plate removes 27% of what the stand-in reports.** So every score
measured on the screenshots is a floor, not a ceiling, and the invented onsets
that survive there are all static decoration and all the stand-in's fault.

A note on the offset line that Phase 3 needs. On a screenshot it is a free
parameter and the user drags it, which is the point of Task 2.2.2. **On a video
it is not free: it is the measured scroll speed times the sampling
granularity.** Set it to two white key widths instead, as the annotation used,
and every onset shows up in five consecutive frames — the onset rate jumps from
8.6 to 29.9 per second. This is V-25.

## 7. The stitched roll — raised, not decided

If the scroll speed is stable, the top 16 rows of each sampled frame are exactly
the strip of the roll nobody has seen yet, so piling them up rebuilds the whole
piece as one tall picture whose vertical axis is time. The strip is taken 40
rows down from the top of the frame, as far from the upper line as it gets, so
**there is no halo, no sparkle and no strike light in it at all.**

[`out/stitch/roll.jpg`](../../../poc-synthesia-frames/out/stitch/roll.jpg) is
ten seconds of the piece rebuilt that way. Every note is one clean separate
shape. Thirty seconds of it, labelled with connected components:

```text
30 s of music, 4800 rows, 268 shapes, 268 kept after dropping specks
notes per second: 8.9
width  in white key widths: median 0.62, 5th..95th 0.62..1.03
length in ms:               median 145, 5th..95th 95..292
distance from the nearest key midpoint, in white key widths:
                            median 0.067, 95th 0.157, worst 0.170
shapes whose midpoint is more than a quarter key from any key: 0 of 268
```

- **Not one shape had to be thrown away.** Every connected component in 30 s of
  music is a note.
- **The widths are the two widths a piano has**: 0.62 is a black key rectangle,
  1.03 a white key one, and nothing falls outside.
- **V-14 is confirmed with a number.** Every one of the 268 shapes sits within
  0.17 white key widths of a key midpoint, and the nearest wrong key is half a
  key away, so attribution has a margin of 0.33 white key widths on every note.
- 8.9 notes per second agrees with the 8.6 the per-frame detector reported, by a
  completely different route.

**What it would replace.** Task 4.1.1 as written follows a rectangle from frame
to frame and V-07 takes the median of its votes. The stitched roll measures each
rectangle once, in a picture where the measurement is easier, and the three
awkward cases Task 4.1.1 names stop being cases at all: a rectangle that appears
already crossing is just a shape that starts at the bottom edge; two notes on
the same key with a small gap are two shapes with a gap between them, which is
visible in the picture above; a rectangle taller than the roll band is one shape,
because the stitched roll has no band.

**What it costs.** It commits to one scroll speed for the whole piece. V-06
already refuses a video whose speed is not stable, and 0.3% over nine tenths of
the piece is well inside what a stitch tolerates, but on a video that fails that
test there is nothing to fall back to except the per-frame tracker.

**It touches V-07 in letter.** V-07 says every rectangle is measured in every
frame it appears in and the note is the median vote. A stitched roll uses every
frame — each contributes 16 rows — but it measures the rectangle once. That is
why this is raised rather than adopted. **The plan's section 8 still describes
the per-frame path,** so Phase 2 and Phase 3 are unaffected either way: nothing
before Phase 4 depends on the answer.

## 8. What Phase 2 should know before it starts

1. **Build the geometry module against these numbers.** White key width 24.6 to
   38.7 px at 1280 wide, depending on how many keys the video shows. Black key
   width 0.58 of a white key. Roll height about 12 white key widths. Default the
   black key mode to the real piano offsets, not to the boundary.
2. **Every geometric threshold in white key widths** (V-22). The examples are
   3600 px wide screenshots and the videos are 1280; a pixel threshold measured
   on one is wrong on the other, and `detectors.py` is written that way already.
3. **Copy the label sheet.** `label_sheet.py` is what made the ground truth
   readable, and Task 2.2.2's page needs the same: cut to the busy part of the
   width, zoom, strips piled up, MIDI numbers on both rows.
4. **The annotation page needs a "the picture cannot say" answer**, and those
   keys come out of the score on both sides.
5. **`superestrella` has no roll and `airplanes` is at an angle.** Expect them to
   be the two the exit criteria has to name.
6. **The detector is `detectors.py`** — the plate difference, lanes with a 0.25
   margin, span fill, coverage, gap close, minimum height, full extent against
   `tauEdge`, the width gate, attribution by nearest midpoint, the clip rule,
   then V-18. It is a research spike and not production code, but the order of
   the steps and the thresholds are the measured ones and it should be ported
   rather than rewritten from the prose.
7. **Do not score anything at the upper line without saying so.** The numbers
   there are dominated by the halo. The detector's real job is read high in the
   roll; the frame window rule at the line is a check of the rule, not of the
   detector.

## 9. What was not done

- **`airplanes` was not fixed.** The automatic finder puts its black keys in the
  wrong place and the spike did not hand correct it, so it is in the catalogue
  and in the halo and uniformity measurements but not in the nine examples the
  detectors were run on.
- **The ground truth is two examples, not nine.** Reading onsets and sustains by
  eye off a picture is slow and the other seven have a halo over the band where
  the answer is. That is Phase 2's job, with a page instead of a JPEG.
- **Task 2.3.4's second check was not tried.** The catalogue says what it has to
  cope with — 4 of 21 examples are grey and 1 changes the rectangle's colour with
  its height — but no number was measured, because it needs the score board.
- **No timing of a whole video through the detector.** Phase 3 Task 3.5.1 asks
  for the wall clock of a four minute video and the spike only timed the pieces:
  download 3.6 s, sampling 3.8 s, the plate 50 frames, the scroll speed over 2135
  pairs 17.6 s.

## 10. The checks, and a baseline the next agent will need

Phase 1 touched no application code at all: `git status` on `aitu-backend` and
`aitu-frontend` is empty. Everything it wrote is under `poc-synthesia-frames/`
and in this folder. The checks were still run, and this is the state they are in
**before** Phase 2 starts:

```text
cd aitu-backend && make test    1 failed, 769 passed
    FAILED tests/test_time_score_payload.py::
           test_the_worked_example_at_00_46_prints_three_equal_corcheas
cd aitu-backend && make lint    4 errors, all pre-existing
    src/aitu_backend/transcription/events_to_matrix.py:68:1: E402
    tests/test_time_matrix_build.py:177:1:        W391
    tests/test_time_score_payload.py:331:1:       W391
    tests/test_transcription_leakage.py:267:1:    W391
cd aitu-frontend && npm run lint  clean
```

The one test failure is the known pre-existing one the plan names. **The four
lint errors are also pre-existing and the plan does not name them**, so they are
written down here: a fifth is Phase 2's, the first four are not.

`make lint` runs flake8 over `src` and `tests` in `aitu-backend` only, so it does
not see `poc-synthesia-frames/`.

---

## 11. Added after the phase closed: the detector was rebuilt

The user looked at a frame of a video where the left hand plays repeated notes
and asked two things: whether the detector would separate rectangles that touch,
and for a picture of what it was doing. Both answers were no and yes. Building
the picture exposed four defects, three of them structural, and the detector was
rebuilt. This section is the account.

**The test video.** `poc-synthesia-frames/data/video/test.mp4` — 90 seconds of
[pgLt4WmPMYQ](https://www.youtube.com/watch?v=pgLt4WmPMYQ), 1280x720, sampled at
10 frames per second into 900 frames in `frames_test/`. Whole 88 key piano, A0 to
C8, 52 white keys, upper line row 561, white key width 24.57 px, black key
pattern margin 224 against 157. Scroll speed **168.9 px/s**, one pixel is
**5.92 ms**, a rectangle is on screen 3.3 s — 33 sampled frames — before it
reaches the upper line. The Synthesia toolbar states **128 BPM**, which makes a
semicorchea 19.8 px and a negra 79.2 px, and those are the numbers the detected
heights are checked against.

### 11.1 The score, before and after

```text
                                    onsets                sustains
                              found invented missed   found invented missed
the two hand read screenshots
  before this section             5        7      0       3        1      0
  after                           5        0      0       3        0      0

test.mp4, frame to frame agreement over 120 sampled frames
  before                       90.6%
  after                        98.2%
```

### 11.2 The measurement that made it possible

There is no hand labelling that scales to a whole video, and the complaint —
"the same rendering, split here and merged there" — is not something a per-frame
score catches. The video catches it for free. **A rectangle falls by exactly the
scroll speed between one sampled frame and the next**, so a run at rows y0..y1
must reappear at y0+s..y1+s with the same height. A run that does not is a run
the detector cut two ways on two pictures of the same rectangle.

`continuity.py`. No labels, runs over the whole video, and it is what every
threshold below is tuned against. It is now V-31.

Two kinds of run are left out of the count because both are supposed to change
shape: one about to be cut by the upper line, and one still coming into view at
the top of the roll. Leaving the second one out was not obvious — the first
version of the metric read 61% and the dominant failure was `dTop = -16.9`,
exactly one frame of travel, which turned out to be rectangles growing downward
as they came into view, not detector errors. **A metric that has not been
debugged is not a measurement.**

### 11.3 Defect one — three answers about one rectangle

A rectangle is visible from its own key's lane and from the lanes either side.
The first version read every lane and then gave each run to the nearest key
midpoint. That looks like V-13 and V-14 but it keeps three answers about one
rectangle, and because each lane produces a different brightness profile, the
three disagree about where to cut.

On frame 629, key G2 carried a merged run of 159 rows **on top of** the four
correct ones, and 23 pairs of runs on the same key overlapped. Drawn on the
picture that is a big box around three rectangles with the right boxes inside
it — exactly what the user saw.

The fix is structural: **the lane of a key is read once, for that key**, and
V-14 becomes a filter — a run centred nearer another key is dropped here,
because that key's own lane will find it. Two runs on one key can no longer
overlap, because they come from one profile. Now V-27.

### 11.4 Defect two — the edge search took its peak over the whole picture

`_full_extent` finds where a rectangle stops and its glow starts by comparing
each column against `tauEdge` of the run's peak. It took that peak over **the
whole image width**. So the brightest column in those rows — some other key's
strike flash — set the bar, this key's own columns failed it, and the search
then walked off to whatever column did pass. On frame 629 that put a run near
the upper line on a key four semitones away, at x 261 instead of x 372.

The peak is now taken over a window of `extentWindow` = 2.0 white key widths
either side of the key, and a run whose own centre is not part of anything
bright is dropped rather than relocated.

### 11.5 Defect three — the roll has a top, and this video has chrome

`test.mp4` carries a Synthesia toolbar over rows 0-28 and a **progress bar with
a sliding playhead** over rows 29-58. The roll only begins at row 62. The plan
had no roll top at all; the detector was reading the chrome.

Finding it needs a cue that cannot be fooled by what the chrome looks like, and
there is a perfect one: **the roll scrolls and nothing else does.** For every
row, does the next sampled frame look like this row moved down by one frame of
travel, or like it did not move at all. `roll_top.py`. The score is −0.5 to −1.0
through the chrome, crosses zero at row 60, and sits flat at +0.30 through the
whole roll.

The same measurement gives the other edge for free: the last 39 rows before the
upper line do not move either, because that is the strike light. So it measures
the halo guard band of V-24 per video instead of defaulting it — 39 rows, 1.59
white key widths on this video. Now V-28.

### 11.6 Defect four — the plate was eating held notes

This is the one behind "lots of false rectangles for D#3". Lane D#3 holds one
long note. Against the plate it came back as three or four stacked rectangles
cut at rows that **never moved between frames** — the signature of static
content.

The plate itself was the static content. V-15 says the per-pixel median of about
50 frames. That lane is lit in more than half the frames at 21 of its 499 rows,
so the median of those pixels is the note: the plate goes blue in bands, the
difference against it is small exactly there, and the detector sees dark bands
across a held rectangle and cuts at them.

More frames do not fix it on their own and neither does picking them at random —
the rows really are lit most of the time. Asking for a lower percentile does:

```text
plate                          agreement   runs/frame
median of 50 frames   (V-15)       90.6%         29.7
median of 100                      97.6%         28.7
median of 200                      98.3%         28.6
20th percentile of 50              98.5%         28.0
20th percentile of 100             98.8%         28.0
20th percentile of 400             98.8%         28.0
```

Both routes fix it independently and together they plateau at 100 frames. The
plate is now **the 20th percentile of 100 frames**. Now V-29.

This assumes the rectangles are lighter than the roll behind them. That is true
of all 21 example screenshots and both videos; a rendering that drew dark notes
on a light roll needs the percentile from the other end, and the way to tell is
which way a frame differs from the plate.

### 11.7 Defect five — a rule that deleted notes

The halo guard band was written as a deletion: a run inside it is not a note. It
cost a real onset. On `shut-up-and-dance` the rectangle is 43 rows tall and the
guard band is 68, so a whole legitimate rectangle sat inside the band and
vanished — the one missed onset in the score board.

V-08 says the tip inside the band is extrapolated rather than read. That is a
**flag on the run, not a reason to throw the run away**. What removes the light
is the width gate and the minimum height, which a halo blob fails anyway. Now
V-30, stated generally: a rule may flag a run, it may not quietly delete one.

### 11.8 The gap, and the split rule that replaced the first one

The original question. Two notes in a row on one key are drawn as two rectangles
touching, with nothing between them but their own dark borders.

`measure_gaps.py`, every lane of 60 sampled frames, 5767 gaps recorded before
anything is closed:

```text
gap rows  count
       1    732     texture and anti-aliasing inside one rectangle
       2    195
       3    179  |
       4    144  |  the border between two rectangles stacked on one key
       5    360  |
       6    495  |
       7    173  |
   8..15    211
     >15   3278     different notes, far apart
```

`_close_gaps` was `binary_closing(flags, structure=np.ones(2 * gap + 1))`. A
closing with a structure of length L closes every gap shorter than L, so
`gapClose` 3 closed **six** rows and merged all 1351 separators in that sample.
The structure is now `gap + 1` and `gapClose` is 2.

Where the border never drops below `tauForeground` the run stays in one piece
and no gap rule can help. The first attempt cut where a row fell below a share
of the run's median. That was the wrong shape of rule and the measurement says
why: on key G2 the plateau is 144 and the borders drop to 36, while on key A#2
the plateau is 88 and the texture inside a **single confirmed quarter note**
ripples down to 72. A share of the median cannot separate those.

**Prominence can.** How far a local minimum drops below the plateau on both
sides of it, as a share of that plateau. Measured on lanes whose content was
read off the pixels by hand:

```text
                                        prominence
texture inside one rectangle            0.01 to 0.13
the border between two rectangles       0.75 to 0.80
```

`splitProminence` is 0.40, in the middle of a gap with a factor of three of
margin on each side. Key G2 splits into four 40-row eighth notes at every
threshold from 0.20 to 0.55, so the answer is not delicate.

**And it says no when the answer is no.** The 78-row run on A#2 at 1:03 looked
like two eighths merged. Its rows are flat from 374 to 446 with no border at
all: it is one negra, 79.2 px at 128 BPM. The detector had it right and the
first reading of it — mine — was wrong.

### 11.9 What the numbers look like now

```text
key G2  at 1:03   (113,152) (153,192) (193,232) (233,271)
                  four rectangles of 40 rows = four corcheas at 39.6 px
key A#2 at 1:03   (267,287) (292,312) (313,371) (372,449) (450,528)
                  21, 21, 59, 78, 79 rows = 1, 1, 3, 4, 4 semicorcheas
key D#3 at 0:11.5 (63,300)
                  one held note of 238 rows, not four fragments
```

### 11.10 The inspection UI

`export_ui.py` writes `out/ui/detection.json` and five sampled frames, with the
piano overlay, every lane, and every run, exported twice — against the plate
V-15 first described and against the measured one. The page draws them on the
frame, pans and zooms, and lists the runs of any lane that is clicked with the
gap above each one, its length in milliseconds and in semicorcheas, and whether
it is still entering, has crossed the line, or has its tip in the guard band.

It is a review surface for the human, not a step toward Phase 2's UI. What Phase
2 should take from it is the shape: **a run is only believable when you can see
it drawn on the pixels it came from**, which is Task 2.3.2, and the lane
inspector's table is the readout that makes a wrong answer obvious. Every one of
the five defects above was found by looking at that page or at a crop built the
same way.


---

## 12. Added after section 11: the momentum rule, and Phase 4 decided

### 12.1 Phase 4 is the stitched roll

The user chose the stitched roll over the frame to frame tracker, accepting the
memory. V-07 is replaced by **V-32**, Task 4.1.1 and 4.1.2 are rewritten, and
section 8 steps 15 and 16 of the plan describe it. It is also the cheaper of the
two: one strip per frame instead of the whole roll, about a thirtieth of the
pixel work, and one labelling pass instead of tracking. A four minute video
stitches to about forty thousand rows, roughly 50 MB as one grey picture.

### 12.2 The momentum rule — V-33 and V-34

Prompted by `more-examples-3`, where **34 of 49 runs are lettering**: a song
title and decorative scrollwork drawn across the roll look exactly like
rectangles to a detector that only sees one picture. The user proposed the rule
and it is right: a rectangle falls and a letter does not.

Tested on `ode1`, `ode2`, `ode3`, three frames of *Ode to Vivian* the user
supplied. `ode_momentum.py`, and the page is built by `export_ode_ui.py`.

Three things had to be got right, and each was got wrong first:

1. **The frames are not aligned.** They are screenshots cropped differently —
   upper lines at rows 423, 426 and 424. They are registered on the keyboard,
   which is the static part, before anything is asked of the roll. On a real
   video this step does not exist.
2. **The travel cannot be correlated from the pictures.** The title is drawn in
   letters a hundred pixels tall across the middle of the roll; any correlation
   that still contains them peaks at a shift of nothing, because the letters
   really did not move. The first attempt answered **0 px**. The rectangles vote
   instead — the travel is the shift at which the most of them line up, with a
   shift of nothing excluded on purpose. **68 px** for the first pair and **51**
   for the second: the three are not evenly spaced, so one number would have
   been wrong too.
3. **A repeated note aliases.** When a key is struck twice and the strokes are
   about one frame of travel apart, the first stroke's rectangle sits, in the
   frame before, exactly where the second stroke's rectangle sits now, so the
   second stroke looks static. The frames are matched **one to one**, best fit
   first: a rectangle already spoken for as the predecessor of the rectangle
   below is not evidence that anything stood still. This is V-34, and the user
   spotted the case before the measurement did.

**The rule refuses, it does not select.** Only a run proven static is dropped; a
run with no neighbour to ask is kept.

```text
policy                                runs dropped   real rectangles lost
drop the proven static (chosen)          42 of 174                      0
keep only the proven moving             128 of 174                     28
one to one off, drop proven static       43 of 174                      1
```

**The check is independent of the rule.** The rectangles of that piece are blue
and its title and scrollwork are white, so the colour of a refused run says
whether the refusal was right. Median blue-minus-red is 118 to 148 over the runs
that fell and **0 over every one of the 42 refused**; not one refused run is
blue. Colour checks the rule and never decides anything (V-17).

Slack when matching is **5 px**, measured: at 3 the vote is stable but a few real
notes are missed, at 7 it collapses onto the static content because that much
slack lets a letter match itself at a small shift.

The grey bucket — no neighbour to ask — is 86 of 174 here, and 28 of those are
real rectangles. That is a property of the sample, not of the rule: these frames
are 51 and 68 px apart while a rectangle is about 40 px tall. A video sampled at
10 frames per second travels about 17 px and a rectangle is on screen for 33
frames, so almost every rectangle has a neighbour, grey becomes rare, and the
room for aliasing shrinks with it.

### 12.3 Where the pages are

Three inspection pages were published for the user, all built from
`poc-synthesia-frames/out/ui*`:

- the five frames of `test.mp4` with the rebuilt detector,
- `more-examples-3` alone, which is where the lettering problem was seen,
- the three `ode` frames with the momentum rule's verdicts.

Phase 2 should build the real one into the app as Task 2.3.2 asks. What these
prove is the shape it needs: the runs drawn on the pixels they came from, a lane
inspector that lists rows, width, gap and verdict, and a switch between two
settings so a change can be seen rather than argued about. **Every defect in
sections 11 and 12 was found by looking at one of these pages.**
