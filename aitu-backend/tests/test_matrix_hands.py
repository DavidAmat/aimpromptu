"""Appendix D two-hands split."""

import numpy as np
import pytest

from aitu_backend.matrix.hands import (
    DEFAULT_SPLIT_ROW,
    combine_hands,
    hand_of_row,
    split_hands,
)
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.validator import is_valid
from aitu_backend.schemas.matrix import Granularity, Hand, MatrixProcessingStep

C3 = note_to_row("Do-3")
B3 = note_to_row("Si-3")  # the key just below middle C
C4 = note_to_row("Do-4")  # middle C — the threshold
E4 = note_to_row("Mi-4")
C5 = note_to_row("Do-5")


def build(rows: dict[int, list[int]], frames: int) -> PianoMatrix:
    grid = np.zeros((KEY_COUNT, frames), dtype=np.int8)
    for row, values in rows.items():
        grid[row, : len(values)] = np.array(values, dtype=np.int8)
    return PianoMatrix.from_dense(
        grid,
        granularity=Granularity.SEMICORCHEA,
        tempo_bpm=72,
        processing_step=MatrixProcessingStep.CLEAN,
    )


def mixed() -> PianoMatrix:
    """A left-hand bass line under a right-hand melody, plus middle C itself."""
    return build(
        {
            C3: [1, -1, 0, 1],
            B3: [0, 0, 1, 0],
            C4: [1, 0, 0, 0],
            E4: [0, 1, -1, 0],
            C5: [0, 0, 0, 1],
        },
        frames=4,
    )


# ------------------------------------------------------------------ the rule


def test_middle_c_is_the_default_threshold() -> None:
    assert DEFAULT_SPLIT_ROW == note_to_row("Do-4")


def test_the_threshold_key_itself_goes_to_the_right_hand() -> None:
    hands = split_hands(mixed())
    assert hands.right.grid[C4].tolist() == [1, 0, 0, 0]
    assert hands.left.grid[C4].tolist() == [0, 0, 0, 0]


def test_the_key_below_the_threshold_goes_to_the_left_hand() -> None:
    hands = split_hands(mixed())
    assert hands.left.grid[B3].tolist() == [0, 0, 1, 0]
    assert hands.right.grid[B3].tolist() == [0, 0, 0, 0]


def test_a_mixed_register_example_splits_correctly() -> None:
    hands = split_hands(mixed())

    # Right hand keeps everything from middle C up.
    assert hands.right.grid[C4].tolist() == [1, 0, 0, 0]
    assert hands.right.grid[E4].tolist() == [0, 1, -1, 0]
    assert hands.right.grid[C5].tolist() == [0, 0, 0, 1]
    assert not hands.right.grid[:C4].any()

    # Left hand keeps everything below it.
    assert hands.left.grid[C3].tolist() == [1, -1, 0, 1]
    assert hands.left.grid[B3].tolist() == [0, 0, 1, 0]
    assert not hands.left.grid[C4:].any()


def test_hand_of_row() -> None:
    assert hand_of_row(C4) is Hand.RIGHT
    assert hand_of_row(C5) is Hand.RIGHT
    assert hand_of_row(B3) is Hand.LEFT
    assert hand_of_row(0) is Hand.LEFT


# ------------------------------------------------------------- the invariants


def test_split_never_cuts_the_matrix() -> None:
    """Both hands are full-size copies, so the staves stay frame-aligned."""
    matrix = mixed()
    hands = split_hands(matrix)

    assert hands.right.shape == hands.left.shape == matrix.shape
    assert hands.right.frame_count == hands.left.frame_count == matrix.frame_count


def test_both_hands_stay_structurally_valid() -> None:
    """Zeroing whole rows cannot create an illegal transition."""
    hands = split_hands(mixed())
    assert is_valid(hands.right)
    assert is_valid(hands.left)


def test_hands_are_labelled_and_marked() -> None:
    hands = split_hands(mixed())
    assert hands.right.hand == Hand.RIGHT.value
    assert hands.left.hand == Hand.LEFT.value
    assert hands.right.processing_step is MatrixProcessingStep.TWO_HANDS
    assert hands.left.processing_step is MatrixProcessingStep.TWO_HANDS


