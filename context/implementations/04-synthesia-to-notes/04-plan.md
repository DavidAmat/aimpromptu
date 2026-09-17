# 04 — Synthesia to notes: implementation plan

Read the prompt this plan answers first: [`04-prompt.md`](04-prompt.md). The frozen decisions of
this plan are [`04-decisions.md`](04-decisions.md), V-01 to V-34. The status lookup is
[`04-checklist.md`](04-checklist.md).

Phase 1 is done: its report is [`04-phase-1-implementation.md`](04-phase-1-implementation.md) and its
work is in [`../../../poc-synthesia-frames/`](../../../poc-synthesia-frames). Phase 2 is done: its
report is [`04-phase-2-implementation.md`](04-phase-2-implementation.md), and its work is in the app
— `aitu-backend/src/aitu_backend/video/` and the Video to Notes section of the frontend. Phase 3 is
done: its report is [`04-phase-3-implementation.md`](04-phase-3-implementation.md), and a real
4.5 minute Synthesia video now goes from a URL to `frames.jsonl` — 168.9 px/s measured, 1755 onsets,
and frame to frame agreement of 97.1%. Phase 4 is done: its report is
[`04-phase-4-implementation.md`](04-phase-4-implementation.md), and that same video is now a piece —
the stitched roll reads 4295 notes off it and `events.json` goes through the hand split, the matrix,
the peaks, the ladder and the sheet with no special case anywhere. A second rendering — a roll drawn
over a photograph — then broke the plate, the roll bounds and the scroll speed; the study is
[`04-second-rendering-study.md`](04-second-rendering-study.md), its rules are built (V-44 to V-46),
and that video reads 1492 notes with 98.7% of the keyboard's strikes found.

## 1. What we are building and why

Today a piece enters the app as audio and a model from ByteDance guesses the notes. The model is far
from perfect: it invents notes, it misses high pitches, and pedal blurs one note into the next. For
one whole family of YouTube videos we do not have to guess at all. A piano roll animation — the
Synthesia kind, where rectangles fall from the sky onto a keyboard — already shows every note, every
start and every release, drawn on purpose to be read.

So for those videos we read the picture instead of listening to the sound. We download the video,
sample its frames, find the falling rectangles, and work out for every key when it is struck and how
long it sounds. The output is the same `events.json` the model writes, so the whole app after that
point — the hand split, the matrix, the peak plot, the ladder, the sheet — is untouched (V-02).

Out of scope in v1: finding the keyboard without the user, reading hands from the colours of the
rectangles, any learned model, any cloud service, and any video where the keyboard moves.

## 2. Terminology

The words of the prompt, used with one meaning each. New work uses these words and no synonyms.

- rectangle: the falling shape that stands for one note. It may be solid, shallow, outlined,
  gradient filled or shining.
- rectangle tip: the lowest side of a rectangle, the one that reaches the piano first.
- last rectangle tip: the opposite side, the one that tells us when the note stops sounding.
- upper line: the horizontal line at the top of the piano. A rectangle tip crossing it is an onset.
- offset line: a second horizontal line above the upper line. The distance between them is how far
  the rectangles fall in one time frame, so the two lines together describe one window of time.
- piano overlay: the SVG keyboard the user fits on top of the piano in the picture.
- vertical lane: the strip of the picture that belongs to one key, from the left border of that key
  to its right border, widened by a margin, and cut at the upper line.
- onset, sustain, released: what a key is doing inside one time frame. Released is the default and
  is never written down (V-19).
- sampled frames: the pictures we take out of the video, at the sampling granularity.
- sampling granularity (`sampleMs`): how often we look at the video. Not `frameMs` (V-04).
- scroll speed: how many pixels the rectangles fall per second.
- halo: the light the animation emits at the upper line when a key is struck.
- sparkles: the small shining particles some animations emit when a note is released.
- piano matrix notation: what the app already uses — onsets and sustains per key over time.

## 3. What already exists and is reused

- `POST /youtube/download` downloads the audio of a video with yt-dlp and ingests it, giving an
  audio uuid. Phase 3 adds the video beside it, on the same uuid (V-03).
- `data/audio/<uuid>/matrices/events.json` is the piece. `transcription/pipeline.py` owns the
  writer and the reader. Phase 4 writes through it.
- `storage/paths.py` owns every path. Every new folder is added there and nowhere else.
- The hand split (`hands/`), the matrix (`matrix/`), the figures (`notation/`) and the sheet all
  read `events.json` and need no change.
- The frontend has an 88-key piano in `src/piano/`, with programmatic geometry in `keyPositions.ts`.
  The piano overlay is a second, calibratable geometry; it does not replace this one. Since
  implementation 05 the overlay is per-key borders found inside one rectangle, not a grid.
- `make serve` runs both services, `make test` in `aitu-backend` runs the suite: 853 pass after
  Phase 3 and one failure that is already there before this plan starts. See
  [`../../04-local-development.md`](../../04-local-development.md).

New dependencies, kept small on purpose: `pillow` for reading and writing frames, and `scipy`
which is already installed for the labelling and filtering the detector needs. `ffmpeg` is already
required by the project and does the frame sampling. **OpenCV is not needed.** Phase 1 built the
whole detector on numpy and scipy and measured it; the finding is in
[`04-phase-1-implementation.md`](04-phase-1-implementation.md) section 1. Phase 2 declared `pillow`
in `pyproject.toml`; everything else was already there.

Phase 2 added, and Phase 3 reuses rather than rebuilds:

- `aitu_backend/video/` — the overlay geometry, the plate, the detector, the momentum rule, the
  colour check, the example store and the score board. `detect()` takes a picture, a calibration and
  one offset line; it does not know whether the picture is a screenshot or a sampled frame.
- `aitu_backend/video/images.py` — every picture is read at one width, 1280, and the browser is
  served that same copy, so a coordinate means the same thing in the UI and in the detector.
- `aitu-frontend/src/components/video/` — the zooming canvas, the calibration editor, the piano
  overlay, the annotation page and the detection view, none of which knows what an example is.

## 4. The shape of the work

