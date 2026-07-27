"""Transition rules: every legal and illegal pair, plus normalization."""

import itertools

import numpy as np
import pytest

from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.text_notation import sequence_to_sparse_payload
from aitu_backend.matrix.validator import (
    ALLOWED_TRANSITIONS,
    TransitionError,
    is_valid,
    normalize,
    normalized_violation_count,
    validate,
    validate_strict,
)
from aitu_backend.schemas.matrix import ONSET, SILENCE, SUSTAIN

DO4 = note_to_row("Do-4")
RE4 = note_to_row("Re-4")


def from_row(values: list[int], row: int = DO4) -> PianoMatrix:
    """A matrix whose only non-silent row is ``row``, holding ``values``."""
    grid = np.zeros((KEY_COUNT, len(values)), dtype=np.int8)
    grid[row] = np.array(values, dtype=np.int8)
    return PianoMatrix.from_dense(grid)


# --------------------------------------------------------------- the rule table


def test_only_silence_to_sustain_is_illegal() -> None:
    illegal = [
        (previous, nxt)
        for previous, nxt in itertools.product((SILENCE, ONSET, SUSTAIN), repeat=2)
        if nxt not in ALLOWED_TRANSITIONS[previous]
    ]
    assert illegal == [(SILENCE, SUSTAIN)]


@pytest.mark.parametrize(
    "previous,nxt",
    [
        (SILENCE, SILENCE),
        (SILENCE, ONSET),
        (ONSET, ONSET),
        (ONSET, SUSTAIN),
        (ONSET, SILENCE),
        (SUSTAIN, ONSET),
        (SUSTAIN, SUSTAIN),
        (SUSTAIN, SILENCE),
    ],
)
def test_every_legal_pair_validates(previous: int, nxt: int) -> None:
    # Prefix with an onset so `previous` itself is reachable legally.
    prefix = [] if previous == SILENCE else [ONSET]
    matrix = from_row(prefix + [previous, nxt])
    assert validate(matrix) == []
    assert is_valid(matrix)


def test_silence_to_sustain_is_reported() -> None:
    matrix = from_row([SILENCE, SUSTAIN])
    violations = validate(matrix)

    assert len(violations) == 1
    violation = violations[0]
    assert (violation.row, violation.column) == (DO4, 1)
    assert violation.key == "Do-4"
    assert violation.previous == SILENCE
    assert violation.found == SUSTAIN
    assert "Do-4 column 1" in violation.message
    assert not is_valid(matrix)


def test_a_sustain_in_the_very_first_column_is_illegal() -> None:
    """The chain starts at silence, so column 0 cannot hold a sustain."""
    violations = validate(from_row([SUSTAIN, SUSTAIN]))
    assert len(violations) == 1
    assert violations[0].column == 0
    assert "the start of the piece" in violations[0].message


def test_a_sustain_after_a_release_is_illegal() -> None:
    violations = validate(from_row([ONSET, SUSTAIN, SILENCE, SUSTAIN]))
    assert [violation.column for violation in violations] == [3]


def test_violations_are_ordered_by_column_then_row() -> None:
    grid = np.zeros((KEY_COUNT, 4), dtype=np.int8)
    grid[RE4, 1] = SUSTAIN
    grid[DO4, 1] = SUSTAIN
    grid[DO4, 3] = SUSTAIN
    violations = validate(PianoMatrix.from_dense(grid))
    assert [(v.column, v.row) for v in violations] == sorted((v.column, v.row) for v in violations)
    assert len(violations) == 3


# ---------------------------------------------------------------- strict mode


def test_validate_strict_passes_a_clean_matrix_through() -> None:
    matrix = from_row([ONSET, SUSTAIN, SILENCE])
    assert validate_strict(matrix) is matrix


def test_validate_strict_raises_with_every_violation_attached() -> None:
    matrix = from_row([SUSTAIN, SILENCE, SUSTAIN])
    with pytest.raises(TransitionError) as caught:
        validate_strict(matrix)
    assert len(caught.value.violations) == 2
    assert "illegal transition" in str(caught.value)


