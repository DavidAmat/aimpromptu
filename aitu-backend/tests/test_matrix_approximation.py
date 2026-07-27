"""Appendix C duration approximation and onset snapping."""

import pytest

from aitu_backend.matrix.approximation import (
    DurationFit,
    approximate_duration,
    available_figures,
    expressible_columns,
    figure_columns,
    snap_note,
    snap_onset,
)
from aitu_backend.matrix.keys import note_to_row
from aitu_backend.schemas.matrix import Granularity

SC = Granularity.SEMICORCHEA  # 0.25 s at 60 BPM


# ---------------------------------------------------------- the worked example


def test_appendix_c_worked_case() -> None:
    """1.23 s at 60 BPM / semicorchea -> a plain negra, `1 -1 -1 -1`.

    The two legal candidates either side of 1.23 s are a negra (1.00 s, 0.23 s
    away) and a dotted negra (1.50 s, 0.27 s away). The negra is nearer, so it
    wins. `negra + semicorchea` would be nearer still at 1.25 s — but it ties
    two figures two steps apart, which the adjacency rule forbids, so it is
    never a candidate.
    """
    fit = approximate_duration(1.23, SC, 60)

    assert fit.columns == 4
    assert fit.sustain_columns == 3
    assert fit.figures == (Granularity.NEGRA,)
    assert fit.seconds == pytest.approx(1.0)
    assert fit.error_seconds == pytest.approx(-0.23)
    assert not fit.is_ligature


def test_appendix_c_the_candidates_that_were_compared() -> None:
    """Spell out the comparison the worked case rests on."""
    table = expressible_columns(SC)

    # The two candidates either side of 4.92 columns.
    assert table[4] == (Granularity.NEGRA,)
    assert table[6] == (Granularity.NEGRA, Granularity.CORCHEA)

    assert abs(1.00 - 1.23) < abs(1.50 - 1.23)  # negra beats dotted negra

    # And the tempting shortcut is simply not on the list.
    assert 5 not in table


def test_a_non_adjacent_ligature_is_never_generated() -> None:
    """`negra + semicorchea` skips corchea — exactly the clutter the rule bans."""
    assert 5 not in expressible_columns(SC)
    # It only appears when the rule is deliberately switched off.
    assert expressible_columns(SC, allow_non_adjacent=True)[5] == (
        Granularity.NEGRA,
        Granularity.SEMICORCHEA,
    )


def test_appendix_c_the_other_worked_number() -> None:
    """ "a 1.1 second at semicorchea resolution ... counted as a 1 second"."""
    fit = approximate_duration(1.1, SC, 60)
    assert fit.columns == 4
    assert fit.figures == (Granularity.NEGRA,)
    assert not fit.is_ligature


def test_the_only_legal_lengths_are_singles_and_dotted_notes() -> None:
    """At semicorchea granularity: 1, 2, 3, 4, 6, 8, 12, 16, 24. Nothing else."""
    assert sorted(expressible_columns(SC)) == [1, 2, 3, 4, 6, 8, 12, 16, 24]


# ------------------------------------------------------------------- figures


def test_figure_columns_at_semicorchea_granularity() -> None:
    assert figure_columns(Granularity.SEMICORCHEA, SC) == 1
    assert figure_columns(Granularity.CORCHEA, SC) == 2
    assert figure_columns(Granularity.NEGRA, SC) == 4
    assert figure_columns(Granularity.BLANCA, SC) == 8
    assert figure_columns(Granularity.REDONDA, SC) == 16


def test_a_figure_finer_than_the_grid_cannot_be_drawn() -> None:
    with pytest.raises(ValueError, match="finer than"):
        figure_columns(Granularity.FUSA, SC)


def test_available_figures_stops_at_the_grid() -> None:
    assert available_figures(Granularity.NEGRA) == [
        Granularity.REDONDA,
        Granularity.BLANCA,
        Granularity.NEGRA,
    ]


def test_expressible_counts_at_semicorchea() -> None:
    table = expressible_columns(SC)
    singles = {1, 2, 4, 8, 16}
    dotted = {3, 6, 12, 24}  # adjacent pairs only
    assert singles <= set(table)
    assert dotted <= set(table)
    # 5 would need a non-adjacent tie; 7 would need three figures.
    assert 5 not in table
    assert 7 not in table


def test_dotted_notes_fall_out_of_the_pair_rule() -> None:
    table = expressible_columns(SC)
    assert table[6] == (Granularity.NEGRA, Granularity.CORCHEA)  # dotted negra
    assert table[3] == (Granularity.CORCHEA, Granularity.SEMICORCHEA)  # dotted corchea
    assert table[12] == (Granularity.BLANCA, Granularity.NEGRA)  # dotted blanca


def test_a_coarser_leading_figure_wins_an_ambiguity() -> None:
    """6 = negra + corchea, never corchea + something."""
    assert expressible_columns(SC)[6][0] is Granularity.NEGRA


def test_every_ligature_is_a_dotted_note() -> None:
    """Two adjacent figures tied *is* a dotted note. There is no other kind."""
    for columns, figures in expressible_columns(SC).items():
        if len(figures) == 2:
            first, second = figures
            assert figure_columns(first, SC) == 2 * figure_columns(second, SC), columns


def test_single_figure_mode() -> None:
    table = expressible_columns(SC, max_figures=1)
    assert set(table) == {1, 2, 4, 8, 16}


# ----------------------------------------------------------------- rounding


