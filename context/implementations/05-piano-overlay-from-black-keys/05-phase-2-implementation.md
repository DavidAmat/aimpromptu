# Phase 2 — Per-key borders in both services: implementation report

Technical, for the agent that takes Phase 3. The plan is [`05-plan.md`](05-plan.md), the status is
[`05-checklist.md`](05-checklist.md), the decisions are V-37 to V-41 in
[`../04-synthesia-to-notes/04-decisions.md`](../04-synthesia-to-notes/04-decisions.md), and what
Phase 1 found is [`05-phase-1-implementation.md`](05-phase-1-implementation.md).

This phase changed the model with nothing found yet: the saved grids are spelt out into borders,
both geometry twins are rewritten and held by the fixture, the detector reads local widths, and the
score board reads what it read before.

## 0. What this phase produced, in one table

| | Where | What it is |
|---|---|---|
| the model | `aitu_backend/schemas/video.py` | `Calibration` is per-key borders: `pianoRect`, `whiteBorders`, `blackBorders`, `blackDepth`, a derived `whiteWidth`, and `found` |
| the upgrade | `aitu_backend/video/upgrade.py` | a grid saved by 04 spelt out into borders, on load and in the seed |
| the geometry | `aitu_backend/video/geometry.py`, `aitu-frontend/src/video/overlayGeometry.ts` | borders read from the lists, the local width, the rotated top edge |
| the fixture | `aitu-backend/tests/fixtures/video/geometry-fixture.json` | two cases: a straight whole piano and a rectangle at 4 degrees whose keys widen |
| the detector | `aitu_backend/video/detector.py` | three lengths in the local width, three in the median |
| the overlay | `aitu-frontend/src/components/video/PianoOverlay.tsx` | each key from its own borders, inside the rotated rectangle |
| the editor | `aitu-frontend/src/components/video/CalibrationEditor.tsx` | emptied: the saved overlay, the upper line, the octave, Save |
| gone | `overlayEdits.ts`, `blackMode`, `blackNudge`, `blackOffsets`, `blackRatio`, `leftBorder`, `whiteCount`, `whiteHeight`, `blackHeight` | the grid |

## 1. The score, which is the regression check

```text
before the change   9 onsets found, 0 invented, 0 missed   6 sustains found, 0 invented, 0 missed
after the change    9 onsets found, 0 invented, 0 missed   6 sustains found, 0 invented, 0 missed
```

Over the five hand readings on `derulo` and `shut-up-and-dance`, with the seeded grids spelt out into
borders. The straight case of the new fixture is 04's test video spelt out, and its keys are the
numbers 04's own fixture carried, to the last digit (`test_a_grid_spelt_out_is_the_grid_04_built`):
the upgrade is the identity on what 04 built.

## 2. The model, as built

Section 5.1 of the plan, with two details settled here:

- **`whiteWidth` is stored and derived.** The validator fills it from the borders when it is left at
  zero — the upper median of the sorted widths — so it is always on the wire, and nothing may set it
  by hand. The frontend has `medianWhiteWidth()` for the day it edits borders (Task 3.2.3) and has to
  recompute it before saving; it uses the same upper median.
- **A wrong count of black borders is refused by the validator**, computed from the pitch class of
  the leftmost white key and the number of white keys (`expected_black_count`). So is a border list
  that does not increase, and a black key whose right border is not past its left.

Two things Phase 3 should know about the shape:

- `blackBorders` are in pitch order, and `geometry.keys()` hands them out to the gaps between white
  keys two semitones apart in order. The finder produces them in that order already.
- `found.corrected` is a list of indexes into `whiteBorders`. It is on the model now and empty
  everywhere; Task 3.2.3 fills it.

## 3. The upgrade, and what it did to the saved records

`examples.load()` passes a saved calibration through `upgrade.upgrade()` before validating it. A
record 04 wrote — recognised by `whiteWidth` and `whiteCount` with no `whiteBorders` — is spelt out
with the same formulas 04's geometry used, including the real piano offsets 04 defaulted to and the
per-octave `blackOffsets` if the record has them. The one rectangle of a spelt-out grid is the full
width of the picture with its top edge on the upper line, at angle zero, so a distance along the top
edge is a picture x.

Nothing was rewritten on disk: a record is written back in the new shape the first time it is saved
from the UI. The 21 records under `data/frame-examples/` are still grids on disk and load either way.
The seed script builds a grid dict from the spike's numbers and passes it through the same function,
so a fresh checkout seeds the new shape directly.

