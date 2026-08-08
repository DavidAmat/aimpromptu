"""Hand inference: the decoder, the cost model, the search and the compact map.

The musical cases here are the ones the fixed ``Do-4`` threshold got wrong. Each
is a passage where a pianist's choice is not in doubt but a pitch boundary
cannot express it — an octave under one hand, a line crossing middle C, a left
hand jumping into the middle register under a stable melody.

Regression values (the exact hand strings) were confirmed against the research
PoC that produced this method, so a drift here means the port changed, not that
the benchmark moved.
"""

import numpy as np
import pytest

from aitu_backend.hands import (
    DEFAULT_CONFIG,
    HandInferenceConfig,
    decode_hand_map,
    decode_matrix,
    encode_hand_map,
    infer_hands,
)
from aitu_backend.hands.candidates import all_partitions, generate, is_feasible, is_overloaded
from aitu_backend.hands.config import HandModel, SearchConfig
from aitu_backend.hands.costs import LEFT, RIGHT, PairState, transition
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep


def matrix_from(rows: dict[str, list[int]], frames: int, bpm: float = 60.0) -> PianoMatrix:
    """Build a clean matrix from ``{"Do-4": [1, -1, 0, ...]}``."""
    grid = np.zeros((KEY_COUNT, frames), dtype=np.int8)
    for name, cells in rows.items():
        grid[note_to_row(name), : len(cells)] = np.array(cells, dtype=np.int8)
    return PianoMatrix.from_dense(
        grid,
        granularity=Granularity.CORCHEA,
        tempo_bpm=bpm,
        processing_step=MatrixProcessingStep.CLEAN,
    )


def melody(names: list[str], bpm: float = 60.0) -> PianoMatrix:
    """One note per frame, in order. A name may repeat — each is its own onset."""
    grid = np.zeros((KEY_COUNT, len(names)), dtype=np.int8)
    for column, name in enumerate(names):
        grid[note_to_row(name), column] = 1
    return PianoMatrix.from_dense(
        grid,
        granularity=Granularity.CORCHEA,
        tempo_bpm=bpm,
        processing_step=MatrixProcessingStep.CLEAN,
    )


def hands_of(matrix: PianoMatrix, method: str = "beam") -> str:
    """The compact hand string, for readable assertions."""
    return infer_hands(matrix, DEFAULT_CONFIG.with_method(method)).hand_map


# ------------------------------------------------------------------- decoding


def test_an_onset_owns_the_sustains_that_follow_it() -> None:
    decoded = decode_matrix(matrix_from({"Do-4": [1, -1, -1, 0]}, frames=4))
    assert len(decoded.events) == 1
    event = decoded.events[0]
    assert event.duration_frames == 3
    assert event.cells == (0, 1, 2)
    assert event.onset_id == f"c0:r{note_to_row('Do-4')}"


def test_a_restruck_key_is_a_new_onset() -> None:
    """``1`` after ``-1`` in the same row is a second strike, not a continuation."""
    decoded = decode_matrix(matrix_from({"Do-4": [1, -1, 1, -1]}, frames=4))
    assert [event.column for event in decoded.events] == [0, 2]


def test_simultaneous_onsets_form_one_group_sorted_by_pitch() -> None:
    decoded = decode_matrix(matrix_from({"Mi-4": [1], "Do-4": [1], "Sol-4": [1]}, frames=1))
    assert len(decoded.groups) == 1
    assert decoded.groups[0].midis == (60, 64, 67)


def test_an_orphan_sustain_is_promoted_and_reported() -> None:
    """A transcription can emit one; losing the note silently would be worse."""
    decoded = decode_matrix(matrix_from({"Do-4": [-1, -1]}, frames=2))
    assert len(decoded.events) == 1
    assert decoded.events[0].column == 0
    assert any("orphan sustain" in warning.lower() for warning in decoded.warnings)


def test_orphan_sustains_can_be_dropped_instead() -> None:
    decoded = decode_matrix(
        matrix_from({"Do-4": [-1, -1]}, frames=2), promote_orphan_sustains=False
    )
    assert decoded.events == []
    assert decoded.warnings


def test_onset_ids_are_in_canonical_column_row_order() -> None:
    """The order the compact hand map indexes against."""
    decoded = decode_matrix(
        matrix_from({"Sol-4": [0, 1], "Do-4": [1, 0], "Mi-4": [1, 0]}, frames=2)
    )
    assert decoded.onset_ids == [
        f"c0:r{note_to_row('Do-4')}",
        f"c0:r{note_to_row('Mi-4')}",
        f"c1:r{note_to_row('Sol-4')}",
    ]


# ------------------------------------------------------- what the threshold got wrong


def test_an_exact_octave_stays_in_one_hand() -> None:
    """Fingers 1 and 5. The threshold split it because middle C sits between."""
    octave = matrix_from({"Do-3": [1], "Do-4": [1]}, frames=1)
    assert hands_of(octave) == "ll"
    assert hands_of(octave, "threshold") == "lr"


