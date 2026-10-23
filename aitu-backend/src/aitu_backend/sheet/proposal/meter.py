"""Meter and downbeat of a matrix, once the quarter is known (phase 6).

For a candidate meter the bar period is ``B`` ms (``bar quarters * quarter``). Put the onsets on a circle of
length ``B``: bass notes and chords gather at the downbeat, so the mean vector of the bass and chord onsets is
long, and its angle gives the phase of the downbeat. Candidates are scored with these lengths (also at the
beat and half-bar periods) and a prior per meter, learnt on train as a conditional logit model (as
``proposal.beat``). The downbeat is the angle of the best candidate, moved to the nearest beat of the
quarter grid.

Meters with the same bar and the same beat (4/4 and 2/2) are one class here (``4/4``): the onsets cannot tell
them apart, and they beam eighths the same way (4 per half bar).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import numpy as np

from aitu_backend.sheet.proposal.beat import BASS_MIDI, FRAME_MS, onset_columns

__all__ = ["METERS", "MeterGuess", "candidates", "estimate", "true_meter"]

# meter -> (bar in quarters, beat in quarters)
METERS = {
    "2/4": (2, 1),
    "3/4": (3, 1),
    "4/4": (4, 1),
    "3/8": (1.5, 1.5),
    "6/8": (3, 1.5),
    "9/8": (4.5, 1.5),
    "12/8": (6, 1.5),
    "3/2": (6, 2),
    "6/4": (6, 3),
}
CLASS_OF = {"2/2": "4/4", "4/2": "4/4", "C": "4/4", "2/8": "2/4", "4/8": "2/4"}
WEIGHTS = Path(__file__).with_name("meter_weights.json")


@dataclass
class MeterGuess:
    meter: str
    phase_ms: float  # time of a downbeat, in [0, bar ms)
    prob: float


def _vec(t: np.ndarray, w: np.ndarray, period: float) -> complex:
    if not len(t) or w.sum() == 0:
        return 0j
    return complex(np.exp(2j * np.pi * t / period) @ w / w.sum())


def grid_phase(t: np.ndarray, w: np.ndarray, period: float, *, tol: float = 30.0) -> float:
    """The offset of a grid of ``period`` that holds the most onset weight within ``tol`` ms (a circular
    mean would be pulled by off-beat notes, e.g. a dotted eighth + sixteenth pattern)."""
    if not len(t):
        return 0.0
    grid = np.arange(0.0, period, 5.0)
    d = np.abs((t[None, :] - grid[:, None] + period / 2) % period - period / 2)
    score = (np.clip(1 - d / tol, 0, None) * w[None, :]).sum(1)
    return float(grid[int(np.argmax(score))])


def candidates(
    cols: np.ndarray, midi: np.ndarray, quarter_ms: float, frame_ms: float = FRAME_MS
) -> list[tuple[str, float, np.ndarray]]:
    """(meter, downbeat phase in ms, features) for each meter."""
    u, count, low = onset_columns(cols, midi)
    t = u * frame_ms
    bass = low < BASS_MIDI
    sets = {
        "all": (t, np.log1p(count)),
        "bass": (t[bass], np.ones(bass.sum())),
        "chord": (t[count >= 3], np.ones((count >= 3).sum())),
    }
    accent = 1.0 + 2.0 * bass + (count >= 3)  # weight of an onset as a downbeat
    tol = min(30.0, quarter_ms / 6)
    eighth_phase = grid_phase(t, np.log1p(count) + bass, quarter_ms / 2, tol=tol)
    quarter_phase = grid_phase(t, np.log1p(count) + bass, quarter_ms, tol=tol)
    out = []
    for meter, (bar_q, beat_q) in METERS.items():
        bar, beat = bar_q * quarter_ms, beat_q * quarter_ms
        x = []
        for name, (tt, ww) in sets.items():
            x.append(np.log(abs(_vec(tt, ww, bar)) + 1e-3))
            x.append(np.log(abs(_vec(tt, ww, beat)) + 1e-3))
            half = bar / 2 if bar_q / beat_q % 2 == 0 else bar
            x.append(np.log(abs(_vec(tt, ww, half)) + 1e-3))
        # downbeat: the beat position of the bar (on the quarter grid, or the eighth grid in compound
        # meters) where the accented onsets gather
        step, base = (
            (quarter_ms, quarter_phase) if beat_q == int(beat_q) else (quarter_ms / 2, eighth_phase)
        )
        n = int(round(bar / step))
        sal = []
        for j in range(n):
            ph = (base + j * step) % bar
            d = np.abs((t - ph + bar / 2) % bar - bar / 2)
            sal.append(float((np.clip(1 - d / tol, 0, None) * accent).sum()))
        sal = np.asarray(sal)
        j = int(np.argmax(sal))
        phase = (base + j * step) % bar
        x.append(np.log((sal[j] + 1) / (sal.mean() + 1)))
        x += [float(m == meter) for m in METERS]
        out.append((meter, float(phase), np.asarray(x)))
    return out


def true_meter(bars: list[tuple[Fraction, Fraction, str]], quarter_ms: float) -> tuple[str, float]:
    """The meter of most bars (class) and the downbeat phase in ms of its full bars."""
    from collections import Counter

    full = [(on, d, CLASS_OF.get(m, m)) for on, d, m in bars]
    meter = Counter(m for _, _, m in full).most_common(1)[0][0]
    if meter not in METERS:
        return meter, 0.0
    bar_q = METERS[meter][0]
    ons = [float(on) for on, d, m in full if m == meter and abs(float(d) - bar_q) < 1e-6]
    if not ons:
        return meter, 0.0
    bar = bar_q * quarter_ms
    ph = Counter(round((o * quarter_ms) % bar, 1) for o in ons).most_common(1)[0][0]
    return meter, float(ph)


def estimate(
    cols: np.ndarray,
    midi: np.ndarray,
    quarter_ms: float,
    *,
    weights: np.ndarray | None = None,
    frame_ms: float = FRAME_MS,
) -> list[MeterGuess]:
    w = np.asarray(json.loads(WEIGHTS.read_text())["weights"]) if weights is None else weights
    cs = candidates(cols, midi, quarter_ms, frame_ms)
    s = np.array([w[0] + x @ w[1:] for _, _, x in cs])
    p = np.exp(s - s.max())
    p /= p.sum()
    return sorted(
        (MeterGuess(m, ph, float(pi)) for (m, ph, _), pi in zip(cs, p)), key=lambda g: -g.prob
    )
