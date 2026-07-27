"""Granularity collapse and upsample.

Every merge and expansion rule from `project-features.md` ("Merging rules") is
reproduced here, plus the documented X//2 -> X//4 -> X//8 chain.
"""

import time

import numpy as np
import pytest

from aitu_backend.matrix.granularity import (
    collapse_one_step,
    collapse_to,
    collapsed_frame_count,
    expand_columns,
    hierarchy_index,
    is_coarser,
    merge_pairs,
    retarget,
    steps_between,
    upsample_one_step,
    upsample_to,
)
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.validator import is_valid
from aitu_backend.progress import CallbackProgress, ProgressEvent
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep

DO4 = note_to_row("Do-4")
RE4 = note_to_row("Re-4")


def from_row(values: list[int], granularity: Granularity = Granularity.SEMIFUSA) -> PianoMatrix:
    grid = np.zeros((KEY_COUNT, len(values)), dtype=np.int8)
    grid[DO4] = np.array(values, dtype=np.int8)
    return PianoMatrix.from_dense(grid, granularity=granularity, tempo_bpm=60)


def row_of(matrix: PianoMatrix) -> list[int]:
    return matrix.grid[DO4].tolist()


# ------------------------------------------------------------------ hierarchy


def test_hierarchy_index_runs_coarse_to_fine() -> None:
    assert hierarchy_index(Granularity.REDONDA) == 0
    assert hierarchy_index("semifusa") == 6
    assert hierarchy_index("negra") < hierarchy_index("corchea")


def test_steps_between_is_signed() -> None:
    # Semifusa (6) down to corchea (3) is three collapses.
    assert steps_between("semifusa", "corchea") == 3
    assert steps_between("corchea", "semifusa") == -3
    assert steps_between("negra", "negra") == 0
    assert is_coarser("negra", than="corchea")


# --------------------------------------------------------------- merge rules


@pytest.mark.parametrize(
    "pair,expected",
    [
        ([1, 1], 1),
        ([1, 0], 1),
        ([1, -1], 1),
        ([0, 1], 1),
        ([0, 0], 0),
        ([-1, 0], -1),
        ([-1, 1], 1),
        ([-1, -1], -1),
    ],
)
def test_every_documented_merge_rule(pair: list[int], expected: int) -> None:
    grid = np.zeros((KEY_COUNT, 2), dtype=np.int8)
    grid[DO4] = np.array(pair, dtype=np.int8)
    assert int(merge_pairs(grid)[DO4, 0]) == expected


def test_merge_is_onset_then_sustain_then_silence() -> None:
    """The whole table in one sentence, checked against the table."""
    merged = row_of(collapse_one_step(from_row([1, 1, 0, 0, -1, -1, -1, 1])))
    assert merged == [1, 0, -1, 1]


def test_odd_column_counts_are_padded_not_truncated() -> None:
    collapsed = collapse_one_step(from_row([1, -1, 1]))
    assert collapsed.frame_count == 2
    assert row_of(collapsed) == [1, 1]


def test_collapse_halves_the_columns_and_doubles_the_time_step() -> None:
    matrix = from_row([1, -1, -1, -1, 0, 0, 1, -1], Granularity.SEMICORCHEA)
    assert matrix.time_step_seconds == pytest.approx(0.25)

    collapsed = collapse_one_step(matrix)
    assert collapsed.frame_count == 4
    assert collapsed.granularity is Granularity.CORCHEA
    assert collapsed.time_step_seconds == pytest.approx(0.5)
    # BPM is untouched: only the column meaning changed.
    assert collapsed.tempo_bpm == matrix.tempo_bpm
    # The piece still lasts the same wall-clock time.
    assert collapsed.duration_seconds == pytest.approx(matrix.duration_seconds)


def test_collapse_marks_the_processing_step() -> None:
    assert collapse_one_step(from_row([1, -1])).processing_step is MatrixProcessingStep.COLLAPSED


def test_collapsing_past_redonda_raises() -> None:
    with pytest.raises(ValueError, match="coarsest"):
        collapse_one_step(from_row([1, -1], Granularity.REDONDA))


# ------------------------------------------------------------- chained collapse


