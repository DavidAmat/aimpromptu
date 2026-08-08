"""Appendix D two-hands split — inferred by default, threshold as a baseline."""

import numpy as np
import pytest

from aitu_backend.matrix.cleaning import clean_sustains
from aitu_backend.matrix.hands import (
    DEFAULT_SPLIT_ROW,
    combine_hands,
    hand_of_row,
    split_hands,
    split_hands_at_row,
)
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.validator import is_valid
from aitu_backend.schemas.matrix import Granularity, Hand, MatrixProcessingStep

C3 = note_to_row("Do-3")
B3 = note_to_row("Si-3")  # the key just below middle C
C4 = note_to_row("Do-4")  # middle C — the old threshold
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


# ----------------------------------------------------------- what changed, and why


def test_the_inferred_split_keeps_an_exact_octave_in_one_hand() -> None:
    """Do-3 + Do-4 together is fingers 1 and 5, not two hands.

    The old ``Do-4`` threshold split this pair every time, because middle C sits
    between them. It is the clearest single case for why absolute pitch cannot
    decide a hand.
    """
    matrix = build({C3: [1], note_to_row("Do-4"): [1]}, frames=1)

    inferred = split_hands(matrix)
    assert inferred.left.active_rows() == [C3, C4]
    assert inferred.right.is_empty()

    # The rule it replaced does the opposite.
    threshold = split_hands_at_row(matrix)
    assert threshold.left.active_rows() == [C3]
    assert threshold.right.active_rows() == [C4]


def test_a_scale_crossing_middle_c_does_not_change_hands() -> None:
    """Sol-3 up to Sol-4 is one gesture; the threshold cuts it in three."""
    names = ["Sol-3", "La-3", "Si-3", "Do-4", "Re-4", "Mi-4", "Fa-4", "Sol-4"]
    rows = {note_to_row(name): [0] * index + [1] for index, name in enumerate(names)}
    matrix = build(rows, frames=len(names))

    hands = split_hands(matrix)
    assert hands.left.is_empty(), "the whole run belongs to one hand"
    assert len(hands.right.active_rows()) == len(names)

    # Under the threshold the first three notes fall to the other hand.
    threshold = split_hands_at_row(matrix)
    assert len(threshold.left.active_rows()) == 3


def test_the_hand_map_marks_every_onset_once() -> None:
    matrix = mixed()
    hands = split_hands(matrix)
    hand_map = hands.hand_map()

    assert hand_map is not None
    assert set(hand_map) <= {"l", "r"}
    # One character per onset, none per sustain.
    assert len(hand_map) == int(np.count_nonzero(matrix.grid == 1))


def test_the_same_matrix_always_splits_the_same_way() -> None:
    """Deterministic tie-breaking: no run-to-run drift in a saved score."""
    matrix = mixed()
    first, second = split_hands(matrix), split_hands(matrix)
    assert first.hand_map() == second.hand_map()
    assert np.array_equal(first.right.grid, second.right.grid)


def test_the_metadata_block_describes_the_matrix_it_came_from() -> None:
    matrix = mixed()
    hands = split_hands(matrix)
    metadata = hands.to_metadata()

    assert metadata is not None
    assert metadata.hand_map == hands.hand_map()
    assert metadata.matches(matrix.granularity, matrix.frame_count, metadata.onset_count)
    assert metadata.method == "beam-dp-v3"


def test_a_two_hands_matrix_cannot_be_split_again() -> None:
    """Re-inferring from one half would silently discard the other."""
    hands = split_hands(mixed())
    with pytest.raises(ValueError, match="already split"):
        split_hands(hands.right)


def test_an_unknown_method_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown hand-inference method"):
        split_hands(mixed(), method="wishful-thinking")


# ------------------------------------------------------------------ the baseline


def test_middle_c_is_the_default_threshold_row() -> None:
    assert DEFAULT_SPLIT_ROW == note_to_row("Do-4")


def test_the_threshold_key_itself_goes_to_the_right_hand() -> None:
    hands = split_hands_at_row(mixed())
    assert hands.right.grid[C4].tolist() == [1, 0, 0, 0]
    assert hands.left.grid[C4].tolist() == [0, 0, 0, 0]


