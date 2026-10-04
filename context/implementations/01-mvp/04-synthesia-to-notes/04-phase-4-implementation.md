# Phase 4 — Piano Matrix Notation: implementation report

Technical, for the agent that takes Phase 5. The plan is [`04-plan.md`](04-plan.md), the frozen
decisions are [`04-decisions.md`](04-decisions.md), the status is [`04-checklist.md`](04-checklist.md),
and the report before this one is [`04-phase-3-implementation.md`](04-phase-3-implementation.md).

Phase 3 read every sampled frame and wrote `frames.jsonl`. **Phase 4 is where the video becomes the
piece**: the whole video stitched into one tall picture whose vertical axis is time (V-32), the notes
read off it, corrected by hand if the reader wants, and written into `events.json` through the writer
that already exists (V-02).

---

## 0. What this phase produced, in one table

| | Where | What it is |
|---|---|---|
| the stitch | `video/stitch.py` | the fresh strip of every sampled frame piled into one picture (V-32) |
| the notes | `video/notes.py` | the shapes of that picture read into notes, with times from distance (V-05) |
| the piece | `video/piece.py` | corrections applied, then `pipeline.save_note_events` — the whole boundary |
| the seam | `video/detector.py` | `runs_from_strength()` pulled out of `find_runs()`, and gates that report what they threw out |
| the shapes | `schemas/video.py` | `VideoNote`, `NoteReport`, `VideoNotes`, `NoteCorrection(s)`, `RejectedRun` |
| the paths | `storage/paths.py` | `video/notes.json` (derived) and `video/corrections.json` (not) |
| the HTTP | `api/video.py` | `POST`/`GET /notes`, `GET`/`PUT /corrections`, `POST /events` |
| the screen | `pages/video/VideoNotesPage.tsx` | a fifth tab: read, look, correct, write |

No new dependency. numpy and scipy were already there; `ndimage.label` is used once, and only to
report the comparison V-20 asks for.

## 1. The numbers, on the same real video

