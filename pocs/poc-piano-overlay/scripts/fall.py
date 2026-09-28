"""Do the rectangles fall vertically on the tilted pictures? (Task 1.1.3)

The lane of a key is a vertical strip of the picture only if the falling
rectangles are vertical in the picture whatever the camera did to the piano.
This measures the lean of the strong near-vertical edges in the roll — the
sides of the rectangles and of the light beams — and the lean of the white key
borders in the front of the keys on the same picture, both in degrees from
vertical, positive when the top leans right.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from scipy import ndimage

from common import DATA, grey, load_rects, load_rgb, slugs


def roll_lean(image: np.ndarray, upper: float) -> tuple[float, float, int]:
    """The lean of the strong near-vertical edges above the upper line.

    Sobel gradients; a pixel is an edge when |gx| is in the top 2% of the roll.
    The edge direction is perpendicular to the gradient, so its lean from
    vertical is atan(gy / gx). Edges leaning more than 25 degrees are left out
    (they are the tops and bottoms of rectangles, lettering, the glow). The
    answer is the median lean and the spread between the quartiles.
    """
    roll = image[: max(10, int(upper) - 8)]
    gx = ndimage.sobel(roll, axis=1)
    gy = ndimage.sobel(roll, axis=0)
    mag = np.abs(gx)
    strong = mag > np.percentile(mag, 98)
    lean = np.degrees(np.arctan2(gy[strong], gx[strong]))
    # an edge whose gradient points left is the same edge: fold to -90..90
    lean = np.where(lean > 90, lean - 180, lean)
    lean = np.where(lean < -90, lean + 180, lean)
    keep = np.abs(lean) < 25
    lean = lean[keep]
    if len(lean) < 50:
        return float("nan"), float("nan"), int(len(lean))
    q1, q3 = np.percentile(lean, [25, 75])
    return float(np.median(lean)), float(q3 - q1), int(len(lean))


def main() -> None:
    truth = json.loads((DATA / "truth.json").read_text())
    rects = load_rects()
    print("picture                  roll lean  spread  edges   key border lean: left  mid  right   (degrees from vertical)")
    for slug in slugs():
        g = grey(load_rgb(slug))
        r = rects[slug]
        med, spread, n = roll_lean(g, r.y)
        t = truth[slug]
        rows = t["v_low"] - t["v_high"]
        def lean_of(lo, hi):
            sel = [b for b in t["borders"] if lo <= b["u_top"] < hi]
            if not sel:
                return float("nan")
            return float(np.degrees(np.arctan(np.median([(b["u_low"] - b["u_high"]) / rows for b in sel]))))
        print(f"{slug:24s} {med:8.2f} {spread:7.2f} {n:7d}     {lean_of(0,427):6.2f} {lean_of(427,854):6.2f} {lean_of(854,1281):6.2f}")


if __name__ == "__main__":
    main()
