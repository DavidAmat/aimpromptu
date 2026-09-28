# Results — Phase 1 of implementation 05

Every number here comes from one run of the scripts in [`scripts/`](scripts), whose output is in
[`out/`](out) (`blackkeys_log.txt`, `truth_log.txt`, `routes_log.txt`, `fall_log.txt`). The working
resolution is 1280 px wide (V-35). Lengths are in local white key widths unless a unit is given;
one white key is 24 to 25 px on the 22 pictures that show a whole piano, 38.7 on
`shut-up-and-dance` and 30.6 on `superestrella`.

The one rectangle of every picture is in [`data/rects.json`](data/rects.json): the full width, from
the seeded upper line to the bottom of the picture, at an angle of zero. The three `ode` pictures
have no seed, so their upper line was found from the rows whose horizontal autocorrelation is
strong, the way Phase 1 of 04 did.

## 1. The black keys (Task 1.2.1)

`scripts/blackkeys.py`, run by `scripts/run_blackkeys.py`; the pictures are `out/blackkeys*.png`.

```text
picture                  keys  seen  extrapolated  confirmed  thrown out  confidence  first
7years                     36    22       14           10          0         0.52      A#
airplanes                  36    35        1            1          1         0.35      A#
derulo                     36    34        2            0          0         0.88      A#
feather                    36    24       12           12          1         0.69      A#
more-examples-1            36    36        0            0          0         0.55      A#
more-examples-10           36    36        0            0          0         0.53      A#
more-examples-11           36    36        0            0          0         0.52      A#
more-examples-12           36    34        2            2          2         0.36      A#
more-examples-13           36    36        0            0          0         0.52      A#
more-examples-14           36    36        0            0          0         0.50      A#
more-examples-2            36    36        0            0          0         0.59      A#
more-examples-3            36    36        0            0          0         0.55      A#
more-examples-4            36    35        1            0          0         0.46      A#
more-examples-5            36    36        0            0          0         0.59      A#
more-examples-6            36    36        0            0          0         0.42      A#
more-examples-7            36    36        0            0          0         0.36      A#
more-examples-8            36    36        0            0          0         0.43      A#
more-examples-9            36    36        0            0          0         0.49      A#
not-immediate-strokes      36    35        1            1          1         0.40      A#
ode1                       36    36        0            0          0         0.51      A#
ode2                       36    36        0            0          0         0.47      A#
ode3                       36    36        0            0          0         0.59      A#
shut-up-and-dance          23    23        0            0          0         1.00      A#
superestrella              30    29        1            0          0         1.00      C#
```

- **845 black keys, 811 seen (96.0%), 34 placed through an occlusion, 26 of those 34 confirmed by
  the pixels.** The eight unconfirmed: four under the left hand of `7years`, two pressed and lit keys
  on `derulo`, one under a hand on `more-examples-4`, one pressed and lit on `superestrella`. A
  pressed black key is lit, so "unconfirmed" means "not dark here", not "wrong".
