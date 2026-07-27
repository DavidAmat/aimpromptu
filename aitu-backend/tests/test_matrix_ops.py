"""Structural matrix operations: transpose, insert, slice/delete/replace, edits."""

import numpy as np
import pytest

from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.ops import (
    EditError,
    add_onset,
    append_silence,
    delete_cells,
    delete_note,
    delete_range,
    extend_sustain,
    fit_to_width,
    insert_columns,
    insert_figure,
    replace_range,
    set_cell,
    slice_range,
    transpose,
    transpose_hands,
)
from aitu_backend.matrix.validator import is_valid
from aitu_backend.schemas.matrix import Granularity

DO4 = note_to_row("Do-4")
RE4 = note_to_row("Re-4")
MI4 = note_to_row("Mi-4")


def build(
    rows: dict[int, list[int]], frames: int, granularity=Granularity.SEMICORCHEA
) -> PianoMatrix:
    grid = np.zeros((KEY_COUNT, frames), dtype=np.int8)
    for row, values in rows.items():
        grid[row, : len(values)] = np.array(values, dtype=np.int8)
    return PianoMatrix.from_dense(grid, granularity=granularity, tempo_bpm=60)


def sample() -> PianoMatrix:
    """Do-4 held two columns, Re-4 struck, Mi-4 struck and held."""
    return build({DO4: [1, -1, 0, 0], RE4: [0, 0, 1, 0], MI4: [0, 0, 0, 1]}, frames=4)


# ---------------------------------------------------------------- transposition


def test_transpose_up_shifts_every_row() -> None:
    report = transpose(sample(), 2)
    assert report.matrix.grid[DO4 + 2].tolist() == [1, -1, 0, 0]
    assert report.matrix.grid[RE4 + 2].tolist() == [0, 0, 1, 0]
    assert report.lossless
    assert "nothing lost" in report.describe()


def test_transpose_down_shifts_every_row() -> None:
    report = transpose(sample(), -3)
    assert report.matrix.grid[DO4 - 3].tolist() == [1, -1, 0, 0]
    assert report.lossless


def test_transposing_by_zero_is_a_copy() -> None:
    matrix = sample()
    report = transpose(matrix, 0)
    assert np.array_equal(report.matrix.grid, matrix.grid)
    assert report.matrix is not matrix


def test_notes_pushed_off_the_top_are_dropped_and_reported() -> None:
    top = build({note_to_row("Do-8"): [1, -1]}, frames=2)
    report = transpose(top, 1)

    assert report.matrix.is_empty()
    assert report.dropped_cells == 2
    assert report.dropped_notes == ["Do-8"]
    assert not report.lossless
    assert "fell off the keyboard" in report.describe()


def test_notes_pushed_off_the_bottom_are_dropped_and_reported() -> None:
    bottom = build({note_to_row("La-0"): [1]}, frames=1)
    report = transpose(bottom, -1)
    assert report.dropped_notes == ["La-0"]


def test_transposition_keeps_the_shape_and_metadata() -> None:
    matrix = sample()
    result = transpose(matrix, 5).matrix
    assert result.shape == matrix.shape
    assert result.granularity is matrix.granularity
    assert result.tempo_bpm == matrix.tempo_bpm


def test_transposition_does_not_mutate_its_input() -> None:
    matrix = sample()
    before = matrix.to_array()
    transpose(matrix, 4)
    assert np.array_equal(matrix.grid, before)


def test_both_hands_transpose_together() -> None:
    right, left = transpose_hands(sample(), sample(), 2)
    assert right.semitones == left.semitones == 2
    assert np.array_equal(right.matrix.grid, left.matrix.grid)


# ------------------------------------------------------------ column insertion


def test_inserting_columns_widens_the_matrix() -> None:
    result = insert_columns(sample(), at_frame=2, count=3)
    assert result.frame_count == 7
    assert result.grid[RE4].tolist() == [0, 0, 0, 0, 0, 1, 0]


def test_inserting_at_the_start_and_end_works() -> None:
    matrix = sample()
    assert insert_columns(matrix, 0, 2).frame_count == 6
    assert insert_columns(matrix, matrix.frame_count, 2).frame_count == 6
    assert append_silence(matrix, 2).frame_count == 6


