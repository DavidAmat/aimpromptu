"""Run the keyboard finder over every example and draw what it found."""
from __future__ import annotations

import sys

import common
import find_keyboard
import overlay

OUT = common.OUT / "calibration"


def main(only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    cals = common.load_calibrations()
    for slug in common.slugs():
        if only and slug not in only:
            continue
        img = common.load(slug)
        try:
            cal = find_keyboard.find(img, slug)
        except RuntimeError as exc:
            print(f"{slug:24s} FAILED  {exc}")
            continue
        cals[slug] = cal
        keys = cal.keys()
        print(f"{slug:24s} upper={cal.upper_line:6.1f} w={cal.white_width:6.2f} "
              f"whites={cal.white_count:3d} keys={len(keys):3d} "
              f"first={cal.first_white_pc:2d} oct={cal.first_white_octave}")
        overlay.draw(img, cal, OUT / f"{slug}.jpg", crop_to_roll=True)
    common.save_calibrations(cals)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
