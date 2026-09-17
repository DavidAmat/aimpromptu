# Frozen decisions — video to notes

Every task in [`04-plan.md`](04-plan.md) cites these by id. A task may not reinterpret a decision.
If implementation shows a decision is wrong, write it in the phase report, stop, and raise it.

These are the decisions of this plan only. The decisions of the wall-clock model,
[`../03-time-based-concept/decisions.md`](../03-time-based-concept/decisions.md) D-01 to D-34, stay
binding and untouched. Nothing here reinterprets one of them.

## A. Where video sits in the project

V-01 — The video is the source. The sampled frames are a cache.
The downloaded video file is kept; the sampled frames are written from it and can be written again
at any sampling granularity. This is the same shape as the wall-clock rule that `events.json` is the
piece and the matrix is a view of it. A video compresses far better than the same frames saved one
by one, so keeping it also costs less disk, not more.

V-02 — Reading a video produces `events.json` and nothing else.
The video path is a new way to produce the transcription, not a new pipeline. Onsets and releases in
seconds go into the same file the model writes, through the same writer. The hand split, the matrix,
the peaks, the ladder and the sheet are untouched and do not know where the notes came from.

V-03 — One piece, one audio uuid, and the audio always comes too.
The video lives inside the audio folder of the piece it belongs to, at `data/audio/<uuid>/video/`.
One YouTube URL gives one piece: the video, and the audio of that same video beside it. There is no
second kind of piece and no second library.

The audio is not optional and the user is never asked for it. The Piano Sheet tab offers to play the
original audio, and the piece has to have one for that to work. So the audio is extracted under the
hood, on the same download, and the user only ever sees the video in the video player.

V-04 — The sampling granularity is not `frameMs`.
`sampleMs` is how often we look at the video. `frameMs` is the column length the sheet is read at
(D-01). They are different numbers with different owners, they are never derived from each other,
and no code may use one where the other is meant.

## B. How time is measured

V-05 — Time comes from distance, not from the frame index.
A rectangle tip that is 37 pixels above the upper line in the frame at 12.300 s crosses it
37 / scrollSpeed seconds later. The onset is `frameTime + (upperLine - tip) / scrollSpeed`. So the
precision of an onset is set by the scroll speed and the pixel grid, not by the sampling
granularity, and 10 frames per second is enough to place a note within a few milliseconds.

V-06 — The scroll speed is measured, never assumed.
It is estimated for every pair of consecutive sampled frames, from the vertical shift that best
aligns the roll band of one with the next. The series is stored. A video whose scroll speed is not
stable is reported as such and is not transcribed silently.

V-07 — Every rectangle is measured in every frame it appears in, and the note is the median vote.
A rectangle is visible for two or three seconds before it reaches the upper line, so at 10 frames
per second it gives twenty or thirty independent estimates of the same onset. The note takes the
median. One bad frame — a sparkle, a flash, a hand — cannot move it.

V-08 — Nothing is trusted inside the halo guard band.
The band of pixels just above the upper line holds the light the animation emits when a key is
struck. Inside it, a rectangle tip is not read from the pixels; it is extrapolated from the votes of
the frames before. The height of the band is a calibration value, measured per video.

## C. The piano overlay

V-09 — **Superseded by V-37 on 2026-09-14, at the user's direction, by implementation 05.** The
text is kept so that the tasks of 04 that cite it still read; nothing new may cite it.
~~The user calibrates the piano overlay. The app never finds the keyboard by itself in v1.
The user places one white key and one black key, presses render the piano, and cuts the overlay on
the left and on the right. This is the twin of D-09: the app presents, the user decides. Automatic
keyboard finding is a later suggestion the user may accept, never the default.~~

V-10 — Pitch class comes from the black key pattern; the octave comes from the user.
The pattern of two and three black keys fixes the pitch class of every white key with no ambiguity.
Only the octave is free, and it is one dropdown with a default guessed from the number of keys. No
pitch is ever inferred from a colour.

V-11 — The upper line is part of the calibration, and it is one horizontal line.
By default it is the top edge of the rendered piano overlay. The user may move it. It is fixed for
the whole video: the keyboard does not move in these renderings, and a video where it does is out of
scope.

