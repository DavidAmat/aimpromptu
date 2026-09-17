# Phase 3 — Download a video and sampling frames: implementation report

Technical, for the agent that takes Phase 4. The plan is [`04-plan.md`](04-plan.md), the frozen
decisions are [`04-decisions.md`](04-decisions.md), the status is [`04-checklist.md`](04-checklist.md),
and the two reports before this one are [`04-phase-1-implementation.md`](04-phase-1-implementation.md)
and [`04-phase-2-implementation.md`](04-phase-2-implementation.md). Implementation 05's last report,
[`../05-piano-overlay-from-black-keys/05-phase-3-implementation.md`](../05-piano-overlay-from-black-keys/05-phase-3-implementation.md),
is what the calibration step reuses.

Phase 2 put the detector into the app and scored it on two screenshots. **Phase 3 is the first time
any of it ran on a video**: the first real plate, the first measured scroll speed, the first caller
the momentum rule has ever had, and the first frame-to-frame agreement number over a whole piece.

---

## 0. What this phase produced, in one table

| | Where | What it is |
|---|---|---|
| the paths | `storage/paths.py` | everything under `data/audio/<uuid>/video/`, and nowhere else |
| the shapes | `schemas/video.py` | `VideoMetadata`, `ScrollSpeed`, `VideoMeasurement`, `VideoSummary`, `FrameLine`, `DetectionReport` |
| the download | `video/download.py` | yt-dlp at 720p, the audio taken out of that same file with ffmpeg, one piece with both (V-03) |
| the sampling | `video/sampling.py` | ffmpeg into `video/frames/` at the sampling granularity, at the working width |
| the store | `video/store.py` | the video, its metadata, its calibration, its frames, its plate, its reading |
| the motion | `video/motion.py` | the scroll speed (V-06) and the two edges of the roll (V-28), from one fact |
| the reading | `video/reading.py` | the plate, then every sampled frame across worker processes, into `frames.jsonl` |
| the detector split | `video/detector.py` | `find_runs()` pulled out of `detect()`, so the momentum rule can sit between the pixels and the window rule |
| the momentum fix | `video/momentum.py` | V-42: an edge the picture pinned is not evidence |
| the HTTP surface | `api/video.py` | `/video`, fourteen endpoints, three of them jobs with progress |
| the screens | `pages/video/`, `components/video/` | the three tabs Phase 2 left as placeholders |

No new dependency. ffmpeg and yt-dlp were already required; numpy, scipy and pillow were already
there. **OpenCV is still not needed.**

## 1. The numbers, on a real video

