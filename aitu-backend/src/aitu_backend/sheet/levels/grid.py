"""The grid of the song (implementation 04-3, Phase 3, plan section 5.3): where a new note of a level may start.

The sheet has no compases, so a pattern of a level cannot be written as "beat 1, beat 2". A note that a level adds
(a bass note, then a chord) needs a time that matches the recording, or the cursor and the lit notes will not match
what the user hears. The grid gives those times, in frames of 40 ms:

* the **negras** and the **corcheas** of the song, from the beat tracker of the algorithm (``proposal.beat.track``:
  a dynamic programming over the onset columns that lets the tempo move slowly, pulled to a period). The tracker
  follows a steady pulse well and a pulse it hears only now and then badly: on 99 Red Balloons (reference figure
  600 ms) the tracker pulled to the negra wanders between 440 and 600 ms, while pulled to the corchea (300 ms) it
  stays steady and 95 % of the onsets fall on a point. So the pulse is tracked at both periods, and the one whose
  local tempo (fitted over every ``FIT_BEATS`` pulses) moves least is kept (:func:`song_grid`);
* the **division** of a negra: two corcheas, or three when the song is ternary (7 Years: 96 % of the onsets on a
  third of the negra, 68 % on a half); chosen by the share of onsets on the points;
* the **semicorcheas**, half a corchea;
* the **onsets** of the original notes, both hands: a level may always start a note where the recording has one.

A frame is on the grid when it is within ``TOLERANCE`` frames of a point (the points are rounded to frames, and a
recorded onset is not exactly on its pulse).
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field

import numpy as np

from aitu_backend.sheet.proposal import beat
from aitu_backend.sheet.sheet.data import FRAME_MS, Sheet

__all__ = ["FIT_BEATS", "TOLERANCE", "Grid", "song_grid"]

#: Frames: a frame this near a point of the grid is on it.
TOLERANCE = 1
#: Pulses per straight-line fit when the steadiness of a tracked pulse is measured.
FIT_BEATS = 16
#: How fine each kind of point is, in points per corchea.
STEPS = {"negra": 0, "corchea": 1, "semicorchea": 2}


@dataclass
class Grid:
    #: The frame (not rounded) of every corchea, from the first onset of the song to its last.
    corcheas: np.ndarray
    #: Corcheas per negra: 2, or 3 in a ternary song.
    division: int
    #: The index in ``corcheas`` of the first negra (the negras are every ``division`` corcheas from there).
    phase: int
    quarter_ms: float
    #: The frames of the original onsets (both hands), sorted.
    onsets: list[int] = field(default_factory=list)
    #: How the grid was found: the tracked period (ms), the local tempo spread, the share of onsets on points.
    info: dict = field(default_factory=dict)

    def _covering(self, start: float, end: float) -> tuple[np.ndarray, int]:
        """The corcheas, continued before the first one and after the last one with the gap of the nearest four
        (a pattern may go on after the last onset of the song), so that they cover ``[start, end)``; and the index
        of the first negra in them."""
        c = list(self.corcheas)
        phase = self.phase
        if len(c) < 2:
            return np.array(c), phase
        tail = float(np.median(np.diff(c[-5:])))
        while c[-1] < end + tail:
            c.append(c[-1] + tail)
        head = float(np.median(np.diff(c[:5])))
        while c[0] > start - head:
            c.insert(0, c[0] - head)
            phase += 1
        return np.array(c), phase % self.division

    def points(self, start: int, end: int, kind: str = "corchea") -> list[int]:
        """The frames of the grid in ``[start, end)``, rounded and sorted: ``kind`` "negra", "corchea" (also the
        negras) or "semicorchea" (also the corcheas)."""
        c, phase = self._covering(start, end)
        if kind == "negra":
            return [int(round(f)) for f in c[phase :: self.division] if start <= round(f) < end]
        split = 2 if kind == "semicorchea" else 1
        out: set[int] = set()
        for i in range(len(c)):
            if c[i] >= end or (i + 1 < len(c) and c[i + 1] < start - 1):
                continue
            nxt = c[i + 1] if i + 1 < len(c) else None
            for k in range(split if nxt is not None else 1):
                f = int(round(c[i] + (nxt - c[i]) * k / split)) if k else int(round(c[i]))
                if start <= f < end:
                    out.add(f)
        return sorted(out)

    def beat_of(self, frame: float) -> float:
        """The place of ``frame`` in negras from the first negra of the song (2.5 = half way between negras 2 and
        3); the grid goes on before the first negra and after the last one."""
        first = self.corcheas[self.phase] if len(self.corcheas) > self.phase else 0.0
        c, phase = self._covering(min(frame, first) - 1, frame + 1)
        b = c[phase :: self.division]
        if len(b) < 2:
            return (frame - (b[0] if len(b) else 0.0)) * FRAME_MS / self.quarter_ms
        zero = int(np.argmin(np.abs(b - first)))
        i = int(np.clip(np.searchsorted(b, frame, side="right") - 1, 0, len(b) - 2))
        return i - zero + (frame - b[i]) / (b[i + 1] - b[i])

    def kind_of(self, frame: int, tolerance: int = TOLERANCE) -> str | None:
        """The coarsest kind of point within ``tolerance`` of ``frame`` ("negra", "corchea", "semicorchea"), or
        "onset" for an original onset that is on no point, or ``None``."""
        for kind in ("negra", "corchea", "semicorchea"):
            if any(abs(p - frame) <= tolerance for p in self.points(frame - 30, frame + 30, kind)):
                return kind
        i = bisect_left(self.onsets, frame - tolerance)
        if i < len(self.onsets) and self.onsets[i] <= frame + tolerance:
            return "onset"
        return None

    def on_grid(self, frame: int, kind: str = "corchea", tolerance: int = TOLERANCE) -> bool:
        """True when ``frame`` is within ``tolerance`` of an original onset or of a point of ``kind`` or coarser."""
        found = self.kind_of(frame, tolerance)
        return found == "onset" or (found is not None and STEPS[found] <= STEPS[kind])

    def text(self, start: int, end: int) -> str:
        """The grid of ``[start, end)`` for a prompt: each negra, then its other corcheas in parentheses."""
        negras = self.points(start, end, "negra")
        corcheas = [f for f in self.points(start, end, "corchea") if f not in set(negras)]
        out = []
        for i, f in enumerate(negras):
            nxt = negras[i + 1] if i + 1 < len(negras) else end
            inner = [c for c in corcheas if f < c < nxt]
            out.append(f"f{f}" + (f" ({' '.join(f'f{c}' for c in inner)})" if inner else ""))
        first = [c for c in corcheas if negras and c < negras[0]]
        head = f"({' '.join(f'f{c}' for c in first)}) " if first else ""
        return head + " ".join(out)


def _track(cols: np.ndarray, midi: np.ndarray, period: float) -> tuple[np.ndarray, float]:
    """The pulse tracked at ``period`` (frames, not rounded) and its local tempo spread: the 90th over the 10th
    percentile of the pulse length fitted over every ``FIT_BEATS`` pulses (1.0 = no change)."""
    b = beat.track(cols, midi, period) / FRAME_MS
    if len(b) < 2 * FIT_BEATS:
        g = np.diff(b) if len(b) > 1 else np.array([1.0])
        return b, float(g.max() / max(g.min(), 1e-6))
    x = np.arange(FIT_BEATS)
    slopes = [np.polyfit(x, b[i : i + FIT_BEATS], 1)[0] for i in range(0, len(b) - FIT_BEATS, FIT_BEATS // 2)]
    return b, float(np.percentile(slopes, 90) / max(np.percentile(slopes, 10), 1e-6))


def _share(onsets: np.ndarray, pts: np.ndarray) -> float:
    """The share of ``onsets`` within ``TOLERANCE`` of a point of ``pts`` (rounded)."""
    if not len(onsets) or not len(pts):
        return 0.0
    r = np.round(pts)
    i = np.clip(np.searchsorted(r, onsets), 1, len(r) - 1)
    near = np.minimum(np.abs(onsets - r[i - 1]), np.abs(onsets - r[i]))
    return float(np.mean(near <= TOLERANCE))


def _split(b: np.ndarray, d: int) -> np.ndarray:
    """``d`` even points per gap of ``b`` (and the last point of ``b``)."""
    if len(b) < 2:
        return b.copy()
    parts = [b[i] + (b[i + 1] - b[i]) * k / d for i in range(len(b) - 1) for k in range(d)]
    return np.array(parts + [b[-1]])


def song_grid(sheet: Sheet, quarter_ms: float | None = None) -> Grid:
    """The grid of a frames sheet (both hands; ornament onsets left out). ``quarter_ms``: the reference figure of the
    sheet unless given."""
    q = float(quarter_ms or sheet.quarter_ms or 500.0)
    notes = [n for n in sheet.notes if not n.covered and n.frame is not None]
    if not notes:
        return Grid(corcheas=np.zeros(0), division=2, phase=0, quarter_ms=q)
    cols = np.array([n.frame for n in notes])
    midi = np.array([n.midi for n in notes])
    onsets = np.array(sorted({int(f) for f in cols}), dtype=float)
    negra, negra_spread = _track(cols, midi, q)
    half, half_spread = _track(cols, midi, q / 2)
    info = {"negra spread": round(negra_spread, 3), "corchea spread": round(half_spread, 3)}
    if half_spread < negra_spread:
        # the corchea is the steady pulse: the negras are every second corchea, on the side with more weight
        corcheas, division = half, 2
        weight = np.zeros(int(cols.max()) + 2)
        np.add.at(weight, cols, 1.0)
        on = [weight[np.clip(np.round(corcheas[p::2]).astype(int), 0, len(weight) - 1)].sum() for p in (0, 1)]
        phase = int(np.argmax(on))
        info["tracked"] = "corchea"
    else:
        shares = {d: _share(onsets, _split(negra, d)) for d in (2, 3)}
        division = 3 if shares[3] > shares[2] + 0.1 else 2
        corcheas, phase = _split(negra, division), 0
        info["tracked"] = "negra"
        info["division shares"] = {d: round(s, 3) for d, s in shares.items()}
    gaps = np.diff(corcheas) * FRAME_MS if len(corcheas) > 1 else np.array([q / 2])
    info["corchea ms"] = round(float(np.median(gaps)), 1)
    info["onsets on corcheas"] = round(_share(onsets, corcheas), 3)
    info["onsets on semicorcheas"] = round(_share(onsets, _split(corcheas, 2)), 3)
    return Grid(
        corcheas=corcheas,
        division=division,
        phase=phase,
        quarter_ms=q,
        onsets=[int(f) for f in onsets],
        info=info,
    )