V-12 — The calibration is kept beside the video, never inside `rhythm.json`.
The overlay, the upper line, the halo guard band, the sampling granularity and the scroll speed are
how the notes were read off the screen. What a reader decided about the sheet is a different thing
with a different file (rule 1 of the wall clock). Re-reading the video is allowed to replace the
piece; it may never touch the reader's marks except through the ordinary version rule.

## D. Detection

V-13 — Detection runs per vertical lane, with a margin on both sides.
A lane is the strip of the frame between the left border and the right border of one key, widened by
a margin, and cut at the upper line. The lanes are independent, so the work is parallel. The margin
is there because these rectangles are not drawn exactly on the key: some are wider than the key they
belong to.

V-14 — A rectangle belongs to the key whose midpoint is nearest its own midpoint.
The overlay gives a midpoint in x for every white key and every black key. A run found in a lane is
attributed by midpoint distance, so a rectangle seen from two lanes is counted once, on the right
key.

V-15 — Everything static is subtracted before anything is detected.
The background plate is the per-pixel median of frames spread over the whole video. Titles,
watermarks, logos, moons, decorative scrolls, the octave guide lines and the steady part of the glow
line are in every frame, so they are in the plate, and they are gone from the difference. This is
the first line of defence against false positive notes, and it costs one pass over a few dozen
frames.

V-16 — A run that ends exactly at the upper line has not got a tip there; it has been cut there.
Rectangles are drawn under an overlay that hides whatever passes the upper line. A run whose lowest
row sits on the upper line is a rectangle that already crossed, so it is sounding, and its real tip
is in the past. Reading that edge as a tip is the single easiest way to invent an onset.

V-17 — Hands are never read from the colours of the rectangles.
Many of these videos colour the left hand and the right hand differently, and the app already has a
way to split hands (D-31). The colour is used, if at all, as a second check that a run is a note at
all — never for which hand plays it.

## E. How a rule earns its place

V-18 — The frame window rule is the contract, and both sides obey it.
Given an upper line `U`, an offset line `d` pixels above it, and a rectangle whose last tip is at
`yTop` and whose tip is at `yBottom` — with y growing downward:

- onset in this window: `U - d <= yBottom < U`
- sustain in this window: `yBottom >= U` and `yTop < U - d`
- released in this window: `yTop >= U - d`
- anything else: released, and nothing is written

The person annotating an example applies this rule and the detector applies this rule. A
disagreement is then about what was seen, never about what the words mean.

V-19 — Released is the default and is never written down.
A key that is not marked onset and not marked sustain is released. There are two labels, not three.

V-20 — A rule ships with its measured score, or it does not ship.
Every threshold and every extra check is reported as what it did to the score over the example set:
how many onsets it found, how many it invented, how many it lost. A rule that is asserted and not
measured is not a rule.

## F. What Phase 1 measured

V-21 to V-25 were added by Phase 1, from
[`04-phase-1-implementation.md`](04-phase-1-implementation.md). Every one of them
has a measurement behind it, as V-20 requires.

V-21 — Classical computer vision per vertical lane, on the background plate
difference. No learned model.
The academic field that reads a piano from video reads a real keyboard, where
the key itself barely moves, and it needs a model to do it. We read a drawing
made on purpose to be read, whose geometry the calibration hands us. The plate
difference is the only foreground rule that does not care how a rectangle is
filled — solid, shallow, outlined, gradient or shining — because it does not
look at the rectangle, it looks at what changed. The gradient stays as a second
channel for the outlined styles. No new dependency, no GPU, no cloud.

V-22 — Every geometric threshold is in white key widths, never in pixels.
The white key width is the one length the calibration always knows, and every
other length in these pictures is a multiple of it: a black key is 0.58 of it, a
rectangle is 0.62 or 1.03 of it, the roll is about twelve of it, the halo guard
band is about 1.75 of it. The example screenshots are 3600 px wide and the videos
are 1280, so a threshold in pixels is a threshold that is right on one of them and
wrong on the other.

