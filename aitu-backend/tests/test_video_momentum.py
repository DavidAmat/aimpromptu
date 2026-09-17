"""A rectangle falls; anything that does not fall is not a note (V-33, V-34)."""

from __future__ import annotations

from aitu_backend.schemas.video import DetectedRun
from aitu_backend.video import momentum


def _run(midi: int, y_top: int, height: int = 40) -> DetectedRun:
    return DetectedRun(
        midi=midi,
        y_top=y_top,
        y_bottom=y_top + height,
        x0=0.0,
        x1=24.0,
        mid=12.0,
        width_keys=1.0,
        clipped=False,
        tip_trusted=True,
        entering=False,
    )


def test_a_rectangle_that_fell_is_kept_and_one_that_stood_still_is_refused() -> None:
    travel = 17
    fell = _run(60, 200)
    static = _run(64, 300)  # lettering: in the same place in both frames
    before = [_run(60, 200 - travel), _run(64, 300)]

    kept, refused = momentum.apply([fell, static], before, travel, [], 0)
    assert [run.midi for run in kept] == [60]
    assert [run.midi for run in refused] == [64]
    assert fell.momentum == "fell" and static.momentum == "static"


def test_a_run_with_no_neighbour_to_ask_is_kept() -> None:
    """The absence of an answer is not an answer. The rule refuses; it does not
    select — keeping only the proven moving ones dropped 28 real rectangles."""
    lonely = _run(60, 200)
    kept, refused = momentum.apply([lonely], [], 0, [], 0)
    assert kept == [lonely] and refused == []
    assert lonely.momentum == "unknown"


def test_the_frame_after_answers_as_well_as_the_frame_before() -> None:
    """A rectangle at the top of the roll has no frame before it that holds it."""
    travel = 17
    entering = _run(60, 70)
    after = [_run(60, 70 + travel)]
    kept, refused = momentum.apply([entering], [], 0, after, travel)
    assert kept and not refused and entering.momentum == "fell"


def test_a_repeated_note_does_not_alias_into_something_static() -> None:
    """V-34. The strokes are one frame of travel apart, so the first stroke's
    rectangle sits — in the frame before — exactly where the second one sits now.
    Without the one to one constraint the second stroke looks like it never moved.
    """
    travel = 45
    first = _run(60, 200)  # struck earlier, now lower down
    second = _run(60, 200 - travel - 45)  # the new stroke, above it
    before = [_run(60, 200 - travel), _run(60, 200 - travel - 45 - travel)]

    kept, refused = momentum.apply([first, second], before, travel, [], 0)
    assert refused == [], "one to one: the blocking rectangle is already spoken for"
    assert all(run.momentum == "fell" for run in kept)


def test_the_travel_is_voted_for_by_the_runs_and_never_zero() -> None:
    """A correlation answers nothing moved, because the letters really did not."""
    travel = 51
    lettering = [_run(70, 400), _run(71, 420), _run(72, 440)]
    falling = [_run(60, 100), _run(62, 150), _run(64, 220)]
    previous = lettering + [_run(60, 100 - travel), _run(62, 150 - travel), _run(64, 220 - travel)]

    best, agreeing, standing_still = momentum.vote_for_travel(falling + lettering, previous)
    assert best == travel
    assert agreeing == 3
    assert standing_still == 3, "how much of the picture is not music"


def _clipped(midi: int, y_top: int, upper: int = 560) -> DetectedRun:
    """A run the upper line cut: its lowest row is the line, not the rectangle."""
    run = _run(midi, y_top, height=upper - 2 - y_top)
    run.clipped = True
    return run


def test_a_pinned_edge_is_not_evidence_either_way() -> None:
    """A run cut by the upper line has not got a tip there, it has been cut there
    (V-16), so its lowest row stays at the line however fast the rectangle falls.
    Comparing that edge can only ever say "it did not move".

    Measured on a real video the first time the rule was wired: it refused 80
    runs in a fourteen second stretch and **every one of them was clipped**, and
    leaving the pinned edge out took frame to frame agreement over the whole
    video from 94.3% to 97.1%.
    """
    travel = 17
    crossing = _clipped(60, 500)  # a real rectangle, still falling past the line
    before = [_clipped(60, 500 - travel)]

    kept, refused = momentum.apply([crossing], before, travel, [], 0)
    assert kept and not refused
    assert crossing.momentum == "fell"


def test_a_glow_pinned_at_the_line_that_never_moves_is_still_refused() -> None:
    """The other half of the same rule: with the pinned edge out, the free one
    still has to answer, and the strike light's top does not move."""
    glow = _clipped(60, 540)
    before = [_clipped(60, 540)]

    kept, refused = momentum.apply([glow], before, 17, [], 0)
    assert refused == [glow] and not kept
    assert glow.momentum == "static"


def test_a_run_pinned_at_both_ends_is_kept_because_nothing_about_it_can_move() -> None:
    """A rectangle taller than the whole roll is cut at the upper line and still
    coming into view at the roll top. Neither edge is its own, so there is no
    answer — and the absence of an answer is not an answer (V-33)."""
    tall = _clipped(60, 62)
    tall.entering = True
    before = [_clipped(60, 62)]
    before[0].entering = True

    kept, refused = momentum.apply([tall], before, 17, [], 0)
    assert kept == [tall] and not refused
    assert tall.momentum == "unknown"
