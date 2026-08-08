"""Tresillos: three notes played in the time the ladder gives to two.

A vocabulary of halves has no figure for three even notes filling one beat. At a negra of 300 ms
they land 100 ms apart, which is a third of the way between a corchea and a semicorchea, so forcing
them onto the nearest figure prints a rhythm nobody played. They are recognised instead.

The rule is deliberately narrow, because a wrong tresillo is worse than a missed one: three gaps
that match each other, and that are a third of a figure the ladder knows.
"""

import pytest

from aitu_backend.matrix.ladder import build_ladder, label_peaks
from aitu_backend.matrix.peaks import Peak
from aitu_backend.notation.tuplets import find_tresillos
from aitu_backend.schemas.time_matrix import FigureName
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.time_pipeline import impose_granularity_and_split, to_score_payload

NEGRA_MS = 300.0


def ladder(negra_ms: float = NEGRA_MS):
    return build_ladder(FigureName.NEGRA, negra_ms)


def peak(ms: float) -> Peak:
    return Peak(
        centre_ms=ms, mass=20, share=0.3, lo_ms=ms - 12, hi_ms=ms + 12, mean_ms=ms, median_ms=ms
    )


# --------------------------------------------------------------------------- the rule


def test_three_even_gaps_a_third_of_a_negra_are_a_tresillo():
    found = find_tresillos([100.0, 100.0, 100.0], ladder())
    assert len(found) == 1
    assert found[0].parent == FigureName.NEGRA
    assert found[0].figure == FigureName.CORCHEA
    assert found[0].indexes == (0, 1, 2)


def test_a_little_human_unevenness_is_still_a_tresillo():
    assert len(find_tresillos([96.0, 104.0, 100.0], ladder())) == 1


def test_three_uneven_gaps_are_not_a_tresillo_however_fast_they_are():
    """The gaps matching each other is what says the player was dividing a beat into three."""
    assert find_tresillos([70.0, 130.0, 100.0], ladder()) == []


def test_three_even_gaps_that_are_not_a_third_of_anything_are_not_a_tresillo():
    """150 ms at a negra of 300 is a corchea, and a corchea is what it should print as."""
    assert find_tresillos([150.0, 150.0, 150.0], ladder()) == []


def test_a_tresillo_can_divide_other_figures_too():
    of_blanca = find_tresillos([200.0, 200.0, 200.0], ladder())
    assert of_blanca[0].parent == FigureName.BLANCA
    assert of_blanca[0].figure == FigureName.NEGRA

    of_corchea = find_tresillos([50.0, 50.0, 50.0], ladder())
    assert of_corchea[0].parent == FigureName.CORCHEA
    assert of_corchea[0].figure == FigureName.SEMICORCHEA


def test_six_even_notes_are_two_tresillos_not_four():
    """Groups do not overlap: a note belongs to one tresillo or to none."""
    found = find_tresillos([100.0] * 6, ladder())
    assert [group.start_index for group in found] == [0, 3]


def test_the_ladder_decides_what_a_third_is():
    """The same three 100 ms gaps mean different things under different ladders.

    At a negra of 300 they divide the negra. At 600 they divide the corchea, which is 300 there. At
    450 they divide nothing the vocabulary has, so they are not a tresillo at all and take the
    nearest ordinary figure like anything else.
    """
    assert find_tresillos([100.0] * 3, ladder(300.0))[0].parent == FigureName.NEGRA
    assert find_tresillos([100.0] * 3, ladder(600.0))[0].parent == FigureName.CORCHEA
    assert find_tresillos([100.0] * 3, ladder(450.0)) == []


# --------------------------------------------------------------------------- on the plot


def test_the_long_half_of_a_swung_pair_is_not_offered_as_a_tresillo():
    """Two thirds of a negra is also a third of a blanca, and a shuffle lands almost exactly there.

    Naming that pile a tresillo would tell a reader the piece is in triplets when it is swung. Only
    a third of the negra is offered, and only closely.
    """
    swung_long = label_peaks([peak(2 * NEGRA_MS / 3)], ladder())[0]
    assert swung_long.tresillo_of is None


