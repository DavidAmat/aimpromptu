"""Write the piano overlay fixture both services assert against.

Task 2.1.1 of 04 says one module owns the geometry and the backend and the
frontend agree on its shape. They cannot literally share the code — the
calibration UI redraws the overlay on every drag and a round trip per drag is
not a UI — so they share a fixture instead:

* `aitu-backend/tests/test_video_geometry.py` asserts `video/geometry.py`
  against it;
* `aitu-frontend/scripts/check-geometry.ts` asserts `src/video/overlayGeometry.ts`
  against the same file.

Neither implementation can drift without one of those failing.

Two cases, since implementation 05 (V-38): a straight one — the whole 88 key
piano of 04's test video, spelt out from its grid, so the keys are the numbers
Phase 1 of 04 measured — and an angled one whose white keys widen from left to
right, so the check covers what a grid could not: borders that are not evenly
spaced, and a top edge that is not horizontal.

    cd aitu-backend
    uv run python scripts/build_geometry_fixture.py
"""

from __future__ import annotations

import json
import sys

from aitu_backend.schemas.video import BlackBorder, Calibration, PianoRect
from aitu_backend.video import geometry
from aitu_backend.video.geometry import DEFAULT_LANE_MARGIN
from aitu_backend.video.upgrade import REAL_BLACK_OFFSETS, grid_to_borders

FIXTURE = "tests/fixtures/video/geometry-fixture.json"

#: A whole 88 key piano at the working resolution — the numbers Phase 1 of 04
#: measured on its test video, `pgLt4WmPMYQ`: 52 white keys, A0 to C8, upper
#: line at row 561, white key width 24.57 px, roll top 62, guard band 39.
STRAIGHT = Calibration.model_validate(
    grid_to_borders(
        {
            "imageWidth": 1280,
            "imageHeight": 720,
            "upperLine": 561.0,
            "leftBorder": 1.5,
            "whiteWidth": 24.571428571428573,
            "whiteCount": 52,
            "whiteHeight": 110.0,
            "blackHeight": 68.0,
            "blackRatio": 0.58,
            "blackMode": "real",
            "blackNudge": 0.0,
            "firstWhitePitchClass": 9,
            "firstWhiteOctave": 0,
            "rollTop": 62.0,
            "guardBand": 39.0,
            "note": "the test video of Phase 1: pgLt4WmPMYQ, 1280x720",
        }
    )
)


def _angled() -> Calibration:
    """Thirty white keys from C2, widening by 0.12 px each, on a rectangle at 4 degrees."""
    borders = [0.0]
    for i in range(30):
        borders.append(borders[-1] + 22.0 + 0.12 * i)
    blacks = []
    pitch_classes = [0, 2, 4, 5, 7, 9, 11]
    for i in range(29):
        pc = pitch_classes[i % 7]
        if pc in (4, 11):
            continue
        local = (borders[i + 1] - borders[i] + borders[i + 2] - borders[i + 1]) / 2
        centre = borders[i + 1] + REAL_BLACK_OFFSETS[pc + 1] * local
        blacks.append(BlackBorder(left=centre - 0.29 * local, right=centre + 0.29 * local))
    return Calibration(
        image_width=1280,
        image_height=720,
        piano_rect=PianoRect(x=40.0, y=500.0, width=1200.0, height=200.0, angle=4.0),
        upper_line=500.0,
        white_borders=borders,
        black_borders=blacks,
        black_depth=60.0,
        first_white_pitch_class=0,
        first_white_octave=2,
        note="a drawn keyboard: borders widening left to right, on a rectangle at 4 degrees",
    )


def main() -> int:
    from pathlib import Path

    cases = []
    for name, cal in (("straight", STRAIGHT), ("angled", _angled())):
        built = geometry.geometry(cal, DEFAULT_LANE_MARGIN)
        cases.append(
            {
                "name": name,
                "calibration": cal.model_dump(by_alias=True),
                "margin": built.margin,
                "keys": [key.model_dump(by_alias=True) for key in built.keys],
                "lanes": [lane.model_dump(by_alias=True) for lane in built.lanes],
            }
        )
        blacks = sum(1 for key in built.keys if key.kind == "black")
        print(
            f"{name}: {len(built.keys)} keys, {blacks} of them black, "
            f"{built.keys[0].name_en} to {built.keys[-1].name_en}"
        )
    payload = {
        "_about": (
            "The piano overlay both services build from the same calibrations. "
            "aitu-backend/tests/test_video_geometry.py and "
            "aitu-frontend/scripts/check-geometry.ts both assert against it, so the "
            "two implementations cannot drift apart without a check failing. "
            "Regenerate with scripts/build_geometry_fixture.py."
        ),
        "cases": cases,
    }
    Path(FIXTURE).write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {FIXTURE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
