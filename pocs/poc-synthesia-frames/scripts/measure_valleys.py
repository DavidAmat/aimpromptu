"""How deep is the border between two rectangles, when it does not break the run?

The gap measurement answered the easy half: where the border falls below
`tauForeground` the run ends by itself. This is the other half. On a real lane
the plateau of a rectangle is flat to about 1% and the borders dip to 25% and to
60% of it, so a rule that cuts below a fixed share of the run's median splits one
border and misses the other.

The rule that works is prominence: how far a local minimum drops below the
plateau on both sides of it, as a share of that plateau. Texture ripples inside
one rectangle have a prominence of a few percent. A border has tens of percent.
This measures both populations so the threshold between them is read off the
data rather than guessed.
"""
from __future__ import annotations

import numpy as np

import testvid

TAU = 24.0
MIN_PIECE = 6          # rows: no rectangle is shorter than this


def valleys(prof: np.ndarray) -> list[tuple[int, float, float]]:
    """Every interior local minimum of a run: (row, value, prominence share)."""
    if len(prof) < 2 * MIN_PIECE + 1:
        return []
    plateau = float(np.percentile(prof, 75))
    if plateau <= 1:
        return []
    # Candidate rows: a local minimum, ties included, so a flat bottom is caught.
    cand = []
    for i in range(MIN_PIECE, len(prof) - MIN_PIECE):
        if prof[i] <= prof[i - 1] and prof[i] <= prof[i + 1]:
            cand.append(i)
    if not cand:
        return []
    # One valley, one answer. A flat bottom is one border, not forty, so
    # neighbouring candidates are grouped and only the deepest is kept.
    groups, cur = [], [cand[0]]
    for i in cand[1:]:
        if i - cur[-1] <= MIN_PIECE:
            cur.append(i)
        else:
            groups.append(cur)
            cur = [i]
    groups.append(cur)

    out = []
    for g in groups:
        i = min(g, key=lambda r: prof[r])
        v = float(prof[i])
        left = float(prof[:g[0]].max()) if g[0] > 0 else 0.0
        right = float(prof[g[-1] + 1:].max()) if g[-1] + 1 < len(prof) else 0.0
        if left <= 0 or right <= 0:
            continue
        out.append((i, v, (min(left, right) - v) / plateau))
    return out


def runs_of(prof: np.ndarray) -> list[tuple[int, int]]:
    on = prof > TAU
    out, st = [], None
    for i, v in enumerate(on):
        if v and st is None:
            st = i
        elif not v and st is not None:
            out.append((st, i))
            st = None
    if st is not None:
        out.append((st, len(on)))
    return [r for r in out if r[1] - r[0] >= 2 * MIN_PIECE + 1]


def main(n_frames: int = 40):
    cal = testvid.calibration()
    bg = testvid.plate()
    u = int(round(cal.upper_line))
    keys = cal.keys()
    idx = np.linspace(0, len(testvid.frames()) - 1, n_frames).round().astype(int)

    proms = []
    for i in idx:
        img = testvid.load(int(i))
        strength = np.abs(img[:u] - bg[:u]).max(axis=2)
        for k in keys:
            a = max(0, int(round(k["left"])))
            b = min(strength.shape[1], int(round(k["right"])) + 1)
            if b - a < 3:
                continue
            prof = strength[:, a:b].mean(axis=1)
            for lo, hi in runs_of(prof):
                for _, _, p in valleys(prof[lo:hi]):
                    proms.append(p)
    proms = np.asarray(proms)
    print(f"{len(proms)} interior local minima, over {n_frames} sampled frames")
    print(f"{'prominence':>11s} {'count':>6s}")
    edges = [0, .02, .04, .06, .08, .10, .15, .20, .25, .30, .40, .50, .70, 1.0, 99]
    hist, _ = np.histogram(proms, bins=edges)
    for i in range(len(hist)):
        bar = "#" * min(60, hist[i] // 20)
        hi = "  +" if edges[i + 1] > 1.5 else f"{edges[i + 1]:4.2f}"
        print(f"{edges[i]:5.2f}-{hi} {hist[i]:6d}  {bar}")
    print()
    for t in (.10, .15, .20, .25, .30, .35, .40):
        print(f"  cutting at prominence {t:.2f}: {int((proms >= t).sum()):6d} borders, "
              f"{int((proms < t).sum()):6d} left as texture")


if __name__ == "__main__":
    main()
