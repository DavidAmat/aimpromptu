"""Figures of the new sheet: the nearest plain figure to a length (implementation 03, Phase 2).

The new sheet has no puntillos, no tuplets and no beat (plan section 3.1): a figure is one of the seven plain
figures, chosen from a length in milliseconds and the **reference figure** (the length of one negra,
``quarter_ms``). The thresholds are the user's (plan section 3.3):

* from the negra up, the middle point between two figures (negra 200 ms, blanca 400 ms: 300 ms is a negra,
  310 ms a blanca);
* for the corchea and shorter (the pairs corchea-negra, semicorchea-corchea, ...), a point ``SPLIT`` of the way
  from the shorter figure to the longer one. Phase 2 measured 0.5 to 0.8 on the 10 viewer songs and took 0.7
  (corchea 100 ms, semicorchea 50 ms: 90 ms is a corchea, 75 ms a semicorchea).

Figures are written as in F1: 1 redonda, 2 blanca, 4 negra, 8 corchea, 16 semicorchea, 32 fusa, 64 semifusa.
"""

from __future__ import annotations

__all__ = ["FIGURES", "NAMES", "SPLIT", "figure_of_ms", "nominal_ms", "steps"]

FIGURES = (1, 2, 4, 8, 16, 32, 64)
NAMES = {
    1: "redonda",
    2: "blanca",
    4: "negra",
    8: "corchea",
    16: "semicorchea",
    32: "fusa",
    64: "semifusa",
}
SPLIT = 0.7


def nominal_ms(figure: int, quarter_ms: float) -> float:
    """The length of a figure when the negra lasts ``quarter_ms``."""
    return quarter_ms * 4 / figure


def figure_of_ms(ms: float, quarter_ms: float, split: float = SPLIT) -> int:
    """The plain figure of a length: middle points from the negra up, ``split`` for the corchea and shorter."""
    for longer in FIGURES[:-1]:
        shorter = 2 * longer
        part = 0.5 if shorter <= 4 else split
        if ms > nominal_ms(shorter, quarter_ms) * (1 + part):
            return longer
    return FIGURES[-1]


def steps(shorter: int, longer: int) -> int:
    """How many figures apart two figures are (fusa 32 and corchea 8: 2 steps)."""
    return (shorter // longer).bit_length() - 1 if shorter >= longer else -steps(longer, shorter)
