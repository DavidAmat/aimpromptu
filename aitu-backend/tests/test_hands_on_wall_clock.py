"""The hand split on a wall-clock grid: does the frame length change who plays what?

P4.3. The splitter was written and tuned against a semifusa grid, which at 178 BPM
is about 21 ms a column. It now runs on 40 ms columns, and it reads its timings
from the columns rather than from the recorded onsets, so every onset it sees
carries up to half a frame of error.

The question is whether that error reaches the answer. These tests measure it
rather than argue about it: the same playing is split at several frame lengths and
the assignments are compared note by note. A splitter that is really reading the
music gives the same answer on every grid fine enough to hold the music.
"""

import pytest

from aitu_backend.hands.config import DEFAULT_CONFIG
from aitu_backend.notation.figures import onset_columns
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.time_pipeline import impose_granularity_and_split


#: A left hand holding low octaves under a right-hand melody that dips below
#: middle C — the case a pitch threshold gets wrong and the beam gets right.
#: Written out rather than generated so the expected split is readable.
def two_handed_passage() -> list[NoteEvent]:
    events: list[NoteEvent] = []
    # Left hand: an octave every 600 ms, held.
    for index in range(8):
        start = index * 0.6
        for midi in (41, 53):  # Fa-2 and Fa-3
            events.append(NoteEvent(midi_note=midi, start=start, end=start + 0.55, velocity=70))
    # Right hand: a melody at 150 ms that crosses under middle C and back.
    line = [72, 69, 67, 64, 60, 59, 57, 59, 60, 64, 67, 69, 72, 69, 67, 64]
    for index, midi in enumerate(line * 2):
        start = 0.075 + index * 0.15
        events.append(NoteEvent(midi_note=midi, start=start, end=start + 0.14, velocity=84))
    return events


def assignment(events: list[NoteEvent], frame_ms: float) -> dict[tuple[int, float], str]:
    """Which hand played each note, keyed by pitch and the time it was really played.

    Keyed on the note's **own** recorded time, from the build report, rather than on
    its column. The columns are exactly what changes between two frame lengths, and
    a column's group time is not the same key either: a chord takes the earliest
    onset in it, and which notes share a column also moves with the frame length.
    """
    hands = impose_granularity_and_split(events, duration_seconds=6.0, frame_ms=frame_ms)
    played = hands.build.event_seconds  # (column, row) -> the recorded second
    out: dict[tuple[int, float], str] = {}
    for name, matrix in (("right", hands.right), ("left", hands.left)):
        for column in onset_columns(matrix):
            for row in matrix.onsets_in_column(column):
                when = played.get((column, row), column * frame_ms / 1000.0)
                out[(row, round(when, 3))] = name
    return out


def disagreements(a: dict, b: dict) -> int:
    return sum(1 for key in set(a) & set(b) if a[key] != b[key])


def test_the_split_is_the_same_at_40_ms_and_at_20_ms() -> None:
    """The measurement P1.9 left open, and the reason 40 ms is safe to keep.

    Halving the frame length halves the snapping error the splitter sees. If that
    error were deciding anything, this is where it would show.
    """
    events = two_handed_passage()

    coarse = assignment(events, 40)
    fine = assignment(events, 20)

    # 16 left-hand notes (eight octaves) and 32 melody notes, and both runs see
    # every one of them: no note is lost to either grid.
    shared = set(coarse) & set(fine)
    assert len(shared) == 48
    assert len(coarse) == len(fine) == 48
    assert disagreements(coarse, fine) == 0


def test_the_split_survives_a_10_ms_grid_too() -> None:
    events = two_handed_passage()
    assert disagreements(assignment(events, 40), assignment(events, 10)) == 0


def test_the_hands_are_the_ones_a_player_would_use() -> None:
    """Not only stable, but right: the held octaves are the left hand.

    A stable wrong answer would pass the two tests above, so this one checks the
    content. The melody dips to Si-3 and La-3, below middle C, and stays in the
    right hand — which is the case a pitch threshold cannot express.
    """
    hands = impose_granularity_and_split(two_handed_passage(), duration_seconds=6.0, frame_ms=40)

    left_rows = set(hands.left.active_rows())
    right_rows = set(hands.right.active_rows())
    # Fa-2 = MIDI 41 = row 20, Fa-3 = MIDI 53 = row 32.
    assert {20, 32} <= left_rows
    # La-3 = MIDI 57 = row 36 and Si-3 = MIDI 59 = row 38 are under middle C.
    assert {36, 38} <= right_rows
    assert not (left_rows & right_rows & {36, 38})


def test_a_frame_longer_than_the_notes_takes_them_away_from_the_splitter() -> None:
    """Where the frame length does start to matter, and why 40 ms is not arbitrary.

    Notes shorter than one frame are refused outright (D-05). A 60 ms note survives
    a 40 ms grid and does not survive an 80 ms one, so the splitter is handed less
    music than was played. That is not a hand-split failure, it is asking for a
    grid the music does not fit on, and it is the reason a coarser default would
    be a bad trade.
    """
    events = [
        NoteEvent(midi_note=41, start=0.0, end=0.55, velocity=70),
        NoteEvent(midi_note=53, start=0.0, end=0.55, velocity=70),
        # A 60 ms melody note: fine at 40 ms, gone at 80.
        NoteEvent(midi_note=72, start=0.20, end=0.26, velocity=84),
        NoteEvent(midi_note=69, start=0.40, end=0.46, velocity=84),
    ]

    fine = assignment(events, 40)
    coarse = assignment(events, 80)

    assert len(fine) == 4
    assert len(coarse) == 2, "the two short melody notes are below one 80 ms frame"


def test_the_splitters_time_floor_sits_below_the_frame_length() -> None:
    """The one constant in `hands/` that could have interacted with the grid.

    `min_available_time` is how long a hand must have to count as free to move.
    It is 20 ms, and the shortest gap a 40 ms grid can express is 40 ms, so the
    floor never binds and the grid never reaches it. If either number moves
    towards the other, this test is the one that should fail first.
    """
    assert DEFAULT_CONFIG.hand.min_available_time == pytest.approx(0.02)
    assert DEFAULT_CONFIG.hand.min_available_time * 1000 < 40
