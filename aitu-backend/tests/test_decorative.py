"""The ornaments a reader may leave off the page.

A sixteenth or shorter printed right before an eighth or longer in the same hand
is decorative. Nothing is written in its place (D-16), and the note before it
runs on to the next onset (D-14).
"""

from __future__ import annotations

from aitu_backend.notation.decorative import decorative_notes
from aitu_backend.schemas.time_matrix import FigureName, PrintedNote


def _note(hand: str, frame: int, row: int, figure: FigureName, group: int) -> PrintedNote:
    return PrintedNote(
        hand=hand,  # type: ignore[arg-type]
        row=row,
        start_frame=frame,
        printed_frames=4,
        printed_ms_exact=100.0,
        figure=figure,
        fit_error=0.0,
        group_id=group,
    )


def test_a_short_note_before_a_long_one_is_decorative() -> None:
    notes = [
        _note("right", 0, 60, FigureName.NEGRA, 0),
        _note("right", 10, 62, FigureName.SEMICORCHEA, 1),
        _note("right", 11, 64, FigureName.CORCHEA, 2),
    ]
    assert [(h.start_frame, h.row) for h in decorative_notes(notes)] == [(10, 62)]


def test_two_short_notes_in_a_row_keep_the_first() -> None:
    """Only the one leaning on the long note goes; the run before it is music."""
    notes = [
        _note("right", 0, 60, FigureName.SEMICORCHEA, 0),
        _note("right", 1, 62, FigureName.SEMICORCHEA, 1),
        _note("right", 2, 64, FigureName.NEGRA, 2),
    ]
    assert [(h.start_frame, h.row) for h in decorative_notes(notes)] == [(1, 62)]


def test_a_decorative_chord_goes_whole_and_hands_never_mix() -> None:
    notes = [
        _note("right", 10, 62, FigureName.FUSA, 1),
        _note("right", 10, 65, FigureName.FUSA, 1),
        _note("left", 10, 40, FigureName.NEGRA, 2),
        _note("right", 12, 64, FigureName.BLANCA, 3),
        _note("left", 11, 41, FigureName.SEMIFUSA, 4),
    ]
    found = {(h.start_frame, h.row) for h in decorative_notes(notes)}
    assert found == {(10, 62), (10, 65)}, "the left hand's last note leans on nothing"
