"""Piano matrix contracts: validation, key tables and lossless conversion."""

import pytest
from pydantic import ValidationError

from aitu_backend.matrix.convert import (
    dense_to_sparse,
    sparse_to_dense,
    to_dense_envelope,
    to_sparse_envelope,
)
from aitu_backend.matrix.keys import (
    KEY_COUNT,
    MIDDLE_C_ROW,
    build_grand_piano_rows,
    build_grand_piano_rows_en,
    es_to_en,
    midi_to_row,
    note_to_row,
    row_to_midi,
)
from aitu_backend.schemas.matrix import (
    GRANULARITY_CODES,
    GRANULARITY_HIERARCHY,
    Granularity,
    MatrixProcessingStep,
    PianoMatrixEnvelope,
    SparseCooMatrix,
    key_labels,
)

# --------------------------------------------------------------------------- keys


def test_row_order_spans_the_88_keys() -> None:
    rows = build_grand_piano_rows()
    assert len(rows) == KEY_COUNT
    assert rows[0] == "La-0"
    assert rows[-1] == "Do-8"


def test_english_names_match_scientific_pitch() -> None:
    english = build_grand_piano_rows_en()
    assert english[0] == "A0"
    assert english[-1] == "C8"
    assert es_to_en("Fa#-5") == "F#5"


def test_midi_mapping_anchors_on_a0_and_middle_c() -> None:
    assert row_to_midi(0) == 21
    assert row_to_midi(KEY_COUNT - 1) == 108
    assert midi_to_row(60) == note_to_row("Do-4") == MIDDLE_C_ROW
    with pytest.raises(ValueError):
        midi_to_row(20)
    with pytest.raises(ValueError):
        note_to_row("Xy-4")


def test_key_labels_carry_both_languages() -> None:
    labels = key_labels()
    assert len(labels) == KEY_COUNT
    assert (labels[0].es, labels[0].en, labels[0].row) == ("La-0", "A0", 0)
    assert labels[MIDDLE_C_ROW].en == "C4"


# --------------------------------------------------------------- granularity


def test_granularity_beats_and_seconds() -> None:
    assert Granularity.NEGRA.beats == 1.0
    assert Granularity.SEMICORCHEA.beats == 0.25
    assert Granularity.FUSA.beats == 0.125
    # At 60 BPM one negra is one second, so a semicorchea is 0.25 s.
    assert Granularity.SEMICORCHEA.seconds(60) == 0.25
    assert Granularity.CORCHEA.seconds(120) == 0.25


def test_granularity_hierarchy_is_coarse_to_fine() -> None:
    beats = [gran.beats for gran in GRANULARITY_HIERARCHY]
    assert beats == sorted(beats, reverse=True)
    assert len(GRANULARITY_CODES) == len(GRANULARITY_HIERARCHY)
    assert GRANULARITY_CODES[Granularity.NEGRA] == "gn"
    assert GRANULARITY_CODES[Granularity.SEMICORCHEA] == "gsc"


# ------------------------------------------------------------------ sparse model


def _sample_sparse() -> SparseCooMatrix:
    """Do-4 struck then held two frames, Mi-4 struck on the last frame."""
    do, mi = note_to_row("Do-4"), note_to_row("Mi-4")
    return SparseCooMatrix(
        shape=[KEY_COUNT, 4],
        rows=[do, do, do, mi],
        cols=[0, 1, 2, 3],
        onset=[do, -1, -1, mi],
    )


def test_sparse_matrix_accepts_a_valid_payload() -> None:
    matrix = _sample_sparse()
    assert matrix.frame_count == 4
    assert not matrix.is_empty()


def test_sparse_matrix_rejects_a_non_piano_row_count() -> None:
    with pytest.raises(ValidationError, match="88 rows"):
        SparseCooMatrix(shape=[64, 2], rows=[], cols=[], onset=[])


def test_sparse_matrix_rejects_unparallel_arrays() -> None:
    with pytest.raises(ValidationError, match="parallel arrays"):
        SparseCooMatrix(shape=[KEY_COUNT, 2], rows=[0, 1], cols=[0], onset=[0, -1])


def test_sparse_matrix_rejects_a_bad_onset_marker() -> None:
    with pytest.raises(ValidationError, match="onset"):
        SparseCooMatrix(shape=[KEY_COUNT, 1], rows=[5], cols=[0], onset=[7])


def test_sparse_matrix_rejects_out_of_range_cells() -> None:
    with pytest.raises(ValidationError, match="outside"):
        SparseCooMatrix(shape=[KEY_COUNT, 1], rows=[5], cols=[3], onset=[5])


# -------------------------------------------------------------------- converters


