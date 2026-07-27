"""Appendix B sustain cleaning, including both worked examples from the doc."""

import numpy as np
import pytest

from aitu_backend.matrix.cleaning import (
    clean_sustains,
    columns_with_onsets,
    cut_sustain_count,
    is_clean,
)
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.matrix.validator import is_valid
from aitu_backend.progress import CallbackProgress, ProgressEvent
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep

C3 = note_to_row("Do-3")
D3 = note_to_row("Re-3")
E3 = note_to_row("Mi-3")
C4 = note_to_row("Do-4")


def build(rows: dict[int, list[int]], frames: int) -> PianoMatrix:
    """A matrix from `{row: [cells...]}`, at 1 second per column (negra @ 60)."""
    grid = np.zeros((KEY_COUNT, frames), dtype=np.int8)
    for row, values in rows.items():
        grid[row, : len(values)] = np.array(values, dtype=np.int8)
    return PianoMatrix.from_dense(grid, granularity=Granularity.NEGRA, tempo_bpm=60)


def note(matrix: PianoMatrix, row: int) -> list[int]:
    return matrix.grid[row].tolist()


# ------------------------------------------------------- the two doc examples


def test_appendix_b_first_example() -> None:
    """C3 held 3 s under a C4 struck at 1 s -> C3 is cut to 1 s.

      C3 -> onset at 00:00 (duration 3 seconds)
      C4 -> onset at 00:01 (duration 2 seconds)
    becomes
      C3 -> onset at 00:00 (duration 1 second)
      C4 -> onset at 00:01 (duration 2 seconds)
    """
    matrix = build({C3: [1, -1, -1], C4: [0, 1, -1]}, frames=3)
    cleaned = clean_sustains(matrix)

    assert note(cleaned, C3) == [1, 0, 0]
    assert note(cleaned, C4) == [0, 1, -1]


def test_appendix_b_classical_accompaniment_example() -> None:
    """The pattern the appendix calls typical of classical music.

      C3, C4 -> chord onset at 00:00 (duration 10 seconds)
      D3     -> onset at 00:01 (duration 1 second)
      E3     -> onset at 00:02 (duration 1 second)
    -> both C3 and C4 are cut to 1 second.
    """
    matrix = build(
        {
            C3: [1] + [-1] * 9,
            C4: [1] + [-1] * 9,
            D3: [0, 1],
            E3: [0, 0, 1],
        },
        frames=10,
    )
    cleaned = clean_sustains(matrix)

    assert note(cleaned, C3) == [1] + [0] * 9
    assert note(cleaned, C4) == [1] + [0] * 9
    assert note(cleaned, D3)[1] == 1
    assert note(cleaned, E3)[2] == 1


def test_appendix_b_note_a_re_onset_of_the_same_key_survives() -> None:
    """The appendix's explicit counter-example.

      C3, C4 -> chord onset at 00:00 (duration 10 s)
      C3     -> onset at 00:01 (duration 10 s)
    -> the chord becomes 1 second; the new C3 keeps its full length,
       since nothing else is played afterwards.
    """
    matrix = build(
        {
            C3: [1] + [1] + [-1] * 8,
            C4: [1] + [-1] * 9,
        },
        frames=10,
    )
    cleaned = clean_sustains(matrix)

    assert note(cleaned, C4) == [1] + [0] * 9
    assert note(cleaned, C3) == [1, 1] + [-1] * 8


# ------------------------------------------------------------------- the rule


def test_a_chord_struck_together_sustains_together() -> None:
    """Nothing else is played, so the whole chord keeps sounding."""
    matrix = build({C3: [1, -1, -1, -1], C4: [1, -1, -1, -1]}, frames=4)
    cleaned = clean_sustains(matrix)

    assert note(cleaned, C3) == [1, -1, -1, -1]
    assert note(cleaned, C4) == [1, -1, -1, -1]
    assert is_clean(matrix)


def test_a_lone_note_keeps_its_whole_sustain() -> None:
    matrix = build({C3: [1, -1, -1, -1]}, frames=4)
    assert note(clean_sustains(matrix), C3) == [1, -1, -1, -1]


def test_the_cut_starts_exactly_at_the_foreign_onset() -> None:
    matrix = build({C3: [1, -1, -1, -1, -1], D3: [0, 0, 0, 1]}, frames=5)
    cleaned = clean_sustains(matrix)
    # The sustain survives columns 1 and 2, then dies at column 3.
    assert note(cleaned, C3) == [1, -1, -1, 0, 0]


def test_onsets_are_never_removed() -> None:
    """Only tails shorten — no note may disappear from the score."""
    matrix = build({C3: [1, -1, -1], D3: [0, 1, -1], E3: [0, 0, 1]}, frames=3)
    cleaned = clean_sustains(matrix)
    assert np.array_equal(cleaned.grid == 1, matrix.grid == 1)