@pytest.mark.parametrize(
    "duration,columns",
    [
        (0.25, 1),  # exactly one semicorchea
        (0.24, 1),
        (0.26, 1),
        (0.5, 2),
        (0.74, 3),  # dotted corchea
        (1.0, 4),  # negra
        (1.1, 4),  # nearer the negra than the dotted negra
        (1.23, 4),  # the appendix's worked case
        (1.25, 4),  # 5 columns is unwritable, and 4 is the nearer neighbour
        (1.40, 6),  # now the dotted negra is nearer
        (1.5, 6),  # dotted negra exactly
        (2.0, 8),
        (4.0, 16),
    ],
)
def test_a_duration_takes_the_nearest_writable_length(duration: float, columns: int) -> None:
    assert approximate_duration(duration, SC, 60).columns == columns


def test_a_very_short_duration_still_gets_one_column() -> None:
    """A note cannot vanish: the floor is a single column."""
    fit = approximate_duration(0.01, SC, 60)
    assert fit.columns == 1
    assert fit.error_seconds > 0


def test_an_unwritable_length_takes_the_nearer_neighbour() -> None:
    """1.75 s = 7 columns, which no legal pair makes. 6 and 8 are equidistant."""
    fit = approximate_duration(1.75, SC, 60)
    assert fit.columns == 6  # the tie goes to the shorter note
    assert fit.figures == (Granularity.NEGRA, Granularity.CORCHEA)
    assert fit.error_seconds < 0  # shortened, never lengthened into the next note


def test_a_duration_past_the_longest_ligature_is_clamped() -> None:
    """24 columns (redonda + blanca) is the longest two-figure note."""
    fit = approximate_duration(100.0, SC, 60)
    assert fit.columns == 24
    assert fit.figures == (Granularity.REDONDA, Granularity.BLANCA)


def test_a_non_positive_duration_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        approximate_duration(0, SC, 60)


def test_tempo_scales_everything() -> None:
    """At 120 BPM a semicorchea is 0.125 s, so the same note takes half the time."""
    slow = approximate_duration(1.0, SC, 60)
    fast = approximate_duration(0.5, SC, 120)
    assert slow.columns == fast.columns == 4
    assert slow.figures == fast.figures == (Granularity.NEGRA,)


def test_fit_describes_itself() -> None:
    assert approximate_duration(1.23, SC, 60).describe() == "negra (4 columns, -0.230 s)"
    assert approximate_duration(1.50, SC, 60).describe() == "negra + corchea (6 columns, +0.000 s)"


# ------------------------------------------------------------ onset snapping


@pytest.mark.parametrize(
    "start,column",
    [
        (0.0, 0),
        (0.10, 0),  # early in column 0
        (0.13, 1),  # past the halfway mark
        (0.25, 1),
        (0.99, 4),
        (1.0, 4),
    ],
)
def test_onsets_snap_to_the_nearest_boundary(start: float, column: int) -> None:
    assert snap_onset(start, SC, 60) == column


def test_a_low_tolerance_pushes_onsets_later() -> None:
    """tolerance is the fraction of a column past which we round up."""
    # 0.30 s = column 1 + 20% of a column.
    assert snap_onset(0.30, SC, 60, tolerance=0.5) == 1
    assert snap_onset(0.30, SC, 60, tolerance=0.1) == 2


def test_tolerance_bounds_are_enforced() -> None:
    for bad in (0, -0.1, 1.5):
        with pytest.raises(ValueError, match="tolerance"):
            snap_onset(0.5, SC, 60, tolerance=bad)


def test_a_negative_onset_is_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        snap_onset(-0.1, SC, 60)


def test_a_slightly_rushed_player_still_lands_on_the_beat() -> None:
    """0.98 s and 1.02 s are the same negra to a human, and to us."""
    assert snap_onset(0.98, SC, 60) == snap_onset(1.02, SC, 60) == 4


# --------------------------------------------------------------- whole notes


def test_snap_note_places_a_transcription_event() -> None:
    note = snap_note(
        note_to_row("Do-4"), start_seconds=1.02, duration_seconds=1.23, granularity=SC, tempo_bpm=60
    )

    assert note.row == note_to_row("Do-4")
    assert note.start_column == 4
    assert note.fit.columns == 4
    assert note.end_column == 8


def test_a_scale_of_negras_lands_on_consecutive_beats() -> None:
    """Do Re Mi Fa Sol as slow negras at 60 BPM, played a touch unevenly."""
    played = [(0.00, 1.01), (1.03, 0.98), (1.98, 1.02), (3.05, 0.97), (3.99, 1.00)]
    names = ["Do-4", "Re-4", "Mi-4", "Fa-4", "Sol-4"]

    notes = [
        snap_note(note_to_row(name), start, duration, SC, 60)
        for name, (start, duration) in zip(names, played)
    ]

    assert [note.start_column for note in notes] == [0, 4, 8, 12, 16]
    assert all(note.fit.columns == 4 for note in notes)
    assert all(note.fit.figures == (Granularity.NEGRA,) for note in notes)
    # No note overlaps the next one's onset.
    assert all(a.end_column <= b.start_column for a, b in zip(notes, notes[1:]))


def test_the_fit_dataclass_is_immutable() -> None:
    fit = approximate_duration(1.0, SC, 60)
    assert isinstance(fit, DurationFit)
    with pytest.raises(Exception):
        fit.columns = 9  # type: ignore[misc]
