"""Trills: two notes trading places, printed as one held note with ``tr`` over it.

The rule is the smallest one that works — two notes a whole tone or less apart, alternating, the
pair coming round at least three times, evenly and fast. Every test here is about the boundary of
that rule, because the cost of the two mistakes is not symmetric: a missed trill costs a reader
nothing and a wrong one hides notes that were really played.
"""

import pytest

from aitu_backend.api.time_score import _with_trills
from aitu_backend.matrix.ladder import build_ladder
from aitu_backend.notation.trills import detect_trills
from aitu_backend.schemas.rhythm import Trill
from aitu_backend.schemas.time_matrix import FigureName
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.time_pipeline import impose_granularity_and_split, to_score_payload

NEGRA_MS = 400.0
#: B3 and C4 — the Si-Do of the worked example.
SI, DO = 71, 72


def note(start_ms: float, midi: int, length_ms: float = 60.0) -> NoteEvent:
    return NoteEvent(midiNote=midi, start=start_ms / 1000.0, end=(start_ms + length_ms) / 1000.0)


def alternation(
    count: int,
    gap_ms: float = 80.0,
    *,
    low: int = SI,
    high: int = DO,
    start_ms: float = 1000.0,
) -> list[NoteEvent]:
    """``count`` notes taking turns, starting on the lower one."""
    return [
        note(start_ms + index * gap_ms, low if index % 2 == 0 else high) for index in range(count)
    ]


def hands_of(events: list[NoteEvent], frame_ms: float = 20.0):
    return impose_granularity_and_split(
        events, 4.0, frame_ms=frame_ms, artifacts=None, leakage=None
    )


def anchor(negra_ms: float = NEGRA_MS):
    return build_ladder(FigureName.NEGRA, negra_ms)


# --------------------------------------------------------------------------- the rule


def test_the_pair_three_times_over_is_a_trill():
    """Si-Do-Si-Do-Si-Do. Six notes, three times round, and that is the threshold."""
    found = detect_trills(hands_of(alternation(6)))
    assert len(found) == 1
    assert found[0].note_count == 6
    assert found[0].pair_repeats == 3
    assert (found[0].row, found[0].other_row) == (SI - 21, DO - 21)
    assert found[0].median_gap_ms == pytest.approx(80.0, abs=1.0)


def test_the_pair_twice_over_is_not_a_trill():
    """Four notes is an ornament somebody played, not a shake. It prints as it was played."""
    assert detect_trills(hands_of(alternation(4))) == []


def test_a_long_shake_is_one_trill_and_not_several():
    found = detect_trills(hands_of(alternation(20)))
    assert len(found) == 1
    assert found[0].note_count == 20


def test_the_lower_note_is_the_one_that_stays():
    """``tr`` means "alternate with the note above", so the note written is the lower one."""
    started_high = [note(1000 + index * 80, DO if index % 2 == 0 else SI) for index in range(8)]
    found = detect_trills(hands_of(started_high))
    assert len(found) == 1
    assert found[0].row == SI - 21


# --------------------------------------------------------------------------- what is not one


def test_two_notes_a_third_apart_are_not_a_trill():
    """A third apart alternating is a tremolo. It is written differently and is not offered."""
    assert detect_trills(hands_of(alternation(8, low=SI, high=SI + 4))) == []


def test_a_scale_is_not_a_trill():
    """Six notes climbing: every one differs from the one two back, so nothing alternates."""
    climbing = [note(1000 + index * 80, 60 + index) for index in range(8)]
    assert detect_trills(hands_of(climbing)) == []


def test_two_notes_alternating_slowly_are_not_a_trill():
    """At 500 ms apart this is a melody that happens to go back and forth."""
    assert detect_trills(hands_of(alternation(8, gap_ms=500.0))) == []


def test_an_uneven_alternation_is_not_a_trill():
    """A shake is even. Gaps that wander are two notes being played, not one note shaking."""
    uneven: list[NoteEvent] = []
    clock = 1000.0
    for index, gap in enumerate([80.0, 260.0, 90.0, 240.0, 85.0, 250.0, 95.0]):
        uneven.append(note(clock, SI if index % 2 == 0 else DO))
        clock += gap
    assert detect_trills(hands_of(uneven)) == []


