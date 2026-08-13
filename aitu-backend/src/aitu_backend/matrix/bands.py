"""Where the line between two figures falls, when one of them is far more common than the other.

:func:`aitu_backend.matrix.ladder.nearest_figure` puts the line at the halfway point *by proportion*
— the geometric mean. With a corchea at 268 ms and a negra at 536 the line is 379 ms, and anything
longer is drawn as a negra.

That is the right line when the two figures are equally likely. It is the wrong one when they are
not. Measured on Chopin's Nocturne Op. 9 no. 1, the left hand plays 588 corcheas against 207 negras.
A gap landing between the two piles is therefore nearly three times more likely to be a corchea the
player leaned on than a negra they cut short, and the halfway line ignores that completely — which
is how a bass note held 397 ms, 18 ms over the line, reached the page as a negra where the printed
score has a corchea.

The rule
--------

Each figure takes a share of the space beside it in proportion to how tall its pile is::

    line between A and B  =  A * (B / A) ** ( pile A / (pile A + pile B) )

**With equal piles the exponent is one half and this is the geometric mean**, to the decimal. So
this is not a new rule, it is :func:`nearest_figure` with the fifty-fifty assumption removed, and a
passage whose piles happen to be even sees no change at all. That property is asserted in the tests
and should stay asserted: it is what makes the change safe to switch on for existing scores.

Worked in the smallest possible example — a corchea pile of 100 at 200 ms against a negra pile of 10
at 400 ms — the corchea claims 100/110 of the space and the line lands at 376 ms rather than 283.

Two things it deliberately does not do
--------------------------------------

**It does not iterate.** The piles are counted once, inside the halfway bands. Recounting inside the
new lines would be a ratchet: every pass moves gaps from the small pile to the big one, which makes
the big pile bigger, which moves the line further out. Measured on the same recording: one pass puts
the corchea/negra line at 447 ms, a second at 466, a third at the clamp.

**It does not run unclamped.** Without a limit a figure that occurs twice in a piece loses its whole
band to a loud neighbour and can never be printed again. :data:`SHARE_CLAMP` keeps every figure at
least a fifth of the room on each side. On this recording the clamp costs nothing where it matters —
the corchea/negra split is 73/27, inside the limit — and buys protection at the quiet end of the
ladder, where the corchea pile is fourteen times the semicorchea pile: the semicorchea/corchea line
stops at 154 ms instead of sliding to 144, and eleven more real semicorcheas survive in the right
hand.

The bands are built **per passage**, from the gaps of **both hands** pooled. Pooled because a
per-hand reading would print the same 400 ms as a corchea on one staff and a negra on the other,
which no reader would accept.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise

from aitu_backend.schemas.time_matrix import FigureLadder, FigureName

__all__ = ["SHARE_CLAMP", "FigureBands", "build_bands"]

#: How lopsided the split may get, as the share the *shorter* figure may claim.
#:
#: 0.5 is the halfway point, so ``(0.5, 0.5)`` reproduces :func:`nearest_figure` exactly. The
#: default lets the taller figure claim at most four fifths of the space beside it.
SHARE_CLAMP = (0.20, 0.80)


@dataclass(frozen=True)
class FigureBands:
    """The lines between the figures of one ladder, for one passage.

    Built once from that passage's own gaps and then asked about each gap in turn. This is why
    choosing a figure is no longer a pure function of a single length: it depends on what the rest
    of the passage looks like.
    """

    ladder: FigureLadder
    #: figure -> how many of the passage's gaps piled up on it, counted in the halfway bands
    height: dict[FigureName, int]
    #: the shorter figure of each adjacent pair -> the line above it, in milliseconds
    line: dict[FigureName, float] = field(default_factory=dict)
    #: the same pairs -> the share of the space the shorter figure took, after clamping
    share: dict[FigureName, float] = field(default_factory=dict)

    @property
    def order(self) -> list[FigureName]:
        """The vocabulary, shortest first. Includes the dotted figures, which sit between rungs."""
        return sorted(self.ladder.ms_by_figure, key=lambda name: self.ladder.ms_by_figure[name])

    def figure_of(self, gap_ms: float) -> FigureName:
        """Which figure a length of time is printed as under these lines."""
        names = self.order
        for name in names[:-1]:
            if gap_ms < self.line[name]:
                return name
        return names[-1]

    def fit(self, gap_ms: float) -> tuple[FigureName, float]:
        """The figure and ``abs(log2(gap / figure_ms))``, the same error :class:`FigureFit` reports.

        The error is still measured against the figure's own length, not against the line, so a note
        printed as a corchea because the piles moved the line still reports honestly how far from a
        corchea it actually was.
        """
        figure = self.figure_of(gap_ms)
        return figure, abs(math.log2(gap_ms / self.ladder.ms_by_figure[figure]))


def build_bands(
    gaps_ms: list[float],
    ladder: FigureLadder,
    *,
    clamp: tuple[float, float] = SHARE_CLAMP,
) -> FigureBands:
    """Count the piles in the halfway bands, then move each line in proportion to the two it parts.

    ``gaps_ms`` is every printed length in the passage, both hands. An empty list gives back the
    halfway lines, so a passage with no notes in it behaves exactly as it does today.
    """
    low, high = clamp
    if not 0.0 < low <= 0.5 <= high < 1.0:
        raise ValueError(f"The share clamp must straddle 0.5 and stay inside (0, 1), got {clamp}")

    names = sorted(ladder.ms_by_figure, key=lambda name: ladder.ms_by_figure[name])
    edges = [0.0]
    for shorter, longer in pairwise(names):
        edges.append(math.sqrt(ladder.ms_by_figure[shorter] * ladder.ms_by_figure[longer]))
    edges.append(math.inf)
    height = {
        name: sum(1 for gap in gaps_ms if edges[index] <= gap < edges[index + 1])
        for index, name in enumerate(names)
    }

    bands = FigureBands(ladder=ladder, height=height)
    for shorter, longer in pairwise(names):
        low_ms, high_ms = ladder.ms_by_figure[shorter], ladder.ms_by_figure[longer]
        total = height[shorter] + height[longer]
        share = 0.5 if total == 0 else height[shorter] / total
        share = min(high, max(low, share))
        bands.share[shorter] = share
        bands.line[shorter] = low_ms * (high_ms / low_ms) ** share
    return bands
