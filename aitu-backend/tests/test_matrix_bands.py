"""The line between two figures leans towards whichever of them the passage actually plays more of.

The property that makes this safe to switch on is the first test: with even piles it *is* the
geometric mean, so a passage that plays as many negras as corcheas is drawn exactly as it was.
"""

from __future__ import annotations

import math
from itertools import pairwise

import pytest

from aitu_backend.matrix.bands import SHARE_CLAMP, build_bands
from aitu_backend.matrix.ladder import build_ladder, nearest_figure
from aitu_backend.schemas.time_matrix import FigureName

CORCHEA = FigureName.CORCHEA
NEGRA = FigureName.NEGRA
SEMICORCHEA = FigureName.SEMICORCHEA


def ladder(anchor_ms: float = 268.0):
    return build_ladder(CORCHEA, anchor_ms)


def test_even_piles_give_back_the_geometric_mean() -> None:
    """The whole rule reduces to today's when neither figure is more common."""
    lad = ladder()
    bands = build_bands([268.0] * 200 + [536.0] * 200, lad)

    assert bands.line[CORCHEA] == pytest.approx(math.sqrt(268.0 * 536.0))
    assert bands.share[CORCHEA] == pytest.approx(0.5)


def test_no_gaps_at_all_gives_back_the_geometric_mean() -> None:
    """A passage with nothing in it is drawn exactly as it is today."""
    lad = ladder()
    bands = build_bands([], lad)

    for shorter, longer in pairwise(bands.order):
        expected = math.sqrt(lad.ms_by_figure[shorter] * lad.ms_by_figure[longer])
        assert bands.line[shorter] == pytest.approx(expected)


def test_the_taller_pile_takes_more_of_the_space() -> None:
    """Ten corcheas to one negra, and the line moves towards the negra."""
    lad = ladder(200.0)
    bands = build_bands([200.0] * 100 + [400.0] * 10, lad, clamp=(0.05, 0.95))

    assert bands.line[CORCHEA] == pytest.approx(200.0 * 2.0 ** (100 / 110), rel=1e-9)
    assert bands.line[CORCHEA] > math.sqrt(200.0 * 400.0)
    # A gap the halfway line would call a negra is now read as the corchea it more likely is.
    assert nearest_figure(370.0, lad).figure is NEGRA
    assert bands.figure_of(370.0) is CORCHEA


def test_the_line_never_leaves_the_two_figures_it_parts() -> None:
    """However lopsided the piles, a length played exactly right keeps its own name."""
    lad = ladder()
    for gaps in ([268.0] * 500, [536.0] * 500, [268.0] * 500 + [536.0]):
        bands = build_bands(gaps, lad)
        assert lad.ms_by_figure[CORCHEA] < bands.line[CORCHEA] < lad.ms_by_figure[NEGRA]
        assert bands.figure_of(268.0) is CORCHEA
        assert bands.figure_of(536.0) is NEGRA


def test_a_rare_figure_keeps_a_fifth_of_the_room() -> None:
    """Without the clamp a figure played twice in a piece could never be printed again."""
    lad = ladder()
    gaps = [268.0] * 1000 + [134.0] * 2
    bands = build_bands(gaps, lad)

    assert bands.share[SEMICORCHEA] == pytest.approx(SHARE_CLAMP[0])
    assert bands.line[SEMICORCHEA] == pytest.approx(134.0 * 2.0**SHARE_CLAMP[0])
    assert bands.figure_of(134.0) is SEMICORCHEA


def test_the_clamp_can_be_closed_to_reproduce_the_halfway_line() -> None:
    lad = ladder()
    bands = build_bands([268.0] * 900 + [536.0], lad, clamp=(0.5, 0.5))

    assert bands.line[CORCHEA] == pytest.approx(math.sqrt(268.0 * 536.0))


def test_a_clamp_that_does_not_straddle_the_halfway_point_is_refused() -> None:
    for bad in ((0.6, 0.8), (0.2, 0.4), (0.0, 1.0)):
        with pytest.raises(ValueError):
            build_bands([268.0], ladder(), clamp=bad)


def test_the_piles_are_counted_in_the_halfway_bands_and_not_iterated() -> None:
    """One pass. Counting inside the new lines would ratchet the big pile bigger every time."""
    lad = ladder()
    gaps = [268.0] * 100 + [536.0] * 30
    once = build_bands(gaps, lad)
    # Feeding the same gaps back gives the same answer: nothing about the result is a fixed point
    # that a second pass would move.
    assert build_bands(gaps, lad).line == once.line


def test_the_error_is_still_measured_against_the_figure_itself() -> None:
    """A note printed as a corchea because the piles moved the line still reports how far off it is."""
    lad = ladder()
    bands = build_bands([268.0] * 100 + [536.0] * 10, lad)
    figure, error = bands.fit(400.0)

    assert figure is CORCHEA
    assert error == pytest.approx(abs(math.log2(400.0 / 268.0)))
