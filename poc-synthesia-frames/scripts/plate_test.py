"""Does the real background plate remove the static decoration?

On the example screenshots the plate has to be stood in for, and every invented
onset left on the two clean examples sat on an octave guide line — static
decoration the stand-in cannot remove. V-15 says the real plate removes it. This
runs both on real video frames and counts what lands on a guide line.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

import common
import detectors
import scroll_speed
from common import Calibration

N_FRAMES = 120


def main():
    paths = scroll_speed.frames()
    bg = np.load(common.DATA / "video" / "plate.npy")
    mid = scroll_speed.load_frame(paths[len(paths) // 2])
    import find_keyboard
    cal = find_keyboard.find(mid, "video")
    print(f"upper={cal.upper_line:.0f} w={cal.white_width:.2f} "
          f"whites={cal.white_count} first={cal.keys()[0]['midi']}")

    # Where the guide lines are: columns that are bright in the plate's roll
    # band and stay bright for most of its height.
    u = int(round(cal.upper_line))
    roll_plate = bg[:u].mean(axis=2)
    colish = roll_plate > np.percentile(roll_plate, 50) + 8
    guide = np.where(colish.mean(axis=0) > 0.6)[0]
    print(f"static vertical decoration in the plate at x = {list(guide)}")

    pick = np.linspace(0, len(paths) - 1, N_FRAMES).round().astype(int)
    d = 2.0 * cal.white_width
    totals = {}
    for label, plate_img in (("stand-in (per-row median)", None),
                             ("real plate (median of 50 frames)", bg)):
        runs = onsets = on_guide = 0
        for i in pick:
            img = scroll_speed.load_frame(paths[i])
            res = detectors.detect(img, cal, d, "plate", plate_img=plate_img)
            runs += len(res["runs"])
            onsets += len(res["onsets"])
            for r in res["runs"]:
                if guide.size and np.min(np.abs(guide - r["mid"])) <= 4:
                    on_guide += 1
        totals[label] = (runs, onsets, on_guide)
        print(f"{label:34s} runs {runs:5d}  onsets {onsets:5d}  "
              f"runs on a guide line {on_guide:5d} "
              f"({100 * on_guide / max(runs, 1):.1f}%)")
    return totals


if __name__ == "__main__":
    main()