def test_the_key_below_the_threshold_goes_to_the_left_hand() -> None:
    hands = split_hands_at_row(mixed())
    assert hands.left.grid[B3].tolist() == [0, 0, 1, 0]
    assert hands.right.grid[B3].tolist() == [0, 0, 0, 0]


def test_a_mixed_register_example_splits_by_pitch_alone() -> None:
    hands = split_hands_at_row(mixed())

    assert hands.right.grid[C4].tolist() == [1, 0, 0, 0]
    assert hands.right.grid[E4].tolist() == [0, 1, -1, 0]
    assert hands.right.grid[C5].tolist() == [0, 0, 0, 1]
    assert not hands.right.grid[:C4].any()

    assert hands.left.grid[C3].tolist() == [1, -1, 0, 1]
    assert hands.left.grid[B3].tolist() == [0, 0, 1, 0]
    assert not hands.left.grid[C4:].any()


def test_the_threshold_method_is_reachable_through_split_hands() -> None:
    """Same rule, but scored by the cost model so it stays comparable."""
    hands = split_hands(mixed(), method="threshold")
    assert hands.inference is not None
    assert hands.inference.method == "threshold-c4"
    assert not hands.right.grid[:C4].any()


def test_hand_of_row() -> None:
    assert hand_of_row(C4) is Hand.RIGHT
    assert hand_of_row(C5) is Hand.RIGHT
    assert hand_of_row(B3) is Hand.LEFT
    assert hand_of_row(0) is Hand.LEFT


# ------------------------------------------------------------- the invariants


@pytest.mark.parametrize("split", [split_hands, split_hands_at_row])
def test_split_never_cuts_the_matrix(split) -> None:
    """Both hands are full-size, so the staves stay frame-aligned."""
    matrix = mixed()
    hands = split(matrix)

    assert hands.right.shape == hands.left.shape == matrix.shape
    assert hands.right.frame_count == hands.left.frame_count == matrix.frame_count


@pytest.mark.parametrize("split", [split_hands, split_hands_at_row])
def test_both_hands_stay_structurally_valid(split) -> None:
    """A sustain always keeps the onset that owns it."""
    hands = split(mixed())
    assert is_valid(hands.right)
    assert is_valid(hands.left)


@pytest.mark.parametrize("split", [split_hands, split_hands_at_row])
def test_the_hands_never_share_a_cell(split) -> None:
    hands = split(mixed())
    assert not np.any((hands.right.grid != 0) & (hands.left.grid != 0))


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


@pytest.mark.parametrize("split", [split_hands, split_hands_at_row])
def test_recombining_reproduces_the_clean_matrix(split) -> None:
    """The acceptance criterion: r + l gives back exactly what went in."""
    matrix = mixed()
    hands = split(matrix)
    assert np.array_equal(hands.combined().grid, matrix.grid)
    assert np.array_equal(combine_hands(hands.right, hands.left).grid, matrix.grid)


def test_recombining_survives_sustains_and_silences() -> None:
    matrix = build({C3: [1, -1, -1, 0], C5: [0, 1, -1, -1]}, frames=4)
    hands = split_hands(matrix)
    assert np.array_equal(hands.combined().grid, matrix.grid)


def test_a_sustain_never_changes_hand_mid_note() -> None:
    """A key is held by the hand that struck it, from strike to release."""
    matrix = build({C3: [1, -1, -1, -1], C5: [1, -1, -1, -1]}, frames=4)
    hands = split_hands(matrix)
    for row in (C3, C5):
        right = hands.right.grid[row]
        left = hands.left.grid[row]
        assert not (right.any() and left.any()), "the note changed hands while sounding"


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
    hands = split_hands_at_row(mixed(), threshold="Mi-4")
    # Middle C now falls to the left hand.
    assert hands.left.grid[C4].tolist() == [1, 0, 0, 0]
    assert hands.right.grid[E4].tolist() == [0, 1, -1, 0]
    assert hands.split_row == E4


def test_the_threshold_accepts_a_row_index() -> None:
    assert split_hands_at_row(mixed(), threshold=C5).split_row == C5


def test_an_out_of_range_threshold_is_rejected() -> None:
    with pytest.raises(ValueError, match="outside"):
        split_hands_at_row(mixed(), threshold=200)


