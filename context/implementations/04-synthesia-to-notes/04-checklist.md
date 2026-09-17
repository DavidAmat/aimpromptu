# 04 — Synthesia to notes: checklist

The status lookup for this implementation. The plan is [`04-plan.md`](04-plan.md); the frozen
decisions are [`04-decisions.md`](04-decisions.md).

One phase is one epic. A story is ticked only when every task under it is done.

Status letters: `[x]` complete, `[p]` in progress, `[b]` blocked, `[c]` cancelled, `[ ]` not started.

# [x] Phase 1 — Research
Understand how to find the falling rectangles before building anything. Survey what other people do,
measure the 21 example screenshots, and decide the algorithm we go for. Work lives in
`poc-synthesia-frames/`; conclusions go into `04-decisions.md`.

Done, then reopened once and rebuilt after the user reviewed it on a video of their own. The report
is [`04-phase-1-implementation.md`](04-phase-1-implementation.md) — section 11 is the rebuild — and
the evidence is [`../../../poc-synthesia-frames/RESULTS.md`](../../../poc-synthesia-frames/RESULTS.md).
The chosen algorithm is section 8 of the plan; V-21 to V-31 were added and V-15 was corrected by
V-29. On the two examples with hand read ground truth the detector now finds every onset and every
sustain and invents none; on a 90 second video it agrees with itself frame to frame 98.2% of the
time.