def test_inserting_zero_columns_is_a_copy() -> None:
    matrix = sample()
    assert np.array_equal(insert_columns(matrix, 1, 0).grid, matrix.grid)


def test_a_note_split_by_an_insertion_restarts_after_the_rest() -> None:
    """The sustain would be orphaned, so it becomes a fresh onset."""
    matrix = build({DO4: [1, -1, -1, -1]}, frames=4)
    result = insert_columns(matrix, at_frame=2, count=2)
    assert result.grid[DO4].tolist() == [1, -1, 0, 0, 1, -1]
    assert is_valid(result)


def test_insertion_bounds_are_checked() -> None:
    matrix = sample()
    with pytest.raises(ValueError, match="outside"):
        insert_columns(matrix, at_frame=99, count=1)
    with pytest.raises(ValueError, match="negative"):
        insert_columns(matrix, at_frame=0, count=-1)


def test_inserting_a_figure_converts_to_columns() -> None:
    matrix = sample()  # semicorchea granularity
    assert insert_figure(matrix, 0, Granularity.NEGRA).frame_count == 4 + 4
    assert insert_figure(matrix, 0, Granularity.CORCHEA).frame_count == 4 + 2
    assert insert_figure(matrix, 0, Granularity.NEGRA, repeats=2).frame_count == 4 + 8


def test_an_addition_finer_than_the_piece_is_refused() -> None:
    """A negra-granularity piece cannot accept a corchea rest."""
    matrix = build({DO4: [1]}, frames=1, granularity=Granularity.NEGRA)
    with pytest.raises(ValueError, match="finer than"):
        insert_figure(matrix, 0, Granularity.CORCHEA)


def test_repeats_must_be_positive() -> None:
    with pytest.raises(ValueError, match="repeats"):
        insert_figure(sample(), 0, Granularity.NEGRA, repeats=0)


# ------------------------------------------------------- slice / delete / replace


def test_slice_range_normalizes_a_note_cut_in_half() -> None:
    matrix = build({DO4: [1, -1, -1, -1]}, frames=4)
    piece = slice_range(matrix, 1, 4)
    assert piece.frame_count == 3
    assert piece.grid[DO4].tolist() == [1, -1, -1]  # the orphan sustain became an onset
    assert is_valid(piece)


def test_delete_range_closes_the_gap() -> None:
    result = delete_range(sample(), 1, 3)
    assert result.frame_count == 2
    assert result.grid[DO4].tolist() == [1, 0]
    assert result.grid[MI4].tolist() == [0, 1]


def test_delete_range_normalizes_the_seam() -> None:
    """Deleting an onset leaves its sustains orphaned; they become an onset."""
    matrix = build({DO4: [1, -1, -1, -1]}, frames=4)
    result = delete_range(matrix, 0, 1)
    assert result.grid[DO4].tolist() == [1, -1, -1]
    assert is_valid(result)


def test_range_bounds_are_checked() -> None:
    matrix = sample()
    for start, end in [(-1, 2), (0, 99), (3, 1)]:
        with pytest.raises(ValueError, match="outside"):
            delete_range(matrix, start, end)


def test_fit_to_width_trims_and_pads() -> None:
    matrix = sample()
    assert fit_to_width(matrix, 2).frame_count == 2
    assert fit_to_width(matrix, 6).frame_count == 6
    assert fit_to_width(matrix, 6).grid[:, 4:].sum() == 0
    assert np.array_equal(fit_to_width(matrix, 4).grid, matrix.grid)


def test_replace_range_keeps_the_total_width() -> None:
    """The editing rule: surrounding music must not move."""
    matrix = sample()
    replacement = build({MI4: [1, -1, -1, -1, -1, -1]}, frames=6)

    result = replace_range(matrix, 1, 3, replacement)

    assert result.frame_count == matrix.frame_count
    # The replacement was trimmed to exactly two columns.
    assert result.grid[MI4].tolist() == [0, 1, -1, 1]
    # Everything outside the range is untouched.
    assert result.grid[DO4].tolist() == [1, 0, 0, 0]


def test_replace_range_pads_a_short_replacement() -> None:
    matrix = sample()
    replacement = build({MI4: [1]}, frames=1)
    result = replace_range(matrix, 0, 3, replacement)
    assert result.frame_count == 4
    assert result.grid[MI4].tolist() == [1, 0, 0, 1]