def test_the_documented_three_step_chain() -> None:
    """7th -> 4th: X -> X//2 -> X//4 -> X//8, exactly as the spec describes."""
    matrix = from_row([1, -1, -1, -1, -1, -1, -1, -1], Granularity.SEMIFUSA)
    collapsed = collapse_to(matrix, Granularity.CORCHEA)

    assert collapsed.frame_count == 1
    assert collapsed.granularity is Granularity.CORCHEA
    assert row_of(collapsed) == [1]
    assert collapsed.duration_seconds == pytest.approx(matrix.duration_seconds)


def test_collapse_chain_reports_one_progress_step_per_hierarchy_step() -> None:
    events: list[ProgressEvent] = []
    collapse_to(
        from_row([1, -1, 0, 0, 1, -1, 0, 0]),
        Granularity.CORCHEA,
        reporter=CallbackProgress(events.append),
    )
    stages = [event.message for event in events if event.message]
    assert stages[:3] == ["fusa", "semicorchea", "corchea"]


def test_collapse_to_the_same_granularity_returns_a_copy() -> None:
    matrix = from_row([1, -1])
    same = collapse_to(matrix, matrix.granularity)
    assert same == matrix
    assert same is not matrix


def test_collapse_to_a_finer_target_raises() -> None:
    with pytest.raises(ValueError, match="finer"):
        collapse_to(from_row([1, -1], Granularity.NEGRA), Granularity.CORCHEA)


@pytest.mark.parametrize(
    "step",
    [
        MatrixProcessingStep.COLLAPSED,
        MatrixProcessingStep.CLEAN,
        MatrixProcessingStep.TWO_HANDS,
    ],
)
def test_collapsing_a_processed_matrix_is_refused_by_default(step: MatrixProcessingStep) -> None:
    processed = from_row([1, -1, 0, 0]).with_grid(
        from_row([1, -1, 0, 0]).grid, processing_step=step
    )
    with pytest.raises(ValueError, match="already at the"):
        collapse_to(processed, Granularity.FUSA)
    # ... but is possible when the caller insists.
    forced = collapse_to(processed, Granularity.FUSA, allow_chaining=True)
    assert forced.granularity is Granularity.FUSA


def test_collapsed_frame_count_matches_reality() -> None:
    for frames in (1, 2, 3, 7, 8, 9, 100):
        matrix = PianoMatrix.empty(frames, granularity=Granularity.SEMIFUSA)
        collapsed = collapse_to(matrix, Granularity.SEMICORCHEA)  # two steps
        assert collapsed.frame_count == collapsed_frame_count(frames, 2)


# ------------------------------------------------------------------- upsample


@pytest.mark.parametrize("value,expected", [(0, [0, 0]), (1, [1, -1]), (-1, [-1, -1])])
def test_every_documented_expansion_rule(value: int, expected: list[int]) -> None:
    grid = np.zeros((KEY_COUNT, 1), dtype=np.int8)
    grid[DO4, 0] = value
    assert expand_columns(grid)[DO4].tolist() == expected


def test_upsample_doubles_the_columns_and_halves_the_time_step() -> None:
    matrix = from_row([1, -1, 0], Granularity.NEGRA)
    assert matrix.time_step_seconds == pytest.approx(1.0)

    finer = upsample_one_step(matrix)
    assert finer.frame_count == 6
    assert finer.granularity is Granularity.CORCHEA
    assert finer.time_step_seconds == pytest.approx(0.5)
    assert row_of(finer) == [1, -1, -1, -1, 0, 0]
    assert finer.duration_seconds == pytest.approx(matrix.duration_seconds)


def test_upsampling_past_semifusa_raises() -> None:
    with pytest.raises(ValueError, match="finest"):
        upsample_one_step(from_row([1], Granularity.SEMIFUSA))


def test_upsample_to_a_coarser_target_raises() -> None:
    with pytest.raises(ValueError, match="coarser"):
        upsample_to(from_row([1], Granularity.CORCHEA), Granularity.NEGRA)


def test_upsampled_matrices_stay_structurally_valid() -> None:
    matrix = from_row([1, -1, 0, 1, 0, 0], Granularity.NEGRA)
    assert is_valid(upsample_to(matrix, Granularity.SEMICORCHEA))


