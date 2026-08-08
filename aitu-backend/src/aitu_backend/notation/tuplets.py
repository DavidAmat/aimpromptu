"""Tresillos: three notes played in the time the ladder gives to two.

A tresillo is the one thing a ladder of halves cannot express. Every figure in the vocabulary is
half or double its neighbour, so a group of three even notes filling one beat has no name in it: at
a negra of 300 ms the three land 100 ms apart, and 100 is a poor corchea (150) and a poor
semicorchea (75). Forced onto the nearest figure they come out as a ragged mix, which is the same
failure this whole refactor exists to remove, one level down.

So they are recognised instead of rounded. The rule is deliberately narrow, because a wrong tresillo
is worse than a missed one: three notes in a row, in the same hand, whose three gaps are the same
length as each other, and whose length is a third of a figure the ladder already knows.

Both conditions matter. "About a third of a negra" alone would catch any three notes that happen to
be fast, and rhythms that are genuinely uneven would be printed as even triplets. Requiring the
three gaps to match each other is what says the player was dividing a beat into three rather than
playing something else at a similar speed.

What is produced is not a new figure. The notes keep the ordinary figure one step below the one they
divide, so a tresillo of a negra is three corcheas; what makes it a tresillo is the number 3 and the
bracket drawn over them.
"""

from __future__ import annotations

from dataclasses import dataclass

from aitu_backend.schemas.time_matrix import FigureLadder, FigureName

__all__ = [
    "DEFAULT_EVENNESS_TOLERANCE",
    "DEFAULT_THIRD_TOLERANCE",
    "TRIPLET_PARENTS",
    "Tresillo",
    "find_tresillos",
]

#: The figures a tresillo may divide, and the figure its three notes are printed as.
#:
#: A tresillo of a negra is three corcheas, of a blanca three negras, and so on: one step down the
#: closed vocabulary. Dotted figures are not here, because a dotted figure already divides into
#: three and a triplet of one would be a way of writing the same rhythm twice.
TRIPLET_PARENTS: dict[FigureName, FigureName] = {
    FigureName.REDONDA: FigureName.BLANCA,
    FigureName.BLANCA: FigureName.NEGRA,
    FigureName.NEGRA: FigureName.CORCHEA,
    FigureName.CORCHEA: FigureName.SEMICORCHEA,
    FigureName.SEMICORCHEA: FigureName.FUSA,
}

#: How far the three gaps may differ from each other, as a fraction of their average.
#:
#: A person dividing a beat into three does not place them perfectly, and 12 % is roughly the
#: jitter a steady player shows. Wider than this and ordinary uneven playing starts being read as
#: triplets.
DEFAULT_EVENNESS_TOLERANCE = 0.12

#: How far the gap may sit from an exact third of the parent figure, as a fraction.
DEFAULT_THIRD_TOLERANCE = 0.15


@dataclass(frozen=True)
class Tresillo:
    """Three notes of one hand that divide a figure into three."""

    #: Position of the first of the three in the hand's list of attacks.
    start_index: int
    #: The figure being divided, for example a negra.
    parent: FigureName
    #: What each of the three is printed as, for example a corchea.
    figure: FigureName
    #: The average of the three gaps, in milliseconds.
    gap_ms: float

    @property
    def indexes(self) -> tuple[int, int, int]:
        return (self.start_index, self.start_index + 1, self.start_index + 2)


def find_tresillos(
    gaps_ms: list[float],
    ladder: FigureLadder,
    *,
    open_ended: bool = False,
    evenness_tolerance: float = DEFAULT_EVENNESS_TOLERANCE,
    third_tolerance: float = DEFAULT_THIRD_TOLERANCE,
) -> list[Tresillo]:
    """Every run of three notes that divides a figure into three.

    ``gaps_ms[i]`` is the gap from attack ``i`` to attack ``i + 1``, so three notes need three gaps:
    the two inside the group and the one that carries the third note to whatever comes next. That
    third gap is what says the group is even all the way through rather than three notes followed by
    a pause.

    ``open_ended`` says the **last** entry is not a gap to another onset but the run-out to the end
    of the hand (D-14's tail). It is then not evidence of anything: a piece can stop on a tresillo,
    and its last note is simply the last note. The final group is judged on its two inner gaps, with
    the tail required only not to be markedly shorter than them. Without this the closing group of
    every piece prints as two odd figures among sixty even ones — the exact raggedness this exists to
    remove, in the one place a reader looks last.

    Groups do not overlap. A run of six even notes gives two tresillos, not four, because the second
    one starts where the first ends: a note belongs to one group or to none.
    """
    found: list[Tresillo] = []
    index = 0
    while index + 2 < len(gaps_ms):
        three = gaps_ms[index : index + 3]
        inner_only = open_ended and index + 2 == len(gaps_ms) - 1
        match = _tresillo_at(index, three, ladder, evenness_tolerance, third_tolerance, inner_only)
        if match is None:
            index += 1
            continue
        found.append(match)
        index += 3
    return found


def _tresillo_at(
    index: int,
    three: list[float],
    ladder: FigureLadder,
    evenness_tolerance: float,
    third_tolerance: float,
    inner_only: bool = False,
) -> Tresillo | None:
    if any(gap <= 0 for gap in three):
        return None
    measured = three[:2] if inner_only else three
    average = sum(measured) / len(measured)
    if any(abs(gap - average) / average > evenness_tolerance for gap in measured):
        return None
    if inner_only and three[2] < average * (1 - evenness_tolerance):
        return None

    best: Tresillo | None = None
    best_error = third_tolerance
    for parent, figure in TRIPLET_PARENTS.items():
        third = ladder.ms_by_figure[parent] / 3.0
        error = abs(average - third) / third
        if error < best_error:
            best_error = error
            best = Tresillo(start_index=index, parent=parent, figure=figure, gap_ms=average)
    return best