V-23 — The rectangles are read high in the roll, never at the upper line.
Twenty of the twenty one examples light the upper line when a key is struck, and
the light is exactly where the rectangle tip is. Counted per white key width of
band height, on the same music, the detector finds two and a half times as many
runs at the upper line as it does high in the roll, and the extra ones are all
halo, strike light and sparkles. There is no reason to pay that: a rectangle is
on the screen for over three seconds — more than thirty sampled frames — before
it reaches the upper line, and up there the picture is clean. This is the
constructive form of V-08: V-08 says do not trust the guard band, V-23 says
where to look instead.

V-24 — The halo guard band is a calibration value, and its default is 1.75 white
key widths.
Measured on all twenty one examples: the band lit in the lane of a key that has
just been struck is 1.73 white key widths at the median and 4.14 at the worst,
and it is zero on the plain Synthesia rendering. The plan's first guess, 12 rows,
is 0.48 white key widths — about a third of what is needed at the median. Because
the range is zero to four, it cannot be one number for every video; it is
calibrated per video, with 1.75 as the value it starts at.

V-25 — On a video the offset line is not a free parameter.
It is the measured scroll speed times the sampling granularity, and nothing else.
The annotation page of Task 2.2.2 lets the user drag it because one screenshot has
no measured speed, and dragging it is how we test that the detector follows the
window. A video has a measured speed, so the window is determined: set it wider
and the same onset is reported in five consecutive frames, which took the onset
rate from 8.6 to 29.9 per second on a real piece.

V-26 — Two rectangles touching are two notes, and nothing may close the gap between them.
Two notes in a row on the same key are drawn as two rectangles with nothing between them but their
own dark borders. Measured over sixty sampled frames of a real video: the gap inside one rectangle
is 1 to 2 rows and there are 927 of them, and the gap between two rectangles is 3 to 7 rows and
there are 1351 of them. Any rule that closes a gap of three rows or more turns two notes into one
and loses the second onset without a sound, which is the worst way to lose one. So `gapClose` stays
under three, and where the border never gets dark enough to break the run by itself, the run is cut
at it: a row that is a local minimum below `tauValley` of the run's own median is a border, not part
of either rectangle.

V-27 — One key, one lane, one answer.
A rectangle is visible from the lane of its own key and from the lanes either side of it. Reading
every lane and then sorting the runs by nearest key midpoint keeps three answers about one
rectangle, and because each lane cuts it into pieces differently, the three disagree. Measured on
one frame: a merged run of 159 rows sitting on top of the four correct ones, and 23 pairs of runs on
the same key overlapping. So the lane of a key is read once, for that key, and V-14 is applied as a
filter: a run centred nearer another key is dropped here, because that key's own lane will find it.
Two runs on one key can then never overlap, because they come from one profile.

V-28 — The roll is bounded above as well as below, and both edges are measured from motion.
A video may carry a toolbar, a progress bar, a title band or a letterbox over the top of the
picture. Nothing above the roll top is music, and a rectangle coming into view appears at that line
rather than at the top of the picture. The roll top is found the only way that cannot be fooled by
what the chrome looks like: the roll scrolls by one frame of travel between sampled frames and
nothing else does. The same measurement gives the other edge, because the strike light at the upper
line does not move either, so it also measures the halo guard band of V-24 instead of defaulting it.

V-29 — **Superseded by V-44 on 2026-09-16.** The text is kept so that the reports that cite it still
read; nothing new may cite it. Its assumption — that the rectangles are lighter than the roll behind
them — is exactly what fails on a roll drawn over a photograph.
~~The background plate is a low percentile, not the median, and it is built from enough frames.~~
V-15 said the median of about 50 frames. A lane that holds a long note is lit in more than half the
frames at some rows, so the median of those pixels is the note: the plate goes bright in bands, and
the difference against it lays dark bands across a held rectangle that the detector then cuts at, in
the same place in every frame. Measured on the lane that broke, the brightest hundredth of the plate
sits 62.5 above the floor at the median of 50 and 7.7 at the 20th percentile, and frame to frame
agreement over 120 sampled frames goes from 90.6% to 98.2%. The plate is the per-pixel 20th
percentile of about 100 frames. This assumes the rectangles are lighter than the roll behind them,
which is true of all 21 examples and both videos; a rendering that drew dark notes on a light roll
needs the percentile taken from the other end, and the way to tell is which way a frame differs from
the plate.