def test_collapsed_matrices_stay_structurally_valid() -> None:
    matrix = from_row([1, -1, -1, 0, 0, 1, -1, -1], Granularity.SEMIFUSA)
    assert is_valid(collapse_to(matrix, Granularity.SEMICORCHEA))


# -------------------------------------------------------------- irreversibility


def test_collapse_then_upsample_does_not_restore_the_original() -> None:
    """Collapsing is lossy — this is why the raw matrix is kept forever."""
    original = from_row([1, 0, 1, 0], Granularity.SEMIFUSA)
    collapsed = collapse_to(original, Granularity.FUSA)
    back = upsample_to(collapsed, Granularity.SEMIFUSA)

    assert back.frame_count == original.frame_count
    assert row_of(original) == [1, 0, 1, 0]
    assert row_of(back) == [1, -1, 1, -1]  # the silences became sustains
    assert back != original


def test_collapsing_is_associative_so_the_guard_is_about_the_other_steps() -> None:
    """Two chained collapses give the same cells as one multi-step collapse.

    `collapse_to` always walks one step at a time, so chaining changes nothing
    here. The `allow_chaining` guard exists to stop a *cleaned* or *split*
    matrix being collapsed — those steps are the lossy ones.
    """
    raw = from_row([1, 0, 0, -1, 0, 0, 1, 0], Granularity.SEMIFUSA)
    from_raw = collapse_to(raw, Granularity.SEMICORCHEA)
    chained = collapse_to(
        collapse_to(raw, Granularity.FUSA), Granularity.SEMICORCHEA, allow_chaining=True
    )
    assert row_of(from_raw) == row_of(chained)
    assert from_raw.processing_step is MatrixProcessingStep.COLLAPSED


# --------------------------------------------------------------------- retarget


def test_retarget_picks_the_direction() -> None:
    matrix = from_row([1, -1, 0, 0], Granularity.SEMICORCHEA)
    assert retarget(matrix, Granularity.CORCHEA).frame_count == 2
    assert retarget(matrix, Granularity.FUSA).frame_count == 8
    assert retarget(matrix, Granularity.SEMICORCHEA) == matrix


# ------------------------------------------------------------------ performance


def test_full_collapse_chain_is_fast_for_a_five_minute_piece() -> None:
    """Exit criterion: the Matrix tab's granularity switch must feel instant.

    Five minutes at fusa granularity and 120 BPM: 0.0625 s per column -> 4800
    frames. Collapse semifusa -> negra is four steps.
    """
    frames = 9600
    rng = np.random.default_rng(0)
    grid = rng.choice(
        np.array([0, 1, -1], dtype=np.int8), size=(KEY_COUNT, frames), p=[0.9, 0.05, 0.05]
    )
    matrix = PianoMatrix.from_dense(grid, granularity=Granularity.SEMIFUSA, tempo_bpm=120)

    started = time.perf_counter()
    collapsed = collapse_to(matrix, Granularity.NEGRA)
    elapsed = time.perf_counter() - started

    assert collapsed.frame_count == 600
    assert elapsed < 0.5, f"collapse chain took {elapsed:.3f}s"


# ------------------------------------------------------------- musical example


def test_a_scale_collapses_without_losing_notes() -> None:
    """Do Re Mi Fa Sol as semifusas -> one onset each at fusa granularity."""
    grid = np.zeros((KEY_COUNT, 10), dtype=np.int8)
    for index, note in enumerate(["Do-4", "Re-4", "Mi-4", "Fa-4", "Sol-4"]):
        row = note_to_row(note)
        grid[row, index * 2] = 1
        grid[row, index * 2 + 1] = -1

    matrix = PianoMatrix.from_dense(grid, granularity=Granularity.SEMIFUSA, tempo_bpm=60)
    collapsed = collapse_to(matrix, Granularity.FUSA)

    assert collapsed.frame_count == 5
    for index, note in enumerate(["Do-4", "Re-4", "Mi-4", "Fa-4", "Sol-4"]):
        assert collapsed.cell(note_to_row(note), index) == 1
    assert collapsed.grid[RE4].tolist() == [0, 1, 0, 0, 0]
