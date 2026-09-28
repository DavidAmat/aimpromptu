"""The momentum rule, on three consecutive frames of Ode to Vivian.

A song title and decorative scrollwork drawn across the roll look exactly like
rectangles to a detector that only ever sees one picture. They give themselves
away the moment there is a second picture: **a rectangle falls and a letter does
not.** So a run is believed when the frame before it held the same run one frame
of travel higher, and refused when the frame before it held the same run in the
same place.

Three screenshots are not three sampled frames of one video: they are cropped
slightly differently, so their upper lines sit at rows 423, 426 and 424 and
nothing lines up. They are registered on the keyboard first, which is the one
part of the picture that is supposed to be static, and only then is the roll
asked what moved.
"""
from __future__ import annotations

import json

import numpy as np

import common
import detectors
import find_keyboard

SLUGS = ["ode1", "ode2", "ode3"]
SEARCH = 14            # px: how far the registration looks
TOL = 5.0              # px of slack when matching a run to the frame before it.
                       # MEASURED: at 3 the vote is stable but a few real notes
                       # are missed, at 7 the vote collapses onto the static
                       # content because the slack lets a letter match itself at
                       # a small shift
STATIC_TOL = 2.0       # px: this close to where it was, it did not move
VOTE_FLOOR = 15        # px: the vote never considers a travel smaller than this,
                       # because that is where the answer "nothing moved" lives
ONE_TO_ONE = True      # a rectangle in the neighbouring frame is the past of at
                       # most one rectangle in this one. Turning this off is what
                       # the aliasing looks like


def register(ref: np.ndarray, img: np.ndarray, upper: int, w: float) -> tuple[int, int]:
    """The (dx, dy) that puts this picture's keyboard on the reference's.

    The keyboard is the static part, so aligning on it aligns everything the
    roll does to the roll alone.
    """
    y0, y1 = upper, min(ref.shape[0], img.shape[0], upper + int(3.0 * w))
    a = ref[y0:y1].mean(axis=2)
    best, best_score = (0, 0), -1e18
    for dy in range(-SEARCH, SEARCH + 1):
        for dx in range(-SEARCH, SEARCH + 1):
            ys, xs = y0 + dy, dx
            if ys < 0 or ys + (y1 - y0) > img.shape[0]:
                continue
            b = img[ys:ys + (y1 - y0)].mean(axis=2)
            if xs >= 0:
                aa, bb = a[:, xs:], b[:, :b.shape[1] - xs] if xs else b
            else:
                aa, bb = a[:, :a.shape[1] + xs], b[:, -xs:]
            n = min(aa.shape[1], bb.shape[1])
            if n < 200:
                continue
            score = -float(np.abs(aa[:, :n] - bb[:, :n]).mean())
            if score > best_score:
                best_score, best = score, (dx, dy)
    return best


