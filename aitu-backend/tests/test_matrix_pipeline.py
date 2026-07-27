"""Epic 2 exit criteria: the whole engine, end to end, as pure functions.

raw -> collapsed -> clean -> two-hands, over examples from the notation spec,
plus the performance target for recomputing a granularity from raw.
"""

import time

import numpy as np
import pytest

from aitu_backend.matrix.cleaning import clean_sustains
from aitu_backend.matrix.granularity import collapse_to
from aitu_backend.matrix.hands import split_hands
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.text_notation import sequence_to_sparse_payload
from aitu_backend.matrix.validator import is_valid
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep
from aitu_backend.storage.matrix_store import load_matrix, save_matrix


def raw_from_notation(sequence: list[str], granularity=Granularity.FUSA) -> PianoMatrix:
    """The notation parser is the cheapest way to author a raw matrix by hand."""
    return PianoMatrix.from_coo_payload(
        sequence_to_sparse_payload(sequence),
        granularity=granularity,
        tempo_bpm=60,
    )


def run_pipeline(raw: PianoMatrix, target: Granularity):
    collapsed = collapse_to(raw, target)
    clean = clean_sustains(collapsed)
    hands = split_hands(clean)
    return collapsed, clean, hands


# ------------------------------------------------------------------ the chain


def test_the_four_steps_run_end_to_end() -> None:
    """Do Re Mi as fusa pairs, collapsed to semicorchea, cleaned and split."""
    raw = raw_from_notation(
        ["*Do-4", "Do-4", "*Re-4", "Re-4", "*Mi-4", "Mi-4", "", ""],
        granularity=Granularity.FUSA,
    )
    collapsed, clean, hands = run_pipeline(raw, Granularity.SEMICORCHEA)

    assert raw.processing_step is MatrixProcessingStep.RAW
    assert collapsed.processing_step is MatrixProcessingStep.COLLAPSED
    assert clean.processing_step is MatrixProcessingStep.CLEAN
    assert hands.right.processing_step is MatrixProcessingStep.TWO_HANDS

    assert collapsed.frame_count == 4
    assert clean.frame_count == 4
    assert hands.right.frame_count == hands.left.frame_count == 4

    # Every note survives as its own onset, one per collapsed column.
    for column, name in enumerate(["Do-4", "Re-4", "Mi-4"]):
        assert clean.cell(note_to_row(name), column) == 1


def test_every_step_stays_structurally_valid() -> None:
    raw = raw_from_notation(["*Do-3", "Do-3", "*Do-5", "Do-5", "*Mi-5", "Mi-5", "", ""])
    collapsed, clean, hands = run_pipeline(raw, Granularity.SEMICORCHEA)

    for matrix in (raw, collapsed, clean, hands.right, hands.left):
        assert is_valid(matrix)


def test_the_duration_of_the_piece_never_changes() -> None:
    raw = raw_from_notation(["*Do-4"] + ["Do-4"] * 7)
    collapsed, clean, hands = run_pipeline(raw, Granularity.CORCHEA)

    for matrix in (collapsed, clean, hands.right, hands.left):
        assert matrix.duration_seconds == pytest.approx(raw.duration_seconds)


def test_hands_stay_aligned_so_the_grand_staff_lines_up() -> None:
    raw = raw_from_notation(["*Do-3 || *Do-5", "Do-3 || Do-5", "*Re-5", "Re-5"])
    _, clean, hands = run_pipeline(raw, Granularity.SEMICORCHEA)

    assert hands.right.shape == hands.left.shape == clean.shape
    assert np.array_equal(hands.combined().grid, clean.grid)


# ----------------------------------------------------- the cleaning pay-off


def test_a_held_bass_under_a_melody_ends_up_short() -> None:
    """The whole reason the clean step exists, run through the real chain.

    Authored as a grid rather than as text notation: the text parser already
    applies its own onset rule, so it cannot express "a pedal note that really
    does keep sounding" — which is exactly what a transcribed recording gives
    us, and exactly what Appendix B has to handle.
    """
    grid = np.zeros((KEY_COUNT, 8), dtype=np.int8)
    bass = note_to_row("Do-3")
    grid[bass] = [1, -1, -1, -1, -1, -1, -1, -1]
    for index, name in enumerate(["Do-5", "Re-5", "Mi-5"]):
        grid[note_to_row(name), index * 2] = 1
        grid[note_to_row(name), index * 2 + 1] = -1
    raw = PianoMatrix.from_dense(grid, granularity=Granularity.FUSA, tempo_bpm=60)

    collapsed, clean, _ = run_pipeline(raw, Granularity.SEMICORCHEA)

    # Collapsed still carries the long bass note ...
    assert collapsed.grid[bass].tolist() == [1, -1, -1, -1]
    # ... and cleaning cuts it back at the first foreign onset.
    assert clean.grid[bass].tolist() == [1, 0, 0, 0]
    # The melody is untouched.
    for column, name in enumerate(["Do-5", "Re-5", "Mi-5"]):
        assert clean.cell(note_to_row(name), column) == 1