V-30 — A rule may flag a run. It may not quietly delete one.
The halo guard band was written as a deletion: a run inside it was not a note. It cost a real onset
— on one example the rectangle is 43 rows tall and the guard band is 68, so a whole legitimate
rectangle sat inside the band and disappeared. V-08 says the tip inside the band is extrapolated
rather than read, and that is a flag on the run, not a reason to throw the run away. A lost note is
worse than a doubtful one, because a doubtful one can still be argued with later and a lost one
cannot.

V-31 — Frame to frame agreement is the score when there is no ground truth.
A rectangle falls by exactly the scroll speed between one sampled frame and the next, so a run at
rows y0 to y1 must reappear at y0+s to y1+s with the same height. A run that does not is a run the
detector cut two ways on two pictures of the same rectangle. This needs no labelling, it runs over a
whole video, and it is what every threshold in the detector is tuned against. Runs that are supposed
to change shape are left out of the count: one being cut by the upper line, and one still coming
into view at the roll top.


V-32 — The piece is read from the stitched roll, not from a tracker.
The scroll speed is constant to 0.3% over a piece, so the top `scrollSpeed x sampleMs` rows of each
sampled frame are exactly the strip of the roll nobody has seen yet. Piling them up rebuilds the
whole piece as one tall picture whose vertical axis is time, and a note is one connected shape in it
whose top and bottom rows convert straight to seconds. Measured: 268 of 268 shapes in thirty seconds
were notes, none had to be thrown away, their widths were the two widths the rendering uses and
nothing else, and every one sat within 0.17 white key widths of a key midpoint.

It replaces the frame to frame tracker of Task 4.1.1, and the three awkward cases that task names
stop being cases: a rectangle that appears already crossing is a shape touching the bottom edge, two
notes on the same key with a small gap are two shapes with a gap between them, and a rectangle
taller than the roll band is one shape because the stitched roll has no band.

The strip is taken well below the roll top and far above the upper line, so no halo, no sparkle and
no strike light enters it at all — which is V-23 applied to the whole piece at once.

It is also the cheaper of the two: it reads one strip per frame instead of the whole roll, about a
thirtieth of the pixel work, and replaces per-frame tracking with one labelling pass. Its cost is
memory — a four minute video stitches to about forty thousand rows, roughly 50 MB as one grey
picture — and the user accepted that.

It commits to one scroll speed for the whole piece. V-06 already refuses a video whose speed is not
stable, and that refusal is now also what protects this.

V-33 — A rectangle falls. Anything that does not fall is not a note.
*(Refined by V-42: an edge the picture pinned is not evidence.)*
A song title, a watermark, decorative scrollwork and an octave guide line all look like rectangles to
a detector that only ever sees one picture, and on `more-examples-3` 34 of the 49 runs found are
lettering. Two pictures settle it without any appeal to what the thing looks like: a run is believed
when a neighbouring sampled frame holds the same run, on the same key and at the same height, one
frame of travel away, and refused when a neighbouring frame holds it in exactly the same place.

Both neighbours are asked, not only the one before. A rectangle at the top of the roll has no frame
before it that holds it, but the frame after it holds it one travel lower, and that answers just as
well.

The travel is voted for by the runs, never taken from a correlation of the pictures. Measured on the
three frames of *Ode to Vivian*: the title is drawn in letters a hundred pixels tall across the
middle of the roll, so a correlation that still contains them peaks at a shift of nothing — the
letters really did not move — and it answered nought. The runs have no such problem: the travel is
the shift at which the most of them line up, with a shift of nothing excluded on purpose. It came out
at 68 px between the first pair and 51 between the second, so one number for all of them would have
been wrong as well.

Measured: 16 of 49 runs on one of those frames did not move at all, and every one of them is
lettering. The slack when matching is 5 px — at 3 the vote is stable but a few real notes are missed,
at 7 it collapses, because that much slack lets a letter match itself at a small shift.