```text
video in ──▶ sampled frames ──▶ piano overlay + upper line (the user calibrates)
                                  │
                                  ├─▶ background plate, one per video
                                  ├─▶ per vertical lane: runs, rectangle tips, last rectangle tips
                                  ├─▶ scroll speed, per frame pair
                                  ├─▶ tracks: one rectangle followed across frames
                                  └─▶ events.json  ──▶ everything the app already does
```

Two files describe the middle of it.

`frames.jsonl` — one line per sampled frame, the simplified notation the prompt asks for. It is the
readable record of what the detector saw and the thing the manual annotation is compared against.

```json
{"t": 12.300, "onsets": [60, 64], "sustains": [48, 55]}
```

`calibration.json` — the piano overlay, the upper line, the halo guard band, the sampling
granularity and the measured scroll speed. It is kept beside the video (V-12).

## 5. Storage

Added to `storage/paths.py`, nowhere else.

```text
data/audio/<uuid>/
  metadata.json                  unchanged
  original.mp3                   unchanged: the audio of the same video
  matrices/events.json           the piece — what Phase 4 writes
  video/
    source.mp4                   the downloaded video (V-01), the audio came out of this file
    metadata_video.json          size, duration, frames per second of the source
    calibration.json             the piano overlay and everything measured from it
    frames/f000001.jpg …         the sampled frames, derived, gitignored
    frames.jsonl                 onsets and sustains per sampled frame, derived
    notes.json                   the notes the stitched roll read (V-32), derived
    corrections.json             what a person changed before the piece was written
    detection/                   debug pictures, only when asked for, gitignored
data/frame-examples/<slug>.json  the manual annotation of one example screenshot
```

The example screenshots stay where the user put them,
[`examples/`](examples), and are read from there. Only the annotations are data.

## 6. The HTTP surface

One new router, `/video`, plus a small one for the example set. Shapes are camelCase on the wire,
like every other router.

- `POST /video/download` — url in, audio uuid out. Downloads the audio through the path that already
  exists and the video beside it.
- `GET /video/{uuid}` — what we have: duration, sampling granularity, how many sampled frames.
- `POST /video/{uuid}/sample` — sample the frames at a sampling granularity. A job with progress,
  like transcription.
- `GET /video/{uuid}/frames/{index}` — one sampled frame, as an image.
- `GET` and `PUT /video/{uuid}/calibration` — the piano overlay and the upper line.
- `POST /video/{uuid}/detect` — run the detector over every sampled frame, write `frames.jsonl`.
  A job with progress.
- `POST /video/{uuid}/notes` — stitch the whole video into one picture and read the notes off it
  (V-32). A job with progress. It does **not** write the piece; it writes what *will* be written.
- `GET /video/{uuid}/notes` — that reading, and the numbers behind it.
- `GET` and `PUT /video/{uuid}/corrections` — the notes a person took off or put on by hand.
- `POST /video/{uuid}/events` — turn the reading into `events.json`. This is the step that
  changes the piece, so it advances the music version.
- `GET /frame-examples` — the example screenshots.
- `GET` and `PUT /frame-examples/{slug}` — the calibration and the manual annotation of one example.
- `POST /frame-examples/{slug}/detect` — run the detector on that one example with that calibration.
- `POST /frame-examples/score` — run all of them and report the score.

## 7. The screens

A new top section, Video to Notes, with five tabs, in the order of the work. Phase 2 built Examples
and the calibration UI behind it, Phase 3 built Video, Calibration and Detection, and Phase 4 built
Notes.

- Video — paste the URL, download, then the video player: spacebar plays, the arrows step one
  sampled frame, a progress bar in mm:ss that can be dragged.
- Calibration — the piano overlay on a chosen frame: zoom, drag one rectangle over the piano area,
  and every key inside it is found (implementation 05, V-37); then the octave and the upper line.
- Detection — run it, see what it found, and step through the frames with the found rectangles drawn
  on top. This is the per-frame reading: what the picture showed at one moment, which is what a hand
  reading is compared against.
- Notes — stitch the whole video into one picture, read the notes off it, see every note put back on
  the frame its rectangle is in, correct what is wrong, then write the piece.
- Examples — the example screenshots, the manual annotation page, and the score board.

Routes are declared in `layout/routes.ts` with everything else. Nothing hardcodes a URL.

## 8. The algorithm

Phase 1 measured this and replaced the parts measurement did not support. Every number below has a
measurement beside it in [`04-phase-1-implementation.md`](04-phase-1-implementation.md) and in
[`../../../poc-synthesia-frames/RESULTS.md`](../../../poc-synthesia-frames/RESULTS.md). The five
things Phase 1 changed are marked **new** or **changed**.

Per video, once:

1. Background plate: **the per-pixel median of what stands still** (V-44), over about 150 frames
   spread over the whole video, each read with its two neighbours either side. A pixel counts only
   where it did not change across those neighbours, so no moving edge is on it; a frame whose roll
   changed on fewer than 0.2% of its pixels is a rest, a card or an end screen and is left out.
   **Changed** from the 20th percentile of 100 frames (V-29), which assumed the rectangles are
   lighter than the roll: on a roll drawn over a photograph a blue rectangle is darker in red and
   green, the percentile took the rectangle's colour in those channels, and the lanes of the three
   most played keys inverted — 3174 of the 4967 notes that reading invented were on them. Measured
   against the keyboard of that video: 4967 notes and 68% of them not shown before, 1492 and 6.5%
   after; and on the plain video the same 4295 notes as before. The full study is
   [`04-second-rendering-study.md`](04-second-rendering-study.md).
2. Scroll speed: **the rectangles' own fall** (V-45). Every run of a sampled frame is followed into
   the next frame, one to one, and the fall of every free edge is collected; the per-pair mean is
   the series V-06 asks for and the mean over every followed edge is the answer. **Changed** from
   the cross correlation of row profiles, which on the photograph was pulled by the light swirls
   and the glow band — things that move, but not with the roll — and answered 6 usable pairs of
   1891. Measured on it: 48 396 followed edges, 20.22 px per frame, the same to 0.05 px in each
   third of the piece. On the plain video 168.9 px/s stays 168.9.

