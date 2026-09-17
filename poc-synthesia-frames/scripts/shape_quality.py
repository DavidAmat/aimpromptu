"""How many of the runs a detector finds look like a note at all?

There is no hand read ground truth high in the roll, and there does not need to
be one. Two things are true of a rectangle that stands for a key and of nothing
else in these pictures: it sits over that key's midpoint, and every rectangle of
the same kind in the same video is the same width as the others.

The second one has to be asked per example, not against fixed numbers. The two
widths are a property of the rendering, not of pianos: this video draws its white
key rectangles at 1.03 white key widths, `shut-up-and-dance` at 0.97 and `derulo`
at 0.83. So the question is not "is this run one of two fixed widths" but "do all
the runs of one kind in one example agree with each other", which is what a
detector that is cutting rectangles consistently would produce.
"""
from __future__ import annotations

import numpy as np

import common
import detectors
from run_detectors import CHOSEN, NAMES

NEAR_MID = 0.25            # of a white key width


def quality(slug: str, mask_name: str, band=(8.0, 3.0)) -> dict:
    cal = common.load_calibrations()[slug]
    img = common.load(slug)
    u, w = int(round(cal.upper_line)), cal.white_width
    res = detectors.detect(img, cal, 2.0 * w, mask_name=mask_name)
    lo, hi = u - int(band[0] * w), u - int(band[1] * w)
    runs = [r for r in res["runs"] if lo <= r["y_bottom"] <= hi]
    kinds = {k["midi"]: k["kind"] for k in cal.keys()}
    mids = np.array([k["mid"] for k in cal.keys()])

    on_mid = sum(1 for r in runs
                 if np.min(np.abs(mids - r["mid"])) / w <= NEAR_MID)
    spreads = {}
    for kind in ("white", "black"):
        ws = [r["width_keys"] for r in runs if kinds.get(r["midi"]) == kind]
        if len(ws) >= 2:
            spreads[kind] = (float(np.median(ws)),
                             float(np.max(ws) - np.min(ws)))
        elif ws:
            spreads[kind] = (float(ws[0]), 0.0)
    return dict(n=len(runs), on_mid=on_mid, spreads=spreads)


def main(band=(8.0, 3.0)):
    print(f"band {band[0]} to {band[1]} white key widths above the upper line")
    print(f"{'detector':10s} {'example':22s} {'runs':>5s} {'on a midpoint':>14s} "
          f"{'white width':>18s} {'black width':>18s}")
    for name in [n for n in NAMES if n != "single-row"]:
        tot_n = tot_m = 0
        worst = 0.0
        for slug in CHOSEN:
            q = quality(slug, name, band)
            tot_n += q["n"]
            tot_m += q["on_mid"]
            cells = []
            for kind in ("white", "black"):
                if kind in q["spreads"]:
                    med, spread = q["spreads"][kind]
                    worst = max(worst, spread)
                    cells.append(f"{med:.2f} +-{spread:.2f}")
                else:
                    cells.append("-")
            print(f"{name:10s} {slug:22s} {q['n']:5d} "
                  f"{q['on_mid']:6d} {100 * q['on_mid'] / max(q['n'], 1):5.0f}% "
                  f"{cells[0]:>18s} {cells[1]:>18s}")
        print(f"{name:10s} {'TOTAL':22s} {tot_n:5d} "
              f"{tot_m:6d} {100 * tot_m / max(tot_n, 1):5.0f}% "
              f"   widest disagreement within one example and kind: {worst:.2f} keys\n")


if __name__ == "__main__":
    main()
