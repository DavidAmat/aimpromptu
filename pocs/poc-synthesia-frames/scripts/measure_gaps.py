"""How big is the gap between two rectangles stacked on the same key?

Two notes in a row on one key are drawn as two rectangles touching, separated
only by their own dark borders. If the detector closes that gap it reports one
long note instead of two, and the second onset is lost — silently, which is the
worst way to lose one. So the size of that gap is measured before anything is
closed, and `gapClose` is set from the measurement.

Two populations are expected and both matter: the small gaps inside one
rectangle, which are texture and noise and have to be closed, and the gaps
between two rectangles, which have to be kept.
"""
from __future__ import annotations

import numpy as np

import testvid

TAU = 24.0
MIN_RUN = 4           # rows: below this a "run" is noise, not a rectangle


def gaps_in(strength: np.ndarray, cal, margin: float = 0.25) -> list[int]:
    out: list[int] = []
    w = cal.white_width
    for lane in cal.lanes(margin):
        a = max(0, int(lane["x0"] + margin * w))
        b = min(strength.shape[1], int(lane["x1"] - margin * w) + 1)
        if b - a < 3:
            continue
        prof = strength[:, a:b].mean(axis=1)
        on = prof > TAU
        runs, st = [], None
        for i, v in enumerate(on):
            if v and st is None:
                st = i
            elif not v and st is not None:
                runs.append((st, i))
                st = None
        if st is not None:
            runs.append((st, len(on)))
        runs = [r for r in runs if r[1] - r[0] >= MIN_RUN]
        for i in range(len(runs) - 1):
            out.append(runs[i + 1][0] - runs[i][1])
    return out


def main(n_frames: int = 60):
    cal = testvid.calibration()
    bg = testvid.plate()
    u = int(round(cal.upper_line))
    idx = np.linspace(0, len(testvid.frames()) - 1, n_frames).round().astype(int)
    gaps = []
    for i in idx:
        img = testvid.load(int(i))
        gaps.extend(gaps_in(np.abs(img[:u] - bg[:u]).max(axis=2), cal))
    gaps = np.asarray(gaps)
    print(f"{len(gaps)} gaps between runs, over {n_frames} sampled frames")
    print(f"{'gap rows':>8s} {'count':>6s}")
    for g in range(0, 16):
        c = int((gaps == g).sum())
        bar = "#" * min(60, c // 4)
        if c:
            print(f"{g:8d} {c:6d}  {bar}")
    big = int((gaps > 15).sum())
    print(f"{'>15':>8s} {big:6d}   (different notes, far apart)")
    near = gaps[gaps <= 15]
    print(f"\ngaps of 15 rows or less: {len(near)}")
    print(f"  1 to 2 rows: {int(((near >= 1) & (near <= 2)).sum())}"
          f"   — texture inside one rectangle, to be closed")
    print(f"  3 to 7 rows: {int(((near >= 3) & (near <= 7)).sum())}"
          f"   — two rectangles touching, to be kept")


if __name__ == "__main__":
    main()
