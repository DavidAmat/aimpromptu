"""PianoMatrix: construction, timing math, conversions and round-trips.

The timing assertions reproduce the worked examples in
`context/music/notation-logic/01-matrix-notation-logic.md`.
"""

from pathlib import Path

import numpy as np
import pytest

from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import (
    HIERARCHY,
    PianoMatrix,
    beats_per_column,
    seconds_per_column,
)
from aitu_backend.matrix.text_notation import sequence_to_sparse_payload
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep

DO4 = note_to_row("Do-4")
RE4 = note_to_row("Re-4")
MI4 = note_to_row("Mi-4")


def sample(granularity: Granularity = Granularity.SEMICORCHEA, bpm: float = 60.0) -> PianoMatrix:
    """Do-4 struck and held two frames, then Mi-4 struck."""
    return PianoMatrix.from_coo_payload(
        sequence_to_sparse_payload(["*Do-4", "Do-4", "Do-4", "*Mi-4"]),
        granularity=granularity,
        tempo_bpm=bpm,
    )


# ----------------------------------------------------------------- construction


def test_empty_matrix_is_silent_and_correctly_shaped() -> None:
    matrix = PianoMatrix.empty(16)
    assert matrix.shape == (KEY_COUNT, 16)
    assert matrix.frame_count == 16
    assert matrix.is_empty()
    assert matrix.active_rows() == []


def test_from_coo_payload_places_onsets_and_sustains() -> None:
    matrix = sample()
    assert matrix.frame_count == 4
    assert matrix.cell(DO4, 0) == 1
    assert matrix.cell(DO4, 1) == -1
    assert matrix.cell(DO4, 2) == -1
    assert matrix.cell(DO4, 3) == 0
    assert matrix.cell(MI4, 3) == 1
    assert matrix.active_rows() == sorted([DO4, MI4])
    assert matrix.onsets_in_column(0) == [DO4]
    assert matrix.onsets_in_column(3) == [MI4]


def test_from_dense_accepts_both_orientations() -> None:
    keys_by_frames = np.zeros((KEY_COUNT, 3), dtype=np.int8)
    keys_by_frames[RE4, 0] = 1
    frames_by_keys = keys_by_frames.T

    a = PianoMatrix.from_dense(keys_by_frames)
    b = PianoMatrix.from_dense(frames_by_keys, frames_as_rows=True)
    assert a == b
    assert b.cell(RE4, 0) == 1


def test_rejects_a_non_piano_row_count() -> None:
    with pytest.raises(ValueError, match="88 x N"):
        PianoMatrix(
            grid=np.zeros((12, 4), dtype=np.int8), granularity=Granularity.NEGRA, tempo_bpm=60
        )


def test_rejects_illegal_cell_values() -> None:
    grid = np.zeros((KEY_COUNT, 2), dtype=np.int8)
    grid[0, 0] = 2
    with pytest.raises(ValueError, match="Illegal cell values"):
        PianoMatrix(grid=grid, granularity=Granularity.NEGRA, tempo_bpm=60)


def test_rejects_a_non_positive_tempo() -> None:
    with pytest.raises(ValueError, match="tempo_bpm"):
        PianoMatrix.empty(4, tempo_bpm=0)


# ------------------------------------------------------------------ timing math


def test_hierarchy_is_coarse_to_fine() -> None:
    assert HIERARCHY == [
        "redonda",
        "blanca",
        "negra",
        "corchea",
        "semicorchea",
        "fusa",
        "semifusa",
    ]


def test_beats_per_column_uses_the_negra_as_the_beat() -> None:
    assert beats_per_column("negra") == 1.0
    assert beats_per_column("corchea") == 0.5
    assert beats_per_column(Granularity.SEMICORCHEA) == 0.25
    assert beats_per_column("fusa") == 0.125


@pytest.mark.parametrize(
    "granularity,bpm,expected",
    [
        # From the doc's table: "Choosing resolution (linking BPM to column width)".
        ("corchea", 60, 0.5),
        ("corchea", 120, 0.25),
        ("semicorchea", 120, 0.125),
        ("semicorchea", 60, 0.25),
    ],
)
def test_seconds_per_column_matches_the_documented_table(
    granularity: str, bpm: float, expected: float
) -> None:
    assert seconds_per_column(granularity, bpm) == pytest.approx(expected)


def test_default_example_from_the_docs() -> None:
    """60 BPM with a 0.5 s column is one corchea per column."""
    matrix = PianoMatrix.empty(8, granularity=Granularity.CORCHEA, tempo_bpm=60)
    assert matrix.time_step_seconds == pytest.approx(0.5)
    assert matrix.beats_per_column == 0.5
    # 8 columns of 0.5 beat = 4 beats = one whole note.
    assert matrix.frame_to_beats(8) == 4.0
    assert matrix.duration_seconds == pytest.approx(4.0)


