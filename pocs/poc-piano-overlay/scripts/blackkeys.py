"""The black keys, found inside the one rectangle, and the pattern read off them.

Section 6.1 of the plan. Works on the rectified strip: rows are v, columns u.

1. the black key band: the rows from the top edge down to where the black keys
   end, found from the share of dark pixels per row;
2. column darkness in that band, against the strip's own dark and light levels;
3. runs of dark columns are candidates, kept when their width is that of a black
   key and not that of a thin line or a hand;
4. the gaps between consecutive candidates are aligned against the repeating
   pattern of five black keys per octave by dynamic programming: a candidate is
   at one of five positions (C#, D#, F#, G#, A#), a gap may skip keys a hand
   hides, and a candidate may be thrown out as not a key. The alignment with the
   lowest cost wins, and the margin over the best alignment that starts on a
   different pitch class is the confidence;
5. a smooth position function — a quadratic in the black key index — is fitted
   over the aligned candidates; every key the pattern needs inside the strip and
   not seen is placed from it and flagged extrapolated, then checked back
   against the pixels and flagged confirmed when the strip is dark there.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from common import runs

#: Semitone slot of each black key of an octave, in pattern order C#, D#, F#, G#, A#.
BLACK_SLOTS = [1, 3, 6, 8, 10]
BLACK_NAMES = ["C#", "D#", "F#", "G#", "A#"]
PATTERN_PITCH_CLASS = [1, 3, 6, 8, 10]


@dataclass
class Candidate:
    u0: int
    u1: int  # exclusive

    @property
    def centre(self) -> float:
        return (self.u0 + self.u1 - 1) / 2

    @property
    def width(self) -> int:
        return self.u1 - self.u0


@dataclass
class BlackKey:
    index: int  # 0 = the leftmost key the strip holds
    position: int  # 0..4 in the pattern
    centre: float
    width: float
    seen: bool
    confirmed: bool = False
    candidate: Candidate | None = None

    @property
    def pitch_class(self) -> int:
        return PATTERN_PITCH_CLASS[self.position]


@dataclass
class BlackKeyResult:
    depth: int
    dark_level: float
    light_level: float
    threshold: float
    candidates: list[Candidate]
    keys: list[BlackKey]
    cost: float
    runner_up: float
    #: 0..1 share of the pattern's cost margin — how sure the pitch class is.
    confidence: float
    semitone_px: float
    thrown_out: list[Candidate] = field(default_factory=list)


# ---------------------------------------------------------------- band ----


def otsu(values: np.ndarray) -> float:
    """The threshold that best splits a two-mode histogram."""
    hist, edges = np.histogram(values, bins=64, range=(0, 255))
    centres = (edges[:-1] + edges[1:]) / 2
    total = hist.sum()
    best, best_t = -1.0, 128.0
    w0 = 0.0
    sum0 = 0.0
    sum_all = float((hist * centres).sum())
    for i in range(64):
        w0 += hist[i]
        if w0 == 0 or w0 == total:
            continue
        sum0 += hist[i] * centres[i]
        m0 = sum0 / w0
        m1 = (sum_all - sum0) / (total - w0)
        between = w0 * (total - w0) * (m0 - m1) ** 2
        if between > best:
            best, best_t = between, float(edges[i + 1])
    return best_t


def black_band(strip: np.ndarray) -> tuple[int, float, float, float]:
    """How deep the black keys go, and the dark and light levels of the strip.

    The threshold is Otsu's over the top rows, where black keys and the tops of
    white keys sit side by side and make two clear modes. The depth is read down
    the black key columns themselves: the columns that are dark in the top rows
    are averaged into one vertical profile, which is flat and dark down the key
    and rises where the key ends and the front of the white key below it begins
    — whatever grey that front is. The depth is the first row where the profile
    has risen halfway from its dark level to its level below the keys.
    """
    h = strip.shape[0]
    top = strip[3 : min(40, h)]
    threshold = otsu(top.ravel())
    dark = float(np.percentile(top, 8))
    light = float(np.percentile(top, 92))
    # columns dark in most of the top rows are black key columns
    head = strip[3 : min(20, h)] < threshold
    black_cols = head.mean(axis=0) >= 0.8
    if black_cols.sum() < 10:
        return h, dark, light, threshold
    profile = np.median(strip[:, black_cols], axis=1)
    dark_level = float(np.median(profile[3:12]))
    below = float(np.percentile(profile[12:], 90))
    half = dark_level + 0.5 * (below - dark_level)
    depth = h
    for y in range(8, h):
        if profile[y] > half:
            depth = y
            break
    return depth, dark, light, threshold


def candidates(strip: np.ndarray, depth: int, threshold: float) -> tuple[list[Candidate], float, np.ndarray]:
    """Runs of dark columns in the band, kept when they are as wide as a black key.

    The score of a column is the share of the band's rows that are dark in it.
    Rows near the top edge and near the bottom of the black keys are left out:
    the top rows may hold the glow line of the roll and the bottom rows the
    rounded end of the key.
    """
    y0, y1 = 3, max(6, depth - 4)
    score = (strip[y0:y1] < threshold).mean(axis=0)
    found = [Candidate(a, b) for a, b in runs(score >= 0.6)]
    if not found:
        return [], 0.0, score
    widths = np.array([c.width for c in found])
    # The black key width is the median of the widths that are not lines: a
    # thin dark line between two white keys is one to three px wide.
    plausible = widths[widths >= 4]
    width = float(np.median(plausible)) if len(plausible) else float(np.median(widths))
    kept = [c for c in found if 0.5 * width <= c.width <= 1.6 * width]
    return kept, width, score


# ------------------------------------------------------------ alignment ----


def _slot_distance(p0: int, p1: int, octaves: int) -> int:
    """Semitones from black key at pattern position p0 to p1, `octaves` later."""
    return BLACK_SLOTS[p1] + 12 * octaves - BLACK_SLOTS[p0]


def align(cands: list[Candidate], spacing: tuple[float, float], forced: tuple[int, int] | None = None,
          max_skip: int = 12, lookback: int = 8):
    """Assign every candidate a pattern position, or throw it out.

    Dynamic programming over the candidates in order. State: the last kept
    candidate and its pattern position. A transition from (i, p) to (j, q) throws
    out the candidates between i and j (each costs `drop`), walks the pattern
    from p to q over `m` black keys (each hidden one costs `hide`), and pays the
    relative error between the measured gap and the gap the pattern predicts.
    Only the last `lookback` candidates are considered as the predecessor,
    because throwing out more than that is never the best alignment.

    `forced` = (i0, p0) pins candidate i0 to position p0 and keeps it, which is
    how the runner up — a different keyboard, not a relabelling — is scored.
    """
    n = len(cands)
    drop, hide, error_weight = 1.5, 0.6, 12.0
    INF = float("inf")
    cost = np.full((n, 5), INF)
    back: dict[tuple[int, int], tuple[int, int, int] | None] = {}
    centres = [c.centre for c in cands]
    for i in range(n):
        for p in range(5):
            if forced is not None and i > forced[0]:
                break
            if forced is not None and i == forced[0] and p != forced[1]:
                continue
            cost[i, p] = drop * i
            back[(i, p)] = None
    # The expected gap for m steps from position p: the pattern in the two gaps
    # the picture itself shows, S inside a group (C#–D#, F#–G#, G#–A#) and L
    # between two groups (D#–F#, A#–C#). No family is assumed: a drawn keyboard
    # has L = 2S and a real one L = 1.5S, and both align the same way.
    small, large = spacing
    step = {0: small, 1: large, 2: small, 3: small, 4: large}  # gap after position p
    expected = {}
    for p in range(5):
        for m in range(1, max_skip + 2):
            total, pos = 0.0, p
            for _ in range(m):
                total += step[pos]
                pos = (pos + 1) % 5
            expected[(p, m)] = total
    for j in range(n):
        for i in range(max(0, j - lookback), j):
            if forced is not None and i < forced[0] < j:
                continue  # would throw the forced candidate out
            gap = centres[j] - centres[i]
            for p in range(5):
                if cost[i, p] == INF:
                    continue
                for m in range(1, max_skip + 2):
                    exp = expected[(p, m)]
                    err = abs(gap - exp) / exp
                    if err > 0.30:
                        if gap < exp:
                            break
                        continue
                    q = (p + m) % 5
                    if forced is not None and j == forced[0] and q != forced[1]:
                        continue
                    c = cost[i, p] + drop * (j - i - 1) + hide * (m - 1) + error_weight * err
                    if c < cost[j, q]:
                        cost[j, q] = c
                        back[(j, q)] = (i, p, m)
    best = None
    for i in range(n):
        if forced is not None and i < forced[0]:
            continue
        for p in range(5):
            if cost[i, p] == INF:
                continue
            c = cost[i, p] + drop * (n - 1 - i)
            if best is None or c < best[0]:
                best = (c, i, p)
    if best is None:
        return INF, [], cost
    # The chain, first candidate first. Each entry carries the number of black
    # keys walked *into* it from the entry before, and the first carries 0.
    chain: list[tuple[int, int, int]] = []
    i, p = best[1], best[2]
    while True:
        prev = back.get((i, p))
        chain.append((i, p, prev[2] if prev is not None else 0))
        if prev is None:
            break
        i, p = prev[0], prev[1]
    chain.reverse()
    return best[0], chain, cost


def find_black_keys(strip: np.ndarray) -> BlackKeyResult:
    depth, dark, light, threshold = black_band(strip)
    cands, width, score = candidates(strip, depth, threshold)
    if len(cands) < 4:
        return BlackKeyResult(depth, dark, light, threshold, cands, [], float("inf"), float("inf"), 0.0, 0.0)

    # The semitone in px: the smallest common gap between candidates is two
    # semitones (C# to D#, F# to G#, G# to A#). The 30th percentile of the gaps
    # is inside that cluster on any strip that shows more than one group.
    gaps = np.diff([c.centre for c in cands])
    small = float(np.percentile(gaps, 30))
    between = gaps[(gaps >= 1.3 * small) & (gaps <= 2.6 * small)]
    large = float(np.median(between)) if len(between) >= 2 else 1.75 * small
    semitone_px = small / 2.0
    spacing = (small, large)

    total, chain, cost = align(cands, spacing)

    # The runner up: the best alignment whose leftmost kept candidate sits on a
    # different pitch class than the winner's — i.e. a different keyboard, not
    # the same keyboard relabelled.
    first_i, first_p, _ = chain[0]
    kept_index = {i for i, _, _ in chain}
    runner = float("inf")
    for p in range(5):
        if p == first_p:
            continue
        other, _, _ = align(cands, spacing, forced=(first_i, p))
        runner = min(runner, other)

    # absolute black key index from the chain
    keys: list[BlackKey] = []
    index = 0
    for n_, (i, p, steps) in enumerate(chain):
        if n_ > 0:
            index += steps
        keys.append(BlackKey(index=index, position=p, centre=cands[i].centre, width=cands[i].width, seen=True, confirmed=True, candidate=cands[i]))
    thrown = [c for k, c in enumerate(cands) if k not in kept_index]

    # smooth position function: quadratic in the index over the seen keys' slots.
    # Fit centre against the semitone coordinate of the key, which handles the
    # uneven spacing of the pattern; the quadratic absorbs the perspective.
    step = {0: small, 1: large, 2: small, 3: small, 4: large}
    first_index, first_p = keys[0].index, keys[0].position
    last_index = keys[-1].index

    def position_of(i: int) -> int:
        return (first_p + (i - first_index)) % 5

    def coordinate(i: int) -> float:
        """The model coordinate of key index i: the pattern's own gaps, walked
        from the first seen key, in px of the two measured gaps. Fitting the
        centres against it leaves only the perspective for the quadratic."""
        s, p = 0.0, first_p
        if i >= first_index:
            for _ in range(i - first_index):
                s += step[p]
                p = (p + 1) % 5
        else:
            for _ in range(first_index - i):
                p = (p - 1) % 5
                s -= step[p]
        return s

    semitone_at = coordinate
    xs = np.array([coordinate(k.index) for k in keys])
    ys = np.array([k.centre for k in keys])
    deg = 2 if len(keys) >= 6 else 1
    f = np.poly1d(np.polyfit(xs, ys, deg))
    seen_by_index = {k.index: k for k in keys}

    all_keys: list[BlackKey] = []
    # extend to both ends of the strip while the predicted key still fits inside
    # it and the function still walks the right way — a quadratic can turn round,
    # and past that point it says nothing. At most 40 keys each side.
    y0, y1 = 3, max(6, depth - 4)

    def dark_at(c: float) -> float:
        a, b = int(round(c - width * 0.3)), int(round(c + width * 0.3)) + 1
        a, b = max(0, a), min(strip.shape[1], b)
        return float((strip[y0:y1, a:b] < threshold).mean()) if b > a else 0.0

    # Inside the seen span every key the pattern needs is placed. Past the ends
    # the keyboard may stop anywhere, so the walk goes on only while the pixels
    # confirm a key there; the first unconfirmed key ends the keyboard. This
    # loses a key a hand hides at the very end, and that is named in the report.
    i = first_index
    prev = float(f(semitone_at(i)))
    for _ in range(40):
        c = float(f(semitone_at(i - 1)))
        if c - width / 2 < 0 or c >= prev or dark_at(c) < 0.6:
            break
        i -= 1
        prev = c
    lo = i
    i = last_index
    prev = float(f(semitone_at(i)))
    for _ in range(40):
        c = float(f(semitone_at(i + 1)))
        if c + width / 2 > strip.shape[1] or c <= prev or dark_at(c) < 0.6:
            break
        i += 1
        prev = c
    hi = i
    for i in range(lo, hi + 1):
        if i in seen_by_index:
            all_keys.append(seen_by_index[i])
            continue
        c = float(f(semitone_at(i)))
        all_keys.append(BlackKey(index=i, position=position_of(i), centre=c, width=width, seen=False, confirmed=dark_at(c) >= 0.6))
    # renumber from 0
    all_keys.sort(key=lambda k: k.index)
    offset = all_keys[0].index
    for k in all_keys:
        k.index -= offset

    margin = (runner - total) / max(total, 1e-6) if np.isfinite(runner) else 1.0
    confidence = float(min(1.0, max(0.0, margin)))
    return BlackKeyResult(depth, dark, light, threshold, cands, all_keys, total, runner, confidence, semitone_px, thrown)
