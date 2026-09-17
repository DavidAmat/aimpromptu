# Phase 3 — The finder in the app, and the one rectangle on the screen: implementation report

Technical, for the agent that takes Phase 3 of implementation 04 next. The plan is
[`05-plan.md`](05-plan.md), the status is [`05-checklist.md`](05-checklist.md), the decisions are
V-37 to V-41 in [`../04-synthesia-to-notes/04-decisions.md`](../04-synthesia-to-notes/04-decisions.md),
and the two earlier reports are [`05-phase-1-implementation.md`](05-phase-1-implementation.md) and
[`05-phase-2-implementation.md`](05-phase-2-implementation.md).

This phase closes implementation 05. The finder of Phase 1 is in the app, every one of the 24
examples has a found overlay, and step 1 of `/video/examples` is the one rectangle.

## 0. What this phase produced, in one table

| | Where | What it is |
|---|---|---|
| the finder | `aitu_backend/video/finder.py` | `find_overlay(image, rect, upper_line, first_white_octave) -> Calibration`, `FinderSettings`, `NoKeyboard` |
| the endpoint | `aitu_backend/api/frame_examples.py` | `POST /frame-examples/{slug}/find`: a `FindRequest` in, a `Calibration` out, 422 with the finder's words when there is no keyboard |
| the request | `schemas/video.py` `FindRequest`, `api/frameExamples.ts` | the one rectangle, and the upper line and the octave when the user has set them |
| the seed | `scripts/seed_frame_examples.py` | finds the overlay of all 24 examples; the octave from 04's spike only where its pitch class agrees |
| the tests | `tests/test_video_finder.py` | seven, on a drawn keyboard: straight, from A, occluded, overreaching, rotated 5 degrees, widening 7%, and no keyboard |
| the one rectangle | `components/video/PianoRect.tsx` | dragged by its body, resized from eight handles, turned from one past its right end |
| step 1 | `components/video/CalibrationEditor.tsx` | the rectangle, the overlay found when it settles, the upper line, the octave, the confidence, the border drag, Save |
| the overlay | `components/video/PianoOverlay.tsx` | extrapolated keys dashed, confirmed ones dotted, corrected borders in the user's colour, and the border grab strips |
| gone | `DragRect.tsx` | the horizontal rectangle of 04 |

## 1. The numbers

**All 24 examples are found**, with the rectangle the seed places — the full width, from the upper
line 04 measured (or Phase 1 of 05 found, for the three `ode` pictures) to the bottom of the picture,
at angle zero:

```text
whole pianos          21 of 21 at 52 white keys and 36 black keys, or 51/35 and 50/35 where the
                      picture cuts one or two off an end — the same count on every picture as the
                      spike's route A, and the same borders to within 2.5 px at the worst (airplanes),
                      0.6 px on the rest
shut-up-and-dance     33 white keys, 23 black
superestrella         42 white keys, 30 black, from C
pitch class           A on 23 pictures, C on superestrella, as Phase 1 measured
confidence            0.36 to 0.69 on the photos, 0.88 and 1.00 on the drawn keyboards
extrapolated          7years 13 (9 confirmed), feather 11 (11), derulo 2 (2, pressed and lit),
                      more-examples-12 2 (2), airplanes / more-examples-4 / not-immediate-strokes /
                      superestrella 1 each
score board           9 onsets found, 0 invented, 0 missed · 6 sustains found, 0 invented, 0 missed
                      — on the found overlays of derulo and shut-up-and-dance, as before
time                  70 to 110 ms per picture in the finder; in the browser the overlay is found
                      again 567 ms after the rectangle stops moving (350 ms of settling, the rest
                      the request)
```

**The seeded octave of `airplanes` was corrected on the way**: 04's spike named its leftmost key G1
and the finder A0, so its octave is now the finder's default of 0 and the overlay reads A0 to C8.

**Task 3.2.4, the timing, was not done by a person.** The flow was driven in a browser: opening an
example shows its overlay at once, moving the rectangle by six pixels finds it again in 567 ms, one
border drag marks one border as corrected, and Save opens step 2. A person's gesture is one drag of a
rectangle that already sits on the piano when the page opens; the thirty second bar is not in doubt,
but the number a stopwatch would give was not taken.

## 2. What the port changed against the spike, and why

The spike's rectangles were the full width of pictures whose keyboards fill the width, so the ends of
a keyboard were always the ends of the picture. The tests draw a keyboard that does not fill its
rectangle, and that found four things the spike never met:

1. **The band's black key columns are the runs of dark columns as wide as a black key**, not every
   dark column: a dark canvas past the end of the keyboard is dark too, and it dragged the depth
   profile down to the bottom of the strip.
2. **The end walk needs light beside a key.** A dark canvas 8 px wide beside the last white key is
   dark where a black key would be and light on its near side, so it read as a black key. The walk
   now requires the top of a white key on the near side — the columns between the new key and its
   neighbour, less the shadowed edges, judged column by column at the 40th percentile so the thin
   line between two white keys does not fail it — and on the far side, eight columns seven px clear
   of the key's predicted edge, unless the strip ends there. The bar a column has to clear is local
   and moves with the walk: a fifth of the way from the black keys' own dark level up to the white
   key top of the gap last accepted. A picture-wide threshold cut three keyboards short at their
   dim ends.
