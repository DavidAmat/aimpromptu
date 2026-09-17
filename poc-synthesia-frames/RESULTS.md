# Results — Phase 1

Every number here comes from [`out/run_log.txt`](out/run_log.txt), which is one
run of every script in [`scripts/`](scripts). The working resolution is 1280 px
wide, because Phase 3 caps the video download at 720p, so a threshold measured
here is a threshold at the resolution the detector will really see.

---

## 1. The casuistry catalogue, the measurable half

One row per example screenshot. `keys` and `first`/`last` are what the keyboard
finder made of the picture; `wkey` is the white key width in pixels; `roll` is
how many pixel rows there are above the upper line and `roll/key` the same in
white key widths; `contr` is how far the brightest hundredth of the roll sits
above its median; `chroma` is how far the roll's colours stray from grey;
`glow` is the band lit across the whole width above the upper line and `guard`
the band lit in a struck lane, both in white key widths; `lit` is the share of
the width that is lit on the row just above the upper line.

```text
example                  keys first last  wkey  roll roll/key contr chroma  glow guard  lit
7years                     88    21  108  24.6   295    12.0   239      5  0.28  1.95 1.00
airplanes                  89    31  119  24.6   312    12.7   209    164  1.67  3.14 1.00
derulo                     87    21  107  24.7   162     6.6   128    102  0.00  0.00 0.00
feather                    87    21  107  24.9   238     9.6   187    230  0.56  1.81 1.00
more-examples-1            87    21  107  24.9   249    10.0   143    156  0.40  0.48 0.94
more-examples-10           87    21  107  25.0   327    13.1   132     64  0.80  1.52 0.99
more-examples-11           85    23  107  25.1   269    10.7   146      4  0.16  3.18 0.61
more-examples-12           87    21  107  25.1   325    12.9   198     52  0.91  2.27 1.00
more-examples-13           87    21  107  24.9   293    11.8   181     69  0.80  1.73 0.99
more-examples-14           87    21  107  24.7   358    14.5   157    108  0.77  1.79 1.00
more-examples-2            87    21  107  25.0   237     9.5   143    206  0.60  1.08 1.00
more-examples-3            87    21  107  24.9   184     7.4   253    209  0.56  0.72 1.00
more-examples-4            85    23  107  25.1   171     6.8   153    136  0.64  0.80 1.00
more-examples-5            87    21  107  24.8   360    14.5   254    145  0.56  0.65 0.99
more-examples-6            87    21  107  24.9   312    12.6   166    200  0.80  2.78 1.00
more-examples-7            87    21  107  24.9   324    13.0   249      6  1.05  4.14 1.00
more-examples-8            87    21  107  24.7   316    12.8   152    168  0.69  1.89 0.99
more-examples-9            87    21  107  24.9   294    11.8   104    185  0.40  0.48 0.97
not-immediate-strokes      87    21  107  25.0   185     7.4   237      6  1.00  3.40 1.00
shut-up-and-dance          56    33   88  38.7   376     9.7   170    130  0.21  0.88 0.97
superestrella              72    24   95  30.6    14     0.5    21     40  0.26  0.39 0.60
```

The half a human has to read is in the phase report, section 2.

What the table says:

- **Nineteen of twenty one show a whole 88 key piano**, with the top C cropped
  off by the screenshot. Only `shut-up-and-dance` (56 keys) and `superestrella`
  (72 keys) show fewer.
- **The white key width is 24.6 to 25.1 px on all nineteen of them.** The two
  others are 38.7 and 30.6, because they show fewer keys across the same width.
- **The roll is about twelve white key widths tall** (median 11.8, from 6.6 to
  14.5). `superestrella` has 0.5, which means it has no roll at all: it is a
  crop of the keyboard and nothing can be read from it.
- **Four examples are grey** — `7years`, `more-examples-7`, `more-examples-11`
  and `not-immediate-strokes` have a chroma of 4 to 6. Colour is not available
  as a cue on one example in five.
- **The glow along the upper line is real on twenty of twenty one.** The share
  of the width that is lit on the row just above the upper line is 1.00 on
  thirteen of them. Only `derulo` has none.