Per sampled frame:

3. **New.** The roll is bounded above as well as below. A video may carry a toolbar, a progress
   bar, a title band or a letterbox over the top of the picture, and nothing above `rollTop` is
   music. It is found from motion, because the roll scrolls and the chrome does not: for every row
   **of the plate difference**, does the next sampled frame look like this row moved down by one
   frame of travel, or like it did not move at all. The roll top is the first row from the top where
   moving wins; the halo guard band is the rows above the upper line, read upward, until it wins.
   **Changed by the second rendering**: on the raw picture every row of a photograph looks still,
   and the answer was a guard band of the whole roll. On the test video: roll top 62, upper line
   561, guard band 39 rows, which is 1.59 white key widths; on the photograph 56 rows, 1.82.
4. Foreground: the absolute difference between the frame and the plate, collapsed over the colour
   channels; a pixel is foreground above `tauForeground`. The difference is kept as a number, not
   only as a yes or a no, because the edge step needs how strong it is. Only rows between `rollTop`
   and the upper line are read.
5. **Changed.** One key, one lane, one answer. The lane of a key is read once, for that key, and
   V-14 becomes a filter rather than a sorting step: a run found in this lane whose rectangle is
   centred nearer another key is dropped here, because that key's own lane will find it. Reading
   every lane and then sorting by nearest midpoint looked like V-13 and V-14 but was wrong — the
   same rectangle is visible from three lanes, each lane cut it into pieces differently, and every
   version survived. On one frame of the test video key G2 carried a merged run of 159 rows on top
   of the four correct ones, and 23 pairs of runs on the same key overlapped. Two runs on one key
   can no longer overlap, because they come from one profile.
6. Per vertical lane, fill each row between its leftmost and its rightmost foreground pixel, so an
   outlined rectangle counts as filled; coverage is the filled fraction of the lane core. Five of the
   twenty one examples draw the rectangle as an outline, so this step is not optional.
7. A row is inside a rectangle when coverage is at least `tauCoverage`. Close gaps of at most
   `gapClose` rows, drop runs shorter than `minHeight` rows — that is what kills the sparkles.
   **Changed.** `gapClose` was 3 rows and closing a gap of six. Two notes in a row on one key are
   drawn as two rectangles touching, with nothing between them but their own dark borders, and that
   border is 3 to 7 rows. Closing six merged them, so the second onset was lost without a sound.
   Measured over 60 sampled frames of a real video: 927 gaps of 1 to 2 rows, which are texture
   inside one rectangle and have to be closed, and 1351 gaps of 3 to 7 rows, which are two
   rectangles and have to be kept.
8. **New.** The split. Closing less is not enough on its own, because the border between two
   rectangles does not always get dark enough to break the run. The run is cut at every local
   minimum whose **prominence** — how far it drops below the plateau on both sides of it, **within
   half a white key either side** (V-46), as a share of that plateau — reaches `splitProminence`.
   Against the brightest row of the whole run instead, which is what was built first, a rendering
   whose rectangles brighten as they fall turned the 8% step at every seam between two strips of
   the stitched roll into a cut: 270 false repeats on the photograph, 92 of them on the seam rows. Prominence is the right measure because the plateau
   of a rectangle is flat to about one percent while a border drops tens of percent, and because it
   does not care how bright the rendering is. Measured on lanes whose content was read off the
   pixels by hand: the texture inside one rectangle reaches 0.13 at the worst, and a real border is
   0.75 to 0.80.
9. For each run: the rectangle tip is its lowest row, the last rectangle tip its highest. A run whose
   lowest row sits on the upper line within `clipTolerance` has been cut there, not tipped there
   (V-16).
10. **New.** The whole width of the rectangle, measured across the lane borders, because a lane only
    shows the part of the rectangle that falls inside it. The rectangle is the bright part and the
    glow around it is the dim part, so a column belongs to the rectangle when it reaches `tauEdge` of
    the strongest column of that run. Measured: this finds a third more rectangles, and it is what
    lets the plate difference read the renderings whose rectangles glow. **The peak is taken over a
    window of `extentWindow` white keys either side of the key, never over the whole width.** Over
    the whole width the brightest column in those rows is some other key's strike flash; it sets the
    bar far too high for this key's own columns, and the search then walks off to whatever column
    does pass — which put a run near the upper line on a key four semitones away.
11. **New.** The width gate: a run narrower than `minWidth` or wider than `maxWidth` is not a note.
   Measured: it halves the invented onsets and takes the invented sustains to zero. It is what kills
   the strike sparkles, which spread over two or three keys.
12. **New.** The momentum rule (V-33, V-34). A run is refused when a neighbouring sampled frame
    holds it in the same place, and only then — a run with no neighbour to ask is kept, because the
    absence of an answer is not an answer. **Changed by Phase 2**: the smallest travel the vote will
    consider is derived from the matching slack rather than chosen — a run matches itself at any
    shift within the slack, so a floor at or below it lets a letter vote for itself. At a slack of 5
    px the floor is 11, which leaves room under the 17 px a video travels at 10 frames per second;
    Phase 1's 15 did not. The vote also answers the middle of its winning plateau rather than the
    first shift of it, because the slack makes the answer a plateau and taking its first shift biases
    every travel low by the whole slack. Frames are matched one to one: a rectangle in the
    neighbouring frame is the past of at most one rectangle in this one, which is what stops a
    repeated note from aliasing into a note that never moved. **Changed by Phase 3**: an edge the
    picture pinned is left out of the comparison (V-42) — a run cut by the upper line keeps its
    lowest row at that line however fast it falls, so comparing that edge can only ever say it did
    not move. Measured on a real video: with both edges compared the rule refused 80 runs in a
    fourteen second stretch and every one of them was clipped; with the pinned edge out, frame to
    frame agreement over the whole video goes from 94.3% to 97.1%. This is what removes a song title, a watermark and decorative scrollwork drawn across the
    roll, and it removes them without any appeal to what they look like. The travel is voted for by
    the runs themselves, not correlated from the pictures: on the frames where the title is a hundred
    pixels tall, a correlation answers that nothing moved, because the letters did not.