def test_extreme_thresholds_put_everything_in_one_hand() -> None:
    matrix = mixed()

    all_right = split_hands_at_row(matrix, threshold=0)
    assert np.array_equal(all_right.right.grid, matrix.grid)
    assert all_right.left.is_empty()

    all_left = split_hands_at_row(matrix, threshold=KEY_COUNT)
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


def test_a_group_no_two_hands_could_play_is_reported_not_hidden() -> None:
    """Eleven simultaneous keys is not a split decision, it is a warning."""
    rows = {row: [1] for row in range(20, 42, 2)}
    matrix = build(rows, frames=1)

    hands = split_hands(matrix)
    assert hands.inference is not None
    assert hands.inference.diagnostics.infeasible_groups >= 1
    assert hands.inference.warnings
    # It is still split into something, and it still recombines.
    assert np.array_equal(hands.combined().grid, matrix.grid)


def test_an_empty_matrix_splits_into_two_empty_hands() -> None:
    hands = split_hands(PianoMatrix.empty(6))
    assert hands.right.is_empty()
    assert hands.left.is_empty()
    assert hands.frame_count == 6


# ------------------------------------- inferring from one matrix, painting another


def test_infer_from_keeps_the_assignment_and_the_uncleaned_sustains() -> None:
    """The seam the pipeline needs: decide on the clean view, paint the collapsed one.

    The beam's `release_aware` relocation reads a hand as pinned for as long as
    its keys sound, and it was tuned against Appendix-B-cleaned sustains — so the
    decision has to come from the cleaned matrix. What gets *rendered* must keep
    the sustains cleaning removed, because per-hand cleaning happens afterwards.
    """
    matrix = build(
        {
            C3: [1, -1, -1, -1],  # a pedal note the whole-keyboard clean would cut
            C5: [1, -1, 1, -1],  # a melody above it, struck twice
        },
        frames=4,
    )
    view = clean_sustains(matrix)
    # They are struck together, so the pedal note survives until the melody's
    # second strike — and is cut there, by a note the other hand plays.
    assert view.grid[C3].tolist() == [1, -1, 0, 0], "the clean view really is shorter"

    hands = split_hands(matrix, infer_from=view)

    # The hands came from the cleaned view ...
    assert hands.inference is not None
    assert hands.left.active_rows() == [C3]
    assert hands.right.active_rows() == [C5]
    # ... but the cells came from `matrix`, sustains and all.
    assert hands.left.grid[C3].tolist() == [1, -1, -1, -1]
    assert np.array_equal(hands.combined().grid, matrix.grid)


def test_infer_from_gives_the_same_answer_as_splitting_the_clean_matrix() -> None:
    """Only the cells differ; nobody's hand changes because of a sustain."""
    matrix = build({C3: [1, -1, -1, -1], C5: [1, -1, 1, -1]}, frames=4)
    view = clean_sustains(matrix)

    direct = split_hands(view)
    repainted = split_hands(matrix, infer_from=view)

    assert direct.hand_map() == repainted.hand_map()
    assert direct.inference is not None and repainted.inference is not None
    assert direct.inference.onset_ids == repainted.inference.onset_ids


def test_infer_from_refuses_a_matrix_with_different_onsets() -> None:
    """Onsets are the contract. If they disagree, something upstream is wrong."""
    matrix = build({C3: [1, -1, 1, -1], C5: [1, -1, -1, -1]}, frames=4)
    other = build({C3: [1, -1, -1, -1], C5: [1, -1, -1, -1]}, frames=4)

    with pytest.raises(ValueError, match="do not share their onsets"):
        split_hands(matrix, infer_from=other)


def test_cleaning_one_hand_keeps_it_labelled_as_a_hand() -> None:
    matrix = build({C3: [1, -1, -1, -1], C5: [1, -1, 1, -1]}, frames=4)
    hands = split_hands(matrix, infer_from=clean_sustains(matrix))

    cleaned = clean_sustains(hands.left, processing_step=MatrixProcessingStep.TWO_HANDS)
    assert cleaned.processing_step is MatrixProcessingStep.TWO_HANDS
    assert cleaned.hand == Hand.LEFT.value
