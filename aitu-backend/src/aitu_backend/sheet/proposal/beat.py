"""The figure scale of a matrix: how long is a quarter note, in milliseconds (phase 6).

The matrix has no tempo and no bars. Today's default ladder takes the most common gap as the negra, which is
wrong in 92 % of the movements (phase 5): the most common gap is usually an eighth, a sixteenth or a triplet
note. Here the quarter is chosen among the periods where the onsets repeat:

1. **Pulse strength.** For a period ``P`` the onset columns are put on a circle of length ``P``; the
   length of their mean vector (``|sum w * exp(2 pi i t / P)| / sum w``) is 1 when every onset falls on the
   pulse and near 0 when they are spread. It is computed for all onsets (weight = log of the notes started)
   and for bass onsets only (the lowest note of the column below MIDI 55).
2. **Candidates.** The peaks of this curve between 150 ms and 2.6 s, and 2/3 of each peak (in 6/8 the
   quarter is not a pulse: the dotted quarter and the eighth are).
3. **Choice.** A linear score of each candidate (the pulse strength at the candidate and at its halves,
   thirds, doubles and triples, and a prior on the tempo) learnt on the train split as a conditional logit
   model; the candidate with the highest score is the quarter.

Only columns and pitches are used: the same information as the F1-frames view the LLM reads (no note
lengths, no hands).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

__all__ = ["Candidate", "candidate_set", "estimate", "features", "load_weights", "pulse", "track"]

FRAME_MS = 40.0
LOW = 150.0
HIGH = 2600.0
GRID = np.exp(np.linspace(np.log(80.0), np.log(8000.0), 1600))
BASS_MIDI = 55
PRIOR_MS = 60000.0 / 116.0  # median written quarter on train: 116 quarters per minute
WEIGHTS = Path(__file__).with_name("beat_weights.json")


@dataclass
class Candidate:
    ms: float
    x: np.ndarray  # features (FEATURES)


def onset_columns(cols: np.ndarray, midi: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Unique onset columns, the number of notes started at each, and the lowest MIDI pitch."""
    order = np.argsort(cols, kind="stable")
    cols, midi = np.asarray(cols)[order], np.asarray(midi)[order]
    u, start, count = np.unique(cols, return_index=True, return_counts=True)
    low = np.minimum.reduceat(midi, start) if len(u) else np.array([])
    return u, count, low


def pulse(times_ms: np.ndarray, w: np.ndarray, periods: np.ndarray) -> np.ndarray:
    """Mean vector length of the onsets on circles of each period (1 = every onset on the pulse)."""
    if not len(times_ms) or w.sum() == 0:
        return np.zeros(len(periods))
    out = np.empty(len(periods))
    for i in range(0, len(periods), 200):  # chunks keep the matrix small on long pieces
        ph = np.exp(2j * np.pi * times_ms[None, :] / periods[i : i + 200, None])
        out[i : i + 200] = np.abs(ph @ w) / w.sum()
    return out


class Curves:
    """Pulse strength of three onset sets, read at any period by interpolation: all onsets (weight = log
    of the notes started), bass onsets (lowest note below MIDI 55) and chord onsets (3 notes or more).
    """

    def __init__(self, cols: np.ndarray, midi: np.ndarray, frame_ms: float = FRAME_MS):
        u, count, low = onset_columns(cols, midi)
        t = u * frame_ms
        self.n_all = len(t)
        self.span_ms = float(t.max() - t.min()) + frame_ms if len(t) else frame_ms
        self.curves = {"all": pulse(t, np.log1p(count), GRID)}
        for name, sel in (("bass", low < BASS_MIDI), ("chord", count >= 3)):
            ok = sel.sum() >= 4
            self.curves[name] = (
                pulse(t[sel], np.ones(sel.sum()), GRID) if ok else np.zeros(len(GRID))
            )

    def at(self, curve: str, ms: float) -> float:
        return float(np.interp(np.log(ms), np.log(GRID), self.curves[curve]))

    def tatum(self, share: float = 0.8) -> float:
        """The finest grid that holds the onsets: the longest period up to 700 ms whose pulse strength is at
        least ``share`` of the best one (every divisor of the tatum is as strong as the tatum)."""
        c = self.curves["all"]
        inside = (GRID >= 60) & (GRID <= 700)
        best = c[inside].max()
        ok = np.where(inside & (c >= share * best))[0]
        return float(GRID[ok.max()]) if len(ok) else 250.0


MULTIPLES = (1, 2, 3, 4, 6, 8, 12, 16)


def features(cv: Curves, ms: float, tatum: float, peak: bool) -> np.ndarray:
    eps = 1e-3
    lg = lambda curve, m: np.log(cv.at(curve, m) + eps)  # noqa: E731
    z = np.log2(ms / PRIOR_MS)
    m = ms / tatum
    near = [float(abs(np.log(m / k)) < 0.04) for k in MULTIPLES]
    per_q = np.log(cv.n_all * ms / cv.span_ms + eps)  # onset columns per candidate quarter
    return np.array(
        [
            lg("all", ms),
            lg("all", ms / 2),
            lg("all", ms / 3),
            lg("all", ms / 4),
            lg("bass", ms),
            lg("bass", 2 * ms),
            lg("bass", 3 * ms),
            lg("bass", 4 * ms),
            lg("chord", ms),
            lg("chord", 2 * ms),
            lg("chord", 3 * ms),
            lg("chord", 4 * ms),
            z,
            z * z,
            per_q,
            per_q * per_q,
            float(peak),
            *near,
        ]
    )