## 2. Is the white key width the same across the picture?

Task 2.1.1 builds the piano overlay from one white key and one black key, which
only holds if every white key is the same width. The octave period was found
separately in the left, the middle and the right third of each keyboard.

```text
worst: airplanes at 5.2%
median spread: 3.4%
```

**A single white key width fits every example to within about 4%,** and the
worst case is 5.2%. A plain rectangle grid is enough; no perspective correction
is needed. The 3.4% floor is the measurement's own noise, not the keyboard's.

## 3. How far above the upper line is the picture unreadable?

```text
glow line, in white key widths: median 0.60 max 1.67
local bloom, in white key widths: median 1.73 max 4.14
the plan guessed a 12 row guard band = 0.48 white keys at this resolution
```

The glow line is the band lit right across the width. The local bloom is the
band lit in the lane of a key that has just been struck, and it is the one that
matters, because it is what covers a rectangle tip.

**The plan's first guess of 12 rows is about a third of what is needed at the
median and an eighth of what is needed at the worst.** In white key widths the
guard band is 1.73 at the median and 4.14 at the worst, and it is zero on the
plain Synthesia rendering, so it has to be a calibration value per video.

## 4. The five detectors

Nine examples chosen to span the catalogue: `derulo` and `shut-up-and-dance`
(plain Synthesia, solid rectangles, drawn keyboard), `7years` (solid, white on
black, heavy halo), `feather` (gradient filled, strong bloom),
`not-immediate-strokes` (outlined, heavy sparkles), `more-examples-9` (colour
changing with height), `more-examples-10` (shallow, low contrast),
`more-examples-12` (outlined, two colours), `more-examples-3` (a title and
decorative scrolls drawn across the roll).

All five share one run extraction, so the only thing that differs is how each
decides a pixel is not background. The pictures are in
[`out/detectors/`](out/detectors): `<slug>.jpg` is the band at the upper line,
`<slug>-high.jpg` the band high in the roll.

### 4a. At the upper line

The score is against the ground truth read by hand on the two examples where a
human can read the picture without guessing, with the offset line two white key
widths above the upper line.

```text
detector      on ok  on inv  on miss  sus ok  sus inv  sus miss
absolute          5       0        0       3        0         0
plate             5       0        0       3        0         0
edges             5       8        0       0        0         3
colour            5       0        0       3        0         0
single-row        5      56        0       0        0         3
```

These are the numbers after the rebuild of section 4e. Before it, the plate
difference found the same five onsets and invented seven.

**The single row watcher is not usable.** On `derulo`, the only example with no
glow at all, it gets all three onsets and invents three. On the other eight it
calls **every key on**, because the row it reads is the row the animation
lights. This is the approach most projects use, and everything else here beats
it.

**Three of the five now get both examples exactly right** — every onset and
every sustain found, nothing invented, nothing missed. The gradient still
invents eight and misses every sustain, which is why it is a second channel and
not the primary. The single row watcher is in a different league of wrong.

That the absolute threshold and the colour clustering also score perfectly here
does not make them equals: these are the two plain Synthesia examples, the only
two a human can label without guessing, and both of those masks collapse on the
glowing renderings. Section 4b is where they separate.

### 4b. High in the roll, and why that is the right place to look

The same nine examples, counting the runs in a band five white key widths tall
that starts three white key widths above the upper line, clear of the measured
guard band:

```text
example                absolute  plate  edges  colour
derulo                       12     10      4      10
shut-up-and-dance            10     10      8      10
7years                       13     16     10       7
feather                      13     15     14      13
not-immediate-strokes        16     15     22      12
more-examples-9              16     18     16      20
more-examples-10             16     16     13      14
more-examples-12             10      7     10       8
more-examples-3              36     33     21      37
```

and the same count in the band that ends at the upper line, 3.2 white key widths
tall:

```text
example                absolute  plate  edges  colour
derulo                       16     16      3      12
shut-up-and-dance            13     16      8      13
7years                       37     21     12      36
feather                      34     17      6      37
not-immediate-strokes        42     32     30      36
more-examples-9              47     25     10      43
more-examples-10             43     24     29      48
more-examples-12             37     26     30      35
more-examples-3              63     43     27      54
```

