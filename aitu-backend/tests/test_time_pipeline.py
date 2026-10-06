"""Raw events to two hands, and the promise that the frame length is only a parameter.

The order under test is the whole backend pipeline: impose the granularity, then split the hands.
Everything after this measures one hand at a time, so the split has to have happened already.
"""

import numpy as np
import pytest

from aitu_backend.matrix.keys import midi_to_row
from aitu_backend.schemas.matrix import ONSET
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.time_pipeline import (
    attack_times_of_hand,
    impose_granularity_and_split,
    layout_hints_for,
    to_time_envelope,
)

BASS, TENOR, TREBLE, HIGH = 41, 48, 72, 79  # Fa-2, Do-3, Do-6, Sol-6


def note(start_ms: float, midi: int, length_ms: float = 200.0) -> NoteEvent:
    return NoteEvent(midi_note=midi, start=start_ms / 1000.0, end=(start_ms + length_ms) / 1000.0)


def two_hand_events() -> list[NoteEvent]:
    """A held low chord under a running melody: the shape success criterion 6 is about."""
    events = [note(0, BASS, 1600.0), note(5, TENOR, 1600.0)]
    for index in range(8):
        events.append(note(index * 200.0, TREBLE + (index % 3), 180.0))
    return events


def run(events, duration_seconds=3.0, **kwargs):
    kwargs.setdefault("artifacts", None)
    kwargs.setdefault("leakage", None)
    return impose_granularity_and_split(events, duration_seconds, **kwargs)


def test_the_pipeline_gives_two_hands_and_nothing_else():
    hands = run(two_hand_events())
    assert hands.right.frame_count == hands.left.frame_count == hands.unsplit.frame_count
    assert hands.right.is_time_based and hands.left.is_time_based
    assert hands.frame_ms == 40.0


def test_the_split_loses_no_note():
    """Every onset ends up in exactly one hand, so the two recombine into what was played."""
    hands = run(two_hand_events())
    rebuilt = hands.right.to_array() + hands.left.to_array()
    assert np.array_equal(rebuilt, hands.unsplit.to_array())


def test_a_held_low_chord_stays_on_the_left_under_a_running_melody():
    hands = run(two_hand_events())
    assert midi_to_row(BASS) in hands.left.active_rows()
    assert midi_to_row(TREBLE) in hands.right.active_rows()
    assert midi_to_row(BASS) not in hands.right.active_rows()


def test_changing_the_frame_length_changes_the_grid_and_nothing_else():
    """`frameMs` is a parameter. The same events at 20 ms are the same music, twice as finely."""
    events = two_hand_events()
    coarse = run(events, frame_ms=40)
    fine = run(events, frame_ms=20)

    assert fine.frame_count == 2 * coarse.frame_count
    assert fine.build.placed == coarse.build.placed
    assert set(fine.right.active_rows()) == set(coarse.right.active_rows())
    assert set(fine.left.active_rows()) == set(coarse.left.active_rows())

    # An onset at 200 ms is column 5 at 40 ms and column 10 at 20 ms: the same instant.
    row = midi_to_row(TREBLE + 1)
    assert coarse.right.cell(row, 5) == ONSET
    assert fine.right.cell(row, 10) == ONSET


def test_an_odd_frame_length_works_just_as_well():
    """Nothing assumes 40, or even a divisor of it."""
    hands = run(two_hand_events(), frame_ms=30)
    assert hands.frame_ms == 30.0
    assert hands.frame_count == 100
    assert hands.build.placed == run(two_hand_events()).build.placed


def test_running_twice_gives_the_same_answer():
    first, second = run(two_hand_events()), run(two_hand_events())
    assert np.array_equal(first.right.to_array(), second.right.to_array())
    assert np.array_equal(first.left.to_array(), second.left.to_array())


def test_a_piece_is_always_sent_as_two_hands():
    """Issue I-02. There is no single-matrix form and no unsplit step in the stored shape."""
    envelope = to_time_envelope(run(two_hand_events()))
    wire = envelope.model_dump(by_alias=True)
    assert wire["matrixProcessingStep"] == "two-hands"
    assert "rMatrix" in wire and "lMatrix" in wire
    assert wire["frameMs"] == 40.0
    assert wire["frameCount"] == envelope.r_matrix.shape[1] == envelope.l_matrix.shape[1]


def test_a_right_hand_only_piece_is_two_hands_with_an_empty_left_and_a_hidden_staff():
    hands = run([note(index * 200.0, TREBLE + index % 4, 180.0) for index in range(6)])
    envelope = to_time_envelope(hands)
    hints = layout_hints_for(hands)

    assert hands.is_right_hand_only
    assert envelope.l_matrix.is_empty()
    assert envelope.l_matrix.shape[1] == envelope.r_matrix.shape[1]
    assert hints.hide_left_hand is True
    assert hints.hide_right_hand is False
    assert hints.model_dump(by_alias=True)["hideLeftHand"] is True


def test_a_left_hand_only_piece_hides_the_other_staff():
    hands = run([note(index * 300.0, BASS + index % 3, 280.0) for index in range(6)])
    assert hands.is_left_hand_only
    assert layout_hints_for(hands).hide_right_hand is True


def test_the_pipeline_describes_itself_in_a_sentence():
    described = run(two_hand_events()).describe()
    assert "75 columns of 40 ms" in described
    assert "right" in described and "left" in described


def test_an_impossible_frame_length_is_refused_before_any_work_happens():
    with pytest.raises(ValueError, match="frameMs"):
        run(two_hand_events(), frame_ms=0)


def test_a_hand_measures_its_own_attack_and_not_the_other_hand_s():
    """Grouping runs before the split, so a shared column carries the earlier hand's time.

    Six right-hand notes 60 ms apart, with a left-hand note landing 20 ms before the fourth of
    them. At 40 ms columns the two share a column, and the group's time is the left hand's. Reading
    that back for the right hand shortens one gap to 40 ms and lengthens the next to 80 — an even
    run printed as a ragged one, which is the failure this whole refactor removes.
    """
    events = [note(index * 60.0, TREBLE, 50.0) for index in range(6)]
    events.append(note(3 * 60.0 - 20.0, BASS, 50.0))

    hands = impose_granularity_and_split(events, 2.0, frame_ms=40, artifacts=None, leakage=None)
    right = attack_times_of_hand(hands, "right")
    gaps = [round((b - a) * 1000.0) for a, b in zip(right, right[1:])]

    assert gaps == [60, 60, 60, 60, 60]


def test_the_two_hands_still_share_the_column_they_were_played_in():
    """The correction is to the measured time only. Where the notes are drawn does not move."""
    events = [note(index * 60.0, TREBLE, 50.0) for index in range(6)]
    events.append(note(3 * 60.0 - 20.0, BASS, 50.0))

    hands = impose_granularity_and_split(events, 2.0, frame_ms=40, artifacts=None, leakage=None)
    shared = int(np.nonzero(hands.left.grid[midi_to_row(BASS)] == ONSET)[0][0])
    assert hands.right.grid[midi_to_row(TREBLE), shared] == ONSET