The rule refuses; it does not select. Only a run **proven** to have stood still is thrown out. A run
with no neighbour to ask is kept, because the absence of an answer is not an answer. Measured over
the three frames: refusing the proven static ones drops 42 runs of 174 and not one of them is a
rectangle, while keeping only the proven moving ones would drop 128 and 28 of those are rectangles.

This is the same fact V-31 scores the detector with, used as a filter instead of as a score, and it
is the same fact V-15 relies on. A background plate removes what never moves and this removes what
moves too little; a video that is too short to build a plate from still has this.

V-34 — A rectangle in the neighbouring frame is the past of at most one rectangle in this one.
Without that constraint the momentum rule aliases and throws away real notes. When a key is struck
twice and the two strokes are about one frame of travel apart, the rectangle of the first stroke
sits — in the frame before — exactly where the second stroke's rectangle sits now. The second stroke
then looks like it never moved. So the frames are matched one to one, best fit first, and a rectangle
that is already spoken for as the predecessor of the rectangle below is not evidence that anything
stood still.

Measured on the three frames of *Ode to Vivian*: without the constraint one real rectangle of 174 is
refused as static; with it, none. The check is independent of the rule: the rectangles of that piece
are blue and its title and scrollwork are white, so the colour of a refused run says whether the
refusal was right. Not one refused run is blue. Colour is used to check the rule and never to decide
anything (V-17).

The aliasing gets worse the further apart the frames are, because the chance that a stroke spacing
lands on the travel grows with the travel. These three screenshots are 51 and 68 px apart; a video
sampled at 10 frames per second travels about 17 px, so there is far less room for it there.

## G. What Phase 2 measured

V-35 and V-36 were added by Phase 2, from
[`04-phase-2-implementation.md`](04-phase-2-implementation.md). Both have a measurement behind them,
as V-20 requires.

V-35 — A picture is read at one width, and the browser is served that same picture.
The example screenshots are 3600 px wide and a downloaded video is capped at 720p. Every picture is
resized to 1280 px wide before anything reads it, and `GET /frame-examples/{slug}/image` serves that
same copy, so a coordinate the user places in the calibration UI is the coordinate the detector
reads, with no scaling anywhere between them. This is V-22 applied to coordinates instead of to
lengths: V-22 puts every length in white key widths because the two sources differ in size, and this
removes the difference for the one thing that cannot be expressed that way, which is where something
is in one picture.

The derived copy is a cache and is gitignored. The calibration and the hand readings beside it are
not: a reading made by a person cannot be reproduced.

V-36 — The colour of a run is a switch, not a step.
Task 2.3.4 asked for the colour of a run compared against the palette of rectangle colours collected
from the picture, as a second reason to believe a run is a note, and said it ships only if the score
board improves. Measured on the ground truth that exists: it refuses 2 runs of 31 and changes no
verdict — 5 onsets found and 0 invented either way. So it does not ship as a step of the detector; it
ships as a switch on the page that is off, and the same is true of the gradient channel, which on
these two examples finds nothing on its own and invents five onsets with the hollow fallback on.

This is not a verdict on either of them. The examples they were proposed for — the five outlined
renderings for the gradient, and the one whose rectangles change colour with their height for the
palette — are among the twenty-one with no hand reading. Both stay reachable so the question can be
answered the moment those readings exist, and neither may be turned on without a number (V-20).

## H. Changed by implementation 05

V-37 and V-38 were written on 2026-09-14 from the brief of
[`../05-piano-overlay-from-black-keys/05-prompt.md`](../05-piano-overlay-from-black-keys/05-prompt.md),
at the user's direction. V-37 replaces V-09. Neither is a measurement; both are the user's decision,
like V-01 to V-20. What implementation 05 measures is added below them by its Phase 1, as V-20
requires.

