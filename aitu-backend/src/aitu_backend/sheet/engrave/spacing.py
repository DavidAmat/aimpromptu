"""The spacing model of the engine (rulebook ``space.1``-``space.6``), fitted on real engravings.

The gap after an onset column depends on the time to the next onset column in either hand (IOI):
``gap = base * f(IOI)``, ``f(16th) = 1``; from the 16th up ``f`` is a power law (×1.30 per doubling in
phase 3), below the 16th the gap flattens to a floor. A printed accidental before the next column adds
a fixed amount, and the gap is never smaller than what the glyphs need. Lines are filled with whole
measures and justified by adding the same amount to every gap (``space.6``).

The numbers are a frozen file (``spacing_model.json``); the research package refits them
(``aitu_research.engrave.spacing.fit``).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

__all__ = ["SpacingModel", "load", "MODEL_PATH"]

MODEL_PATH = Path(__file__).with_name("spacing_model.json")


@dataclass
class SpacingModel:
    alpha: float = 0.38  # power from the 16th up (ratio per doubling = 2 ** alpha)
    alpha_low: float = 0.32  # power below the 16th (flatter: the floor)
    floor: float = 0.78  # lowest f (relative to the 16th)
    accidental: float = 0.26  # extra staff spaces before a column with a printed accidental
    lead: float = 1.6  # barline -> centre of the first notehead (staff spaces), at natural width
    to_barline: float = (
        1.0  # f of the last column -> barline relative to a column gap of the same IOI
    )
    rest: float = 0.92  # a rest column's gap relative to a note column of the same IOI
    base: float = (
        2.0  # natural gap of a 16th IOI (staff spaces) before justification: 4.9 measures per line
    )
    # at the scan line widths against 4.8 printed (E09 density table)
    clearance: float = 0.3  # minimum paper between two glyphs of neighbouring columns
    table: dict[str, float] | None = (
        None  # measured f per IOI (quarters, as text) with 30+ clean gaps
    )
    source: str = "phase 3 defaults"

    def f(self, ioi: float) -> float:
        """Duration factor of an IOI in quarters (f(1/4) = 1): the measured value of the common IOIs,
        log-log interpolation between them, the power law beyond the longest, the floor below."""
        if ioi <= 0:
            return self.floor
        if self.table:
            pts = sorted((float(k), v) for k, v in self.table.items())
            if ioi <= pts[0][0]:
                return pts[0][1]
            if ioi >= pts[-1][0]:
                return pts[-1][1] * (ioi / pts[-1][0]) ** self.alpha
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                if x0 <= ioi <= x1:
                    w = math.log2(ioi / x0) / math.log2(x1 / x0)
                    return y0 * (y1 / y0) ** w
        r = math.log2(ioi / 0.25)
        v = 2 ** (self.alpha * r) if r >= 0 else 2 ** (self.alpha_low * r)
        return max(self.floor, v)

    def gap(self, ioi: float) -> float:
        return self.base * self.f(ioi)


def load(path: Path = MODEL_PATH) -> SpacingModel:
    if path.exists():
        return SpacingModel(**json.loads(path.read_text()))
    return SpacingModel()