# --------------------------------------------------------------- notation spec


def test_the_notation_spec_example_survives_the_chain() -> None:
    """The eight-frame example printed in `02-notation-spec.md`."""
    raw = raw_from_notation(
        [
            "*Do-4 || *Mi-4",
            "*Re-4",
            "Re-4",
            "*Mi-4",
            "Mi-4",
            "Mi-4",
            "Mi-4",
            "*Fa#-5",
        ]
    )
    _, clean, hands = run_pipeline(raw, Granularity.SEMICORCHEA)

    assert clean.frame_count == 4
    # Every struck note in the source is still struck somewhere.
    for name in ["Do-4", "Mi-4", "Re-4", "Fa#-5"]:
        assert 1 in clean.grid[note_to_row(name)].tolist()
    # Fa#-5 and the rest are all above middle C, so the left hand is empty.
    assert hands.left.is_empty()


def test_repeated_strikes_stay_separate_through_the_chain() -> None:
    """Four Re-4 strikes are four notes, not one held note."""
    raw = raw_from_notation(["*Re-4", "*Re-4", "*Re-4", "*Re-4"])
    _, clean, _ = run_pipeline(raw, Granularity.SEMICORCHEA)
    assert clean.grid[note_to_row("Re-4")].tolist() == [1, 1]


# ------------------------------------------------------------------ recompute


def test_any_granularity_recomputes_from_the_same_raw_matrix() -> None:
    raw = raw_from_notation(["*Do-4", "Do-4", "*Re-4", "Re-4", "*Mi-4", "Mi-4", "*Fa-4", "Fa-4"])

    for target, frames in [
        (Granularity.SEMICORCHEA, 4),
        (Granularity.CORCHEA, 2),
        (Granularity.NEGRA, 1),
    ]:
        collapsed = collapse_to(raw, target)
        assert collapsed.frame_count == frames
        assert collapsed.duration_seconds == pytest.approx(raw.duration_seconds)


def test_recompute_from_raw_is_sub_second_for_a_five_minute_piece() -> None:
    """The exit criterion behind instant granularity switching in the UI."""
    rng = np.random.default_rng(7)
    grid = rng.choice(
        np.array([0, 1, -1], dtype=np.int8), size=(KEY_COUNT, 9600), p=[0.92, 0.04, 0.04]
    )
    raw = PianoMatrix.from_dense(grid, granularity=Granularity.SEMIFUSA, tempo_bpm=120)

    started = time.perf_counter()
    _, clean, hands = run_pipeline(raw, Granularity.NEGRA)
    elapsed = time.perf_counter() - started

    assert clean.frame_count == 600
    assert hands.right.frame_count == 600
    assert elapsed < 1.0, f"full pipeline took {elapsed:.3f}s"


# ---------------------------------------------------------------- round trip


def test_the_whole_chain_round_trips_through_storage(tmp_path) -> None:
    raw = raw_from_notation(["*Do-3 || *Do-5", "Do-3 || Do-5", "*Re-5", "Re-5"])
    _, clean, hands = run_pipeline(raw, Granularity.SEMICORCHEA)

    paths = {
        "raw": tmp_path / "piano_matrix_v1_gf.npz",
        "clean": tmp_path / "piano_matrix_v1_gsc.npz",
        "right": tmp_path / "piano_matrix_v1_gsc_right.npz",
        "left": tmp_path / "piano_matrix_v1_gsc_left.npz",
    }
    for name, matrix in [
        ("raw", raw),
        ("clean", clean),
        ("right", hands.right),
        ("left", hands.left),
    ]:
        save_matrix(paths[name], matrix.to_coo_payload())

    assert load_matrix(paths["raw"]).model_dump() == raw.to_coo_payload().model_dump()
    assert load_matrix(paths["clean"]).model_dump() == clean.to_coo_payload().model_dump()
    assert load_matrix(paths["right"]).model_dump() == hands.right.to_coo_payload().model_dump()
    assert load_matrix(paths["left"]).model_dump() == hands.left.to_coo_payload().model_dump()


def test_the_envelope_survives_the_chain() -> None:
    raw = raw_from_notation(["*Do-4", "Do-4", "*Re-4", "Re-4"])
    _, clean, _ = run_pipeline(raw, Granularity.SEMICORCHEA)

    envelope = clean.to_envelope()
    assert envelope.granularity is Granularity.SEMICORCHEA
    assert envelope.matrix_processing_step is MatrixProcessingStep.CLEAN
    assert PianoMatrix.from_envelope(envelope) == clean
