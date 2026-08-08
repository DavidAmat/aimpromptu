"""Peak finding, tatum fitting and the sliding-window tempo scan.

Three estimators, deliberately kept independent so they can disagree:

``peaks``      Smooth the millisecond histogram and read its local maxima. This
               is the picture the user asked for: "the peaks are the figures".
``tatum``      Fit a single unit ``u`` such that most intervals are near-integer
               multiples of it. This is the number a quantizer would actually
               need, and it does not require naming any figure.
``scan``       Run ``tatum`` in a sliding window and plot it against time. If the
               idea works at all, a tempo change has to show up here as a step.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


# --------------------------------------------------------------------------
# Peaks
# --------------------------------------------------------------------------

@dataclass
class Peak:
    centre_ms: float          # smoothed-density argmax
    mass: int                 # intervals inside the peak's basin
    share: float              # mass / total intervals
    lo_ms: float              # basin edges (nearest density minima)
    hi_ms: float
    mean_ms: float            # mean of the intervals in the basin
    median_ms: float


def gaussian_kde_grid(values_ms: np.ndarray, grid_ms: np.ndarray,
                      bandwidth_ms: float) -> np.ndarray:
    """Plain Gaussian KDE evaluated on ``grid_ms``.

    A fixed bandwidth in **milliseconds** (not a rule-of-thumb multiple of the
    spread) is on purpose: the thing being smoothed over is human timing jitter,
    which is roughly constant in absolute terms, while an adaptive bandwidth
    would widen with the long-rest tail and erase the fast peaks.
    """
    if values_ms.size == 0:
        return np.zeros_like(grid_ms)
    z = (grid_ms[:, None] - values_ms[None, :]) / bandwidth_ms
    kernel = np.exp(-0.5 * z * z).sum(axis=1)
    return kernel / (values_ms.size * bandwidth_ms * np.sqrt(2 * np.pi))


def find_peaks(values_ms: np.ndarray, grid_ms: np.ndarray, density: np.ndarray,
               *, min_share: float = 0.02, min_separation_ms: float = 25.0) -> list[Peak]:
    """Local maxima of ``density``, kept if their basin holds ``min_share`` of the data.

    The basin of a peak runs to the neighbouring density minima, so the reported
    mass is a real partition of the intervals -- every interval belongs to
    exactly one basin and the shares are comparable across segments.
    """
    interior = np.arange(1, len(density) - 1)
    maxima = interior[(density[1:-1] > density[:-2]) & (density[1:-1] >= density[2:])]
    minima = interior[(density[1:-1] < density[:-2]) & (density[1:-1] <= density[2:])]
    edges = np.concatenate(([0], minima, [len(density) - 1]))

    peaks: list[Peak] = []
    total = max(1, values_ms.size)
    for index in maxima:
        left = edges[edges <= index].max()
        right = edges[edges >= index].min()
        lo, hi = grid_ms[left], grid_ms[right]
        inside = values_ms[(values_ms >= lo) & (values_ms < hi)]
        if inside.size / total < min_share:
            continue
        peaks.append(Peak(
            centre_ms=float(grid_ms[index]), mass=int(inside.size),
            share=float(inside.size / total), lo_ms=float(lo), hi_ms=float(hi),
            mean_ms=float(inside.mean()), median_ms=float(np.median(inside)),
        ))

    peaks.sort(key=lambda p: p.centre_ms)
    merged: list[Peak] = []
    for peak in peaks:
        if merged and peak.centre_ms - merged[-1].centre_ms < min_separation_ms:
            if peak.mass > merged[-1].mass:
                merged[-1] = peak
            continue
        merged.append(peak)
    return merged


# --------------------------------------------------------------------------
# Tatum
# --------------------------------------------------------------------------

def tatum_score(values_ms: np.ndarray, unit_ms: np.ndarray, *,
                rel_tolerance: float = 0.10, max_multiple: int = 12) -> np.ndarray:
    """How well each candidate unit explains the intervals, in [0, 1].

    For unit ``u`` an interval ``x`` scores ``exp(-d^2 / 2s^2)`` where ``d`` is
    the distance from ``x/u`` to the nearest whole number and ``s`` is
    ``rel_tolerance`` -- i.e. a fixed slack **in units**, so a 10 % miss on a
    fast note and on a slow note cost the same. Intervals longer than
    ``max_multiple`` units score zero: a five-second rest is not evidence about
    the beat, and without the cap a very small ``u`` would score every rest
    perfectly and win.
    """
    ratios = values_ms[None, :] / unit_ms[:, None]
    distance = np.abs(ratios - np.round(ratios))
    weight = (ratios <= max_multiple) & (ratios >= 0.75)
    score = np.exp(-0.5 * (distance / rel_tolerance) ** 2) * weight
    return score.sum(axis=1) / max(1, values_ms.size)


def fit_tatum(values_ms: np.ndarray, *, lo_ms: float = 40.0, hi_ms: float = 900.0,
              step_ms: float = 0.5, accept: float = 0.97,
              **kwargs) -> tuple[float, np.ndarray, np.ndarray]:
    """Best unit, plus the whole score curve for plotting.

    Half of a valid unit is also a valid unit -- every multiple of ``u`` is a
    multiple of ``u/2`` -- so the raw argmax drifts to the bottom of the search
    range. The tie is broken by taking the **largest** unit whose score is
    within ``accept`` of the best, which is the coarsest grid consistent with
    the playing and therefore the one a notation program wants.
    """
    grid = np.arange(lo_ms, hi_ms + step_ms, step_ms)
    score = tatum_score(values_ms, grid, **kwargs)
    if score.max() <= 0:
        return float("nan"), grid, score
    good = grid[score >= accept * score.max()]
    return float(good.max()), grid, score


# --------------------------------------------------------------------------
# Beat anchor and swing
# --------------------------------------------------------------------------

#: Ratios of a figure to the beat that a score is allowed to print.
SIMPLE_RATIOS: dict[float, str] = {
    1 / 8: "fusa", 1 / 6: "semicorchea de tresillo", 1 / 4: "semicorchea",
    1 / 3: "corchea de tresillo", 3 / 8: "semicorchea con puntillo",
    1 / 2: "corchea", 2 / 3: "corchea de tresillo (larga)",
    3 / 4: "corchea con puntillo", 1.0: "negra", 4 / 3: "negra de tresillo (larga)",
    3 / 2: "negra con puntillo", 2.0: "blanca", 3.0: "blanca con puntillo",
    4.0: "redonda",
}


def nearest_ratio(ratio: float) -> tuple[float, str, float]:
    """Nearest printable ratio, its figure name, and the relative error in %."""
    best = min(SIMPLE_RATIOS, key=lambda r: abs(np.log2(ratio / r)))
    return best, SIMPLE_RATIOS[best], abs(ratio / best - 1.0) * 100.0


def fit_beat(peaks: list[Peak], *, lo_ms: float = 250.0, hi_ms: float = 1200.0,
             step_ms: float = 0.5, rel_tolerance: float = 0.08
             ) -> tuple[float, np.ndarray, np.ndarray]:
    """Pick the beat (negra) that makes the *peaks* land on printable ratios.

    Deliberately separate from :func:`fit_tatum`. The tatum is the finest grid;
    the beat is the one the user is asked to name, and it is not always a peak
    that exists -- in a running semiquaver passage the beat itself is never
    played. Scoring peaks rather than raw intervals means a peak carrying 44 % of
    the mass counts 44 %, not once.

    ``lo_ms``/``hi_ms`` bound the search at 50-240 BPM, which is the only prior
    in the whole PoC and the honest place to put one: octave ambiguity is real
    and unresolvable from intervals alone.
    """
    grid = np.arange(lo_ms, hi_ms + step_ms, step_ms)
    score = np.zeros_like(grid)
    total = sum(peak.mass for peak in peaks) or 1
    for index, beat in enumerate(grid):
        accumulated = 0.0
        for peak in peaks:
            ratio = peak.median_ms / beat
            target, _, _ = nearest_ratio(ratio)
            distance = np.log2(ratio / target)
            accumulated += peak.mass * np.exp(-0.5 * (distance / rel_tolerance) ** 2)
        score[index] = accumulated / total
    return float(grid[int(np.argmax(score))]), grid, score


def detect_swing(peaks: list[Peak], beat_ms: float, *, tolerance: float = 0.06
                 ) -> tuple[float, float, float] | None:
    """Find a pair of peaks that sums to the beat: ``(long, short, ratio)``.

    A shuffle shows up as two peaks whose *sum* is the beat and whose ratio is
    somewhere between 1 (straight) and 2 (a written triplet). It is worth
    naming separately because a binary grid cannot hold it at any resolution --
    no power-of-two subdivision of the beat lands on 0.63 of it.
    """
    best = None
    for i, long in enumerate(peaks):
        for short in peaks[:i] + peaks[i + 1:]:
            if short.median_ms >= long.median_ms:
                continue
            total = long.median_ms + short.median_ms
            error = abs(total / beat_ms - 1.0)
            if error > tolerance:
                continue
            mass = long.mass + short.mass
            if best is None or mass > best[0]:
                best = (mass, long.median_ms, short.median_ms,
                        long.median_ms / short.median_ms)
    if best is None:
        return None
    return best[1], best[2], best[3]


def sliding_tatum(attack_seconds: np.ndarray, *, window_s: float = 20.0,
                  hop_s: float = 2.0, min_intervals: int = 25,
                  **kwargs) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """``fit_tatum`` over a sliding window.

    Returns ``(centre_s, unit_ms, score, intervals)``. The score comes back
    because a window over a sparse passage still returns *some* unit, and a
    reader has to be able to tell "the tempo moved" from "there was nothing here
    to measure".
    """
    attacks = np.asarray(attack_seconds, dtype=float)
    if attacks.size < 2:
        return np.array([]), np.array([]), np.array([]), np.array([])
    centres, units, scores, counts = [], [], [], []
    start = attacks[0]
    while start + window_s <= attacks[-1]:
        inside = attacks[(attacks >= start) & (attacks < start + window_s)]
        gaps = np.diff(inside) * 1000.0
        if gaps.size >= min_intervals:
            unit, grid, score = fit_tatum(gaps, **kwargs)
            centres.append(start + window_s / 2)
            units.append(unit)
            scores.append(float(np.interp(unit, grid, score)))
            counts.append(int(gaps.size))
        start += hop_s
    return (np.asarray(centres), np.asarray(units),
            np.asarray(scores), np.asarray(counts))