def test_a_second_chord_restarts_the_clock() -> None:
    matrix = build(
        {
            C3: [1, -1, 0, 1, -1, -1],
            C4: [1, -1, 0, 1, -1, -1],
        },
        frames=6,
    )
    cleaned = clean_sustains(matrix)
    # Each chord is struck together and nothing foreign intervenes.
    assert note(cleaned, C3) == [1, -1, 0, 1, -1, -1]
    assert note(cleaned, C4) == [1, -1, 0, 1, -1, -1]


def test_a_sustain_dies_even_when_the_foreign_onset_is_far_above() -> None:
    """The rule is about *any* other key, not about pitch distance."""
    matrix = build({C3: [1, -1, -1], note_to_row("Do-7"): [0, 1]}, frames=3)
    assert note(clean_sustains(matrix), C3) == [1, 0, 0]


# --------------------------------------------------------------- housekeeping


def test_output_is_marked_clean_and_stays_valid() -> None:
    matrix = build({C3: [1, -1, -1], D3: [0, 1]}, frames=3)
    cleaned = clean_sustains(matrix)
    assert cleaned.processing_step is MatrixProcessingStep.CLEAN
    assert is_valid(cleaned)
    assert cleaned.granularity is matrix.granularity
    assert cleaned.tempo_bpm == matrix.tempo_bpm


def test_cleaning_does_not_mutate_its_input() -> None:
    matrix = build({C3: [1, -1, -1], D3: [0, 1]}, frames=3)
    clean_sustains(matrix)
    assert note(matrix, C3) == [1, -1, -1]


def test_cleaning_is_idempotent() -> None:
    matrix = build({C3: [1, -1, -1, -1], D3: [0, 1, 0, 1]}, frames=4)
    once = clean_sustains(matrix)
    assert np.array_equal(clean_sustains(once).grid, once.grid)
    assert is_clean(once)


def test_cut_count_matches_the_change() -> None:
    matrix = build({C3: [1, -1, -1, -1], D3: [0, 1]}, frames=4)
    assert cut_sustain_count(matrix) == 3


def test_an_orphan_sustain_is_dropped_rather_than_kept() -> None:
    """Structurally illegal input degrades safely instead of crashing."""
    matrix = build({C3: [0, -1, -1]}, frames=3)
    assert note(clean_sustains(matrix), C3) == [0, 0, 0]


def test_empty_and_silent_matrices_are_handled() -> None:
    assert clean_sustains(PianoMatrix.empty(0)).frame_count == 0
    silent = PianoMatrix.empty(8)
    assert clean_sustains(silent).is_empty()
    assert is_clean(silent)


def test_columns_with_onsets_flags_the_right_columns() -> None:
    matrix = build({C3: [1, -1, 0, 1], D3: [0, 0, 1]}, frames=4)
    assert columns_with_onsets(matrix.grid).tolist() == [True, False, True, True]


def test_cleaning_reports_progress() -> None:
    events: list[ProgressEvent] = []
    clean_sustains(
        build({C3: [1, -1, -1], D3: [0, 1]}, frames=3),
        reporter=CallbackProgress(events.append),
    )
    assert any("sustains cut" in event.message for event in events)


# ------------------------------------------------------------------ musical


def test_a_pedal_bass_under_a_melody_collapses_to_short_bass_notes() -> None:
    """The whole point: a walking melody must not drown in tied bass notes."""
    frames = 8
    melody_rows = [note_to_row(n) for n in ["Do-5", "Re-5", "Mi-5", "Fa-5"]]
    rows = {C3: [1] + [-1] * (frames - 1)}
    for index, row in enumerate(melody_rows):
        cells = [0] * (index * 2) + [1, -1]
        rows[row] = cells
    matrix = build(rows, frames=frames)

    cleaned = clean_sustains(matrix)
    # The bass keeps only its onset plus the frame before the first melody note.
    assert note(cleaned, C3) == [1, -1, 0, 0, 0, 0, 0, 0]
    # Every melody note keeps its own onset.
    for row in melody_rows:
        assert 1 in note(cleaned, row)


def test_cleaning_scales_to_a_long_piece() -> None:
    rng = np.random.default_rng(1)
    grid = rng.choice(
        np.array([0, 1, -1], dtype=np.int8), size=(KEY_COUNT, 5000), p=[0.9, 0.05, 0.05]
    )
    matrix = PianoMatrix.from_dense(grid, granularity=Granularity.FUSA, tempo_bpm=120)
    cleaned = clean_sustains(matrix)
    assert cleaned.frame_count == 5000
    assert np.count_nonzero(cleaned.grid) <= np.count_nonzero(matrix.grid)


@pytest.mark.parametrize("frames", [1, 2, 3, 17])
def test_arbitrary_lengths_stay_valid(frames: int) -> None:
    rng = np.random.default_rng(frames)
    grid = rng.choice(
        np.array([0, 1, -1], dtype=np.int8), size=(KEY_COUNT, frames), p=[0.8, 0.1, 0.1]
    )
    matrix = PianoMatrix.from_dense(grid)
    cleaned = clean_sustains(matrix)
    assert cleaned.frame_count == frames