def test_sparse_to_dense_uses_frames_as_rows() -> None:
    grid = sparse_to_dense(_sample_sparse())
    do, mi = note_to_row("Do-4"), note_to_row("Mi-4")
    assert len(grid) == 4
    assert all(len(frame) == KEY_COUNT for frame in grid)
    assert [frame[do] for frame in grid] == [1, -1, -1, 0]
    assert [frame[mi] for frame in grid] == [0, 0, 0, 1]


def test_dense_to_sparse_round_trip_is_lossless() -> None:
    original = _sample_sparse()
    restored = dense_to_sparse(sparse_to_dense(original))
    assert restored.model_dump() == original.model_dump()


def test_coo_arrays_come_back_sorted_by_column_then_row() -> None:
    do, mi = note_to_row("Do-4"), note_to_row("Mi-4")
    # Same cells, deliberately unsorted on the way in.
    unsorted = SparseCooMatrix(
        shape=[KEY_COUNT, 2],
        rows=[mi, do, do],
        cols=[0, 1, 0],
        onset=[mi, do, do],
    )
    restored = dense_to_sparse(sparse_to_dense(unsorted))
    pairs = list(zip(restored.cols, restored.rows))
    assert pairs == sorted(pairs)


def _sample_envelope(sparse: bool = True) -> PianoMatrixEnvelope:
    return PianoMatrixEnvelope(
        tempo_bpm=60,
        time_step_seconds=0.25,
        granularity=Granularity.SEMICORCHEA,
        matrix_processing_step=MatrixProcessingStep.CLEAN,
        sparse=sparse,
        matrix=_sample_sparse() if sparse else None,
        dense_matrix=None if sparse else sparse_to_dense(_sample_sparse()),
    )


def test_envelope_round_trip_dense_sparse_dense_is_lossless() -> None:
    """dense json -> model -> sparse json -> model -> dense json."""
    dense_first = to_dense_envelope(_sample_envelope())
    as_json = dense_first.model_dump(by_alias=True)

    reparsed = PianoMatrixEnvelope.model_validate(as_json)
    sparse = to_sparse_envelope(reparsed)
    assert sparse.sparse is True
    assert sparse.dense_matrix is None

    dense_again = to_dense_envelope(
        PianoMatrixEnvelope.model_validate(sparse.model_dump(by_alias=True))
    )
    assert dense_again.dense_matrix == dense_first.dense_matrix
    assert dense_again.column_headers == dense_first.column_headers
    assert dense_again.row_timestamps == dense_first.row_timestamps


def test_dense_export_carries_headers_and_timestamps() -> None:
    dense = to_dense_envelope(_sample_envelope())
    assert dense.column_headers is not None
    assert len(dense.column_headers) == KEY_COUNT
    assert dense.column_headers[0].es == "La-0"
    # 4 frames at 0.25 s each.
    assert dense.row_timestamps == [0.0, 0.25, 0.5, 0.75]


# --------------------------------------------------------------------- envelope


def test_envelope_rejects_both_hand_forms_at_once() -> None:
    with pytest.raises(ValidationError, match="never both or neither"):
        PianoMatrixEnvelope(
            tempo_bpm=60,
            time_step_seconds=0.25,
            granularity=Granularity.SEMICORCHEA,
            matrix_processing_step=MatrixProcessingStep.TWO_HANDS,
            matrix=_sample_sparse(),
            r_matrix=_sample_sparse(),
            l_matrix=_sample_sparse(),
        )


def test_envelope_requires_hands_to_align() -> None:
    short = SparseCooMatrix(shape=[KEY_COUNT, 2], rows=[], cols=[], onset=[])
    with pytest.raises(ValidationError, match="same number of time frames"):
        PianoMatrixEnvelope(
            tempo_bpm=60,
            time_step_seconds=0.25,
            granularity=Granularity.SEMICORCHEA,
            matrix_processing_step=MatrixProcessingStep.TWO_HANDS,
            r_matrix=_sample_sparse(),
            l_matrix=short,
        )


def test_dense_envelope_rejects_a_foreign_cell_value() -> None:
    grid = sparse_to_dense(_sample_sparse())
    grid[0][0] = 2
    with pytest.raises(ValidationError, match="only 1, -1 and 0"):
        PianoMatrixEnvelope(
            tempo_bpm=60,
            time_step_seconds=0.25,
            granularity=Granularity.SEMICORCHEA,
            matrix_processing_step=MatrixProcessingStep.CLEAN,
            sparse=False,
            dense_matrix=grid,
        )


def test_envelope_uses_camel_case_on_the_wire() -> None:
    payload = _sample_envelope().model_dump(by_alias=True)
    assert "tempoBpm" in payload
    assert "matrixProcessingStep" in payload
    assert "tempo_bpm" not in payload