13. Attribute the run to the key whose midpoint is nearest the run's own midpoint (V-14). Measured on
   a real video: all 268 notes of a thirty second stretch sat within 0.17 white key widths of a key
   midpoint, so the margin is 0.33 white key widths on every note.
14. **Changed.** Inside the halo guard band the tip is not read from the pixels; it is extrapolated
    (V-08). That is a **flag on the run, not a reason to throw the run away**. Throwing it away was
    wrong and it cost a real onset: on one example the rectangle is 43 rows tall and the guard band
    is 68, so a whole legitimate rectangle sat inside the band and vanished. What removes the light
    is the width gate and the minimum height, which a halo blob fails anyway. The band is measured
    per video from the motion of the roll (step 3), with 1.75 white key widths as the value it
    starts at (V-24). The tip is read high in the roll, where the picture is clean (V-23).

Per video, after the frames:

15. **Changed.** The stitched roll (V-32). The top `scrollSpeed x sampleMs` rows of each sampled
    frame are the strip of the roll nobody has seen yet, so piling them up rebuilds the whole piece
    as one tall picture whose vertical axis is time. The strip is taken well below `rollTop` and far
    above the upper line, so no halo, no sparkle and no strike light enters it. A note is one
    connected shape in that picture. Measured: 268 of 268 shapes in thirty seconds were notes, none
    thrown away, every one within 0.17 white key widths of a key midpoint. This replaces the frame
    to frame tracker.
16. Onset and release: the bottom row of a shape is the onset and the top row is the release (V-05).
    **The stitched roll keeps the sense of a frame**, so those words mean here what they mean on a
    frame: time runs *upward*, the rectangle tip is still the lowest row and the last rectangle tip
    still the highest, and `clipped` and `entering` still say what they said — a shape on the bottom
    edge was already sounding when the video started, one on the top edge is still falling when it
    ended. A row is therefore `(upperLine - bottomRow + rowsFromTheBottom) / scrollSpeed` seconds,
    counted from the bottom rather than the top. Measured: one pixel is 6.3 ms on one video and
    5.9 ms on the other, against the ±50 ms that placing an onset in the frame it happened in costs.

Named thresholds, with the value Phase 1 measured. **Every length is in white key widths (V-22)**,
because the examples are 3600 pixels wide and the videos are 1280, and a threshold in pixels is
right on one of them and wrong on the other.

| threshold | value | where it comes from |
|---|---|---|
| `tauForeground` | 24 of 255 | unchanged; the roll's own contrast is 104 at the worst usable example |
| `tauCoverage` | 0.55 of the lane core | unchanged |
| `gapClose` | 2 rows | **changed** from 3; the border between two stacked rectangles is 3 to 7 rows and this has to stay under it |
| `splitProminence` | 0.30 of the plateau beside the dip | **changed** from 0.40 against the whole run (V-46); the middle of the plateau on both keyboards |
| `valleyWindow` | 0.5 white key widths | **new** (V-46); how far either side of a dip its plateau is read |
| `coreWindow` | 0.25 white key widths | **new** (V-46); the columns whose median the extent is measured against |
| `extentWindow` | 2.0 white key widths | **new**; how far the search for a rectangle's own edges may reach |
| plate | median of what stands still, 150 frames | **changed** from the 20th percentile (V-44); 68% of notes not shown to 6.5% on a photograph |
| `rollTop` | measured per video | **new**; found from motion. 62 on the test video |
| momentum slack | 5 px | **new**; at 3 a few real notes are missed, at 7 the travel vote collapses onto the static content |
| `minHeight` | 0.24 white key widths | unchanged (6 rows); the shortest note measured was 95 ms, which is 15 rows |
| `clipTolerance` | 0.12 white key widths | unchanged (3 rows) |
| lane `margin` | 0.25 white key widths | unchanged; attribution has a 0.33 margin, so this is safe |
| `tauEdge` | 0.50 of the run's own peak | **new**; 0.35 to 0.65 all work, 0.00 loses a third of the rectangles |
| `minWidth` | 0.35 white key widths | **new**; a black key rectangle measured 0.62 |
| `maxWidth` | 1.40 white key widths | **new**; a white key rectangle measured 1.03 |
| halo guard band | measured per video, 1.75 white key widths to start | **changed** from 12 rows; measured 1.73 at the median of the screenshots, 4.14 at the worst, 0 on plain Synthesia, 1.59 on the test video, 1.82 on the photograph |
| `sampleMs` | 100 (10 frames per second) | unchanged; gives 33 votes per rectangle, and 16.9 px of travel on the video Phase 3 read |
| scroll speed `MIN_EDGES` | 6 followed edges per pair | **new** (V-45); a lone rectangle's two edges cannot outvote one detection's noise |
| scroll speed `STABLE_SPREAD` | 0.10 of the answer | quartiles of the per-pair fall sit 0.7% and 1.8% apart on the two videos, so this refuses only a video that really is not steady |
| black key width | measured per key by the finder of implementation 05 | was 0.58 white key widths for the grid overlay; a found overlay carries every black key's own borders (V-38) |

What this does not handle, named honestly:

- ~~A keyboard photographed at a strong angle.~~ Handled since implementation 05: the grid is gone,
  the keys are found where they are, and `airplanes` is found with all 88 keys, 2.5 px from the
  borders the spike measured at the worst.
- A video that shows no roll at all. One example of twenty one, `superestrella`, which is a crop of
  the keyboard.
- A video whose scroll speed is not stable. V-06 says it is reported, not transcribed.
- A rectangle entirely past the upper line with the strike light over what is left. A single frame
  cannot say whether the note is still sounding; only the track can. **Phase 3 met this on a real
  video**: on short staccato notes the rectangle crosses the line inside one sampled frame while
  the keyboard keeps the key lit, so the picture shows a pressed key with no rectangle left. The
  detector reports nothing there rather than inventing a sustain from the strike light, which is
  the right answer for a frame and the wrong one for the piece — Phase 4's stitched roll (V-32)
  is what closes it, because a shape in the stitched roll has a top and a bottom whatever the
  upper line did to it. **Measured by Phase 4**: against the keys the rendering lights on its own
  keyboard, the per-frame reading finds 43% of the strikes and the stitched roll 97%.