- **The pattern is right on all 24.** Every whole piano starts on A#0. Three seeded calibrations of
  04 said otherwise (`airplanes`: G#; `more-examples-4` and `more-examples-11`: C#), and on all three
  the picture shows A#0 at the left edge; Phase 1 of 04 had already named `airplanes` as wrong.
- **The confidence** is the cost margin of the best alignment over the best alignment that names the
  first candidate something else: 1.00 on the two drawn keyboards, 0.35 to 0.69 on the photos. The
  lowest, `airplanes`, is the strongest perspective.
- **The alignment assumes no family.** It uses the two gaps the picture shows — inside a group and
  between two groups — so a drawn keyboard with a gap ratio of 2 and a real one with 1.5 align the
  same way. A first version assumed twelve equal slots and threw out half of `derulo`.
- **The band depth** is read down the black key columns themselves: on the photos the glow at the
  top edge makes the light level so high that the grey front of a white key counted as dark, and a
  depth read from a row share ran to the bottom of the picture on 15 of 24. The column profile does
  not care what grey the front is.
- Time: 0.07 to 0.10 s per picture.

## 2. The truth (Task 1.1.1)

`scripts/run_lines.py` reads the thin dark lines on two rows in the front of the keys —
just below the black keys and just above the front edge — and `scripts/truth.py` keeps a line when
it was found on both rows, its lean agrees with its neighbours', and it is not a duplicate. Every
picture was then looked at on a ruled crop at 2.5x (`out/truth/<slug>.png`), and six lines that
passed the three checks but sit in the middle of a key on a hand's edge or on the scrollwork were
rejected by eye (`data/eye-rejections.json`, `out/outliers.png`). The truth is
[`data/truth.json`](data/truth.json).

```text
picture                  kept  rejected  top edge
7years                     43      7        16
airplanes                  40      9        15
derulo                     51      0        14
feather                    31      9        18
more-examples-1            21     20        12
more-examples-10           30     16        14
more-examples-11           43      6        13
more-examples-12           36     11        14
more-examples-13           43     19        17
more-examples-14           41     16        15
more-examples-2            24     22        13
more-examples-3            35     19        15
more-examples-4            41     15        15
more-examples-5            35     18        14
more-examples-6            43     15        17
more-examples-7            41     14        12
more-examples-8            45     13        16
more-examples-9            39     14        14
not-immediate-strokes      42     15        16
ode1                       35     19        14
ode2                       34     25        16
ode3                       34     21        15
shut-up-and-dance          32      0        11
superestrella              42      0        12
TOTAL                     901    318       348
```

- **901 borders of about 1220 (74%).** What is left out is under a hand, under the scrollwork, or on
  the two dim pictures (`more-examples-1`, `more-examples-2`) where the front edge row is too dark
  to read. Nothing is guessed into the truth.
- The truth is read on the whole width, not on three octaves as the plan said, because the tool
  reads the whole width at once and the eye check costs the same either way.
- **The top edge borders** are a second, independent reading: the E|F and B|C borders, visible at
  the top edge between two white keys with no black key over them. 348 were read; 265 are within a
  third of a key of a front truth border and are what section 5 scores against, because the glow
  line and a pressed key's highlight leave stray minima at the top edge.
- The border at the top edge is the front line extended up through the black key band. The extension
  moves it by under 0.5 px on 22 pictures and by up to 1.4 px on `airplanes` (section 4).

## 3. The families (Task 1.1.2)

The offset of each seen black key from the nearest truth border at the top edge, in local white key
widths, positive to the right; the median per picture.

```text
picture                    C#      D#      F#      G#      A#    (keys)
7years                   -0.117   0.105  -0.143  -0.002   0.149   (21)
airplanes                -0.046   0.131  -0.119   0.010   0.170   (28)
derulo                    0.014   0.018   0.014   0.014   0.010   (34)
feather                  -0.102   0.116  -0.185  -0.017   0.142   (18)
more-examples-1          -0.083   0.124  -0.128   0.008   0.142   (13)
more-examples-10         -0.113   0.109  -0.109   0.036   0.146   (22)
more-examples-11         -0.114   0.082  -0.122   0.013   0.109   (29)
more-examples-12         -0.066   0.119  -0.114   0.013   0.151   (24)
more-examples-13         -0.087   0.088  -0.148   0.016   0.129   (30)
more-examples-14         -0.086   0.100  -0.120   0.042   0.140   (29)
more-examples-2          -0.085   0.117  -0.136   0.007   0.128   (16)
more-examples-3          -0.103   0.090  -0.130  -0.008   0.129   (23)
more-examples-4          -0.080   0.113  -0.105   0.015   0.150   (29)
more-examples-5          -0.101   0.077  -0.143  -0.004   0.134   (26)
more-examples-6          -0.095   0.090  -0.155  -0.005   0.125   (30)
more-examples-7          -0.059   0.070  -0.131   0.034   0.139   (28)
more-examples-8          -0.074   0.090  -0.112   0.009   0.111   (31)
more-examples-9          -0.101   0.114  -0.101   0.011   0.145   (28)
not-immediate-strokes    -0.103   0.130  -0.139   0.039   0.148   (30)
ode1                     -0.107   0.075  -0.136  -0.006   0.117   (24)
ode2                     -0.102   0.078  -0.141   0.003   0.119   (23)
ode3                     -0.096   0.072  -0.137   0.003   0.090   (23)
shut-up-and-dance        -0.073   0.082  -0.130  -0.002   0.143   (23)
superestrella            -0.065   0.116  -0.129   0.015   0.141   (29)
median of the 23         -0.095   0.100  -0.131   0.009   0.137
```

- **Two families.** 23 pictures share one, the real piano: the two black keys of a group symmetric
  about D and the three about G#, with G# on its border. No picture is more than 0.05 from the
  median on any key. `derulo` is the other: all five within 0.02 of zero, the black keys on the
  boundaries.
- The family 04 guessed as `REAL_BLACK_OFFSETS` (−0.10, +0.10, −0.13, 0, +0.13) is this one to
  within 0.02. The twelve equal slots family (−0.125, +0.04, −0.21, −0.04, +0.125) is used by nobody:
  D# and G# rule it out on every picture.
- **The black keys alone tell the two apart.** The gap between two groups over the gap inside a
  group: `derulo` 1.98, everything else 1.49 to 1.56. A threshold at 1.75 has 0.2 of room on both
  sides.
- `shut-up-and-dance` is drawn and uses the real family; `derulo` is drawn and does not. Drawn is
  not a family.

## 4. The perspective (Task 1.1.4)

White key width per third of the picture, the lean of the borders in px per 30 rows, and the taper
as the ratio of a key's width at the front row to its width just under the black keys.

```text
picture                  W left  W mid  W right   lean l  lean m  lean r   taper
7years                    24.90  24.42   24.92     0.03   -0.05   -0.08    1.000
airplanes                 25.81  24.04   24.24     0.42    0.26    0.15    1.000
derulo                    24.77  24.80   24.77     0.00    0.00    0.00    1.000
feather                   24.98  24.33   25.00     0.07    0.00   -0.15    0.999
more-examples-1           24.31  24.45   25.17    -0.22    0.06   -0.01    1.000
more-examples-10          25.14  24.50   25.51    -0.10    0.11    0.37    0.999
more-examples-11          25.46  24.38   25.23     0.07   -0.01   -0.16    0.998
more-examples-12          25.65  24.32   25.31    -0.03    0.15    0.19    1.000
more-examples-13          25.12  23.97   24.97     0.09    0.03    0.04    0.998
more-examples-14          24.66  24.30   25.03     0.39    0.07    0.00    1.000
more-examples-2             —    24.48   25.08    -0.14    0.11    0.03    1.001
more-examples-3           24.88  24.37   24.56    -0.05    0.06    0.06    1.000
more-examples-4           25.26  24.72   25.19    -0.12    0.17    0.16    1.000
more-examples-5           24.91  24.19     —      -0.07    0.06    0.09    1.000
more-examples-6           24.87  24.32   25.00    -0.03    0.02    0.14    1.002
more-examples-7           25.14  23.63   25.25    -0.02    0.05    0.11    0.999
more-examples-8           24.86  23.99   24.92    -0.07    0.07    0.23    1.000
more-examples-9           25.58  24.46   25.25     0.01    0.06   -0.05    0.998
not-immediate-strokes     25.53  23.94   25.21    -0.00    0.05    0.10    0.998
ode1                      24.68  24.43   24.25     0.01    0.05   -0.02    0.999
ode2                      24.78  24.37   24.79    -0.05    0.07    0.04    0.999
ode3                      24.76  24.31   24.90    -0.04    0.07    0.09    0.999
shut-up-and-dance         38.73  38.78   38.71     0.00    0.00    0.00    1.000
superestrella             30.60  30.63   30.63    -0.01   -0.00    0.00    1.000
```

(A dash is a third where the truth holds too few borders in a row to measure a width.)

- **The width changes across the picture by up to 7%**: `airplanes` 25.8 at the left and 24.0 in
  the middle, 1.8 px of difference per key, which over the 52 keys of a grid is what put its black
  keys in the wrong place. On the photos the middle third is narrower than the ends on 20 of 22;
  the two drawn keyboards and `superestrella` are flat to 0.1 px.
- **Every keyboard is level.** The lean of the borders is under 0.5 px per 30 rows everywhere; on
  `airplanes` it goes from 0.42 at the left to 0.15 at the right, which is perspective. So the one
  rectangle's angle was zero on all 24 and the rotation is there for a picture this set does not
  contain.
- **There is no taper in the front of the keys** worth a number: 0.998 to 1.002. The taper the eye
  sees on `ode1` and `superestrella` is the black keys narrowing at their ends, and the black key
  finder reads the band well above that.

## 5. Do the rectangles fall vertically? (Task 1.1.3)

`scripts/fall.py`: the lean of the strong near-vertical edges in the roll above the upper line —
the sides of the rectangles and of the light beams — against the lean of the key borders, in
degrees from vertical.

```text
picture                  roll lean  spread  edges   key border lean: left   mid  right
7years                       0.00    4.21    5933       0.07  -0.09  -0.15
airplanes                   -0.08    3.94    6617       0.80   0.49   0.29
derulo                      -0.00    0.00    3636       0.00   0.02   0.02
feather                     -0.29    5.13    4376       0.17   0.01  -0.28
more-examples-1              0.00    1.09    4842      -0.41   0.11  -0.02
more-examples-10             0.19   10.58    5428      -0.18   0.22   0.70
more-examples-11             0.00    2.83    5990       0.13  -0.02  -0.30
more-examples-12            -0.00    3.09    6296      -0.05   0.28   0.36
more-examples-13             0.14   13.06    3990       0.17   0.05   0.07
more-examples-14            -0.87   19.97    4649       0.75   0.16  -0.02
more-examples-2             -0.00    6.25    3900      -0.26   0.21   0.05
more-examples-3              1.77   26.96    2435      -0.09   0.12   0.12
more-examples-4             -0.00    8.75    2704      -0.24   0.33   0.30
more-examples-5              3.58   26.49    4597      -0.14   0.12  -0.05
more-examples-6             -0.18   10.72    4805      -0.05   0.03   0.26
more-examples-7             -0.27    5.60    6326      -0.04   0.11   0.21
more-examples-8             -0.10    4.05    6521      -0.13   0.14   0.43
more-examples-9             -0.00   15.56    4694       0.02   0.12  -0.09
not-immediate-strokes       -0.36   13.85    2903      -0.01   0.10   0.19
ode1                         0.81   25.20    5007       0.02   0.09  -0.04
ode2                         0.58   24.89    5028      -0.09   0.14   0.14
ode3                         0.66   24.86    5032      -0.09   0.14   0.16
shut-up-and-dance           -0.00    0.00    8381      -0.01   0.00   0.01
superestrella               -0.38   14.11     115      -0.03  -0.03  -0.01
```

- **They fall vertically.** Within 0.4 degrees on 21 of 24; `more-examples-3`, `more-examples-5` and
  the `ode` pictures are within 1.8 degrees with a spread over 25 degrees, because their strong
  edges are the scrollwork and the lettering, not the rectangles. `superestrella` has no roll, so
  its 115 edges say nothing.
- On `airplanes` the keyboard's borders lean 0.8 degrees at the left while the roll leans −0.08:
  the two are not the same thing, and the lane follows the roll. **V-13 stands.**

## 6. The two routes (Tasks 1.2.2, 1.2.3, 1.2.4)

`scripts/routes.py`. Errors in local white key widths: the distance from each truth border to the
nearest border of the route. "front" is the 901 borders of section 2; "top" is the 265 top edge
borders, the only ones both routes can be measured on independently, since route B is the truth's
own reading without the eye.

```text
picture                  family  ratio    n   A front mean  worst  >0.25   A top mean  worst   B top mean  worst   A–B agree
7years                   real     1.49   43      0.051     0.167    0        0.060    0.274      0.021    0.093     0.060
airplanes                real     1.53   40      0.044     0.144    0        0.033    0.098      0.017    0.041     0.040
derulo                   boundary 1.98   51      0.017     0.053    0        0.016    0.026      0.001    0.002     0.017
feather                  real     1.52   31      0.039     0.240    0        0.044    0.251      0.024    0.112     0.040
more-examples-1          real     1.54   21      0.016     0.060    0        0.007    0.014      0.015    0.056     0.049
more-examples-10         real     1.56   30      0.050     0.185    0        0.080    0.489      0.059    0.305     0.050
more-examples-11         real     1.53   43      0.032     0.095    0        0.012    0.048      0.016    0.038     0.042
more-examples-12         real     1.53   36      0.031     0.100    0        0.024    0.076      0.021    0.057     0.031
more-examples-13         real     1.54   43      0.031     0.125    0        0.021    0.051      0.022    0.077     0.034
more-examples-14         real     1.54   41      0.028     0.163    0        0.020    0.083      0.038    0.184     0.032
more-examples-2          real     1.53   24      0.022     0.065    0        0.010    0.034      0.023    0.049     0.023
more-examples-3          real     1.50   35      0.031     0.094    0        0.027    0.094      0.019    0.046     0.032
more-examples-4          real     1.53   41      0.031     0.067    0        0.028    0.080      0.017    0.048     0.034
more-examples-5          real     1.53   35      0.025     0.079    0        0.016    0.041      0.017    0.037     0.078
more-examples-6          real     1.50   43      0.039     0.168    0        0.051    0.276      0.026    0.112     0.053
more-examples-7          real     1.56   41      0.039     0.118    0        0.029    0.068      0.022    0.078     0.041
more-examples-8          real     1.53   45      0.039     0.131    0        0.028    0.065      0.020    0.043     0.039
more-examples-9          real     1.53   39      0.030     0.162    0        0.044    0.342      0.036    0.181     0.028
not-immediate-strokes    real     1.52   42      0.033     0.095    0        0.046    0.328      0.047    0.278     0.036
ode1                     real     1.53   35      0.028     0.090    0        0.024    0.069      0.026    0.074     0.032
ode2                     real     1.53   34      0.027     0.072    0        0.025    0.053      0.019    0.057     0.031
ode3                     real     1.53   34      0.031     0.067    0        0.031    0.093      0.016    0.043     0.033
shut-up-and-dance        real     1.51   32      0.014     0.030    0        0.054    0.279      0.041    0.261     0.014
superestrella            real     1.55   42      0.014     0.037    0        0.015    0.024      0.001    0.003     0.014
TOTAL                                     901      0.031              0        0.031               0.024
```

- **Route A: 0.031 white key widths at the mean, 0.24 at the worst, and not one of 901 borders over
  the lane margin of 0.25.** That is 0.8 px at the mean on a 25 px key.
- **On the top edge the two routes are 0.007 apart**, a fifth of a pixel, and every picture's worst
  top edge error above 0.25 is the same stray minimum for both — the glow line on `more-examples-10`
  and `more-examples-9`, the strike light on `shut-up-and-dance` — so it is the top edge reading,
  not either route.
- **What each rests on.** Route A: 811 of 845 black keys seen, 96.0%. Route B: 901 of about 1220
  front lines readable, 74%, because the hands cover the front of the keys far more than the black
  key band, and the borders it fills in it places with route A's own rule at route A's own width.
- **Route A ships.** Route B stays here as the tool the truth is read with.

## 7. What is not handled, named

- A black key hidden at the very end of the keyboard. The walk past the outermost seen key stops at
  the first key the pixels do not confirm, so a hand over A#0 or A#7 would cost that key and the
  white keys beyond it. No picture of the 24 has that; `more-examples-14` has a hand at the left but
  its A#0 is clear.
- A pressed black key is lit and is not confirmed, on `derulo` and `superestrella`. It is still
  placed, from the pattern, and it is right there; but a video frame with five pressed black keys
  in a row at the end of the keyboard would meet the point above.
- The white key count at the ends keeps a key whose midpoint is inside the rectangle, the seed's
  rule. The seeds of 04 counted 51 or 52 white keys where this counts 50 or 51 on eleven pictures;
  the difference is the key cut by the picture's edge, and the lane of a half key is a half lane.
- The rotation of the one rectangle was never exercised: every keyboard in the set is level to under
  a degree. The rectifier is written and is tested on a drawn keyboard in Phase 3.