def test_metadata_carries_over() -> None:
    matrix = mixed()
    hands = split_hands(matrix)
    for hand in (hands.right, hands.left):
        assert hand.granularity is matrix.granularity
        assert hand.tempo_bpm == matrix.tempo_bpm


def test_splitting_does_not_mutate_its_input() -> None:
    matrix = mixed()
    before = matrix.to_array()
    split_hands(matrix)
    assert np.array_equal(matrix.grid, before)


# --------------------------------------------------------------- recombining


def test_recombining_reproduces_the_clean_matrix() -> None:
    """The acceptance criterion: r + l gives back exactly what went in."""
    matrix = mixed()
    hands = split_hands(matrix)
    assert np.array_equal(hands.combined().grid, matrix.grid)
    assert np.array_equal(combine_hands(hands.right, hands.left).grid, matrix.grid)


def test_recombining_survives_sustains_and_silences() -> None:
    matrix = build({C3: [1, -1, -1, 0], C5: [0, 1, -1, -1]}, frames=4)
    hands = split_hands(matrix)
    assert np.array_equal(hands.combined().grid, matrix.grid)


def test_combine_rejects_mismatched_shapes() -> None:
    hands = split_hands(mixed())
    shorter = PianoMatrix.empty(2)
    with pytest.raises(ValueError, match="same shape"):
        combine_hands(hands.right, shorter)


def test_combining_marks_the_result_as_a_single_clean_matrix() -> None:
    combined = split_hands(mixed()).combined()
    assert combined.hand is None
    assert combined.processing_step is MatrixProcessingStep.CLEAN


# ----------------------------------------------------------- custom threshold


def test_the_threshold_accepts_a_note_name() -> None:
    hands = split_hands(mixed(), threshold="Mi-4")
    # Middle C now falls to the left hand.
    assert hands.left.grid[C4].tolist() == [1, 0, 0, 0]
    assert hands.right.grid[E4].tolist() == [0, 1, -1, 0]
    assert hands.split_row == E4


def test_the_threshold_accepts_a_row_index() -> None:
    assert split_hands(mixed(), threshold=C5).split_row == C5


def test_an_out_of_range_threshold_is_rejected() -> None:
    with pytest.raises(ValueError, match="outside"):
        split_hands(mixed(), threshold=200)


def test_extreme_thresholds_put_everything_in_one_hand() -> None:
    matrix = mixed()

    all_right = split_hands(matrix, threshold=0)
    assert np.array_equal(all_right.right.grid, matrix.grid)
    assert all_right.left.is_empty()

    all_left = split_hands(matrix, threshold=KEY_COUNT)
    assert np.array_equal(all_left.left.grid, matrix.grid)
    assert all_left.right.is_empty()


# ------------------------------------------------------------------- musical


def test_a_left_hand_chord_under_a_right_hand_scale() -> None:
    """Do-3 + Sol-3 held while the right hand walks Do Re Mi Fa upward."""
    rows = {
        note_to_row("Do-3"): [1, -1, -1, -1],
        note_to_row("Sol-3"): [1, -1, -1, -1],
    }
    for index, name in enumerate(["Do-4", "Re-4", "Mi-4", "Fa-4"]):
        cells = [0] * index + [1]
        rows[note_to_row(name)] = cells
    matrix = build(rows, frames=4)

    hands = split_hands(matrix)
    assert hands.left.active_rows() == sorted([note_to_row("Do-3"), note_to_row("Sol-3")])
    assert hands.right.active_rows() == sorted(
        note_to_row(name) for name in ["Do-4", "Re-4", "Mi-4", "Fa-4"]
    )
    assert np.array_equal(hands.combined().grid, matrix.grid)


def test_an_empty_matrix_splits_into_two_empty_hands() -> None:
    hands = split_hands(PianoMatrix.empty(6))
    assert hands.right.is_empty()
    assert hands.left.is_empty()
    assert hands.frame_count == 6
