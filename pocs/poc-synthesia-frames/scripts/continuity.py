"""Does the detector give the same answer about the same rectangle twice?

The complaint that started this was that three stacked rectangles were reported
as one in one lane and as three in another, on the same frame and the same
rendering. There is no hand labelling that catches that at scale, but the video
catches it for free: a rectangle falls by exactly the scroll speed between one
sampled frame and the next, so a run seen at rows y0..y1 in this frame must be
seen at y0+s..y1+s in the next one, with the same height.

Every run that is not is a run the detector cut differently in two frames of the
same rectangle. The share that survives is a score with no labels in it, and it
is the score every threshold here is tuned against.

Two kinds of run are left out of the count, because both are supposed to change
height and neither says anything about consistency: one near the upper line,
which is about to be cut by it, and one touching the top edge of the picture,
which is still coming into view and grows downward by exactly one frame of
travel each frame.
"""
from __future__ import annotations

import numpy as np

import detectors
import testvid

TOL = 3.0          # rows of slack on each edge
MARGIN = 60        # rows above the upper line where a run is about to be clipped
TOP_EDGE = 3       # rows: a run this close to the top of the picture is still
                   # coming into view, so its top is the frame edge, not the
                   # rectangle's


def score(n_pairs: int = 40, first: int = 100, speed: float = 16.89,
          verbose: bool = False) -> dict:
    cal = testvid.calibration()
    bg = testvid.plate()
    u = int(round(cal.upper_line))
    d = speed

    matched = total = 0
    heights = []
    prev = None
    for i in range(first, first + n_pairs + 1):
        img = testvid.load(i)
        cur = detectors.detect(img, cal, d, plate_img=bg)["runs"]
        heights.extend(r["y_bottom"] - r["y_top"] + 1 for r in cur)
        if prev is not None:
            by_key: dict[int, list] = {}
            for r in cur:
                by_key.setdefault(r["midi"], []).append(r)
            for r in prev:
                # It will be cut by the upper line in the next frame, so it is
                # allowed to change shape.
                if r["y_bottom"] + speed >= u - 1 or r["y_bottom"] > u - 1 - MARGIN:
                    continue
                if r.get("entering"):
                    continue
                total += 1
                want_top = r["y_top"] + speed
                want_bot = r["y_bottom"] + speed
                for c in by_key.get(r["midi"], ()):
                    if (abs(c["y_top"] - want_top) <= TOL
                            and abs(c["y_bottom"] - want_bot) <= TOL):
                        matched += 1
                        break
        prev = cur
    h = np.asarray(heights)
    return dict(matched=matched, total=total,
                rate=matched / max(total, 1),
                runs_per_frame=len(h) / (n_pairs + 1),
                h_median=float(np.median(h)), h_p95=float(np.percentile(h, 95)),
                h_max=int(h.max()))


def sweep(values, attr: str, **kw):
    keep = getattr(detectors, attr)
    print(f"{attr:18s} {'continuity':>11s} {'runs/frame':>11s} "
          f"{'height med':>11s} {'p95':>6s} {'max':>5s}")
    for v in values:
        setattr(detectors, attr, v)
        r = score(**kw)
        print(f"{v!s:18s} {100 * r['rate']:10.1f}% {r['runs_per_frame']:11.1f} "
              f"{r['h_median']:11.1f} {r['h_p95']:6.1f} {r['h_max']:5d}"
              f"    ({r['matched']} of {r['total']})")
    setattr(detectors, attr, keep)


if __name__ == "__main__":
    sweep([0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.70, 2.0], "SPLIT_PROMINENCE")
