"""The figure ladder: naming one peak fixes every figure, by proportion.

The user looks at the plot of gaps, points at one pile and says what it is. "That 337 ms peak is the
negra." Everything else follows: a negra of 337 ms makes a corchea 168.5, a semicorchea 84.25, a
blanca 674, and so on down and up the closed vocabulary. The app never picks the anchor (D-09), and
it shows the consequence of the choice immediately so the user can judge it before committing
(D-10).

A figure is now only a label. Getting one wrong moves nothing on the page, because the column is the
same width either way. That is why re-pointing the whole ladder (D-18) and overriding a single note
(D-17) are ordinary features rather than escape hatches.

Two rules from the decisions shape the code here:

* **The vocabulary is closed** (D-12). Nine figures, with dots on `blanca` and `negra` only. With
  the dotted corchea banned, both halves of a swung pair land on `corchea`, which is what the
  printed sheet shows. Allowing the dot pulls the long half to a dotted corchea and recreates the
  ragged mix the refactor exists to remove.
* **Nearest is by proportion, not by milliseconds** (D-11). With the negra at 320 ms, a gap of
  120 ms is exactly 40 ms away from both 160 and 80, so an absolute comparison is a coin toss. In
  proportional terms it is 25 % against 50 % and the corchea wins cleanly, every time.

P3.2 owns figure selection for printed notes. It should **import** :func:`nearest_figure` from here
rather than write the comparison again: two implementations of D-11 that disagree is exactly the
class of bug this refactor removes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from aitu_backend.matrix.peaks import Peak
from aitu_backend.notation.tuplets import TRIPLET_PARENTS
from aitu_backend.schemas.time_matrix import FIGURE_NEGRAS, FigureLadder, FigureName

__all__ = [
    "FigureFit",
    "PeakLabel",
    "bpm_of",
    "build_ladder",
    "header_label",
    "label_peaks",
    "nearest_figure",
    "shift_ladder",
]


@dataclass
class FigureFit:
    """Which figure a length of time is closest to, and how far off it is."""

    figure: FigureName
    #: What the ladder says that figure lasts, in milliseconds.
    figure_ms: float
    #: ``abs(log2(gap / figure_ms))``. Zero is exact; 1.0 means out by a factor of two.
    fit_error: float

    @property
    def percent_off(self) -> float:
        """The same error as a percentage of the figure, which reads more easily in the UI."""
        return abs(2.0**self.fit_error - 1.0) * 100.0


@dataclass
class PeakLabel:
    """What one detected peak becomes under a proposed ladder."""

    peak: Peak
    fit: FigureFit
    #: Set when the pile sits a third of the way into a figure, so it is a tresillo rather than a
    #: badly fitting ordinary figure. ``fit`` then names the figure the three notes are printed as.
    tresillo_of: FigureName | None = None

    @property
    def name(self) -> str:
        """What to write next to the pile, in the words a reader uses.

        Spelled out rather than sent as the enum value, because ``dottedNegra`` is a field name and
        "negra con puntillo" is what the figure is called.
        """
        spelled = _SPELLED.get(self.fit.figure, self.fit.figure.value)
        if self.tresillo_of is None:
            return spelled
        return f"{spelled} de tresillo"


#: The figures whose enum value is not the name a musician uses for them.
_SPELLED: dict[FigureName, str] = {
    FigureName.DOTTED_BLANCA: "blanca con puntillo",
    FigureName.DOTTED_NEGRA: "negra con puntillo",
}


def build_ladder(anchor_figure: FigureName, anchor_ms: float) -> FigureLadder:
    """Every figure's length in milliseconds, from the one figure the user named (D-10).

    The ladder is complete: all nine values are computed here and sent to the renderer, so nothing
    downstream re-derives one and the two sides cannot disagree.
    """
    if anchor_ms <= 0 or not math.isfinite(anchor_ms):
        raise ValueError(f"A figure must last a positive number of ms, got {anchor_ms}")
    figure = FigureName(anchor_figure)
    per_negra = anchor_ms / FIGURE_NEGRAS[figure]
    return FigureLadder(
        anchor_figure=figure,
        anchor_ms=float(anchor_ms),
        ms_by_figure={name: per_negra * negras for name, negras in FIGURE_NEGRAS.items()},
    )


def nearest_figure(gap_ms: float, ladder: FigureLadder) -> FigureFit:
    """The figure a length of time is closest to, compared by proportion (D-11).

    Minimising ``abs(log2(gap / candidate))`` asks "which figure is this the smallest multiple away
    from", which is how a listener hears it. Minimising the difference in milliseconds asks a
    question about the clock, and gives a coin toss whenever a gap sits between two figures.
    """
    if gap_ms <= 0 or not math.isfinite(gap_ms):
        raise ValueError(f"A gap must be a positive number of ms, got {gap_ms}")
    best: FigureFit | None = None
    for figure, figure_ms in ladder.ms_by_figure.items():
        error = abs(math.log2(gap_ms / figure_ms))
        if best is None or error < best.fit_error:
            best = FigureFit(figure=figure, figure_ms=figure_ms, fit_error=error)
    assert best is not None  # a ladder always carries all nine figures
    return best


def label_peaks(peaks: list[Peak], ladder: FigureLadder) -> list[PeakLabel]:
    """What every detected peak becomes under this ladder, so the user can judge the choice.

    This is the live preview behind the click-a-peak dialog. A ladder that turns the dominant peak
    into a negra but everything else into badly fitting figures is visibly wrong before it is saved.

    A pile sitting a third of the way into a figure is named as a **tresillo** rather than forced
    onto the nearest ordinary figure. With the negra at 300 ms a pile at 100 is 33 % away from a
    corchea and 33 % from a semicorchea, so calling it either is misleading; calling it a third of a
    negra says exactly what it is. See :mod:`aitu_backend.notation.tuplets` for the rule that decides
    whether the playing really is a tresillo.
    """
    return [_label(peak, ladder) for peak in peaks]


def _label(peak: Peak, ladder: FigureLadder) -> PeakLabel:
    parent = _third_of(peak.median_ms, ladder)
    if parent is None:
        return PeakLabel(peak=peak, fit=nearest_figure(peak.median_ms, ladder))
    printed = TRIPLET_PARENTS[parent]
    third = ladder.ms_by_figure[parent] / 3.0
    return PeakLabel(
        peak=peak,
        fit=FigureFit(
            figure=printed,
            figure_ms=third,
            fit_error=abs(math.log2(peak.median_ms / third)),
        ),
        tresillo_of=parent,
    )


def _third_of(gap_ms: float, ladder: FigureLadder, tolerance: float = 0.08) -> FigureName | None:
    """Is this pile a third of the **negra**, closely enough to be worth naming as one?

    Only the negra, and only closely. Offering a third of every figure sounds more helpful and is
    not: two thirds of a negra is also a third of a blanca, and the long half of a shuffled pair
    sits almost exactly there. Naming that pile a tresillo would tell a reader the piece is in
    triplets when it is swung, and D-12 settled that both halves of a swung pair print as corcheas.

    The tolerance is tighter than the one the printing rule uses, because a label on the plot is
    read as a suggestion and a wrong suggestion is what sends someone down the wrong path. The
    printing rule can afford to be looser: it also demands three gaps that match each other, which
    is much harder evidence than one pile sitting near a number.
    """
    third = ladder.ms_by_figure[FigureName.NEGRA] / 3.0
    return FigureName.NEGRA if abs(gap_ms - third) / third < tolerance else None


def shift_ladder(ladder: FigureLadder, steps: int) -> FigureLadder:
    """Re-point a ladder by whole figures, keeping every millisecond value (D-18).

    "Make everything one step longer" turns ``negra = 300 ms`` into ``blanca = 300 ms``, and every
    other figure moves with it. Positive steps name each length as a longer figure, so a passage
    written in semicorcheas becomes one written in corcheas. Nothing moves on the page: this is a
    change of names.
    """
    order = list(FIGURE_NEGRAS)
    order.sort(key=lambda figure: FIGURE_NEGRAS[figure])
    position = order.index(ladder.anchor_figure) + steps
    if not 0 <= position < len(order):
        raise ValueError(
            f"Shifting {ladder.anchor_figure.value} by {steps} step(s) leaves the vocabulary; it "
            f"runs from {order[0].value} to {order[-1].value}."
        )
    return build_ladder(order[position], ladder.anchor_ms)


def bpm_of(ladder: FigureLadder) -> float:
    """The tempo this ladder is equivalent to, in beats per minute, a negra being the beat.

    No part of the layout uses this. It is printed next to the millisecond value because both carry
    the same information and some readers think in BPM (D-20).
    """
    return 60000.0 / ladder.ms_by_figure[FigureName.NEGRA]


def header_label(ladder: FigureLadder) -> str:
    """What a passage header prints, for example ``negra = 320 ms · ≈188 BPM`` (D-20)."""
    return f"{ladder.anchor_figure.value} = {ladder.anchor_ms:.0f} ms · ≈{bpm_of(ladder):.0f} BPM"
