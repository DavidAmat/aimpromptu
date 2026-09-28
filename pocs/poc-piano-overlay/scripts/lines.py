"""The thin dark line between two white keys, read in the front of the keys.

Used twice, on purpose: as the tool the truth is read with (Task 1.1.1 — every
line it finds is drawn on a ruled crop and checked by eye, and the file of the
truth says which were kept), and as route B (Task 1.2.3), which is the same
reading with nobody checking it.

In the front of the keys — below the black keys and above the front edge of the
keyboard — every white key border is visible as a line one to three pixels wide,
darker than the key on both sides of it. It is read on two rows, one just below
the black keys and one just above the front edge, so each border has a
direction as well as a place, and the border at the top edge of the one
rectangle is the line extended up through the black key band.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from common import runs


@dataclass
class Line:
    u_high: float  # on the row just below the black keys
    u_low: float  # on the row just above the front edge
    strength: float
    paired: bool = True  # found on both rows, so it has a direction of its own

    def at(self, v: float, v_high: float, v_low: float) -> float:
        """The u of this border at row v, extended along its own direction."""
        if v_low == v_high:
            return self.u_high
        return self.u_high + (self.u_low - self.u_high) * (v - v_high) / (v_low - v_high)


def keyboard_bottom(strip: np.ndarray, depth: int, black_columns: np.ndarray) -> int:
    """Where the front of the white keys ends.

    The white key columns are averaged into one vertical profile below the black
    keys. It is bright and flat down the front of the keys and drops at the front
    edge of the keyboard, or runs to the bottom of the picture when the keyboard
    is cut there. The bottom is the first row where it falls below 55% of its
    level just under the black keys.
    """
    h = strip.shape[0]
    white = ~black_columns
    if white.sum() < 10:
        return h
    profile = np.median(strip[:, white], axis=1)
    start = min(h - 1, depth + 8)
    level = float(np.median(profile[start : min(h, start + 12)]))
    for y in range(start + 12, h):
        if profile[y] < 0.55 * level:
            return y
    return h


def dark_lines(profile: np.ndarray, min_strength: float, window: int = 9) -> list[tuple[float, float]]:
    """Local minima of a row profile that are narrow and darker than both sides.

    A border is one to three pixels wide, so the background is the higher of
    the two maxima within `window` px on each side, and the strength is how far
    the minimum sits below the lower of them. The 75th percentile trick of
    Phase 1 of 04 is not needed here because the black keys are excluded by the
    rows this reads.
    """
    p = ndimage.gaussian_filter1d(profile, 0.8)
    n = len(p)
    out: list[tuple[float, float]] = []
    for i in range(2, n - 2):
        if not (p[i] <= p[i - 1] and p[i] <= p[i + 1] and (p[i] < p[i - 1] or p[i] < p[i + 1])):
            continue
        left = p[max(0, i - window) : i].max()
        right = p[i + 1 : i + 1 + window].max()
        strength = float(min(left, right) - p[i])
        if strength < min_strength:
            continue
        # sub-pixel: parabola through the three points
        a, b, c = p[i - 1], p[i], p[i + 1]
        denom = a - 2 * b + c
        shift = 0.5 * (a - c) / denom if denom != 0 else 0.0
        out.append((i + float(np.clip(shift, -0.5, 0.5)), strength))
    # merge minima closer than 3 px: the wider lines give two
    merged: list[tuple[float, float]] = []
    for u, s in out:
        if merged and u - merged[-1][0] < 3.0:
            if s > merged[-1][1]:
                merged[-1] = (u, s)
            continue
        merged.append((u, s))
    return merged


def read_lines(strip: np.ndarray, depth: int, bottom: int, black_width: float) -> tuple[list[Line], int, int]:
    """Every white key border visible in the front of the keys, paired over two rows."""
    front = bottom - depth
    v_high = int(depth + max(6, 0.15 * front))
    v_low = int(bottom - max(6, 0.15 * front))
    if v_low <= v_high + 2:
        v_high, v_low = depth + 4, max(depth + 8, bottom - 4)
    band = 3
    high = strip[max(0, v_high - band) : v_high + band + 1].mean(axis=0)
    low = strip[max(0, v_low - band) : v_low + band + 1].mean(axis=0)
    # the contrast of the front: a line has to be at least a tenth of it
    contrast = float(np.percentile(high, 90) - np.percentile(high, 10))
    min_strength = max(6.0, 0.10 * contrast)
    top_lines = dark_lines(high, min_strength)
    low_lines = dark_lines(low, min_strength)
    # pair each high line with the nearest low line within half a black key
    out: list[Line] = []
    low_us = np.array([u for u, _ in low_lines]) if low_lines else np.array([])
    for u, s in top_lines:
        if len(low_us) == 0:
            out.append(Line(u, u, s, paired=False))
            continue
        j = int(np.argmin(np.abs(low_us - u)))
        if abs(low_us[j] - u) <= 0.5 * black_width:
            out.append(Line(u, float(low_us[j]), s))
        else:
            out.append(Line(u, u, s, paired=False))
    return out, v_high, v_low


def top_edge_lines(strip: np.ndarray, depth: int, black_columns: np.ndarray) -> list[float]:
    """The borders visible at the top edge: E|F and B|C, between two white keys
    with no black key over them. Read on the rows just under the top edge, and
    only in columns no black key claims. Independent of the front reading, so
    both routes can be scored against it."""
    band = strip[3 : max(6, min(depth // 3, 14))].mean(axis=0)
    contrast = float(np.percentile(band, 90) - np.percentile(band, 10))
    found = dark_lines(band, max(6.0, 0.10 * contrast))
    pad = 2
    out = []
    for u, _ in found:
        i = int(round(u))
        lo, hi = max(0, i - pad), min(len(black_columns), i + pad + 1)
        if black_columns[lo:hi].any():
            continue
        out.append(u)
    return out