The music is the same in both bands, so the counts should agree once they are
put on the same footing. Per white key width of band height, the plate detector
finds **28 runs high in the roll and 69 at the upper line — two and a half times
as many.** Those extra runs are the halo, the strike light and the sparkles.

### 4c. Does a run look like a note?

There is no hand read ground truth high in the roll, and there does not need to
be one. Two things are true of a rectangle that stands for a key and of nothing
else in these pictures: it sits over that key's midpoint, and every rectangle of
the same kind in the same video is the same width as the others.

The second has to be asked per example. The two widths are a property of the
rendering, not of pianos: the test video draws its white key rectangles at 1.03
white key widths, `shut-up-and-dance` at 0.97, `derulo` at 0.83. So the question
is whether all the runs of one kind in one example agree with each other.

```text
detector    runs   on a key midpoint
absolute      69    69   100%
plate         71    71   100%
edges        246   246   100%
colour        70    70   100%
```

**Every run every mask finds sits over a key midpoint.** That is V-14, confirmed
on the screenshots as it is confirmed on the video.

Width agreement within one example, for the plate difference:

```text
derulo                  white 0.85 +-0.04
shut-up-and-dance       white 0.97 +-0.03   black 0.57 +-0.03
7years                  white 0.71 +-0.04
more-examples-9         white 1.11 +-0.16   black 0.64 +-0.24
more-examples-10        white 0.92 +-0.28   black 0.48 +-0.00
feather                 white 1.17 +-0.28   black 0.76 +-0.32
not-immediate-strokes   white 1.00 +-0.68   black 0.66 +-0.76
more-examples-3         white 0.68 +-0.97   black 0.66 +-0.80
```

On a plain rendering the detector agrees with itself to **±0.04 white key
widths**. On the glowing and decorated ones it does not, and `more-examples-3` —
a title and white scrolls drawn across the roll, which a single screenshot has no
plate to remove — is the worst. Those are the examples Phase 2's score board will
have to name.

The run counts here are much lower than the first version of this table reported,
and that is the fix rather than a loss: the first version counted the same
rectangle once per lane it was visible from. See section 4e.

### 4d. The two rules that earned their place

**The width gate.** A run whose whole rectangle is narrower than 0.35 or wider
than 1.40 white key widths is not a note.

```text
                  before      after
absolute      6 invented   3 invented
plate         6 invented   4 invented
colour        2 invented   1 invented
sustains      3 invented   0 invented  (absolute and plate)
```

It removes the strike sparkles, which spread over two or three keys and are
short, and the glow that spills sideways out of a rectangle into the lane next
door.

**The relative edge.** The rectangle is the bright part and the glow around it
is the dim part, so the edge of the rectangle is found against the run's own
peak rather than against a fixed threshold. A column belongs to the rectangle
when it reaches `tauEdge` of the strongest column of the run.

```text
tauEdge   runs found high in the roll   on a key midpoint
0.00                              104                 98%
0.35                              142                 99%
0.50                              140                 99%
0.65                              138                 99%
```

Turning it on finds **a third more rectangles** and costs nothing in
attribution. It is what lets the plate difference read `feather`, where it went
from 2 runs to 15, and `not-immediate-strokes`, from 6 to 15.

## 4e. What the video changed