3. **A predicted end key is snapped onto the nearest dark run of a key's width** before it is judged,
   because the position function is up to five px off at the far end and a window that touched the
   key's own shadow read it as canvas.
4. **The first white key past the outermost black key needs no test**: a black key stands between
   two white keys. The keys beyond it are accepted while the top of the key clears the same local
   bar, sampled over the columns no black key claims, so a key cut in half by the picture's edge is
   judged on its own sliver.

Each of these was added, run over the 24 examples, and kept only when all 24 still came out with the
spike's key count. The last one to settle, the far side read, cost `7years` and `feather` their top
two keys in three different ways before it was eight fixed columns clear of the key.

**A count that does not fit the pattern is refused, not crashed.** `find_overlay` turns the model's
validation error into `NoKeyboard` with its words, so the endpoint answers 422 and the seed prints the
picture and goes on.

## 3. The screen, as built

Section 8 of the plan, with three things settled here:

- **The rectangle sits under the overlay, and the keys let the pointer through** when there is
  nothing to press: `PianoOverlay` gives its key rectangles `pointer-events: none` without an
  `onKeyClick`. So the body of the rectangle is dragged through the keys, the eight resize handles
  and the angle handle are reachable, and the border grab strips — seven screen px wide on every
  white key border, rendered on top — are the overlay's one gesture on this step. The cost is that
  the names of the keys on hover are not on step 1; they are on steps 2 and 3, and the summary line
  names the first and the last key, which is what the octave check needs.
- **The finder runs 350 ms after the rectangle last moved and not while it is being dragged.** The
  page keeps `moved`, set by the rectangle and cleared by a successful find; Save is disabled while
  the rectangle has moved and nothing has been found from it. A picture that already has an overlay
  opens showing it and does not find again until the rectangle moves, so a border corrected by hand
  survives opening the page.
- **A dragged border** moves between its two neighbours, is written into `whiteBorders`, pushed into
  `found.corrected`, and recomputes `whiteWidth` with the same upper median the backend derives. A
  calibration with no `found` — a spelt-out grid — gets one with route `hand`.

The angle handle turns the rectangle about its top left corner, which is how the model measures
the angle; it is clamped to ±45 degrees. Every keyboard in the set is level, so the handle was
exercised on a drawn keyboard only (`test_a_rotated_keyboard_is_read_inside_a_rotated_rectangle`).

## 4. The checks

```text
cd aitu-backend
  make test          1 failed, 823 passed        (816 after Phase 2: 7 finder tests)
      the one failure is the known pre-existing
      tests/test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas
  flake8             4 errors, the same four pre-existing
  mypy              30 errors, the same thirty pre-existing
  black             clean on video/, schemas/video.py, api/frame_examples.py and the new tests and scripts

cd aitu-frontend
  npx tsc -b         clean
  npm run lint       clean
  npm run check:geometry   both cases pass
  npm run check:render     26 passed, 0 failed

a browser, headless Chromium driven by Playwright against make serve
  airplanes step 1   88 keys, A0 to C8, found by route A, confidence 0.37
  derulo step 1      the rectangle moved 6 px, the overlay found again 567 ms later, one border
                     dragged and marked corrected, Save, step 2 open — no page error, no console error
```

## 5. What is not done, named

- **No person was timed** on an unseen screenshot (Task 3.2.4). The flow is one drag and a
  dropdown, and the machine numbers are above.
- **The names of the keys are not on hover on step 1**, for the reason in section 3.
- **The rotation handle was not exercised on a real picture.** No picture in the set needs it.
- **`poc-piano-overlay/out/` is 11 MB of pictures** the eye checked. They are the evidence of Phase 1
  and are left in place; whether they are committed is the user's call, as it was for 04's spike.

## 6. What Phase 3 of implementation 04 should know

1. **Task 3.3.2 of 04 is this screen.** `CalibrationEditor` takes a picture URL, a size, a saved
   `Calibration` or null, an `onFind` and an `onSave`; the video page supplies `onFind` from a new
   `POST /video/{uuid}/find` that calls `finder.find_overlay` on the chosen frame, exactly as
   `api/frame_examples.py` does for an example.
2. **`find_overlay` takes the frame as float RGB at the working width** and knows nothing about
   videos. Pass `upper_line` and `first_white_octave` from the saved calibration when there is one.
3. **The lanes are vertical strips** (V-39) and the detector reads the local white key width from
   `geometry.local_widths` (V-38); nothing in Phase 3 of 04 needs to know either.
4. **`rollTop` and `guardBand` are still zero on every found calibration** and are the video's to
   measure, as 04's Phase 2 report said.
5. **The seed is the reference for a found overlay:** `uv run python scripts/seed_frame_examples.py
   --force` re-finds all 24 and keeps the hand readings. The score board must read 9/0/0 and 6/0/0
   afterwards, and `test_video_examples.py` asserts it.