- Decoration that sits in the strip and comes and goes. The strip is seventeen rows of seven hundred
  and twenty, well below the roll top, and the plate removes anything that is in every frame (V-15),
  so a title has to fade in and out *and* land in those seventeen rows to survive both. Nothing like
  it appeared on the video Phase 4 read — the longest shapes were a held chord at the end — but the
  stitched roll has no momentum rule (V-33), which is what catches it on a frame, so the guard here
  is the plate, the strip's narrowness and the width gate, and nothing else.

---

# Phase 1 — Research  ·  done

Understand the problem before writing the detector, and decide what we go for. Nothing in this phase
ships to a user. Its work lives in `poc-synthesia-frames/` at the repository root, beside the
existing `poc-onset-duration-distribution/`, and its conclusions go into
[`04-decisions.md`](04-decisions.md).

What it found is [`04-phase-1-implementation.md`](04-phase-1-implementation.md), the evidence is
[`../../../poc-synthesia-frames/RESULTS.md`](../../../poc-synthesia-frames/RESULTS.md), and the
chosen algorithm is section 8 above. The tasks below are left as they were written, so a reader can
see what was asked as well as what came back.

## Story 1.1 — What other people do

### Task 1.1.1 — Survey

Search for what exists: projects that turn a Synthesia or piano roll video into MIDI, the papers
that read piano performance from video, and the plain computer vision toolbox that applies here —
background subtraction, connected components, contours, edge detection with Canny and Hough,
template matching, adaptive threshold, colour clustering. For each one, one row: what it does, what
it needs, and why it is or is not usable for us, which is local, without a GPU, over a few thousand
frames, in a few minutes.

One approach is known to be the common one and must be compared on purpose: watching a single row of
pixels just above the upper line and calling a key on when the colour there changes. It is the
simplest thing that works and it is what most projects do. Its two weaknesses are the halo, which
lights that exact row, and that it can only place an onset in the frame it happened in, with no
sub-frame precision. It is the baseline every other idea has to beat.

### Task 1.1.2 — Choose the family

Decide: rule based classical computer vision per vertical lane, or a learned detector. Write the
reason. The bar for a learned detector is that it must be trainable from the examples we have,
without labelling thousands of frames by hand, and must run locally in reasonable time. If the
answer is classical, say which primitives and why the others were dropped.

## Story 1.2 — Measure the examples

### Task 1.2.1 — The casuistry catalogue

One row per example screenshot in [`examples/`](examples), 21 of them. Per row: background, how the
rectangle is drawn (solid, shallow, outlined, gradient, shining), halo present, sparkles present,
static decoration in the roll (titles, watermarks, logos, moons, scrolls, guide lines), whether the
keyboard fills the width, how many keys it shows, whether hands are visible, whether the keyboard
sits at the bottom of the picture. This table is the ground for every threshold in the plan and
belongs in the phase report.

### Task 1.2.2 — Try the detectors

On at least eight examples chosen to span the catalogue, run and compare: an absolute threshold; the
background plate difference; edges with a span fill; colour clustering; and the single row watcher
of Task 1.1.1. For each, save the picture of what it saw and count what it found and what it
invented. The examples are single screenshots, so a background plate has to be stood in for — say
how, and say what that costs the comparison.

### Task 1.2.3 — The scroll speed question

Download one real video by hand, sample it, and check the two claims V-05 and V-06 rest on: that the
scroll speed is constant enough over a piece, and that it can be measured from a pair of frames.
Report the measured speed, its spread, and what that spread means in milliseconds of onset error.
If the claim does not hold, V-05 and V-06 are wrong and the phase stops and says so.

## Story 1.3 — The decision

### Task 1.3.1 — Write down what we go for

The chosen pipeline as a numbered algorithm, every threshold named with its value and the
measurement behind it, and an honest list of what it does not handle. Section 8 of this plan is
updated to match, and anything new is added to [`04-decisions.md`](04-decisions.md) as a V number.

Exit criteria: a reader can implement the detector from the report alone, and every number in it has
a measurement beside it.

---

# Phase 2 — Evaluation  ·  done

Build the ground truth by hand, build the detector, and score one against the other. The piano
overlay is built here and reused unchanged by Phase 3, so it is designed for a video from the start.

What it found is [`04-phase-2-implementation.md`](04-phase-2-implementation.md). The score over the
ground truth that exists is **9 onsets found, 0 invented, 0 missed and 6 sustains found, 0 invented,
0 missed**, over five windows on the two examples a person can read without guessing. Three of those
five windows were read in this phase and two of them discriminate, so V-25 is tested rather than
asserted: `derulo` at d = 6 px must answer nothing at all — the strike light lives in exactly those
rows — and `shut-up-and-dance` at d = 30 px must drop one of its two onsets. The detector answers
both correctly.

**Twenty-one of the twenty four examples still have no hand reading**, and the score board names each
one with the reason rather than counting it. That is what the annotation page was built for and it is
the one thing this phase could not finish for itself. Task 2.3.4 was measured and does not ship on:
the colour check refuses two runs of thirty one and changes no verdict. The tasks below are left as
they were written, so a reader can see what was asked as well as what came back.

## Story 2.1 — The piano overlay

> **Replaced by implementation 05 on 2026-09-14.** The grid this story builds — one white key,
> repeated across the picture — cannot fit a keyboard the camera is not square to, and V-09, which
> it rests on, is superseded by V-37. The replacement is one rotatable rectangle over the piano area
> with every key found inside it, and a `Calibration` of per-key borders:
> [`../05-piano-overlay-from-black-keys/05-plan.md`](../05-piano-overlay-from-black-keys/05-plan.md).
> The three tasks below are left as they were written and as they were built, so a reader can see
> what was asked and what came back. Nothing else in Phase 2 changes: Stories 2.2 and 2.3 read the
> overlay through the same `Calibration`.