def test_a_chord_in_the_middle_ends_the_run():
    """Two runs of four either side of a chord do not join into one run of eight."""
    events = alternation(4, start_ms=1000.0)
    events += [note(1320.0, SI), note(1320.0, DO + 7)]  # a chord, in the same hand
    events += alternation(4, start_ms=1400.0)
    assert detect_trills(hands_of(events)) == []


def test_each_hand_is_measured_on_its_own():
    """A left-hand chord under a right-hand shake neither breaks it nor joins it."""
    events = alternation(8, low=SI, high=DO)
    events += [note(1000.0, 40, length_ms=600.0), note(1000.0, 47, length_ms=600.0)]
    found = detect_trills(hands_of(events))
    assert [run.hand for run in found] == ["right"]
    assert found[0].note_count == 8


# --------------------------------------------------------------------------- what it prints as


def test_an_accepted_trill_prints_as_one_held_note():
    """The storm of noteheads comes off the page and one note is left, sounding across the run."""
    events = alternation(8) + [note(2400.0, 79, length_ms=300.0)]
    hands = hands_of(events)
    found = detect_trills(hands)
    assert len(found) == 1

    marked = Trill(
        hand="right", startFrame=found[0].start_frame, endFrame=found[0].end_frame, row=found[0].row
    )
    before = to_score_payload(hands, anchor())
    after = to_score_payload(_with_trills(hands, [marked]), anchor())

    in_run_before = [
        n for n in before.notes if marked.start_frame <= n.start_frame < marked.end_frame
    ]
    in_run_after = [
        n for n in after.notes if marked.start_frame <= n.start_frame < marked.end_frame
    ]
    assert len(in_run_before) == 8
    assert len(in_run_after) == 1
    assert in_run_after[0].row == marked.row
    assert in_run_after[0].start_frame == marked.start_frame


def test_the_held_note_is_as_long_as_the_run_it_replaces():
    """Its printed length is the gap to the next onset, which is now the note after the trill."""
    events = alternation(8, gap_ms=100.0) + [note(2000.0, 79, length_ms=300.0)]
    hands = hands_of(events)
    found = detect_trills(hands)
    marked = Trill(
        hand="right", startFrame=found[0].start_frame, endFrame=found[0].end_frame, row=found[0].row
    )
    after = to_score_payload(_with_trills(hands, [marked]), anchor())
    held = next(n for n in after.notes if n.start_frame == marked.start_frame)
    # Eight notes 100 ms apart start at 1000 and the next onset is at 2000: one negra of 400 ms
    # would be too short by half, so the mark has to print something longer than the alternation.
    assert held.printed_ms_exact == pytest.approx(1000.0, abs=60.0)
    assert held.figure in {FigureName.BLANCA, FigureName.DOTTED_BLANCA}


def test_nothing_outside_the_mark_moves():
    """The locality every editorial mark has (D-21): a trill relabels its own stretch only."""
    events = alternation(8) + [note(2400.0, 79, length_ms=300.0)]
    hands = hands_of(events)
    found = detect_trills(hands)
    marked = Trill(
        hand="right", startFrame=found[0].start_frame, endFrame=found[0].end_frame, row=found[0].row
    )
    before = to_score_payload(hands, anchor())
    after = to_score_payload(_with_trills(hands, [marked]), anchor())

    def outside(payload):
        return sorted(
            (n.hand, n.row, n.start_frame, n.figure)
            for n in payload.notes
            if n.start_frame >= marked.end_frame
        )

    assert outside(before) == outside(after)
    assert before.envelope.frame_count == after.envelope.frame_count


def test_the_recording_is_not_touched():
    """The mark is a reading of the page. Every alternation is still there to play back (D-29)."""
    hands = hands_of(alternation(8))
    found = detect_trills(hands)
    marked = Trill(
        hand="right", startFrame=found[0].start_frame, endFrame=found[0].end_frame, row=found[0].row
    )
    _with_trills(hands, [marked])
    assert len(to_score_payload(hands, anchor()).notes) == 8