def roll_shift(a: np.ndarray, b: np.ndarray, upper: int,
               plate: np.ndarray) -> tuple[float, float]:
    """How far the roll moved down between two registered pictures.

    Measured against the plate, not against a row background. The title of this
    piece is drawn in letters a hundred pixels tall across the middle of the
    roll; they dominate any profile that still contains them, the correlation
    peaks at a shift of zero because the letters really did not move, and the
    answer comes back as nought. Taking the plate out first leaves the
    rectangles, which are the only thing that moves.
    """
    def prof(img):
        band = np.abs(img[int(0.08 * upper):upper] - plate[int(0.08 * upper):upper])
        return band.max(axis=2).mean(axis=1)
    from scroll_speed import shift
    return shift(prof(a), prof(b), max_lag=upper // 2)


def matches_at(runs, prev, s: float) -> int:
    """How many runs of this frame sit exactly `s` pixels below a run of the one
    before, on the same key and with the same height."""
    by_key: dict[int, list] = {}
    for r in prev:
        by_key.setdefault(r["midi"], []).append(r)
    n = 0
    for r in runs:
        for c in by_key.get(r["midi"], ()):
            if (abs(c["y_top"] - (r["y_top"] - s)) <= TOL
                    and abs(c["y_bottom"] - (r["y_bottom"] - s)) <= TOL):
                n += 1
                break
    return n


def vote_for_travel(runs, prev, lo: int = VOTE_FLOOR, hi: int = 220) -> tuple[int, int, int]:
    """Let the rectangles say how far they fell.

    A correlation cannot answer it here. The notes of this piece are stacked
    about 115 px apart and the frames are about 65 px apart, so the picture after
    two steps looks like the picture before one, and the correlation locks onto
    the wrong multiple. The runs themselves have no such problem: the travel is
    the shift at which the most of them line up.

    A shift of nothing is excluded on purpose. That peak is the title and the
    scrollwork, and counting it is the mistake this whole rule exists to avoid —
    but it is returned too, because how big it is says how much of the picture is
    not music.
    """
    best = max(range(lo, hi + 1), key=lambda s: matches_at(runs, prev, s))
    return best, matches_at(runs, prev, best), matches_at(runs, prev, 0)


def _index(runs) -> dict:
    by_key: dict[int, list] = {}
    for i, r in enumerate(runs):
        by_key.setdefault(r["midi"], []).append((i, r))
    return by_key


def _fits(c, r, dy: float, tol: float) -> float | None:
    """How badly c fits as the same rectangle as r, dy pixels away. None = no."""
    a = abs(c["y_top"] - (r["y_top"] + dy))
    b = abs(c["y_bottom"] - (r["y_bottom"] + dy))
    return a + b if a <= tol and b <= tol else None


def link(runs, other, dy: float) -> tuple[list[int | None], set[int]]:
    """Match every run of this frame to its own self in a neighbouring frame.

    One to one, and that is the whole point. A rectangle in the neighbouring
    frame can be the past of exactly one rectangle in this one. Without that
    constraint a repeated note aliases: when a key is struck twice and the two
    strokes are about one frame of travel apart, the rectangle of the first
    stroke sits, in the frame before, exactly where the rectangle of the second
    stroke sits now — so the second stroke looks like it never moved, and a rule
    that only asks "is there something here" throws away a real note.

    Pairs are taken best fit first, so the closest reading of each rectangle wins
    and the leftovers cannot steal it.
    """
    idx = _index(other)
    pairs = []
    for i, r in enumerate(runs):
        for j, c in idx.get(r["midi"], ()):
            cost = _fits(c, r, dy, TOL)
            if cost is not None:
                pairs.append((cost, i, j))
    pairs.sort()
    link_of: list[int | None] = [None] * len(runs)
    taken: set[int] = set()
    for _, i, j in pairs:
        if link_of[i] is None and j not in taken:
            link_of[i] = j
            taken.add(j)
    return link_of, taken


def verdicts(runs, before, before_travel, after, after_travel) -> list[str]:
    """One word per run: did it fall, did it stand still, or is there no telling.

    Both neighbours are asked, not only the one before. A rectangle at the top of
    the roll has no frame before it that holds it, but the frame after it holds
    it one travel lower, and that is just as good an answer.

    Standing still is only believed when the thing standing in the way is not
    already spoken for. That is the anti aliasing part: the rectangle that makes
    a second stroke look static is, very often, the first stroke's own rectangle
    seen one frame earlier — and it is already claimed as the predecessor of the
    rectangle below. A claimed rectangle is not evidence that anything stood
    still.
    """
    fell_b, claimed_b = (link(runs, before, -before_travel) if before
                         else ([None] * len(runs), set()))
    fell_a, claimed_a = (link(runs, after, +after_travel) if after
                         else ([None] * len(runs), set()))
    idx_b, idx_a = _index(before), _index(after)

    out = []
    for i, r in enumerate(runs):
        if fell_b[i] is not None or fell_a[i] is not None:
            out.append("fell")
            continue
        still = False
        for idx, claimed in ((idx_b, claimed_b), (idx_a, claimed_a)):
            for j, c in idx.get(r["midi"], ()):
                if ONE_TO_ONE and j in claimed:
                    continue          # already the past of another rectangle
                if _fits(c, r, 0.0, STATIC_TOL) is not None:
                    still = True
                    break
            if still:
                break
        out.append("static" if still else "unknown")
    return out


def main():
    imgs = {s: common.load(s) for s in SLUGS}
    cal = find_keyboard.find(imgs["ode1"], "ode1")
    u, w = int(round(cal.upper_line)), cal.white_width
    ref = imgs["ode1"]

    aligned = {"ode1": ref}
    offsets = {"ode1": (0, 0)}
    for s in SLUGS[1:]:
        dx, dy = register(ref, imgs[s], u, w)
        offsets[s] = (dx, dy)
        out = np.zeros_like(ref)
        src = imgs[s]
        ys0, ys1 = max(0, dy), min(src.shape[0], ref.shape[0] + dy)
        yd0 = ys0 - dy
        xs0, xs1 = max(0, dx), min(src.shape[1], ref.shape[1] + dx)
        xd0 = xs0 - dx
        out[yd0:yd0 + (ys1 - ys0), xd0:xd0 + (xs1 - xs0)] = src[ys0:ys1, xs0:xs1]
        aligned[s] = out
        print(f"{s}: registered onto ode1 by dx={dx:+d} dy={dy:+d}")

    # Three frames are enough for a plate here: the title and the scrollwork are
    # in all three and the rectangles are not in the same place in any two, so
    # the middle value of three is the background almost everywhere.
    plate = np.median(np.stack([aligned[s] for s in SLUGS]), axis=0)

    d = 2.0 * w
    runs, runs3, res_of = {}, {}, {}
    for s in SLUGS:
        # What one picture alone can do: the single screenshot stand-in.
        res = detectors.detect(aligned[s], cal, d, mask_name="plate")
        runs[s] = sorted(res["runs"], key=lambda r: (r["midi"], r["y_top"]))
        res_of[s] = res
        # What three pictures can do: a real plate, even from only three.
        res3 = detectors.detect(aligned[s], cal, d, plate_img=plate)
        runs3[s] = sorted(res3["runs"], key=lambda r: (r["midi"], r["y_top"]))
        res_of[s + "_3"] = res3

    # How far the rectangles fell between each pair, voted for by the runs. Each
    # set of runs votes for itself: the two plates find different runs, so a
    # travel voted for by one is not the travel the other should be judged by.
    travels = {}
    for label, source in (("alone", runs), ("three", runs3)):
        t = []
        for i in range(1, len(SLUGS)):
            best, n, still = vote_for_travel(source[SLUGS[i]], source[SLUGS[i - 1]])
            t.append(best)
            if label == "alone":
                print(f"{SLUGS[i - 1]} -> {SLUGS[i]}: the rectangles fell {best} px "
                      f"({n} of {len(source[SLUGS[i]])} runs agree); "
                      f"{still} runs did not move at all")
        travels[label] = t

    print()
    print(f"{'plate':22s} {'frame':6s} {'runs':>5s} {'fell':>6s} {'static':>7s} "
          f"{'unknown':>8s} {'kept':>6s}")
    verd, kept = {}, {}
    for label, source, key in (("one screenshot alone", runs, "alone"),
                               ("the three frames", runs3, "three")):
        t = travels[key]
        for i, s in enumerate(SLUGS):
            before = source[SLUGS[i - 1]] if i > 0 else []
            after = source[SLUGS[i + 1]] if i < len(SLUGS) - 1 else []
            v = verdicts(source[s], before, t[i - 1] if i > 0 else 0,
                         after, t[i] if i < len(SLUGS) - 1 else 0)
            if label == "the three frames":
                verd[s], kept[s] = v, v.count("fell")
            else:
                verd[s + "_alone"] = v
            print(f"{label:22s} {s:6s} {len(source[s]):5d} {v.count('fell'):6d} "
                  f"{v.count('static'):7d} {v.count('unknown'):8d} "
                  f"{v.count('fell'):6d}")
    speed = float(np.median(travels["alone"]))
    return dict(cal=cal, aligned=aligned, runs=runs, runs3=runs3, verd=verd,
                speed=speed, travels=travels, offsets=offsets, plate=plate,
                res=res_of, upper=u, white=w, d=d)


if __name__ == "__main__":
    main()