def test_a_pile_a_third_of_a_negra_is_named_a_tresillo_and_not_a_bad_corchea():
    """D-09: the plot has to say what a pile is, and "corchea, 33 % off" says the wrong thing."""
    labelled = label_peaks([peak(100.0)], ladder())[0]
    assert labelled.tresillo_of == FigureName.NEGRA
    assert labelled.fit.figure == FigureName.CORCHEA
    assert labelled.name == "corchea de tresillo"
    assert labelled.fit.percent_off < 5


def test_an_ordinary_pile_is_still_named_ordinarily():
    for ms, expected in [(150.0, "corchea"), (300.0, "negra"), (600.0, "blanca")]:
        labelled = label_peaks([peak(ms)], ladder())[0]
        assert labelled.tresillo_of is None
        assert labelled.name == expected


# --------------------------------------------------------------------------- on the page


def note(start_ms: float, midi: int, length_ms: float = 80.0) -> NoteEvent:
    return NoteEvent(midi_note=midi, start=start_ms / 1000.0, end=(start_ms + length_ms) / 1000.0)


def test_a_tresillo_prints_as_three_corcheas_carrying_the_number_three():
    clock, events = 0.0, []
    for _ in range(2):  # two negras
        events.append(note(clock, 72, 250.0))
        clock += NEGRA_MS
    for _ in range(3):  # the tresillo
        events.append(note(clock, 74))
        clock += NEGRA_MS / 3
    for _ in range(2):  # two more negras
        events.append(note(clock, 76, 250.0))
        clock += NEGRA_MS

    hands = impose_granularity_and_split(events, 4.0, frame_ms=20, artifacts=None, leakage=None)
    score = to_score_payload(hands, ladder())

    inside = [note for note in score.notes if note.tuplet]
    outside = [note for note in score.notes if not note.tuplet]

    assert len(inside) == 3
    assert all(one.figure == FigureName.CORCHEA for one in inside)
    assert len({one.tuplet_id for one in inside}) == 1
    assert all(one.tuplet == 3 for one in inside)
    assert all(one.figure == FigureName.NEGRA for one in outside[:2])
    # A tresillo is not a fitting error: the three notes are exactly what the mark says they are.
    assert all(one.fit_error == pytest.approx(0.0) for one in inside)


def test_the_two_hands_never_claim_the_same_tresillo():
    clock, events = 0.0, []
    for _ in range(6):
        events.append(note(clock, 74))
        events.append(note(clock + 50, 45))
        clock += NEGRA_MS / 3

    hands = impose_granularity_and_split(events, 4.0, frame_ms=20, artifacts=None, leakage=None)
    score = to_score_payload(hands, ladder())

    right = {n.tuplet_id for n in score.notes if n.hand == "right" and n.tuplet_id is not None}
    left = {n.tuplet_id for n in score.notes if n.hand == "left" and n.tuplet_id is not None}
    assert right and left
    assert not (right & left)


# --------------------------------------------------------------------------- the last group


def test_a_piece_may_end_on_a_tresillo():
    """The final gap runs out to the end of the hand, so it says nothing about the group.

    Without this the closing three notes of every tresillo piece print as two odd figures among
    sixty even ones — raggedness in the one place a reader looks last.
    """
    gaps = [100.0, 100.0, 100.0, 100.0, 100.0, 900.0]  # the 900 is the run-out to the end
    assert len(find_tresillos(gaps, ladder(), open_ended=True)) == 2
    assert len(find_tresillos(gaps, ladder())) == 1


def test_a_short_final_gap_still_refuses_the_group():
    """Open-ended forgives a *long* tail, not a short one. A note cut off early was not even."""
    gaps = [100.0, 100.0, 100.0, 100.0, 100.0, 20.0]
    assert len(find_tresillos(gaps, ladder(), open_ended=True)) == 1


def test_only_the_final_group_is_judged_on_two_gaps():
    """Everything before the end is held to the full rule, tail or no tail."""
    gaps = [100.0, 100.0, 400.0, 100.0, 100.0, 900.0]
    found = find_tresillos(gaps, ladder(), open_ended=True)
    assert [group.start_index for group in found] == [3]