FEATURES = (
    "all",
    "all/2",
    "all/3",
    "all/4",
    "bass",
    "bass*2",
    "bass*3",
    "bass*4",
    "chord",
    "chord*2",
    "chord*3",
    "chord*4",
    "z",
    "z2",
    "per_q",
    "per_q2",
    "peak",
    *(f"m={k}" for k in MULTIPLES),
)


def peaks(cv: Curves) -> list[float]:
    """Peaks of the pulse curves: highest point within +-6 % of period and above the noise floor."""
    out: list[float] = []
    half = int(round(np.log(1.06) / np.log(GRID[1] / GRID[0])))
    floor = max(0.05, 3.0 / np.sqrt(max(cv.n_all, 1)))
    for c in cv.curves.values():
        for i in range(half, len(GRID) - half):
            if c[i] > floor and c[i] == c[i - half : i + half + 1].max():
                out.append(float(GRID[i]))
    return out


def candidate_set(
    cols: np.ndarray, midi: np.ndarray, frame_ms: float = FRAME_MS
) -> list[Candidate]:
    """Multiples of the tatum and the peaks of the pulse curves (and 2/3 of them), 150 ms to 2.6 s."""
    cv = Curves(cols, midi, frame_ms)
    t = cv.tatum()
    pk = peaks(cv)
    raw = (
        [(t * k, False) for k in MULTIPLES]
        + [(p, True) for p in pk]
        + [(p * 2 / 3, True) for p in pk]
    )
    raw = sorted((p, f) for p, f in raw if LOW <= p <= HIGH)
    merged: list[tuple[float, bool]] = []
    for p, f in raw:  # one candidate per 3 % of period; the tatum multiple wins over a peak
        if merged and p / merged[-1][0] <= 1.03:
            if not f and merged[-1][1]:
                merged[-1] = (p, True)
            continue
        merged.append((p, f))
    return [Candidate(ms=p, x=features(cv, p, t, f)) for p, f in merged]


def load_weights(path: Path = WEIGHTS) -> np.ndarray:
    return np.asarray(json.loads(path.read_text())["weights"])


def estimate(
    cols: np.ndarray,
    midi: np.ndarray,
    *,
    weights: np.ndarray | None = None,
    frame_ms: float = FRAME_MS,
    top: int = 1,
) -> list[tuple[float, float]]:
    """The quarter in ms (best first) with its probability among the candidates."""
    w = load_weights() if weights is None else weights
    cands = candidate_set(cols, midi, frame_ms)
    if not cands:
        return [(PRIOR_MS, 0.0)]
    s = np.array([w[0] + c.x @ w[1:] for c in cands])
    p = np.exp(s - s.max())
    p /= p.sum()
    order = np.argsort(-p)
    return [(cands[i].ms, float(p[i])) for i in order[:top]]


def track(
    cols: np.ndarray,
    midi: np.ndarray,
    quarter_ms: float,
    *,
    frame_ms: float = FRAME_MS,
    change: float = 30.0,
    pull: float = 2.0,
) -> np.ndarray:
    """Quarter-note beat times (ms) for a matrix whose tempo moves (a real performance), by dynamic programming over
    (beat column, gap to the previous beat): a beat on a strong onset is rewarded (log of the notes started, +1 for
    a bass onset); a gap that differs from the previous gap costs ``change * log(ratio)^2`` (the tempo moves
    slowly) and a gap that differs from ``quarter_ms`` costs ``pull * log(ratio)^2`` (it stays near the estimate).
    Beats cover the first to the last onset; columns between beats are interpolated by the caller.
    """
    u, count, low = onset_columns(cols, midi)
    if not len(u):
        return np.array([0.0])
    n = int(u.max()) + 2
    o = np.zeros(n)
    o[u] = np.log1p(count) + (low < BASS_MIDI)
    tau = quarter_ms / frame_ms
    gaps = np.arange(max(1, int(np.floor(tau * 0.6))), int(np.ceil(tau * 1.6)) + 1)
    g = len(gaps)
    trans = -change * np.log(gaps[None, :] / gaps[:, None]) ** 2  # [old gap, new gap]
    prior = -pull * np.log(gaps / tau) ** 2
    S = np.full((n, g), -np.inf)  # best score of a beat at t whose previous beat is t - gaps[j]
    B = np.full((n, g), -1, dtype=int)  # index of the previous beat's gap
    start = int(u.min())
    for t in range(start, n):
        for j, d in enumerate(gaps):
            p = t - d
            if p < start:
                continue
            if p == start or np.isneginf(S[p]).all():
                base, arg = 0.0, -1
                if p != start and o[p] == 0:
                    continue
            else:
                cand = S[p] + trans[:, j]
                arg = int(np.argmax(cand))
                base = cand[arg]
                if np.isneginf(base):
                    continue
            S[t, j] = base + o[t] + prior[j] + (o[p] if arg == -1 else 0.0)
            B[t, j] = arg
    tail = range(max(start, n - int(np.ceil(tau * 1.6))), n)
    t, j = max(((t, j) for t in tail for j in range(g)), key=lambda tj: S[tj])
    beats = [t]
    while j >= 0:
        p = t - gaps[j]
        beats.append(p)
        t, j = p, B[t, j]
    beats = np.asarray(beats[::-1], dtype=float)
    period = float(np.median(np.diff(beats[-4:]))) if len(beats) > 1 else tau
    while beats[-1] < u.max():
        beats = np.append(beats, beats[-1] + period)
    return beats * frame_ms
