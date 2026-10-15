"""The one operation that changes a part's length: everything from a column on moves later by a
passage's length (implementation 08, Epic 13; implementation 02, plan section 4, rule 2).

A paste (Phase 8) and a promotion of a re-recorded passage (Phase 9) both put their notes in with
:func:`aitu_backend.editing.compose.insert_events`. These tests pin it: a passage occupies whole
columns, the notes from the insertion column on move by exactly its length, a note sounding across
the moment is cut there, and appending moves nothing. The staged session of Epics 11 and 13 that
these tests also covered was removed in Phase 9.
"""

import pytest

from aitu_backend.editing import compose
from aitu_backend.editing.audio_splice import atempo_chain
from aitu_backend.transcription.engine import NoteEvent


def _note(midi: int, start: float, end: float, hand: str | None = None) -> NoteEvent:
    return NoteEvent(midi_note=midi, start=start, end=end, hand=hand)


def test_append_moves_nothing() -> None:
    original = [_note(60, 0.0, 0.4), _note(62, 1.0, 1.4)]
    arriving = [_note(72, 2.4, 2.8)]
    result, moved, duration = compose.insert_events(
        original,
        arriving,
        at_seconds=2.4,
        passage_seconds=0.8,
        duration_seconds=3.0,
        placement="append",
    )
    assert moved == 0
    assert [round(event.start, 4) for event in result] == [0.0, 1.0, 2.4]
    assert duration == pytest.approx(3.2)


def test_append_never_shortens_a_piece_with_trailing_silence() -> None:
    _, _, duration = compose.insert_events(
        [_note(60, 0.0, 0.4)],
        [_note(72, 1.4, 1.8)],
        at_seconds=1.4,
        passage_seconds=0.4,
        duration_seconds=10.0,
        placement="append",
    )
    assert duration == pytest.approx(10.0)


def test_insert_moves_everything_after_the_moment() -> None:
    original = [_note(60, 0.0, 0.4), _note(62, 1.0, 1.4), _note(64, 2.0, 2.4)]
    arriving = [_note(72, 1.0, 1.4)]
    result, moved, duration = compose.insert_events(
        original,
        arriving,
        at_seconds=1.0,
        passage_seconds=0.8,
        duration_seconds=3.0,
        placement="insert",
    )
    assert moved == 2
    assert [round(event.start, 4) for event in result] == [0.0, 1.0, 1.8, 2.8]
    assert duration == pytest.approx(3.8)


def test_a_note_sounding_across_the_moment_is_cut_there() -> None:
    """It was not played against the passage now arriving; letting it ring over it invents a sustain."""
    original = [_note(60, 0.5, 2.5)]
    result, moved, _ = compose.insert_events(
        original,
        [_note(72, 1.0, 1.4)],
        at_seconds=1.0,
        passage_seconds=0.8,
        duration_seconds=3.0,
        placement="insert",
    )
    assert moved == 0
    held = next(event for event in result if event.midi_note == 60)
    assert held.start == pytest.approx(0.5)
    assert held.end == pytest.approx(1.0)


def test_a_passage_with_no_notes_cannot_be_placed() -> None:
    with pytest.raises(ValueError):
        compose.insert_events(
            [],
            [],
            at_seconds=0.0,
            passage_seconds=0.0,
            duration_seconds=0.0,
            placement="append",
        )


def test_a_note_that_rounds_into_the_insertion_column_moves_with_it() -> None:
    """Notes and marks are both decided by the column, so neither is left behind by the other.

    A note at 1.99 s is drawn in column 50 at 40 ms a column, and so is the moment 2.0 s. Under an
    onset test in seconds that note would stay put and end up inside the passage the reader just
    opened, with its fingering gone on ahead without it.
    """
    original = [_note(60, 1.99, 2.1), _note(62, 1.9, 2.0)]
    result, moved, _ = compose.insert_events(
        original,
        [_note(80, 2.0, 2.4)],
        at_seconds=2.0,
        passage_seconds=0.8,
        duration_seconds=4.0,
        placement="insert",
        frame_ms=40.0,
    )
    assert moved == 1
    stayed = next(event for event in result if event.midi_note == 62)
    assert stayed.start == pytest.approx(1.9)
    went = next(event for event in result if event.midi_note == 60)
    assert went.start == pytest.approx(2.79)
    # 1.99 s was column 50; 2.79 s is column 70, which is 50 plus the 20-column passage.
    assert round(went.start * 1000 / 40.0) == 50 + 20


def test_atempo_chain_stays_inside_one_pass() -> None:
    assert atempo_chain(2.0) == ["atempo=2"]
    assert atempo_chain(0.5) == ["atempo=0.5"]
    assert atempo_chain(4.0) == ["atempo=2", "atempo=2"]
