"""Events to a wall-clock matrix: the column an onset lands in depends on the recording only.

The 1.x builder needed a tempo, so the same recording produced different columns depending on a
number somebody typed. These tests hold the new builder to the opposite property, and to the three
rules that decide what reaches the grid: sub-frame notes are refused, chords are grouped before
snapping, and the sustain in the grid is a measurement rather than a printed length.
"""

import inspect

import numpy as np
import pytest

from aitu_backend.matrix.keys import midi_to_row
from aitu_backend.schemas.matrix import ONSET, SILENCE, SUSTAIN
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.events_to_matrix import events_to_time_matrix

DO4_MIDI, MI4_MIDI, SOL4_MIDI = 60, 64, 67
DO4, MI4, SOL4 = midi_to_row(DO4_MIDI), midi_to_row(MI4_MIDI), midi_to_row(SOL4_MIDI)


def note(start_ms: float, midi: int = DO4_MIDI, length_ms: float = 200.0) -> NoteEvent:
    return NoteEvent(midi_note=midi, start=start_ms / 1000.0, end=(start_ms + length_ms) / 1000.0)


def build(events, duration_seconds=4.0, **kwargs):
    """Artifact and leakage filters off, so each test sees only the rule it is about."""
    kwargs.setdefault("artifacts", None)
    kwargs.setdefault("leakage", None)
    return events_to_time_matrix(events, duration_seconds, **kwargs)


def test_no_code_path_accepts_a_tempo():
    """D-01. A tempo argument is the thing this refactor removes, so its absence is asserted."""
    parameters = set(inspect.signature(events_to_time_matrix).parameters)
    assert not {name for name in parameters if "tempo" in name or "bpm" in name.lower()}
    assert "granularity" not in parameters
    assert "frame_ms" in parameters


def test_the_matrix_is_wall_clock_and_has_no_beat_value():
    matrix = build([note(0)]).matrix
    assert matrix.is_time_based
    assert matrix.frame_ms == 40.0
    assert matrix.time_step_seconds == 0.04
    assert matrix.frame_count == 100
    with pytest.raises(ValueError, match="no beats per column"):
        matrix.beats_per_column


def test_an_onset_lands_in_the_column_its_time_says():
    matrix = build([note(337, DO4_MIDI)]).matrix
    assert matrix.cell(DO4, 8) == ONSET
    assert matrix.cell(DO4, 7) == SILENCE


def test_the_same_events_twice_give_an_identical_grid():
    """Success criterion 3, at the level of this one step: no input other than the events."""
    events = [note(0, DO4_MIDI), note(211, MI4_MIDI), note(337, SOL4_MIDI), note(674, DO4_MIDI)]
    first = build(events).matrix
    second = build(list(reversed(events))).matrix
    assert np.array_equal(first.to_array(), second.to_array())


def test_a_chord_lands_in_one_column_even_when_it_straddles_a_boundary():
    """D-04. Snapping each note on its own would put these two a column apart."""
    report = build([note(58, DO4_MIDI), note(77, MI4_MIDI)])
    assert report.groups == 1
    assert report.matrix.onsets_in_column(1) == sorted([DO4, MI4])
    assert report.matrix.onsets_in_column(2) == []


def test_an_arpeggio_wider_than_the_window_stays_three_events():
    report = build([note(0, DO4_MIDI), note(120, MI4_MIDI), note(240, SOL4_MIDI)])
    assert report.groups == 3
    assert report.matrix.onsets_in_column(0) == [DO4]
    assert report.matrix.onsets_in_column(3) == [MI4]
    assert report.matrix.onsets_in_column(6) == [SOL4]


def test_a_note_shorter_than_one_frame_is_refused():
    """D-05. Eight milliseconds under a struck octave is the engine masking itself, not a note."""
    report = build([note(0, DO4_MIDI, length_ms=8), note(200, MI4_MIDI, length_ms=200)])
    assert report.dropped_sub_frame == 1
    assert report.placed == 1
    assert report.matrix.onsets_in_column(0) == []


def test_the_frame_length_decides_what_counts_as_too_short():
    """The same 30 ms note is refused at 40 ms frames and kept at 20 ms frames."""
    short = [note(0, DO4_MIDI, length_ms=30)]
    assert build(short).dropped_sub_frame == 1
    assert build(short, frame_ms=20).dropped_sub_frame == 0


def test_the_sustain_written_down_is_the_measured_release():
    """D-06. A note of 200 ms occupies its onset column plus four more."""
    matrix = build([note(0, DO4_MIDI, length_ms=200)]).matrix
    assert matrix.cell(DO4, 0) == ONSET
    assert [matrix.cell(DO4, column) for column in range(1, 5)] == [SUSTAIN] * 4
    assert matrix.cell(DO4, 5) == SILENCE


def test_notes_of_one_chord_keep_their_own_release_times():
    """The chord shares an onset column; it does not share a length."""
    matrix = build([note(0, DO4_MIDI, length_ms=600), note(10, MI4_MIDI, length_ms=120)]).matrix
    assert matrix.cell(DO4, 0) == ONSET and matrix.cell(MI4, 0) == ONSET
    assert matrix.cell(DO4, 10) == SUSTAIN
    assert matrix.cell(MI4, 10) == SILENCE


def test_a_restrike_of_the_same_key_cuts_the_first_note():
    report = build([note(0, DO4_MIDI, length_ms=400), note(160, DO4_MIDI, length_ms=200)])
    assert report.truncated == 1
    assert report.matrix.cell(DO4, 4) == ONSET
    assert report.matrix.cell(DO4, 3) == SUSTAIN


def test_a_finer_grid_gives_proportionally_more_columns():
    at_forty = build([note(337, DO4_MIDI)], frame_ms=40).matrix
    at_twenty = build([note(337, DO4_MIDI)], frame_ms=20).matrix
    assert at_forty.cell(DO4, 8) == ONSET
    assert at_twenty.cell(DO4, 17) == ONSET
    assert at_twenty.frame_count == 2 * at_forty.frame_count


def test_a_note_outside_the_keyboard_is_reported_not_wrapped():
    report = build([NoteEvent(midi_note=12, start=0.0, end=0.5)])
    assert report.dropped_out_of_range == [12]
    assert report.placed == 0
    assert not report.lossless


def test_an_onset_past_the_end_of_the_audio_is_reported():
    report = build([note(0, DO4_MIDI), note(9000, MI4_MIDI)], duration_seconds=1.0)
    assert report.dropped_past_end == 1
    assert report.placed == 1


def test_an_empty_transcription_gives_a_silent_matrix_of_the_right_length():
    report = build([], duration_seconds=2.0)
    assert report.matrix.frame_count == 50
    assert report.matrix.is_empty()
    assert report.groups == 0


def test_the_report_reads_as_a_sentence():
    report = build([note(0, DO4_MIDI), note(8, MI4_MIDI), note(200, SOL4_MIDI, length_ms=10)])
    assert report.describe() == "2 note(s) placed in 1 attack(s); 1 shorter than one frame."