def test_a_line_crossing_middle_c_keeps_one_hand() -> None:
    run = melody(["Sol-3", "La-3", "Si-3", "Do-4", "Re-4", "Mi-4", "Fa-4", "Sol-4"])
    assert hands_of(run) == "r" * 8
    assert hands_of(run, "threshold") == "lll" + "r" * 5


def test_a_left_hand_reaching_above_middle_c_is_allowed() -> None:
    """A bass line walking up past C4 under a held melody stays in the left hand."""
    rows = {"Do-6": [1, -1, -1, -1, -1, -1]}  # right hand holds a high melody note
    for index, name in enumerate(["Do-3", "Mi-3", "Sol-3", "Do-4", "Mi-4", "Sol-4"]):
        rows[name] = [0] * index + [1]
    hand_map = hands_of(matrix_from(rows, frames=6))
    # The melody note is the first onset of column 0; the rest is the bass line.
    assert hand_map.count("l") >= 5, f"bass line was broken up: {hand_map}"


def test_the_threshold_creates_impossible_spans_that_the_beam_avoids() -> None:
    """The damning difference is structural, not a couple of accuracy points."""
    # A ten-semitone chord straddling middle C: one hand, comfortably.
    chord = matrix_from({"Sol-3": [1], "Si-3": [1], "Re-4": [1], "Fa-4": [1]}, frames=1)
    beam = infer_hands(chord)
    threshold = infer_hands(chord, DEFAULT_CONFIG.with_method("threshold"))
    assert len(set(beam.hand_map)) == 1, "one hand can hold a tenth"
    assert len(set(threshold.hand_map)) == 2
    assert beam.diagnostics.total_cost < threshold.diagnostics.total_cost


# ------------------------------------------------------------------ invariants


def test_every_onset_gets_exactly_one_hand() -> None:
    matrix = melody(["Do-3", "Sol-3", "Do-4", "Mi-4", "Sol-4", "Do-5"])
    result = infer_hands(matrix)
    decoded = decode_matrix(matrix)
    assert len(result.assignments) == len(decoded.events)
    assert {item.onset_id for item in result.assignments} == set(decoded.onset_ids)
    assert all(item.hand in (LEFT, RIGHT) for item in result.assignments)


def test_the_split_grids_recombine_to_the_input() -> None:
    matrix = matrix_from(
        {"Do-3": [1, -1, 0, 1], "Sol-3": [1, -1, 0, 0], "Do-5": [0, 1, -1, -1]}, frames=4
    )
    result = infer_hands(matrix)
    combined = np.where(result.right_grid != 0, result.right_grid, result.left_grid)
    assert np.array_equal(combined, matrix.grid)
    assert not np.any((result.right_grid != 0) & (result.left_grid != 0))


def test_an_empty_matrix_infers_nothing_and_does_not_fail() -> None:
    result = infer_hands(PianoMatrix.empty(8, processing_step=MatrixProcessingStep.CLEAN))
    assert result.assignments == []
    assert result.hand_map == ""


def test_a_two_hands_matrix_is_refused() -> None:
    matrix = melody(["Do-4"])
    already_split = matrix.with_grid(matrix.grid, processing_step=MatrixProcessingStep.TWO_HANDS)
    with pytest.raises(ValueError, match="already split"):
        infer_hands(already_split)


@pytest.mark.parametrize("method", ["beam", "greedy", "exact", "threshold"])
def test_every_method_produces_a_complete_valid_split(method: str) -> None:
    matrix = matrix_from({"Do-3": [1, 0, 1, 0], "Do-5": [1, -1, 0, 1]}, frames=4)
    result = infer_hands(matrix, DEFAULT_CONFIG.with_method(method))
    combined = np.where(result.right_grid != 0, result.right_grid, result.left_grid)
    assert np.array_equal(combined, matrix.grid)
    assert len(result.hand_map) == len(result.assignments)


def test_a_wider_beam_never_costs_more_than_a_narrow_one() -> None:
    """More search cannot find a worse optimum of the same objective."""
    matrix = melody(["Do-3", "Sol-3", "Mi-4", "Do-5", "Sol-4", "Mi-3", "Do-3"])
    narrow = HandInferenceConfig(search=SearchConfig(beam_width=1))
    wide = HandInferenceConfig(search=SearchConfig(beam_width=24))
    assert infer_hands(matrix, wide).diagnostics.total_cost <= (
        infer_hands(matrix, narrow).diagnostics.total_cost + 1e-9
    )


# ------------------------------------------------------------------ candidates


def test_candidate_generation_respects_finger_capacity() -> None:
    group = decode_matrix(
        matrix_from({name: [1] for name in ["Do-4", "Re-4", "Mi-4", "Fa-4", "Sol-4"]}, frames=1)
    ).groups[0]
    candidates, relaxed = generate(group, HandModel(), SearchConfig())
    assert not relaxed
    assert all(is_feasible(group, candidate, HandModel()) for candidate in candidates)