The 04 tests that built a `Calibration` from grid keywords (`test_video_detector.py`) build a grid
dict and spell it out; the detector's own tests draw on an even keyboard on purpose, because they
test rules about rows and an even grid is the case the two widths of V-38 agree on.

## 4. The geometry twins

Both twins: `topEdgeX(cal, u) = rect.x + u · cos(angle)`, the inverse `topEdgeU`, `keys()` from the
two lists, `localWidths()` — a white key's own width, a black key the mean of its two neighbours —
and `lanes()` padded by `margin × local width`. The frontend converts degrees the way Python's
`math.radians` does, `degrees * (Math.PI / 180)`, so the two agree to the bit at 4 degrees; the
check's tolerance is 1e-9 and it passes on both cases.

It was proven by breaking it: subtracting a tenth of a pixel from one lane's `x0` in the TypeScript
makes `npm run check:geometry` say

```text
✗ [straight] lane 21 x0: the frontend says -4.742857142857143, the backend says -4.642857142857143
```

## 5. What the overlay draws, and how it was checked

`PianoOverlay` draws inside `<g transform="translate(rect.x rect.y) rotate(angle)">`; each key's
picture x is turned back into a distance along the top edge with `topEdgeU`, a white key runs to the
bottom of the rectangle and a black key to `blackDepth`. The two gestures that moved the grid —
dragging the whole overlay and dragging one black key — are gone with their props; the annotation
page and the detection view never passed them and did not change.

Checked in a real browser, headless Chromium driven by Playwright against `make serve`, on `derulo`,
`shut-up-and-dance` and `airplanes`: step 1 shows the overlay on the keys, step 2 opens with the
offset line and the saved readings, step 3 runs the detector and draws its rectangles (11 on `derulo`
in 12 ms, 3 onsets as saved), with no page error and no console error on any of the nine screens.
`airplanes` still draws the wrong seed 04 left it — 89 keys from G1 — which is what Phase 3's found
overlay replaces.

## 6. The calibration editor, emptied

Every button of the old flow is gone: place the white key, place the black key, render one octave,
render the piano, move the piano, + key left, + key right, and the backspace trim. What is on the
screen: the saved overlay, the upper line dragged up and down on a grab strip (V-11), the octave
dropdown (V-10), and Save. The leftmost key dropdown is gone too: the pattern fixes the pitch class
and the names on hover show it. `DragRect.tsx` is unused and stays until Phase 3 replaces it with
the one rectangle.

## 7. The checks

```text
cd aitu-backend
  make test          1 failed, 816 passed        (812 before: 4 new tests, net of the replaced ones)
      the one failure is the known pre-existing
      tests/test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas
  flake8             4 errors, all pre-existing and the same four
  mypy              30 errors, all pre-existing, none in anything this phase touched

cd aitu-frontend
  npx tsc -b         clean
  npm run lint       clean
  npm run check:geometry   both cases pass; fails on a tenth of a pixel
  npm run check:render     26 passed, 0 failed
```

## 8. What Phase 3 should know before it starts

1. **The finder returns a `Calibration`**, built as section 4 of the Phase 1 report says: white
   borders from route A in u along the top edge, black borders from each key's `centre ± width / 2`,
   `blackDepth` from the band, `found` from the alignment. `whiteWidth` may be left at zero; the
   validator derives it.
2. **The rectifier is `poc-piano-overlay/scripts/common.py rectify()`**: bilinear sampling of the
   picture inside the rectangle at one sample per pixel of the top edge, rotated by the angle about
   the top left corner. Port it beside the finder; it has never run at a non-zero angle on a real
   picture, so a drawn keyboard at an angle is the test.
3. **The finder must not throw on a rectangle with no keyboard in it**: fewer than four candidates
   is an empty answer with a reason, and the endpoint turns that into a 422 the screen can show.
4. **Pitch class from the pattern**: the first black key's name and how many white borders precede it
   give the pitch class of the leftmost white key; on the 24 examples that is A everywhere but
   `superestrella` (C). `defaultOctaveFor(whiteCount)` is the octave to offer.
5. **The seed rewrites**: Task 3.1.3 replaces the 21 spelt-out grids with found overlays and adds
   the three `ode` pictures that never had one. The two examples with hand readings keep them, and
   the score board is quoted again afterwards.
6. **A driven browser exists for this project**: Playwright from the npx cache with the installed
   browser build, launched with `executablePath` at
   `~/Library/Caches/ms-playwright/chromium_headless_shell-1228/.../chrome-headless-shell`; the
   script is nine lines of `goto`, tab clicks and screenshots. The step 3 page is ready when the text
   "rectangles ·" appears.
