"""Where does the roll actually start?

The plan's calibration bounds the roll below, at the upper line, and assumed the
top of the picture bounds it above. The test video says otherwise: it carries a
Synthesia toolbar over rows 0 to 28 and a progress bar with a sliding playhead
over rows 29 to 58, and the roll only begins at row 59. A rectangle coming into
view appears at row 59 and grows downward, and anything the detector reads above
that row is chrome, not music.

Finding it needs a cue that separates the roll from everything else, and there
is a perfect one: the roll scrolls and nothing else does. So for every row, the
question is whether the next sampled frame looks like this row moved down by one
frame of travel, or like it did not move at all. The roll answers the first, the
toolbar and the progress bar answer the second.
"""
from __future__ import annotations

import numpy as np


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d > 1e-6 else 0.0


def find(load, indices, upper: int, speed: float, smooth: int = 9) -> dict:
    """The first row of the roll, and the score each row got."""
    step = int(round(speed))
    score = np.zeros(upper)
    pairs = 0
    for i in indices:
        a = load(i).mean(axis=2)
        b = load(i + 1).mean(axis=2)
        if a.shape[0] < upper + 1:
            continue
        pairs += 1
        for y in range(0, upper - step - 1):
            moved = _corr(a[y], b[y + step])
            still = _corr(a[y], b[y])
            score[y] += moved - still
    if pairs:
        score /= pairs
    k = np.ones(smooth) / smooth
    sm = np.convolve(score, k, mode="same")

    # The roll is the longest stretch of rows that look like they moved. Its
    # first row is the answer.
    good = sm > 0.05
    best, cur = (0, 0), None
    for y in range(len(good)):
        if good[y] and cur is None:
            cur = y
        elif not good[y] and cur is not None:
            if y - cur > best[1] - best[0]:
                best = (cur, y)
            cur = None
    if cur is not None and len(good) - cur > best[1] - best[0]:
        best = (cur, len(good))
    return dict(roll_top=int(best[0]), roll_bottom=int(best[1]), score=sm)


def main():
    import testvid
    cal = testvid.calibration()
    u = int(round(cal.upper_line))
    r = find(testvid.load, range(200, 230), u, 16.89)
    sm = r["score"]
    print(f"roll top found at row {r['roll_top']}, roll runs to row {r['roll_bottom']}, "
          f"upper line at {u}")
    print("\nrow   does this row look like it moved down one frame of travel?")
    for y in list(range(0, 96, 4)) + [120, 200, 300, 400, 500, 540]:
        if y >= len(sm):
            continue
        v = sm[y]
        bar = "#" * int(max(0, v) * 60)
        print(f"{y:4d} {v:7.3f} {bar}")


if __name__ == "__main__":
    main()