V-37 — The user places one rectangle over the piano area, and the app finds every key inside it.
This replaces V-09. The user drags one rectangle — resizable and rotatable, so it can take whatever
shape the picture needs — over the piano, once, because the piano is static for the whole video.
Everything inside it is found: the black keys first, because they are the strongest thing in the
picture, the pattern of twos and threes from them, the keys a hand covers by extrapolation checked
back against the pixels, and the white keys from the black keys or from the thin dark lines between
them, whichever scores better over the example set. The user still decides three things and the app
never does: where the rectangle is, the octave of the leftmost key (V-10 stands), and where the
upper line is (V-11 stands). The user corrects a wrong overlay by reshaping the rectangle, and when
the found overlay misses completely, by taking any white key border — the thin dark line between two
white keys — and dragging it; the borders of the whole piano are open to that, one at a time. A hand
correction is stored as the border it made and is marked as the user's, and a picture that needs one
is still named on the score board as a finder defect, because the finder is what has to be right.

Why V-09 was wrong: it rested on a grid — one white key, repeated across the picture — and the
cameras that record these videos are not square to the keyboard. Perspective makes one white key
wider than another and some pianos sit at a slight diagonal, so no uniform grid fits either, and no
amount of nudging makes one. Phase 1 of 04 measured the octave period in the three thirds of every
picture and found it differs by 3.4% at the median and 5.2% on `airplanes`, which over 52 white keys
is up to two and a half white keys of drift from one end to the other. Finding the keys where they are
is the only thing that fits, and finding them is not a job the user can do 88 times per picture.

V-38 — The overlay is per-key borders, and the white key width of V-22 is two lengths.
`Calibration` carries the left and the right border of every key, not a left border, a white key
width and a count. V-13 stands word for word — a lane is the strip between the left border and the
right border of one key, widened by a margin — and only where the two borders come from changes: the
key's own borders, from the list. The lane stays a vertical strip of the picture, because the roll is
drawn by the software over the video in screen space and falls straight down whatever the camera did
to the piano; implementation 05's Phase 1 measures that on the tilted pictures before anything is
built on it.

V-22 said every geometric threshold is in white key widths, and that the white key width is the one
length the calibration always knows. There are now two. The **median white key width** is what
`whiteWidth` means, derived from the borders and never set by hand, and it is the unit for every
length that is not about one key: the minimum height, the clip tolerance, the halo guard band and the
offset line defaults. The **local white key width** — the width of the key being read, or for a black
key the mean of the two white keys it stands between — is the unit for every length that is about one
key: the lane margin, the extent window and the width gate. On 23 of the 24 pictures the two differ by
under 5%, inside the noise every threshold was measured with; on the tilted pictures they differ by
more, and that is the point.

## I. What implementation 05 measured

V-39 to V-41 were added by Phase 1 of implementation 05, from
[`../05-piano-overlay-from-black-keys/05-phase-1-implementation.md`](../05-piano-overlay-from-black-keys/05-phase-1-implementation.md)
and the evidence in [`../../../poc-piano-overlay/RESULTS.md`](../../../poc-piano-overlay/RESULTS.md).
Every one of them has a measurement behind it, as V-20 requires.

V-39 — The rectangles fall vertically in the picture, so a lane is a vertical strip whatever the
camera did to the piano.
Measured on all 24 pictures: the median lean of the strong near-vertical edges in the roll — the
sides of the rectangles and of the light beams — is within 0.4 degrees of vertical on 21 of 24 and
within 1.8 degrees on the other three, where the spread says most of those edges are scrollwork and
lettering rather than rectangles. The white key borders lean under 1 degree on every picture, and on
`airplanes` the lean changes from 0.8 degrees at the left to 0.3 at the right, which is perspective
and not rotation. So V-13 stands word for word and the lane of a key is the vertical strip of the
picture under the point where that key's top edge sits; the one rectangle's angle is there for a
picture this set does not contain, and every one of these 24 was rectified at zero.