Nothing is open. Phase 4 takes the stitched roll (V-32, the user's decision) and the momentum rule
that refuses anything drawn across the roll is V-33 and V-34. Section 12 of the report has both.

## [x] Story 1.1 — What other people do
- [x] Task 1.1.1 **Survey**: projects and papers that read a piano roll video, the classical computer vision toolbox, and the single row watcher as the baseline to beat.
- [x] Task 1.1.2 **Choose the family**: rule based per vertical lane or a learned detector, with the reason written down.

## [x] Story 1.2 — Measure the examples
- [x] Task 1.2.1 **The casuistry catalogue**: one row per example — rectangle style, halo, sparkles, static decoration, keyboard extent, hands.
- [x] Task 1.2.2 **Try the detectors**: five candidates on at least eight examples, with the picture of what each saw and a count of found and invented.
- [x] Task 1.2.3 **The scroll speed question**: measure it on one real video and say what its spread costs in milliseconds. This confirms or kills V-05 and V-06.

## [x] Story 1.3 — The decision
- [x] Task 1.3.1 **Write down what we go for**: the numbered algorithm, every threshold named with the measurement behind it, and what it does not handle.

# [x] Phase 2 — Evaluation
Build the piano overlay, annotate the examples by hand, build the detector, and score one against the
other. The overlay built here is the one Phase 3 uses on a video.

Done. The report is [`04-phase-2-implementation.md`](04-phase-2-implementation.md). The detector of
Phase 1 is ported into the app as `aitu_backend/video/`, the whole of Video to Notes is a new top
section with the Examples tab built and the other three tabs waiting for Phase 3, and the score board
reads **9 onsets found, 0 invented, 0 missed and 6 sustains found, 0 invented, 0 missed** over five
windows on the two examples that have a hand reading. Three of those five windows were read in this
phase and two of them discriminate: `derulo` at d = 6 px must answer nothing at all, and
`shut-up-and-dance` at d = 30 px must drop one of its two onsets. The detector follows both.

**The other 21 examples have no hand reading yet**, and that is the one thing Phase 2 cannot finish
for itself: only two of them can be read without guessing, which is why the annotation page exists.
They are named on the score board with the reason rather than counted. Task 2.3.4 was measured and
does not ship on by default: the colour check changes no verdict on the ground truth that exists.

## [x] Story 2.1 — The piano overlay
Built as written, then **replaced by implementation 05** (opened 2026-09-14): the grid cannot fit a
keyboard the camera is not square to, V-09 is superseded by V-37, and the calibration UI becomes one
rotatable rectangle with every key found inside it. Status lives in
[`../05-piano-overlay-from-black-keys/05-checklist.md`](../05-piano-overlay-from-black-keys/05-checklist.md).
- [x] Task 2.1.1 **The geometry**: one white key and one black key plus the cuts give every key its borders, its midpoint and its vertical lane. Built twice, in Python and in TypeScript, and held together by one fixture both assert against.
- [x] Task 2.1.2 **The calibration UI**: zoom, place, drag, resize, render the piano, cut left and right, move the upper line.
- [x] Task 2.1.3 **Which key is which**: pitch class from the black key pattern, octave from one dropdown, names on hover.

## [x] Story 2.2 — The examples and the manual annotation
- [x] Task 2.2.1 **Serve the example set**: list the screenshots, one calibration per example. The 21 calibrations Phase 1 measured are seeded, so no picture starts from nothing.
- [x] Task 2.2.2 **The annotation page**: clickable keys cycling nothing, onset, sustain, cannot say; a draggable offset line; one entry per offset line position; the band cut into strips and piled up, which is the label sheet Phase 1 asked for.
- [x] Task 2.2.3 **The rule on the page**: the frame window rule printed where the person annotating reads it, in V-18's own words.

## [x] Story 2.3 — The detector and the score
- [x] Task 2.3.1 **The detector**: one picture and one calibration in, onsets and sustains out. It has no idea whether the picture came from an example or from a video.
- [x] Task 2.3.2 **See what it saw**: lanes, runs, rectangle tips and last rectangle tips drawn on the picture, plus the lane inspector that lists the rows, the gap, the width and the flags of every run on one key.
- [x] Task 2.3.3 **The score board**: found, invented and missed per example, the keys that disagree, and the examples that could not be scored with the reason.
- [x] Task 2.3.4 **The second check**: measured. The colour check refuses 2 runs of 31 and changes no verdict, so it ships as a switch that is off, not as a rule.

# [x] Phase 3 — Download a video and sampling frames
Bring a real video in, sample its frames, calibrate it, measure the scroll speed, and run the detector
over the whole thing.

Done. The report is [`04-phase-3-implementation.md`](04-phase-3-implementation.md). A 4 minute 32
second Synthesia video goes from a URL to `frames.jsonl` through the app: downloaded at 720p with its
audio beside it, sampled into 2728 frames in 3.9 s, calibrated at 88 keys with confidence 0.91, and
measured at **168.9 px a second with its quartiles 0.74% apart**, roll top row 62 and a guard band of
1.50 white key widths. Reading every frame takes 22.2 s over 8 worker processes and gives 1755
onsets, 6.43 a second, with **frame to frame agreement of 97.1%** (V-31).

**The exit criterion is met**: ten frames were checked by eye against the keys the rendering itself
lights on its keyboard, and nine agree key for key. The tenth is the limitation the plan already
names — a short note whose rectangle crosses the upper line inside one sampled frame — and Phase 4's
stitched roll is what closes it.

Two rules changed, both measured and both in `04-decisions.md`, and both confirmed by the user on
2026-09-15. **V-42**: an edge the picture pinned is not evidence, which took agreement from 94.3% to
97.1%. **V-43**: a pair of sampled frames the roll did not move in is a rest and not a measurement —
without it this video would have been refused as unstable.

The user drove the three screens and confirmed the phase works. **The screens have glitches that are
deliberately left for a later iteration**, at the user's direction; the next agent should not treat
the UI of this section as finished.

## [x] Story 3.1 — Downloading the video
- [x] Task 3.1.1 **The video download, and the audio with it**: yt-dlp at 720p into the audio folder of the same piece, and the audio extracted from that same file with ffmpeg, so one URL gives one piece with both.

## [x] Story 3.2 — Sampling frames
- [x] Task 3.2.1 **Sampling**: ffmpeg into `video/frames/` at the sampling granularity, as a job with progress. Measured: 2728 frames take 211.8 MB against 31.3 MB for the video, which is 6.8 times the video and 46.6 MB per minute of music, written in 3.9 s.

## [x] Story 3.3 — The video player
- [x] Task 3.3.1 **The player**: spacebar, arrows for one sampled frame, a draggable progress bar in mm:ss, drawn from the sampled frames. It does not play the audio and does not mention it.
- [x] Task 3.3.2 **Calibrate from a frame**: the middle frame by default, and the calibration UI of implementation 05 opened on it unchanged.

## [x] Story 3.4 — The scroll speed and the time frame lines
- [x] Task 3.4.1 **Measure the scroll speed**: per frame pair, stored, shown as px/s and px per sampled frame, and refused in words when it is not stable. The same pass measures the roll top and the guard band from the same motion (V-28).
- [x] Task 3.4.2 **Draw the time frames**: the upper line plus six bands of one sampled frame of travel each, spaced by the measured speed, with the roll top and the guard band drawn beside them. There is no slider: on a video the window is not a free parameter (V-25).

## [x] Story 3.5 — Detection over the whole video
- [x] Task 3.5.1 **Run it**: background plate, then every sampled frame across 8 worker processes, writing `frames.jsonl` and a report beside it. 2728 frames in 22.2 s; the momentum rule refused 1001 rectangles of 130 249 and every one looked at was a sparkle, a glow or lettering.

# [x] Phase 4 — Piano Matrix Notation
Turn the rectangles into the piece: the whole video stitched into one picture whose vertical axis is
time (V-32), a note is one shape in it, and its rows become seconds and then `events.json` through
the writer that already exists.

Done. The report is [`04-phase-4-implementation.md`](04-phase-4-implementation.md). The 4.5 minute
video Phase 3 read is now a piece: 2728 sampled frames stitch into **46 504 rows by 1280, 59.5 MB**,
and **4295 notes** come off it in 46 s — median 219 ms long, 0.62 white keys wide, and the furthest
any of them sits from a key midpoint is 0.257 white key widths against V-14's measured margin of
0.33.

**The score is against the rendering's own keyboard**, which lights a key while a note sounds below
the upper line where neither reading ever looks — so it is ground truth that needs no labelling. Over
sixty seconds it shows 826 strikes: the stitched roll finds **804 of them, 97%**, the per-frame
reading of Phase 3 finds 358, **43%**, and the ByteDance model finds 560, **68%**. Task 4.2.2's
comparison against the model on the same audio: 2331 onsets agree within 50 ms, 1964 only the video
found and 1677 only the model found, with the model's onsets sitting a median **45 ms later**.

Nothing in `04-decisions.md` changed. One thing the plan said loosely is now said exactly: the
stitched roll keeps the sense of a frame, so a shape's bottom row is its onset, and section 8 step 16
carries the row-to-seconds arithmetic that follows from it.

## [x] Story 4.1 — From rectangles to notes
- [x] Task 4.1.1 **The stitched roll**: the fresh strip of every sampled frame piled into one picture, and the three awkward cases handled by the shape of the picture rather than by rules. Memory measured: 46 504 rows, 59.5 MB for 4 minutes 32 seconds.
- [x] Task 4.1.2 **Times**: the bottom row of a shape is the onset and the top row the release, both turned into seconds with the measured scroll speed. A shape a gate threw out is reported with the gate that did it, never rounded onto a key.
- [x] Task 4.1.3 **Write the piece**: through `pipeline.save_note_events`, clearing the saved reading, advancing the music version, and with no hand written on any event (V-17).

## [x] Story 4.2 — It is a piece like any other
- [x] Task 4.2.1 **Straight through**: the hand split, the matrix, the peaks, the ladder and the payload, all asked over HTTP for the uuid a video wrote, with no special case anywhere.
- [x] Task 4.2.2 **Against the model**: 2331 agreed within 50 ms, 1964 only the video, 1677 only the model — and against the rendering's own keyboard the video route finds 97% of the strikes and the model 68%.

## [x] Story 4.3 — Corrections before it becomes the piece
- [x] Task 4.3.1 **Review the detection**: every note drawn back onto the frame its rectangle is in, picked with the rules the Piano Roll already uses, taken off or put on by hand, and only then written.

# [x] The second rendering — a roll over a photograph
The detector held on plain Synthesia and broke on a roll drawn over a photograph. The study is
[`04-second-rendering-study.md`](04-second-rendering-study.md); its rules are built.

- [x] **The plate** is the median of what stands still (V-44): 4967 notes and 68% not on the keyboard became 1492 and 6.5%; the plain video reads the same 4295.
- [x] **The scroll speed** is the rectangles' own fall (V-45): 20.22 px per frame from 48 396 followed edges, where the correlation answered 6 pairs.
- [x] **The roll bounds** are read on the plate difference, the guard band upward from the upper line: 56 rows on the photograph, where the raw picture gave the whole roll.
- [x] **The split and the extent** measure what V-26 and V-14 say (V-46): the plateau beside the dip at 0.30, the columns at the key's core.

# [ ] Phase 5 — Piano Sheet
The video derived piece behaves like every other piece, and the rich metadata is kept apart from what
the reader decided.

## [ ] Story 5.1 — The piece opens everywhere
- [ ] Task 5.1.1 **Every screen**: Playground, Piano Sheet, the player, the Piano Library.

## [ ] Story 5.2 — The rich metadata is kept, and kept apart
- [ ] Task 5.2.1 **Decoupled**: the calibration stays under `video/`, reading the video again replaces the piece and says so first.

## [ ] Story 5.3 — Documentation
- [ ] Task 5.3.1 **Write it down**: the context overview, the detail file, and the index entries.