Sections 1 to 4d are measured on the 21 example screenshots. A screenshot cannot
answer whether the detector says the same thing twice about the same rectangle,
and that turned out to be where the defects were. `test.mp4` — 90 seconds of
[pgLt4WmPMYQ](https://www.youtube.com/watch?v=pgLt4WmPMYQ), 1280x720, 900 sampled
frames, 168.9 px/s, 128 BPM — answered it, and the detector was rebuilt.

The measurement: **a rectangle falls by exactly the scroll speed between one
sampled frame and the next**, so a run at rows y0..y1 must reappear at y0+s..y1+s
with the same height. A run that does not is a run the detector cut two ways on
two pictures of the same rectangle. No labels, runs over a whole video.

```text
                                    onsets                sustains
                              found invented missed   found invented missed
the two hand read screenshots
  before                          5        7      0       3        1      0
  after                           5        0      0       3        0      0

test.mp4, agreement over 120 sampled frames
  before                       90.6%
  after                        98.2%
```

Five defects, in the order they were found. The full account is in
[`04-phase-1-implementation.md`](../context/implementations/04-synthesia-to-notes/04-phase-1-implementation.md)
section 11.

1. **Three answers about one rectangle.** Reading every lane and then sorting
   runs by nearest key midpoint keeps one answer per lane, and the three
   disagree. On one frame, key G2 carried a merged run of 159 rows on top of the
   four correct ones, and 23 pairs of runs on one key overlapped. Now a key's
   lane is read once, for that key.
2. **The edge search took its peak over the whole picture.** The brightest
   column in those rows is some other key's strike flash; it set the bar, this
   key's columns failed it, and the search walked off to whatever column passed
   — putting a run near the upper line on a key four semitones away. The window
   is now 2 white keys either side.
3. **The roll has a top.** This video carries a Synthesia toolbar over rows 0-28
   and a progress bar with a sliding playhead over rows 29-58. The roll begins at
   row 62. Found from motion, because the roll scrolls and the chrome does not.
   The same measurement gives the halo guard band: 39 rows, 1.59 white keys.
4. **The plate was eating held notes.** Key D#3 holds one long note and came
   back as four fragments cut at rows that never moved. The lane is lit in more
   than half the frames at 21 of its 499 rows, so the median plate goes blue
   there and lays dark bands across the held rectangle.

```text
plate                          agreement   runs/frame
median of 50 frames   (V-15)       90.6%         29.7
median of 200                      98.3%         28.6
20th percentile of 50              98.5%         28.0
20th percentile of 100             98.8%         28.0
```

5. **A rule that deleted notes.** The halo guard band was a deletion. On one
   example the rectangle is 43 rows and the band is 68, so a legitimate
   rectangle vanished and a real onset was lost. V-08 says the tip is
   extrapolated, not that the run is discarded, so it is a flag now.

### The gap between two stacked rectangles

The question that started it. Every gap between consecutive runs, every lane, 60
sampled frames, before anything is closed. 5767 gaps:

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

`gapClose` was 3 and closed **six** rows, merging all 1351 separators: a closing
with a structure of length L closes every gap shorter than L, and the structure
was `2*gap+1`. It is now `gap+1` with `gapClose` 2.

Where the border never gets dark enough the run stays whole and no gap rule
helps. Cutting below a share of the run's median was the wrong shape of rule:
key G2's plateau is 144 and its borders drop to 36, while key A#2's plateau is 88
and the texture inside a **single confirmed quarter note** ripples to 72.

**Prominence separates them** — how far a minimum drops below the plateau on both
sides, as a share of that plateau:

```text
texture inside one rectangle            0.01 to 0.13
the border between two rectangles       0.75 to 0.80
```

`splitProminence` is 0.40, with a factor of three of margin each way. Key G2
splits into four 40-row corcheas at every value from 0.20 to 0.55, so the answer
is not delicate. And it says no when the answer is no: the 78-row run on A#2 is
flat from end to end, so it is one negra at 79.2 px, not two corcheas merged.

```text
key G2  at 1:03   40, 40, 40, 39 rows           four corcheas
key A#2 at 1:03   21, 21, 59, 78, 79 rows       1, 1, 3, 4, 4 semicorcheas
key D#3 at 0:11.5 one run of 238 rows           a held note, not four fragments
```

## 5. The scroll speed — V-05 and V-06 hold

One video downloaded by hand: *Shut Up and Dance*, the same piece example
`shut-up-and-dance` was screenshotted from, 1280×720, 60 frames per second,
213.7 s, 9.6 MB. Sampled at 10 frames per second into 2136 frames.

```text
usable frame pairs: 1457 of 2135
shift per sampled frame: median 15.84 px, quartiles 15.73..15.91, spread 0.17 px
scroll speed: 158.4 px/s
5th..95th percentile: 15.39..15.97 px per sampled frame
```

The speed over the piece, in ten equal parts:

```text
  1   15.385      6   15.847
  2   15.826      7   15.801
  3   15.841      8   15.852
  4   15.822      9   15.851
  5   15.820     10   15.791
```

**The scroll speed is constant to 0.3% over nine tenths of the piece.** The
first tenth reads low because it is the intro, where there is little falling and
the measurement has little to bite on; the median over the whole series outvotes
it.

**It can be measured from a pair of frames**: 1457 of 2135 pairs answered
sharply, and the interquartile spread of the answer is 0.17 px, about 1% of the
speed. The rest are the quiet stretches, which have nothing to align.

What the spread costs in onset error, timing a tip with the median speed instead
of the true one:

```text
a tip   15.8 px up (one sampled frame):   0.4 ms at the upper quartile,   0.8 ms at the 95th
a tip  262.5 px up (half the roll):       6.4 ms at the upper quartile,  13.5 ms at the 95th
a tip  525.0 px up (the whole roll):     12.7 ms at the upper quartile,  27.0 ms at the 95th
```

And the size of one pixel: 1 / 158.4 s = **6.3 ms**. Placing an onset by the
frame it happened in, which is what every project surveyed does, costs ±50 ms at
10 frames per second. Reading it from the distance costs 6.3 ms per vote. That
is the whole of V-05, measured, and it is an eight fold improvement.

The roll is 525 px tall and the speed is 158 px/s, so a rectangle is on the
screen for **3.3 s before it reaches the upper line — 33 sampled frames at 10
frames per second**. V-07's "twenty or thirty independent estimates" is right.

## 6. The real background plate

The plate is the per-pixel median of 50 frames spread over the video, as V-15
says. In it, the octave guide lines show at x = 76, 348, 619, 890, 1162 —
five lines, 271 px apart, which is seven white keys, one octave. The plate finds
them exactly.

Running the detector over 300 sampled frames in the middle of the piece, with
the offset line set to one sampled frame of travel:

```text
                                            onsets per second
stand-in (the per-row median)                    11.8
real plate (the median of 50 frames)              8.6
```

**The real plate removes 27% of what the stand-in reports.** The score on the
screenshots is therefore a floor, not a ceiling: the four invented onsets left in
section 4 are all static decoration and all of them are the stand-in's fault.

The offset line is worth a note of its own. On a screenshot it is a free
parameter and the user drags it. On a video it is not free: it is the measured
scroll speed times the sampling granularity. Setting it to two white key widths
instead, as the annotation used, makes every onset show up in five consecutive
frames and the onset rate jump from 8.6 to 29.9 per second.

## 7. Stitching the frames into one roll

If the scroll speed is stable, the top 16 rows of each sampled frame are exactly
the strip of the roll nobody has seen yet, so piling them up rebuilds the piece
as one tall picture whose vertical axis is time. The strip is taken 40 rows down
from the top of the frame, which is as far from the upper line as it gets, so
there is no halo, no sparkle and no strike light in it at all.

[`out/stitch/roll.jpg`](out/stitch/roll.jpg) is ten seconds of the piece rebuilt
that way. Every note is one clean separate shape.

Thirty seconds of it, labelled with connected components:

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
- **The widths are the two widths a piano has**: 0.62 white key widths is a
  black key rectangle, 1.03 is a white key one, and nothing falls outside.
- **V-14 is confirmed with a number.** Every one of the 268 shapes sits within
  0.17 white key widths of a key midpoint, and the nearest wrong key is half a
  key away, so attribution by nearest midpoint has a margin of 0.33 white key
  widths on every note in the sample.
- 8.9 notes per second agrees with the 8.6 the per-frame detector reported, by a
  completely different route.

## 8. Disk

```text
video                      9.6 MB
frames at 10 per second   118   MB   (2136 frames, 720p, JPEG quality 3)
```

**The sampled frames cost twelve times the video**, and 33 MB per minute of
music. Sampling took 3.8 s of wall clock for 3.6 minutes of video. This is the
number behind V-01: keeping the video and treating the frames as a cache costs
less disk, not more.
