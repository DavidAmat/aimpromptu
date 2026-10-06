"""Notes too short to have been played, and the octave they hide under.

The threshold here is not a guess. On the reference file the durations are
bimodal with an empty band: 78 events between 4 and 16 ms, **nothing at all**
between 16 and 32 ms, then 2673 real notes from 32 ms up. 20 ms sits in the
middle of that band. The tests below pin the behaviour either side of it, and
one of them pins the reason the floor must stay low.
"""

import pytest

from aitu_backend.transcription.artifacts import (
    DEFAULT_ARTIFACTS,
    ArtifactConfig,
    drop_artifacts,
)
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.events_to_matrix import events_to_time_matrix
from aitu_backend.matrix.keys import midi_to_row
from aitu_backend.schemas.matrix import ONSET

F1, F2, F3 = 29, 41, 53


def phantom_octave() -> list[NoteEvent]:
    """David's case: a played Fa-2/Fa-3 octave with a phantom Fa-1 under it."""
    return [
        NoteEvent(midi_note=F1, start=11.0240, end=11.0297, velocity=72),  # 5.7 ms
        NoteEvent(midi_note=F2, start=11.0243, end=11.4800, velocity=78),
        NoteEvent(midi_note=F3, start=11.0251, end=11.4900, velocity=76),
    ]


def test_the_phantom_octave_goes_and_the_chord_stays() -> None:
    report = drop_artifacts(phantom_octave())

    assert [event.midi_note for event in report.kept] == [F2, F3]
    assert len(report.dropped) == 1
    assert report.dropped[0].event.midi_note == F1
    # Named, not merely counted: 12 semitones under a note struck alongside it.
    assert report.dropped[0].octave_below == 12
    assert report.octave_phantoms == 1


def test_a_short_note_with_nothing_struck_alongside_it_is_kept() -> None:
    """The artifact is created *by* a chord attack. No attack, no explanation.

    Whatever a lone 8 ms blip is, the octave-masking mechanism does not account
    for it, so this filter does not claim it.
    """
    events = [NoteEvent(midi_note=60, start=5.0, end=5.008, velocity=70)]

    report = drop_artifacts(events)

    assert report.dropped == []
    assert report.kept_isolated == 1


def test_the_floor_stays_below_a_real_key_release() -> None:
    """The floor must not be raised to 40 ms, however tempting.

    ByteDance offsets follow the pedal, so its notes are long and a high floor
    looks free. Transkun reports true key release and returns 34–85 ms notes for
    the same music; a 40 ms floor would delete a third of that transcription.
    """
    assert DEFAULT_ARTIFACTS.min_duration_seconds == pytest.approx(0.020)

    shortest_real_key_release = NoteEvent(midi_note=60, start=1.0, end=1.034)
    alongside = NoteEvent(midi_note=64, start=1.0, end=1.4)

    report = drop_artifacts([shortest_real_key_release, alongside])

    assert report.dropped == []


def test_the_duration_floor_is_where_the_config_says() -> None:
    just_under = NoteEvent(midi_note=60, start=1.0, end=1.0199)
    just_over = NoteEvent(midi_note=62, start=1.0, end=1.0201)
    alongside = NoteEvent(midi_note=72, start=1.0, end=1.4)

    report = drop_artifacts([just_under, just_over, alongside])

    assert [note.event.midi_note for note in report.dropped] == [60]
    assert [event.midi_note for event in report.kept] == [62, 72]


def test_the_filter_can_be_relaxed_or_disabled() -> None:
    events = phantom_octave()

    assert drop_artifacts(events, ArtifactConfig(min_duration_seconds=0.0)).dropped == []

    # And raising it eats the music, which is the whole warning: at half a
    # second the played Fa-2 and Fa-3 (456 and 465 ms) go too.
    strict = drop_artifacts(events, ArtifactConfig(min_duration_seconds=0.5))
    assert len(strict.dropped) == 3


def test_an_empty_list_is_not_a_special_case() -> None:
    report = drop_artifacts([])
    assert report.kept == []
    assert report.dropped == []


# ------------------------------------------------------- through the pipeline


def test_the_phantom_never_reaches_the_grid() -> None:
    """The point of running before the hand split: it is simply not there."""
    report = events_to_time_matrix(phantom_octave(), duration_seconds=13.0)

    grid = report.matrix.grid
    assert not (grid[midi_to_row(F1)] == ONSET).any()
    assert (grid[midi_to_row(F2)] == ONSET).any()
    assert (grid[midi_to_row(F3)] == ONSET).any()
    assert len(report.artifacts.dropped) == 1
    assert "1 artifact(s) dropped" in report.describe()


def test_placement_can_be_asked_for_the_engines_events_verbatim() -> None:
    """Turning the filter off stops it *claiming* the note. It does not place it.

    On a wall-clock grid a second rule catches this phantom as well: a note
    shorter than one frame is refused (D-05), and 5.7 ms is far under 40. So the
    grid looks the same either way, and the difference has to be read from the
    report rather than from the cells.

    Both rules are wanted. The artifact filter names *why* the note is wrong and
    runs before the hand split, where a phantom bass note does the real damage.
    The frame rule is only about what a column can hold.
    """
    report = events_to_time_matrix(phantom_octave(), duration_seconds=13.0, artifacts=None)

    assert report.artifacts.dropped == []
    assert report.dropped_sub_frame == 1
    assert not (report.matrix.grid[midi_to_row(F1)] == ONSET).any()


def test_a_fine_enough_grid_does_place_it_when_the_filter_is_off() -> None:
    """The proof that the frame rule, not the filter, is what removed it above."""
    report = events_to_time_matrix(
        phantom_octave(), duration_seconds=13.0, frame_ms=5.0, artifacts=None
    )

    assert (report.matrix.grid[midi_to_row(F1)] == ONSET).any()


def test_the_filter_still_removes_it_on_that_same_fine_grid() -> None:
    """And the proof that the filter is doing real work rather than duplicating it."""
    report = events_to_time_matrix(phantom_octave(), duration_seconds=13.0, frame_ms=5.0)

    assert not (report.matrix.grid[midi_to_row(F1)] == ONSET).any()
    assert len(report.artifacts.dropped) == 1
