"""Music theory the algorithm needs (phase 3 rulebook, product core since phase 15): metric levels of a position,
ledger lines and the clef cost search, key-signature spelling.

Moved from the research modules ``patterns.beaming``, ``patterns.clefs`` and ``patterns.spelling`` (which import them
back), unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from aitu_backend.sheet.sheet.pitch import STEPS

__all__ = [
    "CLEF_LINES",
    "DEFAULT_CLEF",
    "LEVELS",
    "Meter",
    "OTHER_CLEF",
    "Params",
    "SHARP_ORDER",
    "STEP_PC",
    "candidates",
    "diatonic",
    "key_alter",
    "key_family",
    "key_spelling",
    "ledger_lines",
    "metric_level",
    "parse_meter",
    "predict",
    "spell",
    "step_dir",
    "tonic_pc",
]

# ------------------------------------------------------------------ meter and levels (patterns.beaming)

LEVELS = ["bar", "half", "beat", "sub", "sub2", "other"]


class Meter:
    """Bar length and beat of a time signature, in quarters.

    Compound meters (6, 9, 12 over 4, 8, 16, 32) have a dotted beat of three units. 3/8 and 3/16 are
    one dotted beat per bar (their sixteenths are beamed by the bar, the data shows it). The others
    have one beat per unit (2/2: a half note).
    """

    def __init__(self, num: int, den: int) -> None:
        self.num, self.den = num, den
        unit = Fraction(4, den)
        self.bar = num * unit
        self.compound = num in (3, 6, 9, 12) and den >= 8 or num in (6, 9, 12) and den == 4
        self.beat = 3 * unit if self.compound else unit
        self.nbeats = int(self.bar / self.beat) if self.beat else 0
        self.sub = self.beat / 3 if self.compound else self.beat / 2

    def __repr__(self) -> str:
        return f"Meter({self.num}/{self.den})"


def parse_meter(text: str | None) -> Meter | None:
    try:
        num, den = (int(x) for x in str(text).split("/"))
    except ValueError:
        return None
    return Meter(num, den) if num > 0 and den > 0 else None


def metric_level(pos: Fraction, meter: Meter) -> str:
    """Strongest metric level of a position in the bar: bar, half (half bar), beat, sub, sub2, other."""
    pos = Fraction(pos) % meter.bar if meter.bar else Fraction(pos)
    if pos == 0:
        return "bar"
    if meter.nbeats >= 4 and meter.nbeats % 2 == 0 and pos == meter.bar / 2:
        return "half"
    if pos % meter.beat == 0:
        return "beat"
    if pos % meter.sub == 0:
        return "sub"
    if pos % (meter.sub / 2) == 0:
        return "sub2"
    return "other"


# ------------------------------------------------------------------ clefs (patterns.clefs)

DEFAULT_CLEF = {1: "G2", 2: "F4"}
OTHER_CLEF = {1: "F4", 2: "G2"}
# Diatonic index (octave * 7 + step) of the bottom and top line of each clef.
CLEF_LINES = {"G2": (4 * 7 + 2, 5 * 7 + 3), "F4": (2 * 7 + 4, 3 * 7 + 5)}  # E4..F5, G2..A3


def diatonic(step: str, octave: int) -> int:
    return int(octave) * 7 + STEPS.index(step)


def ledger_lines(d: int | np.ndarray, clef: str) -> int | np.ndarray:
    """Ledger lines needed by a note at diatonic index ``d`` on a staff with ``clef``."""
    low, high = CLEF_LINES[clef]
    return np.maximum(0, (low - d) // 2) + np.maximum(0, (d - high) // 2)


@dataclass(frozen=True)
class Params:
    switch: float  # cost of one clef change, in ledger lines
    stay: int  # minimum number of onset slices between two changes
    agg: str  # "max" or "sum": cost of a slice from the ledger lines of its notes
    where: str = "any"  # where a change may go: any slice, "bar" (first slice of a measure),
    # "beat" (a slice on a beat), "group" (not inside a beam group: needs the beams)


def predict(
    cost: np.ndarray, staff: int, p: Params, allowed: np.ndarray | None = None
) -> np.ndarray:
    """Clef per slice (0 = usual clef of the staff, 1 = the other clef).

    ``cost`` is (slices, 2): the slice cost in the usual and in the other clef. States are
    (clef, slices since the last change, capped at ``m = stay``); a change costs ``switch`` and needs
    the cap. Starting in the other clef also costs ``switch``. ``allowed`` marks the slices where a
    change may happen (all when ``None``).
    """
    n, m = len(cost), max(1, p.stay)
    best = np.full((2, m), np.inf)
    best[0, m - 1] = cost[0, 0]
    best[1, 0] = p.switch + cost[0, 1]
    # back[i, c, k] = previous k when staying (>= 0), or -1 when the slice i changed into clef c
    back = np.zeros((n, 2, m), dtype=np.int16)
    for i in range(1, n):
        new = np.full((2, m), np.inf)
        bk = np.zeros((2, m), dtype=np.int16)
        if m > 1:
            new[:, 1:] = best[:, :-1]
            bk[:, 1:] = np.arange(m - 1)
            hold = best[:, m - 1] < new[:, m - 1]
            new[hold, m - 1] = best[hold, m - 1]
            bk[hold, m - 1] = m - 1
        else:
            new[:, 0] = best[:, 0]
        if allowed is None or allowed[i]:
            change = best[::-1, m - 1] + p.switch  # into clef c from the other clef at the cap
            better = change < new[:, 0]
            new[better, 0] = change[better]
            bk[better, 0] = -1
        best = new + cost[i][:, None]
        back[i] = bk
    c, k = (int(x) for x in np.unravel_index(np.argmin(best), best.shape))
    out = np.zeros(n, dtype=np.int8)
    for i in range(n - 1, -1, -1):
        out[i] = c
        if i:
            prev = int(back[i, c, k])
            c, k = (1 - c, m - 1) if prev < 0 else (c, prev)
    return out


# ------------------------------------------------------------------ spelling (patterns.spelling)

STEP_PC = np.array([0, 2, 4, 5, 7, 9, 11])
SHARP_ORDER = "FCGDAEB"


def key_alter(fifths: int, step: str) -> int:
    """Alteration that the key signature gives to a step."""
    if fifths > 0:
        return int(step in SHARP_ORDER[:fifths])
    if fifths < 0:
        return -int(step in SHARP_ORDER[::-1][:-fifths])
    return 0


def tonic_pc(fifths: int) -> int:
    """Pitch class of the major tonic of a key signature."""
    return (7 * fifths) % 12


def key_spelling(fifths: int) -> dict[int, tuple[int, int]]:
    """Diatonic pitch class -> (step index, alter) in the key signature."""
    out = {}
    for i, step in enumerate(STEPS):
        alter = key_alter(fifths, step)
        out[(STEP_PC[i] + alter) % 12] = (i, alter)
    return out


def candidates(pc: int, fifths: int) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """For a non-diatonic pitch class: (lower diatonic note raised, upper diatonic note lowered)."""
    sp = key_spelling(fifths)
    if pc in sp:
        return None
    lo, hi = sp[(pc - 1) % 12], sp[(pc + 1) % 12]
    return (lo[0], lo[1] + 1), (hi[0], hi[1] - 1)


def key_family(pc: int, fifths: int) -> tuple[int, int]:
    """vexflow-v2: white keys natural, black keys sharp (C and sharp keys) or flat (flat keys)."""
    if pc in (0, 2, 4, 5, 7, 9, 11):
        return int(np.flatnonzero(STEP_PC == pc)[0]), 0
    if fifths >= 0:
        return int(np.flatnonzero(STEP_PC == pc - 1)[0]), 1
    return int(np.flatnonzero(STEP_PC == (pc + 1) % 12)[0]), -1


def spell(pc: int, fifths: int, raise_: bool | None) -> tuple[int, int]:
    """Spelling of a pitch class in a key: the key's own spelling when diatonic; otherwise the raised
    lower note (``raise_``), the lowered upper note (not ``raise_``), or the key family (``None``).
    """
    cand = candidates(pc, fifths)
    if cand is None:
        return key_spelling(fifths)[pc]
    if raise_ is None:
        raise_ = fifths >= 0
    return cand[0] if raise_ else cand[1]


def step_dir(next_int: float, prev_int: float) -> str:
    """Melodic direction around a note: by step (≤ 2 semitones) to the next note, else from the previous."""
    if not np.isnan(next_int) and 0 < abs(next_int) <= 2:
        return "up" if next_int > 0 else "down"
    if not np.isnan(prev_int) and 0 < abs(prev_int) <= 2:
        return "from_below" if prev_int > 0 else "from_above"
    return "other"
