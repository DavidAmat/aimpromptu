"""The two routes to the white key borders, and the score that decides.

Route A (section 6.2 of the plan): the white key borders derived from the black
keys. The family is chosen from the black keys alone — the ratio of the gap
between two groups to the gap inside a group is 2.0 on a drawn keyboard whose
black keys sit on the white key boundaries and about 1.5 on a real one — and
then each black key gives the border it stands on, offset by the family's
number for that key, in the local white key width. The two borders of an octave
with no black key over them, E|F and B|C, are the midpoints of the borders on
each side. Past the outermost black keys the borders continue at the local
width to the edge of the rectangle.

Route B (section 6.3): the thin dark lines between two white keys, read in the
front of the keys with the same three checks the truth uses, extended to the
top edge, and the borders a hand hides filled from the black key pattern — the
number of white keys between two kept borders is what the pattern says it is.

Neither route reads the truth.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np

from blackkeys import BLACK_NAMES, find_black_keys
from common import DATA, OUT, grey, load_rects, load_rgb, rectify, slugs
from lines import keyboard_bottom, read_lines
from truth import keep_lines

#: The family of a real piano, measured in Task 1.1.2 over 23 of the 24 pictures:
#: the median offset of each black key from the border it stands on, in local
#: white key widths, positive to the right.
REAL = {"C#": -0.095, "D#": 0.100, "F#": -0.131, "G#": 0.009, "A#": 0.137}
#: The family of a drawn keyboard whose black keys sit on the boundaries
#: (derulo). Every offset is zero.
BOUNDARY = {n: 0.0 for n in BLACK_NAMES}

#: Which white key border each black key stands on, counted from C|D = 0 inside
#: an octave of seven borders C|D, D|E, E|F, F|G, G|A, A|B, B|C.
BORDER_OF = {"C#": 0, "D#": 1, "F#": 3, "G#": 4, "A#": 5}


def family_of(keys) -> tuple[str, float]:
    """From the black keys alone: the ratio of the between-group gap to the
    inside-group gap. 2.0 is the boundary family, 1.5 the real one."""
    inside, between = [], []
    for a, b in zip(keys, keys[1:]):
        if b.index != a.index + 1:
            continue
        gap = b.centre - a.centre
        (between if a.position in (1, 4) else inside).append(gap)
    if not inside or not between:
        return "real", float("nan")
    ratio = float(np.median(between) / np.median(inside))
    return ("boundary" if ratio > 1.75 else "real"), ratio


def route_a(keys, width_px: int) -> tuple[list[float], str, float]:
    """The white key borders at the top edge, from the black keys."""
    family, ratio = family_of(keys)
    offsets = BOUNDARY if family == "boundary" else REAL
    # the local white key width at each black key: the octave period around it
    # over seven, from the same-name neighbours; the nearest measured value
    # where a key has none
    centres = {k.index: k.centre for k in keys}
    local: dict[int, float] = {}
    for k in keys:
        periods = []
        if k.index + 5 in centres:
            periods.append(centres[k.index + 5] - k.centre)
        if k.index - 5 in centres:
            periods.append(k.centre - centres[k.index - 5])
        if periods:
            local[k.index] = float(np.mean(periods)) / 7
    if not local:
        return [], family, ratio
    for k in keys:
        if k.index not in local:
            nearest = min(local, key=lambda i: abs(i - k.index))
            local[k.index] = local[nearest]
    # one border per black key, in octave slots; then the two borders without
    # a black key from their neighbours
    borders: dict[float, float] = {}  # slot number (float) -> u
    # slot numbering: black key k stands on border BORDER_OF[name] + 7 * octave,
    # where the octave is counted from the first C# (position 0) in the strip
    first = keys[0]
    # octave offset so that slots are consistent: position p at index i
    # -> octave = (i - i_of_first_C#) // 5 ... simpler: walk
    slot_of: dict[int, int] = {}
    # find the index of a key with position 0 (C#) to anchor octaves
    oct_base = None
    for k in keys:
        if k.position == 0:
            oct_base = k.index
            break
    if oct_base is None:
        oct_base = keys[0].index - keys[0].position
    for k in keys:
        octave = (k.index - oct_base) // 5 if k.index >= oct_base else -((oct_base - k.index + 4) // 5)
        # position within the octave must match: (k.index - oct_base) % 5 == k.position
        slot = BORDER_OF[BLACK_NAMES[k.position]] + 7 * octave
        slot_of[k.index] = slot
        borders[slot] = k.centre - offsets[BLACK_NAMES[k.position]] * local[k.index]
    # E|F (slot 2 mod 7) and B|C (slot 6 mod 7) from neighbours
    slots = sorted(borders)
    for s in list(slots):
        if s % 7 == 1 and s + 2 in borders:  # D|E and F|G -> E|F
            borders[s + 1] = (borders[s] + borders[s + 2]) / 2
        if s % 7 == 5 and s + 2 in borders:  # A|B and C|D (next octave) -> B|C
            borders[s + 1] = (borders[s] + borders[s + 2]) / 2
    # fill any slot still missing between the ends with the local width
    slots = sorted(borders)
    lo, hi = slots[0], slots[-1]
    for s in range(lo, hi + 1):
        if s in borders:
            continue
        below = max(t for t in borders if t < s)
        above = min(t for t in borders if t > s)
        borders[s] = borders[below] + (borders[above] - borders[below]) * (s - below) / (above - below)
    # extend to both edges at the local width of the nearest black key. A key
    # is kept while its midpoint is inside the rectangle — at least half of it
    # shows, so its lane still holds a whole rectangle — which is the rule the
    # seed of 04 used; the border past the edge is kept as the key's far side.
    w_lo = local[keys[0].index]
    w_hi = local[keys[-1].index]
    s = lo
    while borders[s] - w_lo / 2 >= 0:
        borders[s - 1] = borders[s] - w_lo
        s -= 1
    s = hi
    while borders[s] + w_hi / 2 <= width_px:
        borders[s + 1] = borders[s] + w_hi
        s += 1
    return sorted(borders.values()), family, ratio


def route_b(strip: np.ndarray, keys, depth: int, entry_like: dict) -> list[float]:
    """The white key borders from the thin dark lines, with the hidden ones filled
    from the black key pattern."""
    kept, _ = keep_lines(entry_like)  # route B never sees the eye's rejections
    us = sorted(l["u_top"] for l in kept)
    if len(us) < 2:
        return us
    # local width from the black keys, as route A
    borders_a, _, _ = route_a(keys, strip.shape[1])
    w_local = float(np.median(np.diff(borders_a))) if len(borders_a) > 2 else float(np.median(np.diff(us)))
    out = [us[0]]
    for a, b in zip(us, us[1:]):
        n = int(round((b - a) / w_local))
        for k in range(1, max(1, n)):
            out.append(a + (b - a) * k / n)
        out.append(b)
    # extend to the edges, keeping a key whose midpoint is inside the rectangle
    while out[0] - w_local / 2 >= 0:
        out.insert(0, out[0] - w_local)
    while out[-1] + w_local / 2 <= strip.shape[1]:
        out.append(out[-1] + w_local)
    return out


def score(borders: list[float], truth_us: list[float], whites: list[float]) -> tuple[float, float, int, int]:
    """Mean and worst absolute error in local white key widths, how many truth
    borders are off by more than the lane margin (0.25), and how many were scored."""
    if not borders or not truth_us:
        return float("nan"), float("nan"), 0, 0
    b = np.array(borders)
    errs = []
    for u, w in zip(truth_us, whites):
        errs.append(abs(b - u).min() / w)
    errs = np.array(errs)
    return float(errs.mean()), float(errs.max()), int((errs > 0.25).sum()), int(len(errs))


def main() -> None:
    truth = json.loads((DATA / "truth.json").read_text())
    draft = json.loads((DATA / "truth-draft.json").read_text())
    rects = load_rects()
    print("route A: from the black keys        route B: from the thin dark lines        (errors in local white key widths)")
    print("picture                  family ratio   n  A:mean  worst >0.25 | top: mean  worst | B:mean  worst >0.25 | top: mean  worst | A-B agree")
    totals = {"A": [], "B": [], "At": [], "Bt": [], "Abad": 0, "Bbad": 0, "n": 0, "nt": 0}
    results = {}
    for slug in slugs():
        g = rectify(grey(load_rgb(slug)), rects[slug])
        r = find_black_keys(g)
        t = truth[slug]
        truth_us = [b["u_top"] for b in t["borders"]]
        whites = [b["white"] for b in t["borders"]]
        w_med = float(np.median(whites)) if whites else 25.0
        a, family, ratio = route_a(r.keys, g.shape[1])
        b = route_b(g, r.keys, r.depth, draft[slug])
        am, aw, abad, n = score(a, truth_us, whites)
        bm, bw, bbad, _ = score(b, truth_us, whites)
        # the top edge reading is kept where the front truth has the same
        # border within a third of a key: both are truth, neither is a route,
        # and the glow line and a pressed key's highlight leave stray minima
        # at the top edge that nothing should be scored against
        top = [u for u in t["top_edge"] if truth_us and abs(np.array(truth_us) - u).min() < 0.34 * w_med]
        atm, atw, _, nt = score(a, top, [w_med] * len(top))
        btm, btw, _, _ = score(b, top, [w_med] * len(top))
        # agreement of the two routes: nearest border of B for each of A
        agree = float(np.mean([abs(np.array(b) - u).min() for u in a]) / w_med) if a and b else float("nan")
        print(f"{slug:24s} {family:8s} {ratio:4.2f} {n:3d}  {am:6.3f} {aw:6.3f} {abad:5d} |     {atm:6.3f} {atw:6.3f} | {bm:6.3f} {bw:6.3f} {bbad:5d} |     {btm:6.3f} {btw:6.3f} |  {agree:6.3f}")
        totals["A"].append(am); totals["B"].append(bm); totals["At"].append(atm); totals["Bt"].append(btm)
        totals["Abad"] += abad; totals["Bbad"] += bbad; totals["n"] += n; totals["nt"] += nt
        results[slug] = {"family": family, "ratio": ratio, "route_a": [round(x, 2) for x in a], "route_b": [round(x, 2) for x in b],
                         "black_keys": [{"name": BLACK_NAMES[k.position], "centre": round(k.centre, 2), "width": k.width, "seen": k.seen, "confirmed": k.confirmed} for k in r.keys],
                         "score": {"a": [am, aw, abad], "b": [bm, bw, bbad], "a_top": [atm, atw], "b_top": [btm, btw], "n": n, "n_top": nt}}
    print(f"\nTOTAL over {totals['n']} truth borders and {totals['nt']} top edge borders:")
    print(f"  route A  mean {np.nanmean(totals['A']):.3f}  over the margin {totals['Abad']}   top edge mean {np.nanmean(totals['At']):.3f}")
    print(f"  route B  mean {np.nanmean(totals['B']):.3f}  over the margin {totals['Bbad']}   top edge mean {np.nanmean(totals['Bt']):.3f}")
    (DATA / "routes.json").write_text(json.dumps(results, indent=1) + "\n")


if __name__ == "__main__":
    main()