V-40 — These pictures use two families of black key placement, and the black keys alone say which.
Measured against 901 white key borders read by hand in the front of the keys: on 23 of the 24
pictures each black key sits at the same offset from the white key border it stands on, in local
white key widths — C# at −0.095, D# at +0.100, F# at −0.131, G# at +0.009, A# at +0.137 at the
median, with no picture more than 0.05 from the median on any key. That is the family of a real
piano, where the two black keys of a group sit symmetric about D and the three about G#, and it is
what 04's `REAL_BLACK_OFFSETS` guessed to within 0.02. The one exception is `derulo`, a drawn
Synthesia keyboard whose five offsets are all within 0.03 of zero: its black keys sit on the
boundaries. The family that cuts the octave into twelve equal slots, whose F# would sit at −0.21, is
not used by any of the 24. The two families are told apart from the black keys alone: the gap
between two groups over the gap inside a group is 1.98 on `derulo` and 1.49 to 1.56 on every other
picture, so a threshold at 1.75 never has to be tuned.

V-41 — The white keys are derived from the black keys, route A, and the thin dark lines stay as the
tool the truth is read with.
Both routes were built and scored on the same truth. On the only borders both can be measured on
independently — the 265 borders visible at the top edge, between two white keys with no black key
over them — route A is 0.031 white key widths off at the mean and route B 0.024, a difference of a
fifth of a pixel at 1280 px wide. On the 901 borders of the front truth route A is 0.031 at the mean,
0.24 at the worst, and not one border is off by more than the lane margin of 0.25; route B cannot be
scored there because the truth is its own reading with the eye's corrections. What decides it is what
each route rests on: the black keys were seen on 811 of 845 keys, 96.0%, and the 34 a hand or a
pressed key hid were placed from the pattern and 26 of them confirmed by the pixels; the front lines
were readable on 901 of about 1230 borders, 73%, because the hands cover the front of the keys far
more than the black key band, and every border route B has to fill it fills with route A's own rule.
So route A ships, and the line reader is kept in the spike as the truth's tool, not in the app.

## J. What Phase 3 measured

V-42 and V-43 were added by Phase 3 of this implementation, from
[`04-phase-3-implementation.md`](04-phase-3-implementation.md). Both have a measurement behind them,
as V-20 requires, and both come from the same thing: Phase 3 is the first time these rules ran on a
real video rather than on a screenshot.

V-42 — A pinned edge is not evidence, on either side.
The momentum rule of V-33 compares two edges of a run against the same run in a neighbouring sampled
frame. A run cut by the upper line has not got a tip there, it has been cut there (V-16), so its
lowest row is the line and not the rectangle: it stays at the same row however fast the rectangle
falls. A run still coming into view at the roll top (V-28) has the same problem at its other end. So
the edge the picture pinned is left out of the comparison and the free one decides; a run pinned at
both ends — a rectangle taller than the whole roll — has nothing that can move, so nothing fits it
and it stays `unknown`, which is V-33's own answer.

Measured on the 4.5 minute video Phase 3 read. Comparing both edges, the rule refused 80 runs in a
fourteen second stretch and **every single one of them was clipped**: with the bottom pinned at the
line on both sides a falling rectangle can never be shown to have fallen, so it can only ever be
refused or left undecided. Over the same stretch it decided 90% of runs; with the pinned edge left
out it decides 97%, 583 clipped runs move from `unknown` to proven `fell`, and seven runs in the
middle of the roll are refused for the first time — all seven inside the halo guard band, which is
where the strike light is. Over the whole video, frame to frame agreement (V-31) goes from **94.3%
to 97.1%** and the sustains kept go from 9992 to 10325.

This is V-30 applied to V-33: refusing a run on an edge that cannot move is a deletion on evidence
that is not evidence.

V-43 — A pair of sampled frames the roll did not move in is a rest, not a measurement.
V-06 says the scroll speed is estimated for every pair of consecutive sampled frames and the median
is taken, and Phase 1 judged a pair usable by how sharp its correlation peak is. That is not enough
on a whole piece: two pictures of the same silence correlate perfectly with themselves at a shift of
nothing, so a rest answers *sharply* that the roll did not move. Measured on the 4.5 minute video:
of 2727 pairs, 726 answer sharply and 219 of those answer nothing at all, which puts the quartiles
100.5% apart and calls a perfectly steady video unstable. With the still pairs counted and left out
of the median, 507 pairs answer, the quartiles sit **0.74%** apart and the answer is 168.9 px/s.

