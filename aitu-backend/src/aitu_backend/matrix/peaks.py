"""Peaks in the distribution of gaps between onsets: the picture the user is asked to read.

The app does not choose the rhythm. It shows where the gaps pile up and the user says what one of
those piles is called (D-09). Interval statistics cannot settle the question on their own: a beat
and twice that beat explain the same gaps equally well, and on the second half of the piece this was
measured on, two candidates scored within 0.1 % of each other. That ambiguity is a question, not
something to infer.

So this module's job is to find the piles honestly and report how much of the data each one holds.

**It reads raw timestamps and never columns (D-07).** :func:`peaks_of` runs the guard from
:mod:`aitu_backend.matrix.intervals` before it does anything else.

Two parameters shape the answer, and both are deliberate:

* The smoothing bandwidth is a fixed **12 ms**, not a multiple of the spread of the data. What is
  being smoothed over is human timing jitter, which is roughly constant in absolute terms. A
  bandwidth that adapted to the spread would widen with the long-rest tail and erase the fast peaks.
* A peak's **basin** runs to the neighbouring minima of the density, so the reported mass is a real
  partition: every gap belongs to exactly one basin and the shares can be compared between passages.

Ported from ``poc-onset-duration-distribution/scripts/analysis.py``, whose output is the table in
``RESULTS.md``. The defaults below are the values that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aitu_backend.matrix.intervals import check_measured_on_raw_times
from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS

__all__ = [
    "DEFAULT_BANDWIDTH_MS",
    "DEFAULT_GRID_STEP_MS",
    "DEFAULT_MAX_GAP_MS",
    "DEFAULT_MIN_SEPARATION_MS",
    "DEFAULT_MIN_SHARE",
    "Peak",
    "density_grid",
    "find_peaks",
    "gaussian_kde",
    "peaks_of",
]

#: Width of the smoothing kernel, in milliseconds. See the module docstring.
DEFAULT_BANDWIDTH_MS = 12.0
#: The density is evaluated every millisecond, which is finer than any peak is sharp.
DEFAULT_GRID_STEP_MS = 1.0
#: Gaps longer than this are rests rather than rhythm, and are not plotted.
DEFAULT_MAX_GAP_MS = 1200.0
#: A pile holding less than this share of the gaps is not offered to the user.
DEFAULT_MIN_SHARE = 0.02
#: Two maxima closer than this are one peak; the heavier of the two wins.
DEFAULT_MIN_SEPARATION_MS = 25.0


@dataclass
class Peak:
    """One pile of gaps, with how much of the data it holds."""

    #: Where the smoothed density is highest, in milliseconds. This is the value the user names.
    centre_ms: float
    #: How many gaps fall in this peak's basin.
    mass: int
    #: ``mass`` as a share of every gap measured, between 0 and 1.
    share: float
    #: The basin edges, the nearest minima of the density either side of the centre.
    lo_ms: float
    hi_ms: float
    mean_ms: float
    #: The middle gap of the basin. Steadier than the mean when a few long gaps sit in the tail.
    median_ms: float


def gaussian_kde(values_ms: np.ndarray, grid_ms: np.ndarray, bandwidth_ms: float) -> np.ndarray:
    """Smooth the gaps into a density curve, evaluated on ``grid_ms``.

    A histogram with fixed bins would move a peak by up to half a bin depending on where the bins
    happen to start, which is the same phase problem D-07 is about, one level up.
    """
    values = np.asarray(values_ms, dtype=float)
    if values.size == 0:
        return np.zeros_like(grid_ms)
    if bandwidth_ms <= 0:
        raise ValueError(f"The smoothing bandwidth must be positive, got {bandwidth_ms}")
    z = (grid_ms[:, None] - values[None, :]) / bandwidth_ms
    kernel = np.exp(-0.5 * z * z).sum(axis=1)
    return kernel / (values.size * bandwidth_ms * np.sqrt(2 * np.pi))


def density_grid(
    max_gap_ms: float = DEFAULT_MAX_GAP_MS,
    step_ms: float = DEFAULT_GRID_STEP_MS,
) -> np.ndarray:
    """The millisecond values the density is evaluated at, from 0 to ``max_gap_ms``."""
    if step_ms <= 0:
        raise ValueError(f"The grid step must be positive, got {step_ms}")
    return np.arange(0.0, max_gap_ms + step_ms, step_ms)


def find_peaks(
    values_ms: np.ndarray,
    grid_ms: np.ndarray,
    density: np.ndarray,
    *,
    min_share: float = DEFAULT_MIN_SHARE,
    min_separation_ms: float = DEFAULT_MIN_SEPARATION_MS,
) -> list[Peak]:
    """Local maxima of the density, kept when their basin holds enough of the data."""
    values = np.asarray(values_ms, dtype=float)
    interior = np.arange(1, len(density) - 1)
    maxima = interior[(density[1:-1] > density[:-2]) & (density[1:-1] >= density[2:])]
    minima = interior[(density[1:-1] < density[:-2]) & (density[1:-1] <= density[2:])]
    edges = np.concatenate(([0], minima, [len(density) - 1]))

    found: list[Peak] = []
    total = max(1, values.size)
    for index in maxima:
        left = edges[edges <= index].max()
        right = edges[edges >= index].min()
        lo, hi = grid_ms[left], grid_ms[right]
        inside = values[(values >= lo) & (values < hi)]
        if inside.size / total < min_share:
            continue
        found.append(
            Peak(
                centre_ms=float(grid_ms[index]),
                mass=int(inside.size),
                share=float(inside.size / total),
                lo_ms=float(lo),
                hi_ms=float(hi),
                mean_ms=float(inside.mean()),
                median_ms=float(np.median(inside)),
            )
        )

    found.sort(key=lambda peak: peak.centre_ms)
    merged: list[Peak] = []
    for peak in found:
        if merged and peak.centre_ms - merged[-1].centre_ms < min_separation_ms:
            if peak.mass > merged[-1].mass:
                merged[-1] = peak
            continue
        merged.append(peak)
    return merged


def peaks_of(
    values_ms: np.ndarray,
    *,
    bandwidth_ms: float = DEFAULT_BANDWIDTH_MS,
    max_gap_ms: float = DEFAULT_MAX_GAP_MS,
    grid_step_ms: float = DEFAULT_GRID_STEP_MS,
    min_share: float = DEFAULT_MIN_SHARE,
    min_separation_ms: float = DEFAULT_MIN_SEPARATION_MS,
    frame_ms: float = DEFAULT_FRAME_MS,
    guard: bool = True,
) -> list[Peak]:
    """Every peak in a set of gaps, in order of length. Raises if the gaps came from columns.

    The guard is first on purpose. Measuring on snapped columns is silent when it happens and
    produces a plausible-looking plot with every peak split in two, which is the one failure this
    whole approach cannot survive.

    ``guard=False`` measures anyway. Only one caller sets it: a machine-perfect source produces the
    same signature honestly, and the API would rather show that plot with a warning attached than
    refuse to draw a piece for being too exact. Nothing inside the pipeline may set it.
    """
    values = np.asarray(values_ms, dtype=float)
    if guard:
        check_measured_on_raw_times(values, frame_ms)
    if values.size == 0:
        return []
    grid = density_grid(max_gap_ms, grid_step_ms)
    density = gaussian_kde(values, grid, bandwidth_ms)
    return find_peaks(
        values,
        grid,
        density,
        min_share=min_share,
        min_separation_ms=min_separation_ms,
    )
