"""Chord grouping on raw times: the step that stops a chord from looking like three fast notes.

The case that matters most is the straddle. Two notes of one chord can fall either side of a column
boundary, so any rule that reads columns gives a different answer depending on where the chord
happens to sit in the piece. Grouping before snapping removes that.
"""

import pytest

from aitu_backend.matrix.time_grid import frame_of_seconds
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.grouping import (
    DEFAULT_GROUP_WINDOW_MS,
    group_onsets,
    group_start_seconds,
)


def note(start_ms: float, midi: int = 60, length_ms: float = 200.0) -> NoteEvent:
    return NoteEvent(midi_note=midi, start=start_ms / 1000.0, end=(start_ms + length_ms) / 1000.0)


def test_the_window_is_one_frame_wide():
    """D-04. One parameter drives the whole convergence step: a piece at 20 ms groups at 20 ms."""
    from aitu_backend.matrix.time_grid import DEFAULT_FRAME_MS

    assert DEFAULT_GROUP_WINDOW_MS == DEFAULT_FRAME_MS == 40.0


def test_a_chord_is_one_attack():
    groups = group_onsets([note(0, 60), note(8, 64), note(15, 67)])
    assert len(groups) == 1
    assert groups[0].midi_notes == [60, 64, 67]
    assert groups[0].start_seconds == 0.0
    assert groups[0].spread_ms == pytest.approx(15.0)


def test_a_slowly_rolled_arpeggio_inside_one_frame_becomes_a_chord():
    """The accepted cost of widening the window from 20 ms to one frame."""
    groups = group_onsets([note(0, 60), note(18, 64), note(35, 67)])
    assert len(groups) == 1
    assert groups[0].midi_notes == [60, 64, 67]


def test_notes_further_apart_than_the_window_are_separate_attacks():
    groups = group_onsets([note(0, 60), note(120, 62), note(240, 64)])
    assert [group.size for group in groups] == [1, 1, 1]
    assert group_start_seconds(groups) == pytest.approx([0.0, 0.12, 0.24])


def test_the_window_is_measured_from_the_first_onset_not_the_previous_one():
    """Chaining would let a fast run swallow itself one short hop at a time. This cannot.

    Every hop here is 35 ms, inside the 40 ms window, so a chaining rule would collect all four
    notes into one attack. Measuring from the group's first onset closes the group at 70 ms.
    """
    groups = group_onsets([note(0, 60), note(35, 62), note(70, 64), note(105, 65)])
    assert [group.midi_notes for group in groups] == [[60, 62], [64, 65]]


def test_a_chord_that_straddles_a_column_boundary_is_still_one_attack():
    """This is the case D-04 exists for.

    The two notes are 19 ms apart, well inside one 40 ms column, but they sit either side of a
    boundary: on their own the first snaps to column 1 and the second to column 2. Grouping first
    means both carry the group's single start time, so the chord lands in one column instead of
    being drawn as two events a column apart.
    """
    first, second = note(58, 60), note(77, 64)
    assert frame_of_seconds(first.start) == 1
    assert frame_of_seconds(second.start) == 2

    groups = group_onsets([first, second], window_ms=20.0)
    assert len(groups) == 1
    assert groups[0].start_seconds == pytest.approx(0.058)
    assert frame_of_seconds(groups[0].start_seconds) == 1

    # The same chord a few milliseconds later, now on the same side of the boundary. Grouping gives
    # one attack either way, which is the phase independence the decision asks for.
    later = group_onsets([note(62, 60), note(81, 64)], window_ms=20.0)
    assert len(later) == 1
    assert frame_of_seconds(later[0].start_seconds) == 2


def test_grouping_does_not_depend_on_the_order_the_engine_emitted_events():
    forward = group_onsets([note(0, 60), note(8, 64), note(300, 67)])
    shuffled = group_onsets([note(300, 67), note(8, 64), note(0, 60)])
    assert [group.midi_notes for group in forward] == [group.midi_notes for group in shuffled]
    assert group_start_seconds(forward) == group_start_seconds(shuffled)


def test_groups_are_numbered_in_order_so_the_payload_can_carry_a_group_id():
    groups = group_onsets([note(0, 60), note(8, 64), note(300, 67), note(600, 69)])
    assert [group.index for group in groups] == [0, 1, 2]


def test_an_empty_transcription_gives_no_attacks():
    assert group_onsets([]) == []


def test_a_window_of_zero_is_refused():
    with pytest.raises(ValueError, match="positive"):
        group_onsets([note(0)], window_ms=0)