The video is [pgLt4WmPMYQ](https://www.youtube.com/watch?v=pgLt4WmPMYQ) — *Elektronomia — The Other
Side*, the one Phase 1's spike cut 90 seconds out of because its left hand plays repeated notes and
the rectangles touch. Phase 3 downloaded the whole of it through the app, 4 minutes 32 seconds.

```text
download        1280x720 at 60 fps, 31.3 MB, about 10 s of wall clock
sample          2728 frames at 100 ms, 211.8 MB, 3.9 s of wall clock
                  the frames cost 6.8x the video and 46.6 MB per minute of music
calibrate       88 keys, A0 to C8, white key 24.6 px, found by route A, confidence 0.91, 28 ms
measure         168.9 px/s  ·  16.89 px per sampled frame  ·  quartiles 16.83 to 16.95, 0.74% apart
                  507 of 2727 pairs answered, 219 of them were rests
                  roll top row 62, guard band 37 rows = 1.50 white key widths
                  13.2 s over 8 worker processes (56 s on one)
read            2728 frames in 22.2 s over 8 worker processes, plus 4.2 s for the plate
                  129 248 rectangles kept, 1001 refused for not falling
                  1755 onsets and 10 325 sustains  ·  6.43 onsets a second
                  frame to frame agreement (V-31): 97.1%
```

**The measurement agrees with the spike to the third digit**, by a completely different route and on
the whole piece instead of 90 seconds of it: the spike read 16.89 px per sampled frame, roll top 62
and a guard band of 39 rows; the app reads 16.888, 62 and 37. That is the strongest evidence there is
that the port is faithful, because nothing in `video/motion.py` was copied from
`poc-synthesia-frames/scripts/` without being rewritten.

### 1.1 The exit criterion: ten frames, checked by eye

The plan asks for `frames.jsonl` whose onsets are right on ten frames spot checked by hand. The check
is easy to make honest, because **the rendering carries its own ground truth**: Synthesia lights the
key on the keyboard while a note sounds, and the keyboard is below the upper line where the detector
never looks. So the keys lit at the bottom of the picture can be read off and compared against what
`frames.jsonl` says, with no circularity at all.

Ten frames were drawn with the detection on them and read this way:

| frame | t | what the keyboard shows | what the detector said |
|---|---|---|---|
| 402 | 40.2 s | 7 keys lit | 3 onsets + 4 sustains — all seven, and the right three as onsets |
| 403 | 40.3 s | 1 key lit | 1 sustain; 3 sparkle blobs refused for not falling |
| 405 | 40.5 s | 5 keys lit | 2 onsets + 3 sustains — the two onsets are the two rectangles that just crossed |
| 600 | 60.0 s | 6 keys lit | 6 sustains |
| 900 | 90.0 s | 6 keys lit | 1 onset + 5 sustains; one sparkle refused |
| 1200 | 120.0 s | 3 keys lit | 3 sustains |
| 1500 | 150.0 s | 4 keys lit | 4 sustains |
| 1800 | 180.0 s | 6 keys lit | 6 sustains |
| 2100 | 210.0 s | 6 keys lit | 2 onsets + 3 sustains — one short note's rectangle has fully crossed (see below) |
| 2400 | 240.0 s | 4 keys lit | 4 sustains |

**Nine of ten agree key for key.** The tenth, frame 2100, is the limitation the plan already names:
*a rectangle entirely past the upper line with the strike light over what is left*. On a short
staccato note the rectangle is about 17 px long — one sampled frame of travel — so it crosses the
upper line entirely within one frame while the keyboard keeps the key lit for a moment longer. The
pixels above the line then hold only the strike glow, which is too wide for the width gate on one key
and refused for not falling on the other. The detector reports nothing there rather than inventing a
sustain out of the strike light, which is the right answer for one frame and the wrong one for the
piece. **Phase 4's stitched roll (V-32) is what closes it**, because a shape in the stitched roll has
its own top and bottom whatever the upper line did to it.

Frame 403 is worth looking at on its own: the three magenta boxes there are Synthesia's release
sparkles, refused by the momentum rule, on three keys that had just stopped sounding. That is V-33
doing exactly what it was written for, on a video, for the first time.

## 2. The two rules Phase 3 changed, and why

Both are in [`04-decisions.md`](04-decisions.md) as V-42 and V-43. Both came out of running on a real
video, and both are cases where a rule that is right on a screenshot is wrong on a piece.

### 2.1 V-42 — a pinned edge is not evidence

`momentum._fits` compared the top **and** the bottom of a run against the same run in a neighbouring
frame. A run cut by the upper line has not got a tip there, it has been cut there (V-16): its lowest
row is the line and stays at the line however fast the rectangle falls. So for a clipped run that
comparison can only ever say *it did not move*.

Measured over fourteen seconds of the video, with both edges compared:

```text
kept  fell     7714        refused clipped  80        refused mid-roll  0
kept  unknown   772        of 8566 runs
```

**Every refusal was a clipped run**, and not one falling rectangle that reached the line could ever
be shown to have fallen. With the pinned edge left out:

```text
kept  fell     8297        refused clipped  87        refused mid-roll  7
kept  unknown   175        of 8566 runs
```

583 clipped runs move from *undecided* to *proven to have fallen*, the rule decides 97% of runs
instead of 90%, and seven runs in the middle of the roll are refused for the first time — all seven
at rows 540 to 554, inside the halo guard band, which is where the strike light lives. Over the whole
video, **frame to frame agreement goes from 94.3% to 97.1%** and the sustains kept go from 9992 to
10 325.

A run pinned at both ends — a rectangle taller than the whole roll — has no free edge, so nothing
fits it and it stays `unknown` and is kept, which is V-33's own answer.

### 2.2 V-43 — a rest is not a measurement

Phase 1 judged a pair of sampled frames usable by how sharp its correlation peak is. On a whole piece
that is not enough: two pictures of the same silence correlate perfectly with themselves at a shift
of nothing, so **a rest answers sharply that the roll did not move**.

```text
filter                        pairs   median   q1       q3       spread
everything                     2727    0.795    0.174   16.684   2078%
sharp only (Phase 1's rule)     726   16.836    0.000   16.922    100.5%   ← calls a steady video unstable
moved only                     1318   16.698   15.905   16.870      5.78%
sharp and moved  ← chosen       507   16.888   16.825   16.950      0.74%
```

The `MOVED` floor is 1 px and is not a tuned number: 0.5, 1 and 2 all keep exactly the same 507
pairs. The still pairs are counted and reported (`stillPairs`), because how many there are says how
much of the video is silence.

This matters beyond the number: without it, **this video would have been refused as unstable** and
V-06 would have stopped the whole pipeline on a piece whose scroll speed is constant to three parts
in a thousand.

## 3. The shape of the backend, for the agent that extends it

### 3.1 `find_runs` is the seam Phase 4 will want too

`detect()` was one call: pixels → colour check → frame window rule. A video needs the momentum rule
between the pixels and the window rule, and the momentum rule needs the runs of the frames either
side, so the two halves cannot be one call. `detector.find_runs(image, cal, plate=, channel=,
settings=)` is now the pixel half and `detect()` calls it. **Nothing about the detector's behaviour
changed** — `test_video_detector.py` and the score board are untouched, and the board still reads
9/0/0 and 6/0/0.

### 3.2 The reading is two passes and only one of them is parallel

```python
reading.read_video(uuid)          # plate → find_runs per frame (processes) → momentum → window rule
reading.measure_video(uuid)       # plate → row profile per frame (processes) → align pairs → bounds
reading.detect_frame(uuid, i)     # one frame with its two neighbours, for the screen to draw
```

The pixel work is what parallelises and it is all a worker does. `_read_chunk` answers with plain
dicts, not runs: what crosses the process boundary is the reading of twelve frames and nothing else.
The momentum rule and the window rule then run in the parent, where every frame's runs are in one
place — they are pure Python over a few hundred thousand small objects and they cost under a second
on this video.

**The plate is a file, not an argument.** `data/audio/<uuid>/video/plate.npy` is 11 MB; passing it to
eight workers down a pipe costs more than each of them reading it. It is a cache and
`store.clear_frames` deletes it with the frames it was built from, because a plate built from frames
that no longer exist is wrong without saying so.

Measured: 2728 frames in 22.2 s over 8 workers, which is 123 frames a second. On one process the same
run takes about three minutes.

### 3.3 The frame index and its time

A sampled frame is addressed by its **index, counted from zero**, and its time is
`index * sampleMs / 1000`. ffmpeg's `fps` filter emits its first frame at t = 0 — measured, a two
second clip at 10 frames per second gives exactly twenty frames — so the index and the time line up
with nothing to correct for. The file on disk keeps ffmpeg's own one-based `f%06d.jpg` name so the
folder sorts in time order, and `store.frames()` is what turns the listing into an index; nothing
outside `store.py` parses a name.

### 3.4 The download, and the one thing that bit

`POST /video/download` is yt-dlp with `bestvideo[height<=720]+bestaudio/best[height<=720]/best`,
merged to mp4, then `ffmpeg -vn -q:a 0` for the audio, then the ordinary `ingest.ingest_path`. One
URL, one network fetch, one piece with both (V-03). The uuid comes from the audio ingest and the
video is moved into that piece's folder afterwards.

Two things the first real run taught:

- **`shutil.move`, not `Path.replace`.** The temp folder is on the system disk and `data/` may be on
  another volume; a rename across two devices fails with `Cross-device link`.
- **The title comes from `--write-info-json`.** The output template is a fixed `source.%(ext)s`
  rather than `%(title)s`, because the merge step leaves one file per stream behind before it joins
  them and a glob over the folder could pick the wrong one. yt-dlp already has the title, so the info
  json costs nothing and there is no second call to YouTube for a name. Without it the piece was
  ingested as "source".

`clean_error` and `PROGRESS_LINE` in `audio/youtube.py` were made public, because the video download
parses the same lines from the same tool. Nothing else in that module changed.

### 3.5 The HTTP surface

```text
POST /video/download                      url in, VideoMetadata out
GET  /video                               every piece with a video, for the picker
GET  /video/{uuid}                        VideoSummary: metadata, calibration, measurement, reading
POST /video/{uuid}/sample?sampleMs=        job
GET  /video/{uuid}/frames/{index}          one sampled frame, as an image
GET  /video/{uuid}/calibration
PUT  /video/{uuid}/calibration
POST /video/{uuid}/find?index=             the finder of implementation 05 on one frame
POST /video/{uuid}/measure                 job — the scroll speed and the two edges
POST /video/{uuid}/detect                  job — every frame, into frames.jsonl
GET  /video/{uuid}/detection               frames.jsonl as it was written
GET  /video/{uuid}/report                  what the last whole-video run did, in numbers
POST /video/{uuid}/frames/{index}/detect   one frame with its neighbours, for the screen
GET  /video/progress/{jobId}               SSE, the same plumbing transcription uses
```

Three deviations from section 6 of the plan, all small and all deliberate:

1. **`POST /video/{uuid}/measure` instead of a scroll-speed endpoint.** V-28 says the same
   measurement that gives the scroll speed gives the two edges of the roll, because both rest on the
   roll scrolling and nothing else doing so. Splitting them into two endpoints would read the whole
   video twice.
2. **`GET /video` was added.** The plan's screens need a way to pick a video and it did not name one.
   The per-pair shift series is left out of the rows — it is 2727 numbers and a picker has no use for
   any of them — and is still on `GET /video/{uuid}`, which is where V-06 wants it readable.
3. **`GET /video/{uuid}/report` and `POST /video/{uuid}/frames/{index}/detect` were added.** The
   first is V-20: a change to a threshold has to be comparable against the run before it without
   re-reading the video, so `detection-report.json` is written beside `frames.jsonl`. The second is
   what lets the detection tab draw the rectangles on the pixels they were found in.

`POST /video/{uuid}/events` is **not** built. It is Phase 4's, because it is the step that writes the
piece.

### 3.6 The storage tree, as built

```text
data/audio/<uuid>/
  metadata.json            unchanged
  original.mp3             the audio, taken out of source.mp4
  normalized.wav           unchanged
  video/
    source.mp4             the download (V-01)
    metadata_video.json    size, duration, fps, sampleMs, frameCount, framesBytes
    calibration.json       { "calibration": …, "measurement": … }
    plate.npy              derived, deleted with the frames
    frames/f000001.jpg …   derived, deleted and rewritten on every sample
    frames.jsonl           derived
    detection-report.json  derived
```

`data/audio/**` is already gitignored whole, so nothing was added to `.gitignore`. Everything under
`video/` except `source.mp4` and `calibration.json` is a cache; `store.clear_frames` is the one place
that throws the caches away, and `sampling.sample` calls it first.

## 4. The screens

The three tabs Phase 2 left as placeholders are built. Everything on them that draws on a picture is
Phase 2's or implementation 05's, unchanged.

| Tab | What it is |
|---|---|
| Video | paste a URL and download; pick a sampling granularity and sample, with a progress bar; then the player |
| Calibration | `CalibrationEditor` on a frame of the video — the same component, untouched — then Measure, and the time frame lines drawn on the player |
| Detection | Read it, the report, and the player with every rectangle drawn on the frame it was found in |

New components: `FramePlayer` (Task 3.3.1), `TimeFrameLines` (Task 3.4.2), `VideoBar` and
`videoSteps` (which video, and how far it has got).

Four things worth knowing:

- **The player draws the sampled frames, not a video element.** What the user sees is the JPEG the
  detector reads, at the width the detector reads it (V-35). Playing is a `setInterval` over the
  indexes at `sampleMs`, with the next six frames fetched into the browser's cache ahead of it.
  Spacebar plays and pauses, the arrows step one frame, shift with an arrow steps ten, and the bar
  is draggable and reads mm:ss through `formatTime`. **It does not play the audio and does not
  mention it**, as Task 3.3.1 asks.
- **The keys are caught on the player's own element, not on the window.** Typing a YouTube URL into
  the field on the same page must not step the video.
- **The offset line is drawn, not offered.** `TimeFrameLines` draws the upper line, the halo guard
  band, the roll top and six bands of one sampled frame of travel each, spaced by the measured speed.
  There is no slider: on a video the window is the measured speed times the sampling granularity and
  nothing else (V-25), so `OffsetLine` — which exists to be dragged — is not on any of these screens.
- **Which video is shared through session storage, not a context.** Each tab is a route and every
  route remounts, so reading `aitu.video.selected` on mount is all the sharing three screens need,
  and it survives a reload.

`steps()` lives in its own module because a file that exports a component may not also export a
function — the same ESLint rule Phase 2's report names.

## 5. The checks

```text
cd aitu-backend
  make test          1 failed, 853 passed        (823 after implementation 05: 30 new tests)
      the one failure is the known pre-existing
      tests/test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas
  flake8             4 errors, the same four pre-existing
  mypy              30 errors, the same thirty pre-existing
  black             clean on everything this phase wrote

cd aitu-frontend
  npx tsc -b         clean
  npm run lint       clean
  npm run check:geometry   both cases pass
  npm run check:render     26 passed, 0 failed

a browser, headless Chromium driven by Playwright against make serve
  /video/player        the picker, the five chips, the player; the bar seeks to frame 401
  /video/calibration   the overlay found, 88 keys A0 to C8 confidence 0.91; 168.9 px a second,
                       507 of 2727 pairs, roll top 62, guard band 37
  /video/detection     1755 onsets over 2728 frames, agreement 97.1%; frame 402 draws 3 onsets and
                       4 sustains, which is what frames.jsonl holds at t = 40.2 s
  no page error and no console error on any of the three

over HTTP, end to end, with the SSE followed to its `done` frame
  POST /video/{uuid}/sample    2728 frames
  POST /video/{uuid}/measure   168.9 px/s, stable
  POST /video/{uuid}/detect    the same report as the module-level run, to the digit
  POST /video/download with a non-YouTube URL   422, in yt-dlp's own words
```

New tests, 30 of them:

```text
tests/test_video_motion.py     6   the alignment, the median, the rests, an unstable speed, the roll top
tests/test_video_sampling.py   8   the frame count, index 0 is t = 0, the working width, resampling, the disk cost
tests/test_video_reading.py    6   one line per frame, the onset in one frame only, the sustain, the lettering, agreement
tests/test_video_api.py        7   the 404s, the summary, the image, the two 409s, and that no route takes frameMs
tests/test_video_momentum.py   3   V-42: a pinned edge is not evidence, a glow is still refused, both ends pinned
```

`test_video_sampling.py` makes its own video with `ffmpeg -f lavfi`, and `test_video_reading.py`
draws its frames with numpy — a black roll, one rectangle falling at a known speed, and one blob of
lettering that comes and goes. Neither needs the network and neither needs the example screenshots.

One thing the drawn test taught and the comment in it now records: **the lettering has to come and go
to test the momentum rule at all.** A blob that is in every frame is in the background plate, and the
plate removes it before anything looks at it (V-15). The momentum rule is what catches the decoration
the plate cannot.

## 6. What Phase 3 did not do, named plainly

- **Nobody was timed on the calibration.** Task 3.3.2 inherits implementation 05's bar of under a
  minute of clicking. The flow is one drag of a rectangle that is already over the piano when the
  page opens, plus a dropdown and Save, and the finder answers in 28 ms plus a 350 ms settle. A
  stopwatch was not held to it.
- **One video, one rendering.** Every number above is about plain Synthesia with solid rectangles.
  The twenty-one example screenshots still have no hand reading, which is Phase 2's open item and
  still open.
- **The detection tab does not let a run be thrown out.** `DetectionView`'s judge-in-place gesture is
  for making ground truth on an example; on a video, correcting the piece is Task 4.3.1 and it is
  meant to reuse the note selection that already exists on the Piano Roll.
- **The sampling granularity has not been varied.** 50, 100 and 200 ms are offered on the screen and
  only 100 has been read end to end. At 50 ms the travel halves to 8.4 px, which is under the
  momentum rule's vote floor of 11 — that floor is only used when the travel is voted for rather than
  measured, and on a video it is measured, so nothing should break; it has not been checked.
- **The screens have glitches the user saw and chose to leave.** The user drove all three tabs,
  confirmed the phase works, and said the rough edges are for a later iteration rather than for this
  phase. They are not written down one by one here because they were not enumerated; the next agent
  should not treat the UI as finished, and should ask before polishing it.
- **`GET /video/{uuid}/detection` serves the whole file.** 2728 lines is 157 KB and the page asks for
  all of it. It takes `start` and `limit`; nothing pages yet.

## 7. What Phase 4 should know before it starts

1. **`frames.jsonl` is not what Phase 4 reads.** V-32 replaced the frame-to-frame tracker with the
   stitched roll: the top `scrollSpeed × sampleMs` rows of each sampled frame piled up. `frames.jsonl`
   is the readable record of what the detector saw per frame and the thing a hand reading is compared
   against — it is not the input to the piece. What Phase 4 needs from this phase is
   `store.frames()`, `store.load_measurement()` and `store.load_calibration()`.
2. **The strip is 16.89 rows per frame on this video.** 2728 frames stitch to about 46 000 rows at
   1280 px wide, which is 59 MB as one grey picture. The user accepted that cost in V-32.
   `poc-synthesia-frames/scripts/stitch.py` is the spike's version and its numbers are in
   `RESULTS.md` section 7 — 268 of 268 shapes in thirty seconds were notes.
3. **The limitation frame 2100 showed is Phase 4's to close.** A short staccato note's rectangle
   crosses the upper line inside one sampled frame, so no frame holds it as a sustain. In the
   stitched roll it is an ordinary shape with a top and a bottom, because the stitch is taken well
   above the upper line and never sees it.
4. **The measurement is on disk and is the contract.** `measurement.scrollSpeed.pxPerFrame` is what
   turns a row into a second (V-05) and `measurement.scrollSpeed.stable` is what V-06 refuses on. A
   video whose speed is not stable must not be turned into a piece quietly.
5. **`calibration.rollTop` and `calibration.guardBand` are measured now**, not zero as they were on a
   screenshot. The strip of V-32 must be taken below `rollTop` and above `upperLine - guardBand`.
6. **Do not use `frameMs` anywhere in this** (V-04). `sampleMs` is on `VideoMetadata` and nothing on
   `/video` takes `frameMs`; `test_video_api.py` asserts that against the OpenAPI schema so it stays
   true.
7. **The piece already exists.** `POST /video/download` created an ordinary audio uuid with the audio
   in it, so Phase 4's `pipeline.save_note_events` writes into a piece that the Playground can
   already open. Nothing new has to be created.
8. **The video on disk to work with** is
   `data/audio/ddd8bce8-3e3f-4262-9595-46aaf66de54b/` — downloaded, sampled at 100 ms, calibrated,
   measured and read. It is gitignored, so it is on this machine only; re-download it with
   `POST /video/download` on `https://www.youtube.com/watch?v=pgLt4WmPMYQ` if it is gone.
