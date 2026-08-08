"""The rules a stored hand map has to satisfy.

This file used to guard a sidecar, ``hands_<granularity>.json``, written next to
a stored matrix so the piano roll, the falling notes and the score could not
disagree about who played what. Phase 4 removed both halves of that problem. The
hand split runs while a request is answered and is never written down, so there
is no second copy to disagree with the first, and the screens that read it are
gone.

What is left is the schema itself, which still travels inside a saved version's
metadata: a map has to match the matrix it describes, and it may not carry a
hand nobody can play with.
"""

from aitu_backend.schemas.metadata import HandAssignments
from aitu_backend.schemas.matrix import Granularity

import pytest


# ------------------------------------------------------------------- the schema


def test_a_map_that_does_not_match_its_counts_is_rejected() -> None:
    with pytest.raises(ValueError, match="onsetCount"):
        HandAssignments(
            method="beam",
            hand_map="rrl",
            onset_count=5,
            granularity=Granularity.FUSA,
            frame_count=10,
        )


def test_an_unknown_hand_character_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown hand characters"):
        HandAssignments(
            method="beam",
            hand_map="rxl",
            onset_count=3,
            granularity=Granularity.FUSA,
            frame_count=10,
        )


def test_matches_checks_the_matrix_identity() -> None:
    assignments = HandAssignments(
        method="beam",
        hand_map="rl",
        onset_count=2,
        granularity=Granularity.FUSA,
        frame_count=10,
    )
    assert assignments.matches(Granularity.FUSA, 10, 2)
    assert not assignments.matches(Granularity.CORCHEA, 10, 2)
    assert not assignments.matches(Granularity.FUSA, 11, 2)