def test_a_group_beyond_ten_fingers_is_flagged_not_searched() -> None:
    """Eleven distinct keys has no two-hand answer, so there is nothing to explore."""
    group = decode_matrix(
        matrix_from(
            {f"Do-{octave}": [1] for octave in range(1, 8)}
            | {"Mi-1": [1], "Sol-1": [1], "Mi-2": [1], "Sol-2": [1]},
            frames=1,
        )
    ).groups[0]
    assert is_overloaded(group, HandModel())
    candidates, relaxed = generate(group, HandModel(), SearchConfig())
    assert relaxed
    assert len(candidates) <= 3, "a hopeless group must not spawn a wide search"


def test_all_partitions_is_exhaustive() -> None:
    assert len(all_partitions(4)) == 16
    assert len(set(all_partitions(4))) == 16


# ---------------------------------------------------------------- the cost model


def test_an_unreachable_span_is_infeasible_rather_than_expensive() -> None:
    """Hard constraints return None; they are not a large penalty to outweigh."""
    group = decode_matrix(matrix_from({"Do-2": [1], "Do-6": [1]}, frames=1)).groups[0]
    both_left = (LEFT, LEFT)
    assert transition(PairState(), group, both_left, HandModel(), DEFAULT_CONFIG.weights) is None


def test_zeroing_a_weight_removes_its_term() -> None:
    """Every term is ablatable, which is what makes disagreements diagnosable."""
    matrix = matrix_from({"Do-3": [1], "Do-4": [1]}, frames=1)
    group = decode_matrix(matrix).groups[0]
    weights = DEFAULT_CONFIG.with_weights(span=0.0, octave=0.0, split=0.0).weights
    result = transition(PairState(), group, (LEFT, LEFT), HandModel(), weights)
    assert result is not None
    assert result.breakdown.span != 0.0, "the component is still measured"
    assert weights.span * result.breakdown.span == 0.0, "but it no longer scores"


def test_costs_are_reported_per_component() -> None:
    result = infer_hands(melody(["Do-3", "Do-6", "Do-3"]))
    assert any(item.cost_breakdown for item in result.assignments)
    assert all(
        isinstance(value, float)
        for item in result.assignments
        for value in item.cost_breakdown.values()
    )


# -------------------------------------------------------------------- encoding


def test_the_hand_map_round_trips() -> None:
    matrix = matrix_from({"Do-3": [1, 0, 1], "Do-5": [1, -1, 1]}, frames=3)
    result = infer_hands(matrix)
    decoded = decode_matrix(matrix)

    assert decode_hand_map(decoded.onset_ids, result.hand_map) == result.hand_of()
    assert encode_hand_map(decoded.onset_ids, result.hand_of()) == result.hand_map


def test_the_hand_map_lines_up_with_the_sparse_payload() -> None:
    """The contract a VexFlow or piano-roll consumer actually relies on.

    Walk the COO arrays, count onsets, read the character at that index.
    """
    matrix = matrix_from(
        {"Do-3": [1, -1, 1, 0], "Mi-4": [0, 1, -1, 1], "Do-5": [1, 0, 0, 1]}, frames=4
    )
    result = infer_hands(matrix)
    payload = matrix.to_coo_payload()

    walked: dict[tuple[int, int], str] = {}
    onset_index = 0
    for row, col, onset in zip(payload.rows, payload.cols, payload.onset):
        if onset == -1:
            continue  # a sustain inherits its onset's hand
        walked[(row, col)] = result.hand_map[onset_index]
        onset_index += 1

    assert onset_index == len(result.hand_map)
    for item in result.assignments:
        expected = "r" if item.hand == RIGHT else "l"
        assert walked[(item.row, item.column)] == expected


def test_a_hand_map_from_a_different_matrix_is_refused() -> None:
    """Silently mis-coloring a score is worse than refusing to color it."""
    with pytest.raises(ValueError, match="does not belong"):
        decode_hand_map(["c0:r39", "c1:r40"], "rrr")


def test_encoding_refuses_an_incomplete_assignment() -> None:
    with pytest.raises(ValueError, match="no hand assignment"):
        encode_hand_map(["c0:r39", "c1:r40"], {"c0:r39": "right"})


def test_the_map_is_one_byte_per_onset() -> None:
    """The reason it is a string and not a list of objects."""
    matrix = melody([f"Do-{octave}" for octave in range(1, 8)] * 4)
    result = infer_hands(matrix)
    assert len(result.hand_map.encode()) == len(result.assignments)


# ------------------------------------------------------------------ diagnostics


def test_diagnostics_report_the_search_that_happened() -> None:
    result = infer_hands(melody(["Do-3", "Mi-4", "Sol-5", "Mi-4", "Do-3"]))
    diagnostics = result.diagnostics
    assert diagnostics.onsets == len(result.assignments)
    assert diagnostics.onset_groups == 5
    assert diagnostics.states_expanded > 0
    assert diagnostics.runtime_ms >= 0.0


def test_confidence_is_bounded_and_ordered() -> None:
    """It is uncalibrated, but it must at least be a usable ordering."""
    result = infer_hands(melody(["Do-3", "Sol-3", "Do-4", "Mi-4"]))
    assert all(0.0 <= item.confidence <= 1.0 for item in result.assignments)
    assert result.ambiguous() == sorted(result.ambiguous(), key=lambda item: item.confidence)