def test_replace_range_leaves_a_valid_matrix() -> None:
    matrix = build({DO4: [1, -1, -1, -1]}, frames=4)
    result = replace_range(matrix, 0, 2, build({RE4: [1, -1]}, frames=2))
    assert is_valid(result)


# ------------------------------------------------------------------ cell edits


def test_add_onset_places_a_strike() -> None:
    result = add_onset(sample(), RE4, 0)
    assert result.grid[RE4].tolist() == [1, 0, 1, 0]


def test_add_onset_over_a_sustain_shortens_the_previous_note() -> None:
    matrix = build({DO4: [1, -1, -1]}, frames=3)
    result = add_onset(matrix, DO4, 2)
    assert result.grid[DO4].tolist() == [1, -1, 1]
    assert is_valid(result)


def test_extend_sustain_after_an_onset() -> None:
    matrix = build({DO4: [1, 0, 0]}, frames=3)
    result = extend_sustain(matrix, DO4, 1)
    assert result.grid[DO4].tolist() == [1, -1, 0]


def test_extend_sustain_after_a_sustain() -> None:
    matrix = build({DO4: [1, -1, 0]}, frames=3)
    assert extend_sustain(matrix, DO4, 2).grid[DO4].tolist() == [1, -1, -1]


def test_extend_sustain_over_silence_is_refused() -> None:
    matrix = build({DO4: [1, 0, 0]}, frames=3)
    with pytest.raises(EditError, match="nothing is sounding"):
        extend_sustain(matrix, DO4, 2)


def test_extend_sustain_in_the_first_column_is_refused() -> None:
    with pytest.raises(EditError, match="the start of the piece"):
        extend_sustain(sample(), RE4, 0)


def test_delete_note_removes_the_whole_run() -> None:
    matrix = build({DO4: [1, -1, -1, 0]}, frames=4)
    for clicked in (0, 1, 2):
        assert delete_note(matrix, DO4, clicked).grid[DO4].tolist() == [0, 0, 0, 0]


def test_delete_note_leaves_neighbouring_notes_alone() -> None:
    matrix = build({DO4: [1, -1, 1, -1]}, frames=4)
    result = delete_note(matrix, DO4, 3)
    assert result.grid[DO4].tolist() == [1, -1, 0, 0]


def test_deleting_silence_is_a_no_op() -> None:
    matrix = sample()
    assert np.array_equal(delete_note(matrix, RE4, 0).grid, matrix.grid)


def test_delete_cells_handles_a_multi_select() -> None:
    matrix = build({DO4: [1, -1], RE4: [1, -1], MI4: [1, -1]}, frames=2)
    result = delete_cells(matrix, [(DO4, 1), (MI4, 0)])
    assert result.grid[DO4].tolist() == [0, 0]
    assert result.grid[MI4].tolist() == [0, 0]
    assert result.grid[RE4].tolist() == [1, -1]


def test_set_cell_dispatches_on_the_value() -> None:
    matrix = build({DO4: [1, 0, 0]}, frames=3)
    assert set_cell(matrix, DO4, 1, 1).grid[DO4].tolist() == [1, 1, 0]
    assert set_cell(matrix, DO4, 1, -1).grid[DO4].tolist() == [1, -1, 0]
    assert set_cell(matrix, DO4, 0, 0).grid[DO4].tolist() == [0, 0, 0]


def test_set_cell_rejects_a_foreign_value() -> None:
    with pytest.raises(EditError, match="1, -1 or 0"):
        set_cell(sample(), DO4, 0, 7)


def test_cell_bounds_are_checked() -> None:
    matrix = sample()
    with pytest.raises(EditError, match="88-key range"):
        add_onset(matrix, 200, 0)
    with pytest.raises(EditError, match="Column"):
        add_onset(matrix, DO4, 99)


def test_edits_never_mutate_their_input() -> None:
    matrix = sample()
    before = matrix.to_array()
    add_onset(matrix, RE4, 0)
    delete_note(matrix, DO4, 0)
    assert np.array_equal(matrix.grid, before)


def test_every_edit_leaves_a_valid_matrix() -> None:
    matrix = sample()
    assert is_valid(add_onset(matrix, RE4, 1))
    assert is_valid(delete_note(matrix, DO4, 0))
    assert is_valid(extend_sustain(matrix, RE4, 3))