### Task 2.1.1 — The geometry

One module owns it, and the backend and the frontend agree on its shape. Inputs: the white key
rectangle the user placed, the black key rectangle the user placed, the pitch of the leftmost key,
the cut on the left, the cut on the right, the upper line. Outputs: for every key, its type, its
MIDI pitch, its left border, its right border and its midpoint in x, plus the vertical lane of that
key with the margin applied.

Black keys are placed from the white key geometry by the standard pattern, and **where each of the
five sits is one number the user sets by hand** (changed during Phase 2, at the user's direction):
an offset from the boundary between the two white keys it stands between, in white key widths. The
user aligns one octave and the calibration replicates it across the keyboard, because every
rendering puts its black keys somewhere slightly different and not all of them by the same amount.

The two modes this task first asked for — centred on the boundary, or the real piano offsets — are
what the octave *starts* at, not what it can say. They stay in the calibration so a calibration saved
before the octave step still means what it meant, and the nudge that moved all five as a block is
gone, because five numbers say everything it said and more.

### Task 2.1.2 — The calibration UI

The picture fills the screen and can be zoomed in hard and panned, because the user is matching a
few pixels.

**Four steps, one at a time, and the screen only ever offers the step you are on** (rewritten during
Phase 2, at the user's direction; the reason is in the phase report):

1. **place the white key** — one rectangle, put on one white key, dragged by its body and resized
   from its edges. It stays a horizontal rectangle and never rotates. Accept or cancel;
2. **place the black key** — the same, and the white key is put away, because what it measured has
   already been kept;
3. **render one octave** — eight white keys and all five black ones, and **each black key is
   dragged onto the black key under it**. The white keys are already right, because the white key
   width is what step 1 measured; the black keys are not. Eight white keys and not seven: seven is an
   octave only when it starts on a C, and from a D it holds four black keys and the fifth never
   appears to be aligned;
4. **render the piano** — that octave, repeated across the whole keyboard. **Only now does a whole
   overlay appear**, and an example that was calibrated before still opens with a bare picture: this
   step is *fit the piano*, so an overlay drawn before the keys are placed says the work is done when
   it is exactly what the user came to redo. *Move the piano* brings a saved overlay back, so nothing
   saved is out of reach, and the later steps read it as they always did;
5. **move the piano** — drag it onto the keyboard, press keys the picture does not show, sweep a box
   over several of them, and backspace takes them off. Two buttons, **+ key left** and
   **+ key right**, put one back at either end: the overlay is rendered to span the whole picture, so
   keys only go missing after a move or a trim, and the way back has to be smaller than rendering
   again.

Then save. Everything after step 3 is done on the picture: there are no cut buttons and no slider for
the upper line. Cutting the overlay one key at a time from two pairs of buttons was slow and blind —
the user had to count keys off the screen and press once per key — and dragging the piano is what
fixes a grid that is the right size and lands a few pixels to one side.

What is not a gesture and stays: the octave of the leftmost white key, because V-10 says the octave
comes from the user and from nowhere else, and which white key the overlay starts on, which the
black key pattern guesses and the user confirms. A rectangle already placed comes back exactly where
it was left when its button is pressed again.

This is an operation the user will do from scratch for every example, so it is measured: doing it on
an unseen screenshot should take under a minute.

### Task 2.1.3 — Which key is which

The pattern of two and three black keys fixes the pitch class of every white key. The octave of the
leftmost key is one dropdown, defaulting to a guess from the number of keys — 88 keys start at A0,
61 start at C2. Hovering a key shows its name, so a wrong octave is obvious at a glance. No pitch
comes from a colour (V-10).

## Story 2.2 — The examples and the manual annotation

### Task 2.2.1 — Serve the example set

List the screenshots, serve one image, and keep one calibration per example under
`data/frame-examples/`. Every example needs its own calibration because every example is a different
piano.

### Task 2.2.2 — The annotation page

The rendered piano overlay is drawn over the screenshot with one clickable element per key, sized
and placed by the geometry of Task 2.1.1 — the same piano that was accepted on the step before.
Pressing a key cycles it: nothing, onset, sustain, cannot say. The offset line is **dragged up and
down the picture with the mouse**, not set from a field, and the band between it and the upper line
is shaded, because the window is the thing being judged.

The annotation saved is the triple (example, offset line position, the keys marked), so the same
example annotated with the offset line in three places is three entries, which is exactly the point:
it tests whether the detector follows the window and not a fixed guess.

**One picture and one line, and nothing else on the screen.** Phase 2 first built this with a zoomed
strip sheet beside the picture — the band cut into four pieces and piled up, copied from the label
sheet Phase 1 read its own ground truth off — and the user rejected it: the strips stretch the
picture unevenly, they are ugly, and the piano the user has just fitted is already the thing to press.

### Task 2.2.3 — The rule on the page### Task 2.2.3 — The rule on the page

The frame window rule (V-18) is printed on the annotation page in the words of the decision, so the
person annotating applies the rule the detector applies.

## Story 2.3 — The detector and the score

### Task 2.3.1 — The detector

The algorithm Phase 1 chose, as a module: background handling, vertical lanes, runs, rectangle tip
and last rectangle tip, attribution by midpoint, and the frame window rule turned into two lists of
MIDI pitches. It takes one picture and one calibration and returns onsets and sustains. It has no
idea whether the picture came from an example or from a video.

### Task 2.3.2 — See what it saw

An overlay drawn on the picture: the runs it found, the rectangle tips, and the keys it called onset
and sustain. A disagreement with the ground truth must be something you can look at, not something
you have to imagine.

**And judged in place, which is how the ground truth gets made** (added during Phase 2, at the
user's direction). Pressing a rectangle throws it out — a false positive — and the key it stood for
stops being called. Pressing a key says what it should have been — a false negative — cycling onset,
sustain, cannot say. What comes out is the hand reading for that window, so the fastest way to read
an example is to let the detector read it first and correct what it got wrong. That is only sound
because every box is drawn on the rectangle it claims to be: accepting one is looking at it, not
trusting it.

The offset line is dragged here too and the detector re-reads as it moves. There is no run button, no
channel picker and no colour switch on this screen: the answer is what the screen is about, and the
two settings that exist for measuring a change live on the score board, where a change is measured.

### Task 2.3.3 — The score board

Run every example at every annotated offset line position and report, per example: onsets found,
onsets invented, onsets missed, and the same three for sustains, plus the list of keys that
disagree. A total at the top. The board is what says whether a change helped, and every change from
here on quotes it.

Exit criteria for the phase: over the whole example set, every onset in the ground truth is found and
no onset is invented; sustains agree except where the report names the example and the reason. If
that cannot be reached, the report says which examples fail, what they have in common, and what
would fix them — an honest failure list is a result, a rounded up number is not.

### Task 2.3.4 — The second check

The optional double validation the prompt suggests: the colour of a run compared against the palette
of rectangle colours collected from the picture, as a second reason to believe a run is a note. It
ships only if the score board improves, and the report gives the numbers either way (V-20).

---

# Phase 3 — Download a video and sampling frames  ·  done

## Story 3.1 — Downloading the video

### Task 3.1.1 — The video download, and the audio with it

`POST /video/download`: yt-dlp with a video format, capped at 720p because nothing in the detector
needs more and the file stays small, saved as `video/source.mp4` in the audio folder of the same
piece. yt-dlp errors are surfaced word for word, as they are now.

The audio of that same video is extracted from the file we just downloaded, with ffmpeg, and goes
into the store through `ingest.ingest_path` exactly as a YouTube audio does today. One URL, one
network fetch, one piece that has both (V-03). Extracting from the video rather than fetching the
audio stream a second time halves the download and removes any question of the two being aligned;
if the audio quality of the video file ever matters, switching back to a separate `bestaudio` fetch
is a one line change in the same function.

The user is not asked about any of this. They paste a URL and get a video they can play; the audio is
there because the Piano Sheet tab plays the original audio later.

## Story 3.2 — Sampling frames

### Task 3.2.1 — Sampling

ffmpeg writes the sampled frames into `video/frames/` at the sampling granularity, as a job with
progress on the existing SSE plumbing. `sampleMs` is stored in `metadata_video.json`. Sampling again
at another granularity replaces the folder; the video is still there, so nothing is lost (V-01). The
report states the measured disk cost of one four minute video at 10 frames per second, because that
number decides whether the default is right.

## Story 3.3 — The video player

### Task 3.3.1 — The player

Minimal and useful: spacebar plays and pauses, the left and right arrows step one sampled frame, a
progress bar shows mm:ss and can be dragged. It draws the sampled frames, not the video element, so
what the user sees is exactly what the detector sees.

~~This player shows the video only. It does not play the audio and does not mention it: the audio
belongs to the tabs that read the sheet, not to the tab that calibrates the picture.~~

**It plays the original audio, and the audio is the clock** (changed after Phase 4, at the user's
direction). The reason the first version gave — that the audio belongs to the tabs that read the
sheet — does not survive the tab being used: you cannot tell whether the picture on screen is the
music you think it is without hearing it. The audio was taken out of this very video file with
ffmpeg on the same download (V-03), so its t = 0 **is** the video's t = 0 and there is nothing to
align; measured, the mp3 and the mp4 are 272.913 and 272.914 seconds long.

It is driven the only way that does not drift: the frame on screen is `currentTime / sampleMs`, read
off the audio element every animation frame, and dragging the bar moves the audio. A timer counting
frames with an audio element told to keep up is the version that drifts, because a `setInterval` of
100 ms is not 100 ms and an audio clock is. Measured over five seconds of playing: the audio reads
4.80 s and the player is on the frame for 4.80 s, every second, with no drift. A speaker button turns
the sound off, and with it off the player is the timer Phase 3 had.

### Task 3.3.2 — Calibrate from a frame

Pick a frame — the middle one by default, since the piano is static and any frame will do — and open
the calibration UI of implementation 05 unchanged: one rectangle, and the overlay found inside it.
Save on the video.

## Story 3.4 — The scroll speed and the time frame lines

### Task 3.4.1 — Measure the scroll speed

Per pair of consecutive sampled frames, the vertical shift that best aligns the roll band. Store the
series, report the median and the spread, and show it in the UI as pixels per second and as pixels
per sampled frame. If the spread says the speed is not stable, say so plainly on the screen and do
not go on quietly (V-06).

### Task 3.4.2 — Draw the time frames

On the player, draw the upper line and then one offset line for each of the next few time frames,
spaced by the measured scroll speed. This is what lets the user see, on a real frame, which
rectangles will land in which time frame — the same picture the annotation page shows, now with the
spacing measured instead of dragged.

## Story 3.5 — Detection over the whole video

### Task 3.5.1 — Run it

The background plate, then the detector of Story 2.3 over every sampled frame, writing
`frames.jsonl`. A job with progress. The lanes are independent (V-13), so the frames are processed
across several worker processes; the report gives the wall clock time for a four minute video.

Exit criteria: a real Synthesia video downloads, samples, calibrates in under a minute of clicking,
and produces a `frames.jsonl` whose onsets, spot checked on ten frames by hand, are right.

---

# Phase 4 — Piano Matrix Notation

Turn what was seen into the piece. This phase writes `events.json` and touches nothing downstream.

## Story 4.1 — From rectangles to notes

### Task 4.1.1 — The stitched roll

Rebuild the piece as one tall picture by piling up the fresh strip of each sampled frame, then label
it: one connected shape is one note (V-32). The three awkward cases the tracker had are handled by
the shape of the picture rather than by rules — a rectangle that appears already crossing is a shape
touching the bottom edge, two notes on the same key with a small gap are two shapes with a gap, and
a rectangle taller than the roll band is one shape. Report the memory the stitch takes for a four
minute video; it is about forty thousand rows.

### Task 4.1.2 — Times

The bottom row of a shape is the onset and its top row is the release, both turned into seconds with
the measured scroll speed (V-05). A shape whose width or whose midpoint does not match a key is
reported rather than rounded onto one, because that is a detection problem wearing the mask of a
timing problem.

The floor on note length (D-05) is not applied here. It belongs to the step that builds the matrix,
which already applies it. This step writes what it saw.

### Task 4.1.3 — Write the piece

Through `pipeline.save_note_events`, with `durationSeconds` from the video and the title from the
video, clearing the saved rhythm as a transcription does. No `hand` field is written on any event:
the hand split does that job and is never given a hint from a colour (V-17).

## Story 4.2 — It is a piece like any other

### Task 4.2.1 — Straight through

A test that a video derived `events.json` goes through the hand split, the matrix, the peaks, the
ladder and the payload with no special case anywhere. If any of them needs to know where the notes
came from, that is a defect in this phase, not a feature of the others.

### Task 4.2.2 — Against the model

Run the existing engine on the same audio and report the difference: onsets both agree on within
50 ms, onsets only the video found, onsets only the model found. It is a report, not a second piece.
This is the number that says whether the whole plan was worth it, so it is stated plainly whichever
way it comes out.

## Story 4.3 — Corrections before it becomes the piece

### Task 4.3.1 — Review the detection

Before `events.json` is written, show what will be written over the video player, and let a note be
removed or a missed note be added by hand. The note selection that already exists on the Piano Roll
is the model for this; do not invent a second way of picking notes.

Exit criteria: a video goes end to end to `events.json`, the Piano Roll drawn from it matches what is
on the video when the two are stepped side by side, and the comparison against the model is written
down.

---

# Phase 5 — Piano Sheet

## Story 5.1 — The piece opens everywhere

### Task 5.1.1 — Every screen

A video derived piece appears in the Playground like any other: the Piano Roll and Notes Falling
draw it, the Piano Sheet tab names the ladder and prints the staff, the player plays the audio that
came from the same download, and it can be promoted into the Piano Library. Nothing new is built
here; this task is the check that nothing was missed.

## Story 5.2 — The rich metadata is kept, and kept apart

### Task 5.2.1 — Decoupled

The calibration, the sampling granularity, the scroll speed and `frames.jsonl` stay under `video/`
and are never merged into `rhythm.json` (V-12). Reading the video again is one button; it replaces
the piece and therefore advances the music version, and it says so before it does it. Everything the
reader decided about the sheet is subject to the ordinary rule for a piece whose music changed —
nothing new is invented for it here.

## Story 5.3 — Documentation

### Task 5.3.1 — Write it down

`context/backend/video-to-notes.md` for what it is and how it flows, and
`documentation/services/backend/synthesia-detection.md` for the thresholds, the file shapes and the
exact commands. Add both to `context/00-index.md`, add a line to
`context/00-project-complete-overview.md`, and add this implementation to the table in
`context/implementations/README.md`. Follow
[`../../00-documentation-instructions.md`](../../00-documentation-instructions.md).

Exit criteria: a reader who has never seen this plan can download a Synthesia video, calibrate it,
read it and print the sheet, using the documentation alone.

---

# 9. Risks, named now

- Disk. Sampled frames are big. The video is kept and the frames are a cache (V-01), so the fallback
  when the cost is too high is a smaller sampling granularity or frames stored at a smaller size —
  both are parameters, not rewrites.
- yt-dlp and video formats. Audio downloads work today; video formats are a different negotiation
  and may need a format string that survives what YouTube serves. The error text is shown as it
  comes.
- Moving decoration. The background plate removes what is static. An animated title crossing the
  roll is not static, and the guard against it is the run shape and the minimum height, not the
  plate. Phase 1 must say which examples have it.
- A keyboard that moves, or a camera that pans. Out of scope. Detect it from the scroll speed series
  and say so rather than producing nonsense.
- Rectangles wider than their key. That is why lanes have a margin and attribution is by midpoint
  (V-13, V-14).
- Two strikes of the same key with no visible gap. The tracker has to split them or admit it did
  not; it is named in Task 4.1.1 for that reason.
- Videos where the rectangle does not vanish at the upper line but continues over the key. Handled
  by never looking below the upper line, but it has to be checked on the Synthesia style examples.

# 10. How a phase is handed off

One agent per phase, with the phase's whole context in one session. At the end of a phase the agent
writes `04-phase-X-implementation.md` in this folder — technical, for the next agent, as detailed as
it likes — updates [`04-checklist.md`](04-checklist.md), and writes the walkthrough message in the
structure of
[`../../language/communication-implementation-plans.md`](../../language/communication-implementation-plans.md).
The handoff sentence for the next agent is short and tags what it must read:

```text
You are working on an implementation plan. Read @context/implementations/04-synthesia-to-notes/04-plan.md,
@context/implementations/04-synthesia-to-notes/04-decisions.md,
@context/language/communication-implementation-plans.md and
@context/implementations/04-synthesia-to-notes/04-phase-3-implementation.md. Start Phase 4.
```

Each phase replaces the report it tags with its own. A phase that needs what an earlier one found
reads that report too — Phase 2's report names the parts of Phase 1's that still matter.

Every worker, every phase:

- Reads [`04-decisions.md`](04-decisions.md) and does not reinterpret a V number. A decision that
  looks wrong is raised and the work stops there.
- Reads the five rules in
  [`../01-epics-master-plan/plan/wall-clock-rewrite.md`](../01-epics-master-plan/plan/wall-clock-rewrite.md)
  and D-01 to D-34. They are still binding. In particular there is no BPM anywhere in this plan
  either, and `sampleMs` is never used where `frameMs` is meant (V-04).
- Follows [`../../09-coding-conventions.md`](../../09-coding-conventions.md), and keeps paths in
  `storage/paths.py` and routes in `layout/routes.ts`.
- Runs `make test` and `make lint` in `aitu-backend` and `npm run lint` in `aitu-frontend` before
  reporting done, and states the counts. One failure is known and pre-existing; a second one is not.
- Marks the checklist in progress when starting and complete when finished.
- Quotes numbers, not impressions. A rule with no measurement beside it does not ship (V-20).