The floor is not a tuned number: 0.5, 1 and 2 px all keep exactly the same 507 pairs. It is the same
fact V-33 rests on — a shift of nothing is not an answer — used on the pictures instead of on the
runs, and the count of still pairs is reported, because how many there are says how much of the
video is silence.

## K. What the second rendering measured

V-44 to V-46 were added on 2026-09-16 from
[`04-second-rendering-study.md`](04-second-rendering-study.md), the study of a roll drawn over a
photograph, at the user's direction. Every one of them has a measurement behind it on both videos,
as V-20 requires.

V-44 — The background plate is the median of what stands still.
This replaces V-29. About 150 frames spread over the video, each read with the two sampled frames
either side; a pixel of a frame counts only where it did not change across those neighbours, so no
moving edge of a rectangle is on it, and a frame whose roll changed on fewer than 0.2% of its pixels
is a rest, a title card or an end screen and is left out whole. The plate is the per-pixel median of
what counts.

Why V-29 was wrong: the 20th percentile per colour channel assumes the rectangles are lighter than the
roll in every channel. On a mid-grey photograph a blue rectangle is darker in red and green, so once a
lane held one in a fifth of the frames the plate took the rectangle's colour in those channels and the
lane inverted: the empty roll read as foreground, the rectangle as background, and the column became
one tall shape cut every 94 ms. Measured: the lane of the most played key was foreground in 92% of
frames under the percentile and 39% under the median, while the keyboard lit it in 35%; the reading
went from 4967 notes with 68% not on the keyboard to 1492 with 6.5%. Why not a longer stillness — the
first idea, a value held longer than a rectangle can fall: in a busy lane the background is never
still that long, and on the plain video an end screen and a chord held longer than the roll is tall
both took over the lanes they sat on. Two frames either side keeps 74 background votes a pixel at the
10th percentile on one video and 97 on the other. What it cannot do: a key held still for more than
half the piece would enter the plate; the reading names any lane foreground over six tenths of the
time rather than trusting it.

V-45 — The rectangles measure their own scroll speed.
V-06 stands — measured for every pair of consecutive sampled frames, the series stored, a video that
is not stable refused — and only the method changes: every run of a frame is followed into the next
frame one to one, the way the momentum rule already does (V-33, V-34), and the fall of every free edge
(V-42) is collected. The per-pair mean is the series and the mean over every followed edge is the
answer. A pair with fewer than six followed edges is unusable and is reported rather than averaged
in. Measured on the photograph: the correlation of row profiles answered 6 usable pairs of 1891 with
the shipped plate and 15 with a right one, and four profiles disagreed by 4%, because the light
swirls the rendering animates and the glow band at the line move — but not with the roll — and pull
the correlation; the followed edges answer 48 396 times over 1815 pairs, 20.22 px per frame, the same
to 0.05 px in each third of the piece. This is V-33's own sentence — *the travel is voted for by the
runs, never taken from a correlation of the pictures* — applied to the speed.

V-46 — A valley is measured against the plateau beside it, and an extent against the key's own core.
Two rules that did not do what the plan said. V-26 says a border is a dip below *the plateau on both
sides of it*; what was built measured it against the brightest row of the whole run on each side, so
on a rendering whose rectangles brighten as they fall, the 8% step at every seam between two strips of
the stitched roll read as a 40% valley and cut a note in two: 270 false repeats on the photograph, 92
of them on the seam rows against 39 if they were spread evenly. The plateau is now read within half a
white key either side of the dip, and `splitProminence` is 0.30, the middle of the plateau on both
keyboards — at 0.40 under the local measure four real strikes go, because five short repeats on one
key merge into one note. On the plain video this changes 3 notes of 4295: its own cuts form a comb at
the beat and are real borders, so Phase 4's count stands. And the extent of a rectangle was measured
against the brightest column of the window, which on a rendering that draws a light rim around a
darker fill is the rim: at half of it only the rim passed, the run read a third of a key wide and the
piece's second note was refused as too narrow. It is now measured against the median of the columns
within a quarter key of the key's own centre. Both are measured in section 3.3 and section 4 of the
study.
