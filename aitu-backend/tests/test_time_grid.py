"""The wall-clock grid: a column is 40 ms and nothing else decides where an onset lands.

What these protect is the property the whole refactor rests on. A column index must depend only on
the onset time and the frame length, so that two runs of the pipeline over the same audio agree and
so that changing a figure moves nothing.
"""

import pytest

from aitu_backend.matrix.time_grid import (
    DEFAULT_FRAME_MS,
    frame_count_for_duration,
    frame_of_ms,
    frame_of_seconds,
    frame_span_of_ms,
    frame_start_ms,
    frame_start_seconds,
    seconds_per_frame,
    validate_frame_ms,
)


def test_a_frame_is_forty_milliseconds_by_default():
    assert DEFAULT_FRAME_MS == 40.0
    assert seconds_per_frame() == 0.04
    assert seconds_per_frame(20) == 0.02


def test_an_onset_snaps_to_the_nearest_column():
    assert frame_of_ms(0) == 0
    assert frame_of_ms(19.9) == 0
    assert frame_of_ms(21) == 1
    assert frame_of_ms(337) == 8
    assert frame_of_ms(360) == 9
    assert frame_of_seconds(0.337) == 8


def test_a_half_lands_on_the_later_column_everywhere_in_the_piece():
    """Python's own round() sends a half to the even column, which is not what D-02 reads like."""
    assert frame_of_ms(20) == 1
    assert frame_of_ms(60) == 2
    assert frame_of_ms(100) == 3
    assert frame_of_ms(140) == 4


def test_the_column_of_an_onset_does_not_depend_on_a_tempo():
    """The point of the refactor: the same onset gives the same column in every piece."""
    for _ in range(3):
        assert frame_of_seconds(46.12) == 1153


def test_a_finer_grid_gives_proportionally_more_columns():
    assert frame_of_ms(337, frame_ms=20) == 17
    assert frame_of_ms(337, frame_ms=40) == 8


def test_a_column_starts_where_the_arithmetic_says():
    assert frame_start_seconds(0) == 0.0
    assert frame_start_ms(8) == 320.0
    assert frame_start_seconds(25) == 1.0


def test_the_grid_covers_the_whole_recording():
    """The last column is rounded up, so the audio never runs past the end of the matrix."""
    assert frame_count_for_duration(1.0) == 25
    assert frame_count_for_duration(1.001) == 26
    assert frame_count_for_duration(0.001) == 1


def test_a_length_of_time_is_not_an_instant():
    """`frame_span_of_ms` answers how wide, `frame_of_ms` answers which column."""
    assert frame_span_of_ms(45) == 1
    assert frame_of_ms(45) == 1
    assert frame_span_of_ms(10) == 1
    assert frame_of_ms(10) == 0
    assert frame_span_of_ms(320) == 8


def test_an_impossible_frame_length_is_refused_where_it_is_set():
    for bad in (0, -40, float("inf"), float("nan")):
        with pytest.raises(ValueError, match="frameMs"):
            validate_frame_ms(bad)


def test_a_negative_time_is_refused():
    with pytest.raises(ValueError):
        frame_of_ms(-1)
    with pytest.raises(ValueError):
        frame_of_seconds(-0.001)
    with pytest.raises(ValueError):
        frame_start_ms(-1)
    with pytest.raises(ValueError):
        frame_count_for_duration(0)