def test_error_message_truncates_a_long_violation_list() -> None:
    grid = np.zeros((KEY_COUNT, 1), dtype=np.int8)
    grid[:10, 0] = SUSTAIN
    with pytest.raises(TransitionError, match=r"\+5 more"):
        validate_strict(PianoMatrix.from_dense(grid))


# --------------------------------------------------------------- normalization


def test_normalize_promotes_an_orphan_sustain_to_an_onset() -> None:
    fixed = normalize(from_row([SILENCE, SUSTAIN, SUSTAIN]))
    assert fixed.grid[DO4].tolist() == [SILENCE, ONSET, SUSTAIN]
    assert is_valid(fixed)


def test_normalize_fixes_a_leading_sustain() -> None:
    fixed = normalize(from_row([SUSTAIN, SUSTAIN, SILENCE]))
    assert fixed.grid[DO4].tolist() == [ONSET, SUSTAIN, SILENCE]


def test_normalize_fixes_each_run_independently() -> None:
    fixed = normalize(from_row([SUSTAIN, SILENCE, SUSTAIN, SUSTAIN, SILENCE, SUSTAIN]))
    assert fixed.grid[DO4].tolist() == [ONSET, SILENCE, ONSET, SUSTAIN, SILENCE, ONSET]
    assert is_valid(fixed)


def test_normalize_leaves_a_valid_matrix_untouched() -> None:
    matrix = from_row([ONSET, SUSTAIN, SUSTAIN, SILENCE, ONSET])
    assert np.array_equal(normalize(matrix).grid, matrix.grid)


def test_normalize_does_not_mutate_its_input() -> None:
    matrix = from_row([SILENCE, SUSTAIN])
    normalize(matrix)
    assert matrix.cell(DO4, 1) == SUSTAIN


def test_normalize_keeps_the_metadata() -> None:
    matrix = from_row([SILENCE, SUSTAIN])
    fixed = normalize(matrix)
    assert fixed.granularity is matrix.granularity
    assert fixed.tempo_bpm == matrix.tempo_bpm
    assert fixed.processing_step is matrix.processing_step


def test_normalize_is_idempotent() -> None:
    once = normalize(from_row([SUSTAIN, SUSTAIN, SILENCE, SUSTAIN]))
    assert np.array_equal(normalize(once).grid, once.grid)


def test_violation_count_matches_what_normalize_changes() -> None:
    matrix = from_row([SUSTAIN, SILENCE, SUSTAIN, SUSTAIN])
    assert normalized_violation_count(matrix) == 2
    changed = int(np.count_nonzero(normalize(matrix).grid != matrix.grid))
    assert changed == 2


# ---------------------------------------------------- notation-spec agreement


def test_the_text_notation_parser_already_produces_valid_matrices() -> None:
    """Its "cannot hold a key that was never struck" rule is the same rule."""
    matrix = PianoMatrix.from_coo_payload(
        sequence_to_sparse_payload(["Do-4", "Do-4", "*Re-4", "Re-4", "", "Mi-4"])
    )
    assert validate(matrix) == []


def test_repeated_onsets_stay_separate_notes() -> None:
    """Four strikes are four notes; the validator must not merge them."""
    matrix = PianoMatrix.from_coo_payload(
        sequence_to_sparse_payload(["*Re-4", "*Re-4", "*Re-4", "*Re-4"])
    )
    assert validate(matrix) == []
    assert matrix.grid[RE4].tolist() == [ONSET, ONSET, ONSET, ONSET]


def test_one_onset_plus_sustains_stays_one_note() -> None:
    matrix = PianoMatrix.from_coo_payload(
        sequence_to_sparse_payload(["*Re-4", "Re-4", "Re-4", "Re-4"])
    )
    assert validate(matrix) == []
    assert matrix.grid[RE4].tolist() == [ONSET, SUSTAIN, SUSTAIN, SUSTAIN]


def test_an_empty_matrix_is_valid() -> None:
    assert validate(PianoMatrix.empty(0)) == []
    assert validate(PianoMatrix.empty(8)) == []
