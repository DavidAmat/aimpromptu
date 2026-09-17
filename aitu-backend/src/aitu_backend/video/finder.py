"""One picture and one rectangle in, the piano overlay out (V-37, V-41).

The user drags one rectangle over the piano area and everything inside it is
found. This is the port of `poc-piano-overlay/scripts/blackkeys.py` and the
route A half of `routes.py`; every threshold below carries the measurement Phase
1 of implementation 05 made for it, in
`context/implementations/05-piano-overlay-from-black-keys/05-phase-1-implementation.md`
and `poc-piano-overlay/RESULTS.md`. A rule with no measurement beside it does
not ship (V-20).

The order of the steps:

1. rectify: the picture inside the rectangle, rotated straight, so rows are
   ``v`` down the keys and columns are ``u`` along the top edge;
2. the black key band: Otsu's threshold over the top rows, and the depth read
   down the black key columns themselves;
3. candidates: runs of dark columns as wide as a black key;
4. the alignment: a dynamic programme that gives every candidate a position in
   the pattern of five black keys per octave, or throws it out, using the two
   gaps the picture itself shows and no family;
5. the position function: a quadratic in the pattern's own coordinate, fitted
   over the seen keys; every key the pattern needs and the picture did not show
   is placed from it, flagged extrapolated, and checked back against the pixels;
6. route A: the family from the gap ratio, then one white key border per black
   key, the two borders with no black key over them from their neighbours, and
   the ends at the local width while a key's midpoint is inside the rectangle.

It does not know whether the picture is a screenshot or a sampled frame, and it
does not read or write any file — the same shape ``detect()`` has, for the same
reason.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from aitu_backend.schemas.video import (
    WHITE_PITCH_CLASSES,
    BlackBorder,
    Calibration,
    Found,
    PianoRect,
)
from aitu_backend.video import geometry

#: Pattern order of the five black keys of an octave, and their names.
BLACK_NAMES = ["C#", "D#", "F#", "G#", "A#"]
BLACK_PITCH_CLASS = [1, 3, 6, 8, 10]
#: Which white key border each black key stands on, counted from C|D = 0 inside
#: an octave of seven borders C|D, D|E, E|F, F|G, G|A, A|B, B|C.
BORDER_OF = [0, 1, 3, 4, 5]
#: The gap after each pattern position is inside a group (S) or between two
#: groups (L): C#→D# S, D#→F# L, F#→G# S, G#→A# S, A#→C# L.
GAP_AFTER = ["S", "L", "S", "S", "L"]


class NoKeyboard(ValueError):
    """The rectangle holds nothing the finder can read as a keyboard."""


@dataclass(frozen=True)
class FinderSettings:
    """The named thresholds, with the measurement behind each (Phase 1 of 05)."""

    #: Rows under the top edge the Otsu threshold is taken over: black keys and
    #: the tops of white keys make two clear modes there.
    level_rows: int = 40
    #: Rows under the top edge whose dark columns are the black key columns the
    #: depth is read down.
    head_rows: int = 20
    #: Share of the head rows a column must be dark in to be a black key column.
    head_share: float = 0.8
    #: Share of the band's rows a column must be dark in to be a candidate.
    column_share: float = 0.6
    #: A candidate is kept when its width is inside this range of the median
    #: candidate width: a thin line is 1 to 3 px, a hand is wider than a key.
    width_low: float = 0.5
    width_high: float = 1.6
    #: The cost of throwing a candidate out, of walking past a hidden key, and
    #: the weight on the relative error between a gap and the pattern's gap.
    drop_cost: float = 1.5
    hide_cost: float = 0.6
    error_weight: float = 12.0
    #: A gap more than this far from the pattern's is not a transition at all.
    max_gap_error: float = 0.30
    #: How many earlier candidates are considered as the predecessor.
    lookback: int = 8
    #: How many hidden keys one transition may walk past: both hands together.
    max_skip: int = 12
    #: Share of dark pixels in the middle of an extrapolated key for the pixels
    #: to confirm it.
    confirm_share: float = 0.6
    #: The gap ratio between and inside groups that separates the two families:
    #: 1.98 on the drawn keyboard with black keys on the boundaries, 1.49 to
    #: 1.56 on the 23 real pianos (V-40).
    boundary_ratio: float = 1.75
    #: The real piano family, measured over 23 of 24 pictures (V-40): the offset
    #: of each black key from the border it stands on, in local white key widths.
    real_offsets: tuple[float, ...] = (-0.095, 0.100, -0.131, 0.009, 0.137)
    #: Fewer candidates than this is no keyboard.
    min_candidates: int = 4


DEFAULTS = FinderSettings()


# -------------------------------------------------------------- rectify ----


def rectify(image: np.ndarray, rect: PianoRect) -> np.ndarray:
    """The grey picture inside the rectangle, rotated straight: rows v, columns u.

    Sampled with bilinear interpolation at one sample per pixel of the top edge,
    so a length in u is a length in picture pixels along that edge.
    """
    grey = image.mean(axis=2) if image.ndim == 3 else image
    w, h = max(1, int(round(rect.width))), max(1, int(round(rect.height)))
    a = math.radians(rect.angle)
    u = np.arange(w)[None, :]
    v = np.arange(h)[:, None]
    xs = rect.x + u * math.cos(a) - v * math.sin(a)
    ys = rect.y + u * math.sin(a) + v * math.cos(a)
    return np.asarray(
        ndimage.map_coordinates(grey, [ys, xs], order=1, mode="nearest"), dtype=np.float32
    )


# ---------------------------------------------------------- the band -------


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


def black_band(strip: np.ndarray, settings: FinderSettings) -> tuple[int, float, float]:
    """How deep the black keys go, the threshold that separates dark from light,
    and the dark level of the black keys themselves.

    The depth is read down the black key columns themselves: the columns that
    are dark in the top rows are averaged into one vertical profile, flat and
    dark down the key and rising where the front of the white key below it
    begins — whatever grey that front is. A row share failed on 15 of 24
    pictures because the glow at the top edge made the grey front count as dark.
    """
    h = strip.shape[0]
    top = strip[3 : min(settings.level_rows, h)]
    if top.size == 0:
        raise NoKeyboard("the rectangle is too short to hold a keyboard")
    threshold = otsu(top.ravel())
    head = strip[3 : min(settings.head_rows, h)] < threshold
    dark_cols = head.mean(axis=0) >= settings.head_share
    # The black key columns are the runs of dark columns as wide as a black key.
    # A dark canvas past the end of the keyboard, or a hand, is dark too, but
    # not fourteen pixels wide.
    runs = _runs(dark_cols)
    widths = np.array([b - a for a, b in runs if b - a >= 4])
    if len(widths) < 4:
        raise NoKeyboard("no dark, tall columns under the top edge: no black keys")
    key_width = float(np.median(widths))
    black_cols = np.zeros(strip.shape[1], dtype=bool)
    for a, b in runs:
        if settings.width_low * key_width <= b - a <= settings.width_high * key_width:
            black_cols[a:b] = True
    if black_cols.sum() < 10:
        raise NoKeyboard("no dark, tall columns under the top edge: no black keys")
    profile = np.median(strip[:, black_cols], axis=1)
    dark_level = float(np.median(profile[3:12]))
    below = float(np.percentile(profile[12:], 90)) if h > 12 else dark_level
    half = dark_level + 0.5 * (below - dark_level)
    depth = h
    for y in range(8, h):
        if profile[y] > half:
            depth = y
            break
    return depth, threshold, dark_level


def _runs(flags: np.ndarray) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    start: int | None = None
    for i, value in enumerate(flags):
        if value and start is None:
            start = i
        elif not value and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(flags)))
    return out


def candidates(
    strip: np.ndarray, depth: int, threshold: float, settings: FinderSettings
) -> tuple[list[tuple[int, int]], float]:
    """Runs of dark columns in the band that are as wide as a black key."""
    y0, y1 = 3, max(6, depth - 4)
    score = (strip[y0:y1] < threshold).mean(axis=0)
    found = _runs(score >= settings.column_share)
    if not found:
        return [], 0.0
    widths = np.array([b - a for a, b in found])
    plausible = widths[widths >= 4]
    width = float(np.median(plausible)) if len(plausible) else float(np.median(widths))
    kept = [
        (a, b)
        for a, b in found
        if settings.width_low * width <= b - a <= settings.width_high * width
    ]
    return kept, width


# ---------------------------------------------------------- alignment ------


def _expected(spacing: tuple[float, float], max_skip: int) -> dict[tuple[int, int], float]:
    small, large = spacing
    step = {p: (small if GAP_AFTER[p] == "S" else large) for p in range(5)}
    out: dict[tuple[int, int], float] = {}
    for p in range(5):
        for m in range(1, max_skip + 2):
            total, pos = 0.0, p
            for _ in range(m):
                total += step[pos]
                pos = (pos + 1) % 5
            out[(p, m)] = total
    return out


def align(
    centres: list[float],
    spacing: tuple[float, float],
    settings: FinderSettings,
    forced: tuple[int, int] | None = None,
) -> tuple[float, list[tuple[int, int, int]]]:
    """Give every candidate a pattern position, or throw it out.

    Dynamic programming over the candidates in order. State: the last kept
    candidate and its pattern position. A transition throws out the candidates
    between (each ``drop_cost``), walks the pattern over ``m`` keys (each hidden
    one ``hide_cost``), and pays ``error_weight`` times the relative error
    between the measured gap and the gap the pattern predicts from the two gaps
    the picture shows. ``forced`` pins one candidate to one position, which is
    how the runner up — a different keyboard, not a relabelling — is scored.

    Returns the cost and the chain: (candidate, position, keys walked into it).
    """
    n = len(centres)
    INF = float("inf")
    cost = np.full((n, 5), INF)
    back: dict[tuple[int, int], tuple[int, int, int] | None] = {}
    for i in range(n):
        for p in range(5):
            if forced is not None and i > forced[0]:
                break
            if forced is not None and i == forced[0] and p != forced[1]:
                continue
            cost[i, p] = settings.drop_cost * i
            back[(i, p)] = None
    expected = _expected(spacing, settings.max_skip)
    for j in range(n):
        for i in range(max(0, j - settings.lookback), j):
            if forced is not None and i < forced[0] < j:
                continue
            gap = centres[j] - centres[i]
            for p in range(5):
                if cost[i, p] == INF:
                    continue
                for m in range(1, settings.max_skip + 2):
                    exp = expected[(p, m)]
                    err = abs(gap - exp) / exp
                    if err > settings.max_gap_error:
                        if gap < exp:
                            break
                        continue
                    q = (p + m) % 5
                    if forced is not None and j == forced[0] and q != forced[1]:
                        continue
                    c = (
                        cost[i, p]
                        + settings.drop_cost * (j - i - 1)
                        + settings.hide_cost * (m - 1)
                        + settings.error_weight * err
                    )
                    if c < cost[j, q]:
                        cost[j, q] = c
                        back[(j, q)] = (i, p, m)
    best: tuple[float, int, int] | None = None
    for i in range(n):
        if forced is not None and i < forced[0]:
            continue
        for p in range(5):
            if cost[i, p] == INF:
                continue
            c = cost[i, p] + settings.drop_cost * (n - 1 - i)
            if best is None or c < best[0]:
                best = (c, i, p)
    if best is None:
        return INF, []
    chain: list[tuple[int, int, int]] = []
    i, p = best[1], best[2]
    while True:
        prev = back.get((i, p))
        chain.append((i, p, prev[2] if prev is not None else 0))
        if prev is None:
            break
        i, p = prev[0], prev[1]
    chain.reverse()
    return best[0], chain


# ------------------------------------------------------- the black keys ----


@dataclass
class BlackKey:
    index: int
    position: int
    centre: float
    width: float
    seen: bool
    confirmed: bool


@dataclass
class BlackKeys:
    depth: int
    keys: list[BlackKey]
    confidence: float
    spacing: tuple[float, float]
    thrown_out: int = 0
    cost: float = 0.0
    runner_up: float = 0.0
    extra: dict = field(default_factory=dict)


def find_black_keys(strip: np.ndarray, settings: FinderSettings = DEFAULTS) -> BlackKeys:
    depth, threshold, dark_level = black_band(strip, settings)
    cands, width = candidates(strip, depth, threshold, settings)
    if len(cands) < settings.min_candidates:
        raise NoKeyboard(f"only {len(cands)} black key candidates inside the rectangle")
    centres = [(a + b - 1) / 2 for a, b in cands]
    widths = [b - a for a, b in cands]

    gaps = np.diff(centres)
    small = float(np.percentile(gaps, 30))
    between = gaps[(gaps >= 1.3 * small) & (gaps <= 2.6 * small)]
    large = float(np.median(between)) if len(between) >= 2 else 1.75 * small
    spacing = (small, large)

    total, chain = align(centres, spacing, settings)
    if not chain:
        raise NoKeyboard("the black key candidates do not align to the pattern of twos and threes")
    first_i, first_p, _ = chain[0]
    runner = float("inf")
    for p in range(5):
        if p == first_p:
            continue
        other, _ = align(centres, spacing, settings, forced=(first_i, p))
        runner = min(runner, other)

    keys: list[BlackKey] = []
    index = 0
    for n_, (i, p, steps) in enumerate(chain):
        if n_ > 0:
            index += steps
        keys.append(
            BlackKey(
                index=index,
                position=p,
                centre=centres[i],
                width=float(widths[i]),
                seen=True,
                confirmed=True,
            )
        )
    thrown = len(cands) - len(chain)

    step = {p: (small if GAP_AFTER[p] == "S" else large) for p in range(5)}
    first_index = keys[0].index
    last_index = keys[-1].index

    def position_of(i: int) -> int:
        return (first_p + (i - first_index)) % 5

    def coordinate(i: int) -> float:
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

    xs = np.array([coordinate(k.index) for k in keys])
    ys = np.array([k.centre for k in keys])
    deg = 2 if len(keys) >= 6 else 1
    f = np.poly1d(np.polyfit(xs, ys, deg))
    seen_by_index = {k.index: k for k in keys}
    y0, y1 = 3, max(6, depth - 4)

    def dark_at(c: float) -> float:
        a, b = int(round(c - width * 0.3)), int(round(c + width * 0.3)) + 1
        a, b = max(0, a), min(strip.shape[1], b)
        return float((strip[y0:y1, a:b] < threshold).mean()) if b > a else 0.0

    def gap(a: float, b: float) -> np.ndarray:
        # the columns between two black keys, less two on each side: the keys'
        # shadowed edges, and the couple of pixels the position function can be
        # off by at the far end of a keyboard
        lo_, hi_ = int(round(min(a, b) + width / 2 + 3)), int(round(max(a, b) - width / 2 - 2))
        lo_, hi_ = max(0, lo_), min(strip.shape[1], hi_)
        return strip[y0:y1, lo_:hi_] if hi_ > lo_ else np.zeros((0, 0))

    def bar_from(region: np.ndarray) -> float:
        # The bar a gap has to clear to be the top of a white key: a fifth of
        # the way from the black keys' own dark level up to the white key top of
        # the gap last accepted. Local and moving on purpose: a white key in
        # shadow at the end of a photographed keyboard is far darker than the
        # ones under the glow, and a picture-wide threshold cut three of the 24
        # keyboards short.
        ref = float(np.median(region)) if region.size else threshold
        return dark_level + 0.2 * (max(ref, dark_level + 1.0) - dark_level)

    def light_cols(region: np.ndarray, bar: float) -> bool:
        # Column by column: the median of each column down the band, then the
        # 40th percentile over the columns. Half a gap of canvas and half of
        # white key fails it; the thin line between two white keys and the
        # shadowed edges of the two black keys — up to a third of a gap between
        # two groups — pass it, which a percentile over pixels did not.
        if region.ndim < 2 or region.shape[1] == 0:
            return False
        columns = np.median(region, axis=0)
        return float(np.percentile(columns, 40)) > bar

    def light_between(a: float, b: float, bar: float) -> bool:
        return light_cols(gap(a, b), bar)

    def far_side_ok(c: float, bar: float, left: bool) -> bool:
        # A black key has a white key on both sides, so the far side has to be
        # light too: a dark canvas beside the last white key of a drawn keyboard
        # looks like a black key from the near side alone. The far side read is
        # the top of the white key right beside the key — the columns up to
        # where the nearest possible black key would start, a short gap away —
        # so neither the next black key nor the end of the keyboard beyond that
        # white key enters into it. Fewer than three columns is a keyboard cut
        # by the picture's edge, and is accepted.
        # eight columns, seven px clear of the key's predicted edge: the
        # prediction at the far end of a keyboard is up to five px off, and a
        # window that touched the key's own shadow read it as canvas
        if left:
            lo_, hi_ = int(round(c - width / 2 - 15)), int(round(c - width / 2 - 7))
        else:
            lo_, hi_ = int(round(c + width / 2 + 7)), int(round(c + width / 2 + 15))
        lo_, hi_ = max(0, lo_), min(strip.shape[1], hi_)
        if hi_ - lo_ < 3:
            return True
        return light_cols(strip[y0:y1, lo_:hi_], bar)

    bar_left = bar_from(gap(keys[0].centre, keys[1].centre)) if len(keys) > 1 else threshold
    bar_right = bar_from(gap(keys[-2].centre, keys[-1].centre)) if len(keys) > 1 else threshold

    # Past the ends the walk goes on only while the pixels confirm a key — dark
    # where the key is, light between it and its neighbour — and the first key
    # the pixels do not confirm ends the keyboard. Inside the seen span every
    # key the pattern needs is placed.
    # The runs of dark columns across the band, for snapping: the position
    # function is a couple of pixels off at the far end of a keyboard, which is
    # where the end walk reads, so a predicted key is moved onto the centre of
    # the dark run nearest its prediction when there is one of a key's width
    # within half a key. A key that is not there stays where it was predicted,
    # and is refused there.
    column_dark = (strip[y0:y1] < threshold).mean(axis=0)
    dark_runs = [
        ((a + b - 1) / 2, b - a)
        for a, b in _runs(column_dark >= settings.column_share)
        if settings.width_low * width <= b - a <= settings.width_high * width
    ]

    def snap(c: float) -> float:
        near = [centre for centre, _w in dark_runs if abs(centre - c) <= width / 2]
        if not near:
            return c
        return min(near, key=lambda centre: abs(centre - c))

    walk: list[tuple[str, float, float, float, float, bool]] = []  # what each end step saw
    i = first_index
    prev = float(f(coordinate(i)))
    for _ in range(40):
        c = snap(float(f(coordinate(i - 1))))
        if c - width / 2 < 0 or c >= prev:
            break
        region = gap(c, prev)
        p30 = float(np.percentile(np.median(region, axis=0), 40)) if region.size else -1.0
        # a black key has a white key on both sides: the far side has to be
        # light too, unless the strip ends there — a dark canvas beside the
        # last white key looks like a black key from the near side alone
        far_ok = far_side_ok(c, bar_left, left=True)
        ok = dark_at(c) >= settings.confirm_share and light_between(c, prev, bar_left) and far_ok
        walk.append(("left", c, dark_at(c), p30, bar_left, ok))
        if not ok:
            break
        bar_left = bar_from(region)
        i -= 1
        prev = c
    lo = i
    i = last_index
    prev = float(f(coordinate(i)))
    for _ in range(40):
        c = snap(float(f(coordinate(i + 1))))
        if c + width / 2 > strip.shape[1] or c <= prev:
            break
        region = gap(prev, c)
        p30 = float(np.percentile(np.median(region, axis=0), 40)) if region.size else -1.0
        far_ok = far_side_ok(c, bar_right, left=False)
        ok = dark_at(c) >= settings.confirm_share and light_between(prev, c, bar_right) and far_ok
        walk.append(("right", c, dark_at(c), p30, bar_right, ok))
        if not ok:
            break
        bar_right = bar_from(region)
        i += 1
        prev = c
    hi = i

    snapped = {}
    for side, c, _d, _p, _b, ok in walk:
        if ok:
            snapped[round(c, 3)] = c
    all_keys: list[BlackKey] = []
    for i in range(lo, hi + 1):
        if i in seen_by_index:
            all_keys.append(seen_by_index[i])
            continue
        c = float(f(coordinate(i)))
        if i < first_index or i > last_index:
            c = snap(c)
        all_keys.append(
            BlackKey(
                index=i,
                position=position_of(i),
                centre=c,
                width=width,
                seen=False,
                confirmed=dark_at(c) >= settings.confirm_share,
            )
        )
    all_keys.sort(key=lambda k: k.index)
    offset = all_keys[0].index
    for k in all_keys:
        k.index -= offset

    margin = (runner - total) / max(total, 1e-6) if math.isfinite(runner) else 1.0
    confidence = float(min(1.0, max(0.0, margin)))
    return BlackKeys(
        depth=depth,
        keys=all_keys,
        confidence=confidence,
        spacing=spacing,
        thrown_out=thrown,
        cost=total,
        runner_up=runner,
        extra={"bar_left": bar_left, "bar_right": bar_right, "threshold": threshold, "walk": walk},
    )


# --------------------------------------------------------------- route A ---


def family_of(keys: list[BlackKey], settings: FinderSettings) -> tuple[str, float]:
    """From the black keys alone: the gap between groups over the gap inside one."""
    inside: list[float] = []
    between: list[float] = []
    for a, b in zip(keys, keys[1:]):
        if b.index != a.index + 1:
            continue
        (between if GAP_AFTER[a.position] == "L" else inside).append(b.centre - a.centre)
    if not inside or not between:
        return "real", float("nan")
    ratio = float(np.median(between) / np.median(inside))
    return ("boundary" if ratio > settings.boundary_ratio else "real"), ratio


def white_borders_from(
    keys: list[BlackKey],
    width_px: int,
    settings: FinderSettings,
    is_white_key=None,
) -> tuple[dict[int, float], dict[int, int], str, float]:
    """Route A: the white key borders by slot, from the black keys.

    Also answers the slot each black key stands on, by its index, so the caller
    can say which white keys it sits between."""
    family, ratio = family_of(keys, settings)
    offsets = (0.0,) * 5 if family == "boundary" else settings.real_offsets
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
        raise NoKeyboard("fewer than one octave of black keys: no white key width to measure")
    for k in keys:
        if k.index not in local:
            nearest = min(local, key=lambda i: abs(i - k.index))
            local[k.index] = local[nearest]

    oct_base = next((k.index for k in keys if k.position == 0), keys[0].index - keys[0].position)
    borders: dict[int, float] = {}
    slot_of: dict[int, int] = {}
    for k in keys:
        octave = (
            (k.index - oct_base) // 5 if k.index >= oct_base else -((oct_base - k.index + 4) // 5)
        )
        slot = BORDER_OF[k.position] + 7 * octave
        slot_of[k.index] = slot
        borders[slot] = k.centre - offsets[k.position] * local[k.index]
    for s in sorted(borders):
        if s % 7 == 1 and s + 2 in borders:
            borders[s + 1] = (borders[s] + borders[s + 2]) / 2
        if s % 7 == 5 and s + 2 in borders:
            borders[s + 1] = (borders[s] + borders[s + 2]) / 2
    slots = sorted(borders)
    lo, hi = slots[0], slots[-1]
    for s in range(lo, hi + 1):
        if s in borders:
            continue
        below = max(t for t in borders if t < s)
        above = min(t for t in borders if t > s)
        borders[s] = borders[below] + (borders[above] - borders[below]) * (s - below) / (
            above - below
        )
    # Past the outermost black keys the borders continue at the local width
    # while the key's midpoint is inside the rectangle and the strip there still
    # looks like the top of a white key — light between the black keys. The
    # second half of that rule is what stops the walk at the end of a keyboard
    # that does not fill the rectangle.
    # The first white key past the outermost black key needs no test: a black
    # key stands between two white keys. Every key beyond that one does.
    w_lo = local[keys[0].index]
    w_hi = local[keys[-1].index]
    first_black_slot = min(slot_of.values())
    last_black_slot = max(slot_of.values())
    s = lo
    while borders[s] - w_lo / 2 >= 0:
        certain = s == first_black_slot
        if not certain and is_white_key is not None and not is_white_key(borders[s] - w_lo / 2):
            break
        borders[s - 1] = borders[s] - w_lo
        s -= 1
    s = hi
    while borders[s] + w_hi / 2 <= width_px:
        certain = s == last_black_slot
        if not certain and is_white_key is not None and not is_white_key(borders[s] + w_hi / 2):
            break
        borders[s + 1] = borders[s] + w_hi
        s += 1
    return borders, slot_of, family, ratio


# ------------------------------------------------------------- the whole ---


def find_overlay(
    image: np.ndarray,
    rect: PianoRect,
    upper_line: float | None = None,
    first_white_octave: int | None = None,
    settings: FinderSettings = DEFAULTS,
) -> Calibration:
    """Read one picture inside one rectangle and answer the piano overlay.

    ``upper_line`` and ``first_white_octave`` are the user's when given: the
    upper line defaults to the higher end of the rectangle's top edge (V-11) and
    the octave to what the key count suggests (V-10).
    """
    height, width = image.shape[:2]
    strip = rectify(image, rect)
    blacks = find_black_keys(strip, settings)
    depth = blacks.depth
    half_key = float(np.median([k.width for k in blacks.keys])) * 0.5
    bar = min(blacks.extra["bar_left"], blacks.extra["bar_right"])

    black_cols = np.zeros(strip.shape[1], dtype=bool)
    for k in blacks.keys:
        a_, b_ = int(round(k.centre - k.width / 2)), int(round(k.centre + k.width / 2)) + 1
        black_cols[max(0, a_) : min(strip.shape[1], b_)] = True

    def is_white_key(centre: float) -> bool:
        # the top of a white key, between the black keys, clears the local bar;
        # sampled over the part of the key the rectangle shows and no black key
        # claims, so a key cut in half by the picture's edge is judged on the
        # sliver of its own top that is there
        a, b = int(round(centre - half_key)), int(round(centre + half_key)) + 1
        a, b = max(0, a), min(strip.shape[1], b)
        if b <= a:
            return False
        cols = np.arange(a, b)[~black_cols[a:b]]
        if len(cols) == 0:
            return False
        return float(np.median(strip[3 : max(6, depth - 4), cols])) > bar

    borders_by_slot, slot_of, family, ratio = white_borders_from(
        blacks.keys, strip.shape[1], settings, is_white_key
    )
    slots = sorted(borders_by_slot)
    lo, hi = slots[0], slots[-1]
    borders = [borders_by_slot[s] for s in slots]
    white_count = len(borders) - 1

    # A black key at slot s stands on border s, between white keys s - lo - 1
    # and s - lo. Only the black keys with a white key on both sides are kept;
    # the end rule may have dropped a half key at either edge.
    kept = [k for k in blacks.keys if lo < slot_of[k.index] < hi]
    if not kept:
        raise NoKeyboard("no black key with a white key on both sides of it")
    first = kept[0]
    left_white_pc = (BLACK_PITCH_CLASS[first.position] - 1) % 12
    steps_back = slot_of[first.index] - lo - 1
    first_pc = WHITE_PITCH_CLASSES[(WHITE_PITCH_CLASSES.index(left_white_pc) - steps_back) % 7]
    black_borders = [
        BlackBorder(left=k.centre - k.width / 2, right=k.centre + k.width / 2) for k in kept
    ]

    top_edge_high = min(rect.y, rect.y + rect.width * math.sin(math.radians(rect.angle)))
    from pydantic import ValidationError

    try:
        cal = _calibration(
            width,
            height,
            rect,
            upper_line,
            top_edge_high,
            borders,
            black_borders,
            first_pc,
            first_white_octave,
            white_count,
            blacks,
            family,
            ratio,
        )
    except ValidationError as exc:
        raise NoKeyboard(
            f"the keys found do not make a keyboard: {exc.errors()[0]['msg']}"
        ) from exc
    black_midis = [k.midi for k in geometry.keys(cal) if k.kind == "black"]
    assert cal.found is not None
    cal.found.extrapolated = [midi for midi, k in zip(black_midis, kept) if not k.seen]
    cal.found.confirmed = [midi for midi, k in zip(black_midis, kept) if not k.seen and k.confirmed]
    return cal


def _calibration(
    width,
    height,
    rect,
    upper_line,
    top_edge_high,
    borders,
    black_borders,
    first_pc,
    first_white_octave,
    white_count,
    blacks,
    family,
    ratio,
) -> Calibration:
    return Calibration(
        image_width=width,
        image_height=height,
        piano_rect=rect,
        upper_line=float(upper_line) if upper_line is not None else max(1.0, float(top_edge_high)),
        white_borders=borders,
        black_borders=black_borders,
        black_depth=float(max(1, blacks.depth)),
        first_white_pitch_class=first_pc,
        first_white_octave=(
            int(first_white_octave)
            if first_white_octave is not None
            else geometry.default_octave_for(white_count)
        ),
        found=Found(route="A", confidence=blacks.confidence),
        note=(
            f"found by route A · family {family} · gap ratio {ratio:.2f} · "
            f"{blacks.thrown_out} candidates thrown out"
        ),
    )
