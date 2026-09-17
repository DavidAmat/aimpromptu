"""The five candidates of Task 1.2.2, all fed into the same run extraction.

Only the foreground mask differs between the first four, which is the point: if
they are compared with different run logic the comparison says nothing. The
fifth, the single row watcher, has no runs at all and is the baseline to beat.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from common import Calibration

# Named thresholds, in the plan's words. Values are re-measured in the report.
TAU_FOREGROUND = 24.0    # of 255, for the absolute and the plate difference
TAU_COVERAGE = 0.55      # filled fraction of the lane core
GAP_CLOSE = 2            # rows: close a gap of at most this many. MEASURED: the
                         # gap between two rectangles stacked on one key is 3 to
                         # 7 rows and the gaps inside one rectangle are 1 to 2,
                         # so this must stay below 3 or two notes become one
MIN_HEIGHT = 6           # rows
CLIP_TOLERANCE = 3       # rows
LANE_MARGIN = 0.25       # of a white key width
HALO_BAND = 12           # rows above the upper line that are not trusted
MIN_WIDTH = 0.35         # of a white key width: narrower than a black key is not a note
MAX_WIDTH = 1.40         # of a white key width: wider than a white key is not a note
TAU_EDGE = 0.50          # of the run's own peak: where the rectangle stops and its glow starts
SPLIT_PROMINENCE = 0.40  # of a run's plateau: how far a local minimum has to
                         # drop below the plateau on BOTH sides of it before it
                         # counts as the border between two rectangles. MEASURED
                         # on lanes whose content was read off the pixels by
                         # hand: the texture inside one rectangle reaches 0.13
                         # at the worst, and a real border is 0.75 to 0.80. This
                         # sits in the middle of that gap
GUARD_BAND = 1.75        # white key widths above the upper line: nothing that
                         # lives entirely in here and is not clipped is a note


# ---------------------------------------------------------------- masks -----

def mask_absolute(roll: np.ndarray, cal: Calibration) -> np.ndarray:
    """Anything brighter than the darkest part of the roll by tauForeground."""
    grey = roll.mean(axis=2)
    floor = np.percentile(grey, 20)
    return grey - floor


def mask_plate(roll: np.ndarray, cal: Calibration) -> np.ndarray:
    """The background plate difference, with the plate stood in for.

    A video gives the plate as the per-pixel median of frames spread over the
    whole video. One screenshot cannot, so the stand-in is the per-row median
    across the width of the roll: whatever most of a row looks like is the
    background of that row. It removes a vertical gradient and the glow that
    fades upward from the upper line, which is most of what the real plate
    removes. It does not remove a title drawn across the roll, and a real plate
    does, so every score here is a floor for that case, not a ceiling.
    """
    diff = np.abs(roll - np.median(roll, axis=1, keepdims=True))
    return diff.max(axis=2)


def mask_edges(roll: np.ndarray, cal: Calibration) -> np.ndarray:
    """Edges, then the span between the outermost edges of a row is filled.

    This is the one that is supposed to cope with an outlined rectangle, where
    the inside of the shape is the background colour and only the border is
    drawn.
    """
    grey = ndimage.gaussian_filter(roll.mean(axis=2), 1.0)
    gx = ndimage.sobel(grey, axis=1)
    gy = ndimage.sobel(grey, axis=0)
    mag = np.hypot(gx, gy)
    scale = max(30.0, float(np.percentile(mag, 97))) / TAU_FOREGROUND
    return mag / max(scale, 1e-6)


def mask_colour(roll: np.ndarray, cal: Calibration) -> np.ndarray:
    """Colour clustering: the biggest cluster is the background, the rest is not.

    k-means on a sample of the roll pixels, five clusters, the cluster holding
    the most pixels dropped. No library beyond numpy; five clusters over a few
    thousand samples converges in a handful of passes.
    """
    flat = roll.reshape(-1, 3)
    rng = np.random.default_rng(0)
    sample = flat[rng.choice(len(flat), size=min(20000, len(flat)), replace=False)]
    centres = sample[rng.choice(len(sample), size=5, replace=False)].astype(np.float64)
    for _ in range(12):
        d = ((sample[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2)
        who = d.argmin(axis=1)
        for c in range(5):
            if (who == c).any():
                centres[c] = sample[who == c].mean(axis=0)
    d = ((flat[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2)
    who = d.argmin(axis=1)
    background = np.bincount(who, minlength=5).argmax()
    far = np.sqrt(((flat - centres[background]) ** 2).sum(axis=1))
    return np.where(who == background, 0.0, far).reshape(roll.shape[:2])


MASKS = {
    "absolute": mask_absolute,
    "plate": mask_plate,
    "edges": mask_edges,
    "colour": mask_colour,
}


# ----------------------------------------------------------------- runs -----
#
# One key, one lane, one answer.
#
# The first version of this ran the extraction in every lane and then attributed
# each run to the nearest key midpoint. That looked like V-13 and V-14 but it was
# wrong: the same rectangle is visible from three lanes, each lane cut it into
# pieces differently, and every version survived. On one frame of the test video
# key G2 carried a merged run of 159 rows on top of the four correct ones, and 23
# pairs of runs on the same key overlapped. A picture drawn from that shows a big
# box around three rectangles and the right boxes inside it at the same time.
#
# So the lane of a key is read once, for that key, and V-14 becomes a filter: a
# run found in this lane whose rectangle is centred nearer some other key is
# dropped here, because that other key's own lane will find it. Two runs on one
# key can no longer overlap, because they come from one profile.


def _fill_span(sub: np.ndarray) -> np.ndarray:
    """Fill each row between its leftmost and its rightmost foreground pixel."""
    idx = np.arange(sub.shape[1])[None, :]
    any_row = sub.any(axis=1)
    first = np.where(any_row, np.where(sub, idx, sub.shape[1]).min(axis=1), 0)
    last = np.where(any_row, np.where(sub, idx, -1).max(axis=1), -1)
    return (idx >= first[:, None]) & (idx <= last[:, None]) & any_row[:, None]


def _close_gaps(flags: np.ndarray, gap: int) -> np.ndarray:
    """Close gaps of at most `gap` rows, and no more.

    `binary_closing` with a structure of length L closes every gap shorter than
    L, so the structure is `gap + 1` long. Getting this wrong is expensive: with
    a structure of 2*gap+1 and gap 3 it closes six rows, and the border between
    two rectangles stacked on one key is three to seven.
    """
    if gap <= 0:
        return flags
    return ndimage.binary_closing(flags, structure=np.ones(gap + 1))


def _runs(flags: np.ndarray) -> list[tuple[int, int]]:
    out, start = [], None
    for i, v in enumerate(flags):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(flags)))
    return out


def valleys(prof: np.ndarray) -> list[tuple[int, float]]:
    """The interior local minima of one run, with their prominence.

    Prominence is how far the minimum sits below the lower of the two peaks
    beside it, as a share of the run's plateau. It is the right measure because
    the plateau of a rectangle is flat to about one percent while a border drops
    tens of percent, and because it does not care what the absolute brightness
    of the rendering is.

    A flat bottom is one border, not forty, so neighbouring candidates are
    grouped and only the deepest of each group is answered for.
    """
    if len(prof) < 2 * MIN_HEIGHT + 1:
        return []
    plateau = float(np.percentile(prof, 75))
    if plateau <= 1:
        return []
    cand = [i for i in range(MIN_HEIGHT, len(prof) - MIN_HEIGHT)
            if prof[i] <= prof[i - 1] and prof[i] <= prof[i + 1]]
    if not cand:
        return []
    groups, cur = [], [cand[0]]
    for i in cand[1:]:
        if i - cur[-1] <= MIN_HEIGHT:
            cur.append(i)
        else:
            groups.append(cur)
            cur = [i]
    groups.append(cur)

    out = []
    for g in groups:
        i = min(g, key=lambda r: prof[r])
        left = float(prof[:g[0]].max()) if g[0] > 0 else 0.0
        right = float(prof[g[-1] + 1:].max()) if g[-1] + 1 < len(prof) else 0.0
        if left <= 0 or right <= 0:
            continue
        out.append((i, (min(left, right) - float(prof[i])) / plateau))
    return out


def split_run(prof: np.ndarray, a: int, b: int) -> list[tuple[int, int]]:
    """Cut one run wherever two rectangles touch.

    Where the border between two rectangles gets dark enough the run has already
    ended and there is nothing to do here. Where it does not — and on the test
    video two of the three borders of one lane did not — the run is one piece and
    the second onset would be lost without a sound. So the run is cut at every
    valley whose prominence reaches `splitProminence`.
    """
    piece = prof[a:b]
    cuts = [i for i, prom in valleys(piece) if prom >= SPLIT_PROMINENCE]
    if not cuts:
        return [(a, b)]
    out, start = [], a
    for c in cuts:
        if a + c - start >= MIN_HEIGHT:
            out.append((start, a + c))
            start = a + c + 1
    if b - start >= MIN_HEIGHT:
        out.append((start, b))
    return out or [(a, b)]


EXTENT_WINDOW = 2.0       # white key widths either side of the key: how far the
                          # search for the rectangle's own edges may reach
HOLLOW_FALLBACK = False   # only the gradient channel needs it: a gradient is
                          # strong on a rectangle's border and empty in its
                          # middle, so the middle fails a test written for a
                          # filled shape. Turning it on for the plate difference
                          # lets the glow through and costs two invented onsets


def _full_extent(strength: np.ndarray, y0: int, y1: int, centre: float,
                 w: float, filled: np.ndarray | None = None,
                 filled_x0: int = 0) -> tuple[float, float] | None:
    """How wide the rectangle really is, ignoring where the lane borders are.

    The rectangle is the bright part; the glow around it is the dim part. So the
    edge is found against the run's own peak rather than a fixed threshold: a
    column belongs to the rectangle when it reaches `tauEdge` of the strongest
    column of the run.

    The peak is taken over a window of `extentWindow` white keys either side of
    the key, not over the whole width. Taking it over the whole width was a real
    bug: the brightest column in those rows is some other key's strike flash, it
    set the bar far too high for this key's own columns, and the search then
    walked off to whatever column did pass — which put a run near the upper line
    on a key four semitones away.

    None means the key's own centre is not part of anything bright in these
    rows, so this run does not belong to this key.
    """
    lo = max(0, int(round(centre - EXTENT_WINDOW * w)))
    hi = min(strength.shape[1], int(round(centre + EXTENT_WINDOW * w)) + 1)
    if hi - lo < 3:
        return None
    per_col = np.median(strength[y0:y1 + 1, lo:hi], axis=0)
    peak = float(per_col.max())
    if peak <= 0:
        return None
    col = per_col >= max(TAU_EDGE * peak, TAU_FOREGROUND)
    c = int(round(centre)) - lo
    if not (0 <= c < len(col)):
        return None
    if not col[c] and filled is not None and HOLLOW_FALLBACK:
        # An outlined rectangle is hollow: the gradient that drew its border is
        # strong and its middle is empty, so the middle fails a test written for
        # a filled shape. The span filled mask knows the shape is there, so it
        # answers for the columns the strength cannot.
        a0 = max(0, lo - filled_x0)
        b0 = min(filled.shape[1], hi - filled_x0)
        if b0 > a0:
            share = filled[y0:y1 + 1, a0:b0].mean(axis=0) >= 0.5
            pad = np.zeros(len(col), dtype=bool)
            n = min(len(share), len(pad) - max(0, filled_x0 - lo))
            pad[max(0, filled_x0 - lo): max(0, filled_x0 - lo) + n] = share[:n]
            col = col | pad
    if not col[c]:
        return None
    a = c
    while a > 0 and col[a - 1]:
        a -= 1
    b = c
    while b < len(col) - 1 and col[b + 1]:
        b += 1
    return float(lo + a), float(lo + b)


def runs_for_key(strength: np.ndarray, mask: np.ndarray, cal: Calibration,
                 key: dict, mids: np.ndarray, midis: np.ndarray,
                 upper: int, roll_top: int, guard: float) -> list[dict]:
    """Every rectangle this key's own lane holds, and no other key's."""
    w = cal.white_width
    lane0 = max(0, int(round(key["left"] - LANE_MARGIN * w)))
    lane1 = min(mask.shape[1], int(round(key["right"] + LANE_MARGIN * w)) + 1)
    core0 = max(0, int(round(key["left"])))
    core1 = min(mask.shape[1], int(round(key["right"])) + 1)
    if lane1 - lane0 < 3 or core1 - core0 < 2:
        return []

    filled_roll = _fill_span(mask[roll_top:, lane0:lane1])
    filled = np.zeros((mask.shape[0], lane1 - lane0), dtype=bool)
    filled[roll_top:] = filled_roll
    coverage = filled_roll[:, core0 - lane0: max(core0 - lane0 + 1, core1 - lane0)].mean(axis=1)
    inside = _close_gaps(coverage >= TAU_COVERAGE, GAP_CLOSE)
    profile = strength[roll_top:, core0:core1].mean(axis=1)

    out = []
    for a, b in _runs(inside):
        if b - a < MIN_HEIGHT:
            continue
        for ry0, ry1 in split_run(profile, a, b - 1):
            y0, y1 = ry0 + roll_top, ry1 + roll_top
            if y1 - y0 + 1 < MIN_HEIGHT:
                continue
            extent = _full_extent(strength, y0, y1, key["mid"], w,
                                  filled=filled, filled_x0=lane0)
            if extent is None:
                continue
            x0, x1 = extent
            width = (x1 - x0 + 1) / w
            if not (MIN_WIDTH <= width <= MAX_WIDTH):
                continue
            # V-14 as a filter: if this rectangle is centred nearer another key,
            # that key's own lane will report it.
            mid = (x0 + x1) / 2
            if midis[int(np.argmin(np.abs(mids - mid)))] != key["midi"]:
                continue
            # V-08: inside the halo guard band the tip is not read from the
            # pixels, it is extrapolated. That is a flag on the run, not a
            # reason to throw it away. Throwing it away was wrong and it cost a
            # real onset: on one example the rectangle is 43 rows tall and the
            # guard band is 68, so a whole legitimate rectangle sat inside the
            # band and vanished. What removes the light is the width gate and
            # the minimum height, which a halo blob fails anyway.
            clipped = y1 >= upper - 1 - CLIP_TOLERANCE
            tip_trusted = clipped or y1 <= upper - guard
            out.append(dict(y_top=int(y0), y_bottom=int(y1), x0=x0, x1=x1,
                            mid=float(mid), midi=int(key["midi"]),
                            width_keys=float(width), clipped=bool(clipped),
                            tip_trusted=bool(tip_trusted),
                            entering=bool(y0 <= roll_top + 2)))
    return out


def detect(img: np.ndarray, cal: Calibration, offset_d: float,
           mask_name: str = "plate", plate_img: np.ndarray | None = None) -> dict:
    """One picture and one calibration in, onsets and sustains out.

    `plate_img` is the real background plate of V-15, the per-pixel median of
    frames spread over the whole video. When it is given the plate difference is
    the real one; when it is not, the single screenshot stand-in is used.
    """
    u = int(round(cal.upper_line))
    roll = img[:u]
    global HOLLOW_FALLBACK
    if plate_img is not None:
        strength = np.abs(roll - plate_img[:u]).max(axis=2)
        HOLLOW_FALLBACK = False
    else:
        strength = MASKS[mask_name](roll, cal)
        HOLLOW_FALLBACK = mask_name == "edges"
    mask = strength > TAU_FOREGROUND

    keys = cal.keys()
    mids = np.array([k["mid"] for k in keys])
    midis = np.array([k["midi"] for k in keys])

    roll_top = int(round(cal.roll_top))
    guard = cal.guard_band if cal.guard_band > 0 else GUARD_BAND * cal.white_width

    runs: list[dict] = []
    for key in keys:
        runs.extend(runs_for_key(strength, mask, cal, key, mids, midis, u,
                                 roll_top, guard))

    onsets, sustains = window_rule(runs, u, offset_d)
    return dict(onsets=sorted(onsets), sustains=sorted(sustains), runs=runs,
                mask=mask, strength=strength)


def window_rule(runs: list[dict], upper: int, d: float) -> tuple[set, set]:
    """V-18, word for word, with V-16 applied to the tip.

    y grows downward. The roll was cut at the upper line, so a run whose lowest
    row sits on that cut has been cut there, not tipped there: its real tip is
    already past the upper line, so the note is sounding and its onset is in the
    past.
    """
    onsets, sustains = set(), set()
    for r in runs:
        y_bottom = upper if r.get("clipped") else r["y_bottom"]
        y_top = r["y_top"]
        if upper - d <= y_bottom < upper:
            onsets.add(r["midi"])
        elif y_bottom >= upper and y_top < upper - d:
            sustains.add(r["midi"])
    return onsets, sustains - onsets


# ------------------------------------------------- the baseline to beat -----

def detect_single_row(img: np.ndarray, cal: Calibration, offset_d: float,
                      rows_above: int = 2) -> dict:
    """One row of pixels just above the upper line, the common approach.

    A key is on when the colour in its row differs from what that row looks like
    without a note. It cannot say when inside the window the note started and it
    cannot tell an onset from a sustain, so every key it calls on is reported as
    an onset. That is the whole of its weakness and the reason it is here.
    """
    u = int(round(cal.upper_line))
    y = max(0, u - rows_above)
    row = img[y]
    on = set()
    for k in cal.keys():
        a, b = int(round(k["left"])), int(round(k["right"])) + 1
        a, b = max(0, a), min(img.shape[1], b)
        if b - a < 2:
            continue
        # What this key's lane looks like when nothing is on it: the median of
        # the lane over the whole roll, which is background almost everywhere.
        quiet = np.median(img[:u, a:b].reshape(-1, 3), axis=0)
        here = np.median(row[a:b], axis=0)
        if float(np.abs(here - quiet).max()) > TAU_FOREGROUND:
            on.add(k["midi"])
    return dict(onsets=sorted(on), sustains=[], runs=[], mask=None)
