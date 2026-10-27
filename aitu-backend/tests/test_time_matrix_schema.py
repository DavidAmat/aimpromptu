"""The vocabulary of the time model that is still read: the column length, the figures, two old marks.

The schema 2.0 contracts with vexflow-v2 (the envelope, the ladder, the passages, the score payload)
went with that sheet in implementation 03, Phase 10. The new sheet and the reader of the old
``sheet.json`` keep these names, so a rename here is still a silent break.
"""

import pytest
from pydantic import ValidationError

from aitu_backend.schemas.time_matrix import (
    DEFAULT_FRAME_MS,
    FIGURE_NEGRAS,
    BeamBreak,
    FigureName,
    FigureOverride,
)


def test_a_frame_is_forty_milliseconds():
    """D-01: the grid is wall clock."""
    assert DEFAULT_FRAME_MS == 40.0


def test_the_figure_vocabulary_is_closed_and_dotted_only_on_blanca_and_negra():
    """D-12: allowing a dotted corchea is what turns an even swing pair into a ragged mix."""
    dotted = sorted(f.value for f in FigureName if f.value.startswith("dotted"))
    assert dotted == ["dottedBlanca", "dottedNegra"]
    assert len(FigureName) == 9
    assert set(FIGURE_NEGRAS) == set(FigureName)


def test_each_figure_is_twice_the_one_below():
    assert FIGURE_NEGRAS[FigureName.REDONDA] == 4.0
    assert FIGURE_NEGRAS[FigureName.CORCHEA] == 0.5
    assert FIGURE_NEGRAS[FigureName.DOTTED_NEGRA] == 1.5


def test_a_figure_override_and_a_beam_break_travel_as_camel_case():
    override = FigureOverride(hand="right", row=40, start_frame=12, figure=FigureName.CORCHEA)
    assert override.model_dump(by_alias=True, mode="json") == {
        "hand": "right",
        "row": 40,
        "startFrame": 12,
        "figure": "corchea",
    }
    assert BeamBreak.model_validate({"hand": "left", "startFrame": 3}).start_frame == 3


def test_a_mark_names_one_staff_and_a_key_of_the_piano():
    with pytest.raises(ValidationError):
        FigureOverride(hand="both", row=40, start_frame=0, figure=FigureName.NEGRA)
    with pytest.raises(ValidationError):
        FigureOverride(hand="right", row=88, start_frame=0, figure=FigureName.NEGRA)