def test_frame_and_time_conversions_are_inverse() -> None:
    matrix = sample(Granularity.SEMICORCHEA, 60)  # 0.25 s per column
    assert matrix.frame_to_time(0) == 0.0
    assert matrix.frame_to_time(3) == pytest.approx(0.75)
    assert matrix.time_to_frame(0.0) == 0
    assert matrix.time_to_frame(0.74) == 2
    assert matrix.time_to_frame(0.75) == 3
    assert matrix.frames_for_seconds(1.0) == 4


def test_two_frame_note_at_the_documented_default() -> None:
    """Doc example: *Re-4 held over 2 frames at 60 BPM / 0.5 s = 1 beat."""
    matrix = PianoMatrix.from_coo_payload(
        sequence_to_sparse_payload(["*Re-4", "Re-4"]),
        granularity=Granularity.CORCHEA,
        tempo_bpm=60,
    )
    assert matrix.frame_to_beats(2) == 1.0
    assert matrix.duration_seconds == pytest.approx(1.0)


def test_negative_times_are_rejected() -> None:
    matrix = sample()
    with pytest.raises(ValueError):
        matrix.time_to_frame(-0.1)
    with pytest.raises(ValueError):
        matrix.frames_for_seconds(-1)


# ------------------------------------------------------------------ round-trips


def test_dense_round_trip_in_both_orientations() -> None:
    matrix = sample()
    assert PianoMatrix.from_dense(matrix.to_dense()) == matrix
    assert (
        PianoMatrix.from_dense(matrix.to_dense(frames_as_rows=True), frames_as_rows=True) == matrix
    )


def test_coo_payload_round_trip() -> None:
    matrix = sample()
    payload = matrix.to_coo_payload()
    assert payload.shape == [KEY_COUNT, 4]
    assert PianoMatrix.from_coo_payload(payload) == matrix


def test_coo_payload_is_sorted_by_column_then_row() -> None:
    grid = np.zeros((KEY_COUNT, 3), dtype=np.int8)
    grid[MI4, 0] = 1
    grid[DO4, 0] = 1
    grid[DO4, 2] = 1
    payload = PianoMatrix.from_dense(grid).to_coo_payload()
    assert list(zip(payload.cols, payload.rows)) == sorted(zip(payload.cols, payload.rows))


def test_envelope_round_trip_sparse_and_dense() -> None:
    matrix = sample()
    matrix.processing_step = MatrixProcessingStep.CLEAN
    for sparse in (True, False):
        envelope = matrix.to_envelope(sparse=sparse)
        assert envelope.granularity is Granularity.SEMICORCHEA
        assert envelope.time_step_seconds == pytest.approx(0.25)
        assert PianoMatrix.from_envelope(envelope) == matrix


def test_npz_round_trip(tmp_path: Path) -> None:
    matrix = sample()
    target = tmp_path / "piano_matrix_v1_gsc.npz"
    matrix.save_npz(target)
    restored = PianoMatrix.load_npz(target, granularity=matrix.granularity, tempo_bpm=60)
    assert restored == matrix


def test_empty_matrix_survives_every_round_trip(tmp_path: Path) -> None:
    matrix = PianoMatrix.empty(5, granularity=Granularity.NEGRA, tempo_bpm=90)
    assert PianoMatrix.from_coo_payload(matrix.to_coo_payload()).frame_count == 5
    target = tmp_path / "empty.npz"
    matrix.save_npz(target)
    assert PianoMatrix.load_npz(target, Granularity.NEGRA, 90) == matrix


# -------------------------------------------------------------------- structure


def test_copy_does_not_share_the_grid() -> None:
    matrix = sample()
    clone = matrix.copy()
    clone.grid[RE4, 0] = 1
    assert matrix.cell(RE4, 0) == 0
    assert clone != matrix


def test_to_array_returns_a_copy() -> None:
    matrix = sample()
    array = matrix.to_array()
    array[RE4, 0] = 1
    assert matrix.cell(RE4, 0) == 0


def test_slice_frames_keeps_metadata_and_cells() -> None:
    matrix = sample()
    piece = matrix.slice_frames(1, 3)
    assert piece.frame_count == 2
    assert piece.granularity is matrix.granularity
    assert piece.tempo_bpm == matrix.tempo_bpm
    # The held note keeps its orphan sustain; normalizing is the validator's job.
    assert piece.cell(DO4, 0) == -1


def test_slice_frames_rejects_a_bad_range() -> None:
    matrix = sample()
    with pytest.raises(ValueError, match="outside"):
        matrix.slice_frames(2, 99)
    with pytest.raises(ValueError, match="outside"):
        matrix.slice_frames(3, 1)


def test_with_grid_can_override_metadata() -> None:
    matrix = sample()
    other = matrix.with_grid(matrix.to_array(), granularity=Granularity.NEGRA)
    assert other.granularity is Granularity.NEGRA
    assert other.tempo_bpm == matrix.tempo_bpm


def test_repr_is_informative() -> None:
    assert "88x4" in repr(sample())
    assert "semicorchea" in repr(sample())