[pgLt4WmPMYQ](https://www.youtube.com/watch?v=pgLt4WmPMYQ) — *Elektronomia — The Other Side*,
4 minutes 32 seconds, 2728 sampled frames at 100 ms, calibrated at 88 keys, measured at 168.9 px/s.

```text
stitch          46 504 rows x 1280, uint8 = 59.5 MB
                  strip of 17 rows from row 74, with a head of 432 rows
read            4295 notes in 46 s, one process
                  15.74 notes a second  ·  median 219 ms long  ·  median 0.62 white keys wide
                  furthest from a key midpoint: 0.257 white key widths (V-14's margin is 0.33)
                  thrown out by a gate: 1400 nearer another key, 557 no bright column,
                                        178 too wide, 2 too narrow
                  0 already sounding at the start, 0 still falling at the end, 0 past the end
write           events.json, 4295 events, 272.914 s, no `hand` on any of them
```

**The memory the plan asked for** (Task 4.1.1): 46 504 rows, which is the "about forty thousand rows"
V-32 predicted, at one byte a pixel. The strip is read out of each frame and nothing else is, so
building it is about a thirtieth of the pixel work of reading the whole roll in every frame — the
46 s is almost all JPEG decoding, the same cost the per-frame reading pays.

### 1.1 The score: the rendering's own keyboard

There is no hand reading of a whole video and there never will be. But **the rendering carries its own
ground truth**: Synthesia lights the key on the keyboard while a note sounds, and the keyboard is
below the upper line, where neither reading ever looks. So a key going from unlit to lit is a strike,
and it is evidence neither route can have been fitted to.

The tool is `lit_keys()`: for each key, the median difference between the frame and the plate over a
patch of that key below the upper line. Four keys — 36, 43, 48, 55 — read as lit in every frame,
because the rendering paints a permanent marker on them; they are a defect of the tool and come out of
both sides. It is sampled at 10 frames a second, so **it cannot see two strikes of one key closer
together than 100 ms and undercounts those**: every number below is a floor.

Over frames 400 to 1000 — 40 s to 100 s, sixty seconds of music — the keyboard shows **826 strikes,
13.8 a second**:

```text
                  onsets   found of 826       not shown
stitched roll      1364     804   (97%)          560
frames.jsonl        408     358   (43%)           50
ByteDance model    1109     560   (68%)          549
```

The per-frame reading of Phase 3 finds fewer than half the strikes. That is not a defect Phase 3
introduced: its window is one sampled frame of travel and it can only ever place an onset inside it,
so every repeated note closer together than that is one onset to it. The stitched roll reads at the
pixel — 5.9 ms a row on this video — so it separates them.

**The 560 the keyboard does not show are not invented notes.** 552 of them sit within 250 ms of
another note on the same key, median 231 ms, which is exactly what the 10 fps ground truth cannot
resolve; their median width is 0.93 white key widths, which is the width of a white key rectangle, and
their worst distance from a key midpoint is 0.079 white key widths. They are repeated notes.

### 1.2 Task 4.2.2 — against the model

ByteDance was run directly on the same audio, and its answer was never written anywhere: this is a
report, not a second piece.

```text
video 4295 notes  ·  model 4008 notes
onsets both agree on within 50 ms:  2331
onsets only the video found:        1964
onsets only the model found:        1677
```

**The model's onsets sit a median 45 ms later than the video's**, and the distribution is tight: the
25th percentile is +41 ms and the 75th is +54 ms. Taking that offset out lifts the agreement to 2520.
The offset is not noise, it is a difference of definition — the video route places a note where the
rendering says the key is struck, and the model places it where the audio's attack peaks — and it is
worth knowing before anyone compares the two again.

**Which of them is right is decided by the keyboard, not by each other**: 97% against 68%. That is the
number the whole plan was for, and it comes out the way the plan hoped, on one video and one
rendering.

## 2. The stitched roll, as built

### 2.1 It keeps the sense of a frame

This is the one thing the plan said loosely and the code has to say exactly. The picture is built so
that **time runs upward**, exactly as in the video: the top of the roll is the future and the
rectangle about to touch the piano is the present. Everything follows from that and nothing has to be
renamed:

* a shape's **lowest** row is its onset and its **highest** row is its release — the rectangle tip and
  the last rectangle tip, in the plan's own words;
* `DetectedRun.clipped` — a run whose lowest row is the bottom edge — means *already sounding when
  the video started*, which is the same fact it records about a run the upper line cut (V-16);
* `DetectedRun.entering` — a run on the top edge — means *still falling when the video ended*, which
  is the same fact it records about a run coming into view at the roll top (V-28).

Section 8 step 16 of the plan said `rollTime + row / scrollSpeed`, which is the arithmetic for the
opposite orientation. It is now written as it is built: a row counted **from the bottom** is a
distance above the upper line at the moment the video started, and
`seconds = (rowsFromTheBottom + upperLine - bottomRow) / pxPerSecond`.

### 2.2 The strips tile, and they tile against the float travel

`stitch.plan()` works out where every strip goes before a pixel is read, and `stitch.rows_of(i)`
answers which rows of the picture frame `i` fills. The offset of frame `i` is `round(i x travel)`
against the **exact float travel**, so frame `i` contributes `round(i x t) - round((i-1) x t)` rows —
sixteen or seventeen on this video — and consecutive frames are contiguous with no gap and no row read
twice. `test_video_stitch.py` asserts exactly that.

Stepping by a whole number of rows instead would lose 0.11 px a frame at a travel of 16.888, which
over 2728 frames is **305 px — 1.8 seconds of music**. That is the drift this arithmetic exists to
prevent, and it is why V-32 rests on V-06.

### 2.3 The head, and what happened to it on this video

A strip one travel tall catches every row of the roll exactly once — except the rows that were already
*below* the strip in the very first sampled frame, which are the first few seconds of the piece. Those
are read out of frame 0 in one go, from the strip down to the guard band, and they are the bottom 432
rows of the picture. Without them a video that starts playing immediately loses its first 2.8 seconds
without saying so.

**On this video the head is worthless, and the width gate is what said so.** Frame 0 is a fade-in: its
roll has a mean of 2.8 against the plate's 48.2, so the plate difference is bright everywhere and every
lane holds one band 464 rows tall. The width gate threw out 88 of them on the first 300 frames and 178
over the whole video, and **not one note was invented**. The piece's first note is at 5.53 s, so
nothing was lost either. It degrades the way a gate should.

A one-sided plate difference — foreground is *brighter* than the plate, which is what V-29 already
assumes — would fix the head properly, and it was measured rather than assumed: over 140 sampled
frames of the body of the video, frame to frame agreement (V-31) goes from **97.16% to 96.98%** and
the runs kept from 8820 to 8819. It does not earn its place (V-20), so `foreground_strength` is
unchanged.

### 2.4 A note is one run in one key's lane, not one connected shape

V-32 says a note is one connected shape in the stitched roll, and that is the picture it describes.
What ships is the same idea read with **the detector's own machinery**: `runs_from_strength()` on the
stitched roll, with the two edges of the picture standing in for the upper line and the roll top. So
the stitched roll gets the span fill for outlined rectangles, the coverage, the gap close of 2 rows,
the split at a prominent border (V-26), the extent measured across the lane borders, the width gate and
attribution by midpoint (V-14) — every rule Phase 1 measured, at the same pixel scale, with nothing
retuned.

Two things plain connected components cannot do and this can: it cuts two notes of the same key that
touch, which V-26 counted as 1351 borders in sixty frames of a real video, and it keeps two keys struck
together apart when their rectangles touch sideways.

Measured, as V-20 requires, on the same picture: **plain connected components find 3102 shapes and the
lane reading finds 4295 notes**. The 1193 extra are touching repeats, and section 1.1 is what says they
are real. The comparison is not a one-off: `notes.py` runs it on every reading and `connectedShapes` is
in the report beside the count, so the day a rendering makes the two disagree the other way, the number
says so.

The split threshold was swept against the keyboard ground truth rather than left where it was:

```text
split_prominence   notes   found of 826   not shown   median length
       0.25         1394      806  (98%)      588         201 ms
       0.30         1390      804  (97%)      586         201 ms
       0.40  ←       1364      804  (97%)      560         207 ms
       0.50         1281      784  (95%)      497         207 ms
       0.60         1145      738  (89%)      407         201 ms
       0.75         1114      731  (88%)      383         201 ms
       off          939       723  (88%)      216         124 ms
```

0.40 is what Phase 1 measured and it is kept: it sits on the plateau, and everything above 0.5 starts
losing strikes the keyboard shows.

## 3. The seam in the detector

`find_runs()` was pixels → runs in one call, and the stitched roll is a foreground picture that no
frame ever showed. So the pixel-to-foreground half and the foreground-to-runs half are now two calls:

```python
detector.runs_from_strength(strength, cal, *, upper, roll_top, guard, settings, rejected=None)
detector.find_runs(image, cal, plate=, channel=, settings=)   # calls it, with the frame's own edges
```

**Nothing about the detector's behaviour changed.** `test_video_detector.py`, `test_video_reading.py`
and the score board are untouched, and the board still reads 9/0/0 and 6/0/0.

The second change is `rejected`, an optional list the gates append to. Task 4.1.2 asks for a shape
whose width or whose midpoint does not match a key to be **reported rather than rounded onto one**,
because that is a detection problem wearing the mask of a timing problem. It is off unless a caller
asks for it: the per-frame reading throws out hundreds of thousands of these and has no use for any of
them.

## 4. Writing the piece

`video/piece.py` is the whole boundary — the stitched roll's notes on one side,
`pipeline.save_note_events` on the other, and no third thing anywhere.

* **No `hand` on any event** (V-17). The test checks the file, not the model, because `hand` is left
  out of the JSON entirely unless somebody has said so.
* **Every note carries velocity 64.** The rendering draws a rectangle, not a loudness. Giving every
  note the same middling value is the honest answer; a number nobody measured would not be.
* **The saved reading is cleared**, as a transcription clears it: a reading is a set of column numbers
  over the notes that were there before.
* **It advances the music version**, through `history.snapshot_current`, and only when there was
  something to snapshot — the first write on a fresh video piece leaves the version at 1.
* **A video whose speed is not stable is refused in words** (V-06). The refusal is here as well as in
  the reading, because this is the last door before the piece changes.
* **The floor on note length (D-05) is not applied.** It belongs to the step that builds the matrix,
  which already applies it. This step writes what it saw.

Task 4.2.1, straight through, is a test rather than a claim: the uuid a video wrote is asked over HTTP
for `/matrix/{uuid}/events`, `/time/{uuid}/peaks` and `/time/{uuid}/score`, and every one of them
answers without being told where the notes came from. On the real video the score payload prints 4294
notes over one passage.

## 5. Corrections, and what is a cache

```text
data/audio/<uuid>/video/
  notes.json         derived — what the stitched roll read. Deleted with the frames.
  corrections.json   NOT derived — what a person decided. Survives a re-sample and a re-stitch.
```

That split is V-12 applied one level down: a reading made by a person cannot be reproduced, so it is
kept beside the video like the calibration, and `store.clear_frames` does not touch it.

A removal names a note by `(midi, round(start, 4))` — the same key `POST /matrix/removals` uses. An
addition carries the whole note, because there is nothing in the picture to name it by. A correction
that names a note the reading no longer holds is **reported**, not dropped in silence: `unmatched`
comes back from the write and the screen prints it.

## 6. The screen

A fifth tab, **Notes**, after Detection. Detection and Notes are two readings of the same video and
both are kept, because they answer different questions: Detection is what the picture showed at one
moment, which is what a hand reading is compared against; Notes is the whole video as one picture,
which is what becomes the piece.

**The reading is drawn back onto the video**, and that is the point of the screen. A note that sounds
at `start` has its tip on the upper line at `start`, so at the time of the frame on screen its tip is
`(start - t) x scrollSpeed` pixels above the line and its last tip `(end - t) x scrollSpeed` above
that (`video/notePlacement.ts`). If the reading is right, every box lands on a rectangle. There is no
second roll to compare against, because a second roll would only ever agree with itself.

**The picking is the one the Piano Roll already has** (Task 4.3.1 asks for exactly that): click a note
and it is the selection, ⌘-click adds or takes out, drag a band over the picture and everything under
it is picked, click empty picture and nothing is. A note taken off is drawn struck through and never
hidden (V-30). The one gesture that is not a selection is **shift-drag on a key**, which draws a note
the reading missed: the key is the one under the pointer and the two rows are the two times, read with
the same arithmetic.

`FramePlayer` now passes `onPictureMouseDown`, `onPictureClick` and `panDisabled` through to
`FrameCanvas`, which already had them. Nothing else in Phase 3's components changed.

## 7. The checks

```text
cd aitu-backend
  make test          1 failed, 874 passed        (853 after Phase 3: 21 new tests)
      the one failure is the known pre-existing
      tests/test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas
  flake8             4 errors, the same four pre-existing
  mypy              30 errors, the same thirty pre-existing
  black              clean on everything this phase wrote

cd aitu-frontend
  npx tsc -b               clean
  npm run lint             clean
  npm run check:geometry   both cases pass
  npm run check:render     26 passed, 0 failed

over HTTP, end to end, against `make serve`
  POST /video/{uuid}/notes      the SSE followed to its `done`; the same report as the module run
  GET  /video/{uuid}/notes      4295 notes, 46 504 rows, 59.5 MB
  PUT  /video/{uuid}/corrections  round-trips
  POST /video/{uuid}/events     4295 notes written, music version 1 → 2

a browser, headless Chromium driven by Playwright
  /video/notes   the picker, the six chips, the report, the player
                 at frame 601: 78 notes drawn on the frame
                 a click picks one and names it — "A#5 at 00:58.99, 355 ms long"
                 a band drag picks 31
                 no page error and no console error
```

New tests, 21 of them:

```text
tests/video_fixtures.py        —   one video drawn on the spot, shared by the two below
tests/test_video_stitch.py     8   the tiling, the row-to-seconds, the memory, and the three
                                   awkward cases of V-32 as ordinary shapes
tests/test_video_piece.py     13   the write, no hand, the version, the cleared reading, the two
                                   refusals, the corrections, straight through, and the HTTP surface
```

`video_fixtures.py` is a module and not a test file on purpose: a test importing another test module
makes mypy see the same file under two names, and the suite has no `__init__.py` to fix that with.

## 8. What Phase 4 did not do, named plainly

- **One video, one rendering.** Every number above is plain Synthesia with solid rectangles. The
  twenty-one example screenshots still have no hand reading; that is Phase 2's open item and it is
  still open.
- **The head is untested on a video that starts playing at once.** On this one frame 0 is black, so
  the head contributed nothing and the width gate threw it out. A video whose first frame already
  shows music would use it, and nobody has read one.
- **Decoration inside the strip has no guard but the plate.** The stitched roll has no momentum rule
  (V-33): something drawn across the roll that fades in and out *and* lands in the seventeen rows of
  the strip would become one long shape. The plate removes what is in every frame, the strip is
  seventeen rows of seven hundred and twenty, and the width gate refuses anything the wrong width —
  nothing like it appeared on this video, where only 5 of 4295 notes are over two seconds and the four
  longest are a held chord at 248 s. It is a gap, not a measurement.
- **The stitch is one process.** 46 s for 4.5 minutes, almost all JPEG decoding. The per-frame reading
  spreads the same decoding over eight workers and takes 22 s; this could too, and does not.
- **`notes.json` is served whole.** 4295 notes is about 900 KB and the page asks for all of it. There
  is no paging.
- **The sampling granularity has still not been varied.** 100 ms only, as in Phase 3.
- **The headless screenshots do not rasterise the frame.** The SVG `<image>` that draws the sampled
  frame comes back blank in a Playwright capture — on the Notes tab **and on Phase 3's Detection tab,
  which this phase did not touch**. The requests succeed and the user drove those screens for real in
  Phase 3, so it is a capture artefact; it is written down here so the next agent does not chase it.

## 9. What Phase 5 should know before it starts

1. **The piece is already an ordinary piece.** Task 4.2.1 proves the hand split, the matrix, the peaks,
   the ladder and the payload all read it with no special case. Story 5.1 is a check, not a build.
2. **The rich metadata is already decoupled.** The calibration, the measurement, `frames.jsonl`,
   `notes.json` and `corrections.json` all live under `video/` and nothing of them is in
   `rhythm.json` (V-12). Story 5.2's remaining work is the words on the screen before a re-read
   replaces the piece — `POST /video/{uuid}/events` advances the music version and returns it, but the
   button does not warn first.
3. **The video on disk to work with** is `data/audio/ddd8bce8-3e3f-4262-9595-46aaf66de54b/` —
   downloaded, sampled, calibrated, measured, read, and now written into `events.json`. It is
   gitignored, so it is on this machine only.
4. **The numbers to quote in the documentation** are section 1 of this report. Story 5.3 asks for
   `context/backend/video-to-notes.md` and
   `documentation/services/backend/synthesia-detection.md`, and the thresholds are the table in
   section 8 of the plan plus `stitch.STRIP_MARGIN`, which is the one length Phase 4 added: 0.5 median
   white key widths below the roll top.
5. **Nothing in `04-decisions.md` changed in this phase.** V-32's letter — one connected shape — is
   read as one run in one key's lane, and section 2.4 is the measurement that says why; the
   connected-component count ships in the report beside it so the question stays open to a number.
