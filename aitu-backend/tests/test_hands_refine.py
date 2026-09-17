"""The second pass: the register gate, figuration detection, and the two together.

Three properties matter more than any single hand string here.

**It must be inert where there is nothing to fix.** A pass that rewrites ordinary music
to satisfy a page-level rule is worse than no pass. So the figuration term is asserted
to change *nothing* on textures that contain no figure, and the register term nothing on
notes it cannot help.

**The gate must decide, not the distance.** A high left hand under a right hand that
could take it is a mistake; the same note under a right hand that physically cannot is
the correct reading. Both are tested, and they differ only in what the other hand does.

**A pattern must outrank the page.** Schubert's left hand climbs out of the bass staff
one turn at a time and prints with a treble clef inside the bass staff. The register rule
alone would cut it in half; the relief is what stops it.
"""

from __future__ import annotations

import numpy as np
import pytest

from aitu_backend.hands import DEFAULT_CONFIG, decode_matrix, infer_hands
from aitu_backend.hands.figuration import detect
from aitu_backend.hands.refine import evaluate, refine_map, relief_map
from aitu_backend.hands.staff import (
    direction_of,
    ledger_charge,
    reach_gate,
)
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep

HAND = DEFAULT_CONFIG.hand


def build(events: list[tuple[str, int, int]], granularity=Granularity.SEMICORCHEA) -> PianoMatrix:
    """``[(note, start_frame, duration)]`` -> a clean matrix."""
    frames = max(start + duration for _n, start, duration in events)
    grid = np.zeros((KEY_COUNT, frames), dtype=np.int8)
    for name, start, duration in events:
        row = note_to_row(name)
        grid[row, start] = 1
        grid[row, start + 1 : start + duration] = -1
    return PianoMatrix.from_dense(
        grid,
        granularity=granularity,
        tempo_bpm=120.0,
        processing_step=MatrixProcessingStep.CLEAN,
    )


def figure(turns: list[list[str]], start: int = 0) -> list[tuple[str, int, int]]:
    return [
        (name, start + index, 1)
        for index, name in enumerate(name for turn in turns for name in turn)
    ]


def hands_of(matrix: PianoMatrix, **overrides) -> dict[str, str]:
    config = DEFAULT_CONFIG
    for key, value in overrides.items():
        config = getattr(config, f"with_{key}")(**value)
    return infer_hands(matrix, config).hand_of()


# ======================================================================================
# the gate
# ======================================================================================


def test_the_gate_is_open_when_the_other_staff_is_empty() -> None:
    gate = reach_gate(
        (72,),
        (),
        (),
        max_simultaneous=5,
        hard_span=15.0,
        free=HAND.ledger_gate_free,
        busy=HAND.ledger_gate_busy,
        unreachable=HAND.ledger_gate_unreachable,
    )
    assert gate == pytest.approx(1.0)


def test_the_gate_is_shut_when_the_other_hand_cannot_reach() -> None:
    """Left hand at Do-5 while the right is at Sol-6: nineteen semitones, no hand."""
    gate = reach_gate(
        (72,),
        (91,),
        (),
        max_simultaneous=5,
        hard_span=15.0,
        free=HAND.ledger_gate_free,
        busy=HAND.ledger_gate_busy,
        unreachable=HAND.ledger_gate_unreachable,
    )
    assert gate == pytest.approx(0.0)


def test_the_gate_is_shut_when_the_other_hand_has_no_fingers_left() -> None:
    full = (60, 62, 64, 65, 67)
    gate = reach_gate(
        (69,),
        full,
        (),
        max_simultaneous=5,
        hard_span=15.0,
        free=1.0,
        busy=1.0,
        unreachable=0.0,
    )
    assert gate == pytest.approx(0.0)


def test_an_unreachable_note_is_charged_nothing() -> None:
    """The point of the gate: no constant left behind to skew the rest of the group."""
    charge, _lines = ledger_charge("left", (72,), (91,), (), HAND)
    assert charge == pytest.approx(0.0)
    reachable, _lines = ledger_charge("left", (72,), (), (), HAND)
    assert reachable > 0.0


def test_outward_register_is_not_charged_across() -> None:
    """The bottom octave of the piano is register, not a mistake."""
    assert direction_of(note_to_row("La-0") + 21, "left") == "outward"
    charge, _lines = ledger_charge("left", (note_to_row("La-0") + 21,), (), (), HAND)
    assert charge == pytest.approx(0.0)


# ======================================================================================
# the register repair
# ======================================================================================


def test_a_lone_high_left_hand_note_moves_when_the_right_hand_is_free() -> None:
    matrix = build(
        [
            ("Do-2", 0, 2),
            ("Sol-2", 2, 2),
            ("Do-3", 4, 2),
            ("Do-5", 6, 2),
            ("Sol-2", 8, 2),
            ("Do-2", 10, 4),
        ],
        granularity=Granularity.CORCHEA,
    )
    hands = hands_of(matrix)
    spike = next(event for event in decode_matrix(matrix).events if event.note == "Do-5")
    assert hands[spike.onset_id] == "right"


def test_the_same_note_stays_put_when_the_right_hand_is_already_high() -> None:
    """Do-5 under a right hand at Do-6/Mi-6/Sol-6 is nineteen semitones out of reach."""
    matrix = build(
        [
            ("Do-6", 0, 2),
            ("Mi-6", 0, 2),
            ("Sol-6", 0, 2),
            ("Do-5", 0, 2),
            ("Do-6", 2, 2),
            ("Mi-6", 2, 2),
            ("Sol-6", 2, 2),
            ("Sol-4", 2, 2),
        ],
        granularity=Granularity.CORCHEA,
    )
    hands = hands_of(matrix)
    for name in ("Do-5", "Sol-4"):
        event = next(e for e in decode_matrix(matrix).events if e.note == name)
        assert hands[event.onset_id] == "left", name


def test_the_pass_reports_what_it_flagged_and_moved() -> None:
    matrix = build(
        [
            ("Do-2", 0, 2),
            ("Sol-2", 2, 2),
            ("Do-3", 4, 2),
            ("Do-5", 6, 2),
            ("Sol-2", 8, 2),
            ("Do-2", 10, 4),
        ],
        granularity=Granularity.CORCHEA,
    )
    result = infer_hands(matrix, DEFAULT_CONFIG)
    assert result.method == "beam-refine-v1"
    assert "refine" in result.diagnostics.extra
    assert "ledgerCost" in result.diagnostics.extra


# ======================================================================================
# figuration
# ======================================================================================


ALBERTI = figure([["Do-3", "Sol-3", "Mi-3", "Sol-3"]] * 6)
CLIMB = figure(
    [
        ["Sol-2", "Si-2", "Re-3"],
        ["Si-2", "Re-3", "Sol-3"],
        ["Re-3", "Sol-3", "Si-3"],
        ["Sol-3", "Si-3", "Re-4"],
        ["Si-3", "Re-4", "Sol-4"],
        ["Re-4", "Sol-4", "Si-4"],
        ["Sol-4", "Si-4", "Re-5"],
        ["Si-4", "Re-5", "Sol-5"],
    ]
)


def test_alberti_bass_is_a_figure() -> None:
    matrix = build(ALBERTI)
    decoded = decode_matrix(matrix)
    figures = detect(decoded, hands_of(matrix), DEFAULT_CONFIG.figures)
    assert len(figures) == 1
    assert figures[0].period == 4
    assert figures[0].n_cycles == 6


@pytest.mark.parametrize(
    "events",
    [
        pytest.param(
            [
                (name, index, 1)
                for index, name in enumerate(
                    [
                        "Do-4",
                        "Re-4",
                        "Mi-4",
                        "Fa-4",
                        "Sol-4",
                        "La-4",
                        "Si-4",
                        "Do-5",
                        "Re-5",
                        "Mi-5",
                        "Fa-5",
                        "Sol-5",
                        "La-5",
                        "Si-5",
                        "Do-6",
                    ]
                )
            ],
            id="a scale is not a figure",
        ),
        pytest.param(
            [("Do-5" if index % 2 == 0 else "Si-4", index, 1) for index in range(16)],
            id="a trill is not a figure",
        ),
        pytest.param(
            [
                (name, index, 1)
                for index, name in enumerate(
                    [
                        "Sol#-5",
                        "Sol-5",
                        "Fa-5",
                        "Mi-5",
                        "Fa-5",
                        "Sol-5",
                        "Sol#-5",
                        "La#-5",
                        "Do-6",
                        "La#-5",
                        "Sol#-5",
                        "Sol-5",
                        "Fa-5",
                        "Mi-5",
                        "Fa-5",
                        "Sol-5",
                    ]
                )
            ],
            id="a wandering melody is not a figure",
        ),
    ],
)
def test_things_that_repeat_but_are_not_figurations(events) -> None:
    matrix = build(events)
    decoded = decode_matrix(matrix)
    assert detect(decoded, hands_of(matrix), DEFAULT_CONFIG.figures) == []


def test_a_figure_the_search_split_is_detected_whole() -> None:
    """Schubert's climb migrates hand to hand; the detector must see all of it."""
    matrix = build(CLIMB)
    decoded = decode_matrix(matrix)
    beam_hands = hands_of(matrix, method={"method": "beam"})
    assert len(set(beam_hands.values())) == 2, "expected the beam to split this"
    figures = detect(decoded, beam_hands, DEFAULT_CONFIG.figures)
    assert len(figures) == 1
    assert len(figures[0].onset_ids) >= 0.9 * len(decoded.events)


def test_the_pass_puts_a_split_figure_back_in_one_hand() -> None:
    matrix = build(CLIMB)
    beam_hands = hands_of(matrix, method={"method": "beam"})
    assert len(set(beam_hands.values())) == 2
    refined = hands_of(matrix)
    assert len(set(refined.values())) == 1, "the figure should end up in one hand"


def test_relief_reaches_the_owner_of_a_figure_and_nobody_else() -> None:
    matrix = build(CLIMB)
    decoded = decode_matrix(matrix)
    beam_hands = hands_of(matrix, method={"method": "beam"})
    figures = detect(decoded, beam_hands, DEFAULT_CONFIG.figures)
    relief = relief_map(figures, beam_hands, DEFAULT_CONFIG)
    owner = max(
        ("left", "right"),
        key=lambda hand: sum(1 for o in figures[0].onset_ids if beam_hands[o] == hand),
    )
    owned = [o for o in figures[0].onset_ids if beam_hands[o] == owner]
    taken = [o for o in figures[0].onset_ids if beam_hands[o] != owner]
    assert owned and taken
    assert all(relief.get(o, 1.0) < 0.2 for o in owned)
    assert all(relief.get(o, 1.0) == 1.0 for o in taken), "a stolen note earns no relief"


def test_relief_does_not_leak_to_notes_with_no_figure_behind_them() -> None:
    """The control: with no pattern, a high left hand is still a high left hand."""
    matrix = build(
        [
            ("Do-2", 0, 2),
            ("Sol-2", 2, 2),
            ("Do-3", 4, 2),
            ("Do-5", 6, 2),
            ("Sol-2", 8, 2),
            ("Do-2", 10, 4),
        ],
        granularity=Granularity.CORCHEA,
    )
    decoded = decode_matrix(matrix)
    beam_hands = hands_of(matrix, method={"method": "beam"})
    figures = detect(decoded, beam_hands, DEFAULT_CONFIG.figures)
    assert relief_map(figures, beam_hands, DEFAULT_CONFIG) == {}


def test_the_figuration_term_is_inert_where_there_is_no_figuration() -> None:
    matrix = build(
        [
            (name, index * 2, 2)
            for index, name in enumerate(["Do-5", "Mi-5", "Sol-5", "Mi-5", "Do-5", "Si-4"])
        ]
        + [
            ("Do-3", 0, 4),
            ("Sol-3", 0, 4),
            ("Fa-2", 4, 4),
            ("Do-3", 4, 4),
            ("Sol-2", 8, 4),
            ("Re-3", 8, 4),
        ],
        granularity=Granularity.CORCHEA,
    )
    only_ledger = hands_of(matrix, refine={"pattern_weight": 0.0})
    both = hands_of(matrix)
    assert both == only_ledger


# ======================================================================================
# invariants of the pass itself
# ======================================================================================


@pytest.mark.parametrize("events", [ALBERTI, CLIMB])
def test_the_pass_never_makes_the_music_or_the_pattern_worse(events) -> None:
    """Its licence is to buy readability with ergonomic cost, and only that.

    The pattern term is held to never rise, and neither is infeasibility. The *ledger*
    term may rise, and on the climbing figure it does: reuniting a figure that walked out
    of the bass staff is precisely a trade of ledger lines for an unbroken gesture. What
    may not rise is the total, which is where the trade is judged.
    """
    matrix = build(events)
    decoded = decode_matrix(matrix)
    before_map = hands_of(matrix, method={"method": "beam"})
    figures = detect(decoded, before_map, DEFAULT_CONFIG.figures)
    before = evaluate(decoded, before_map, DEFAULT_CONFIG, figures)
    after_map, _stats, _figures = refine_map(decoded, dict(before_map), DEFAULT_CONFIG)
    after = evaluate(decoded, after_map, DEFAULT_CONFIG, figures)
    assert after.pattern <= before.pattern + 1e-9
    assert after.infeasible <= before.infeasible
    assert after.total(DEFAULT_CONFIG.refine) <= before.total(DEFAULT_CONFIG.refine) + 1e-9


def test_incremental_replay_agrees_with_a_full_one() -> None:
    """The pass rests on this shortcut; if it drifts, every acceptance is wrong."""
    import random

    matrix = build(CLIMB)
    decoded = decode_matrix(matrix)
    hand_map = hands_of(matrix, method={"method": "beam"})
    figures = detect(decoded, hand_map, DEFAULT_CONFIG.figures)
    reference = evaluate(decoded, hand_map, DEFAULT_CONFIG, figures)

    from aitu_backend.hands.refine import changed_span

    rng = random.Random(11)
    for _ in range(12):
        candidate = dict(hand_map)
        for onset_id in rng.sample(sorted(candidate), rng.randint(1, len(candidate))):
            candidate[onset_id] = "left" if candidate[onset_id] == "right" else "right"
        span = changed_span(decoded, hand_map, candidate)
        fast = evaluate(
            decoded, candidate, DEFAULT_CONFIG, figures, reference=reference, changed=span
        )
        slow = evaluate(decoded, candidate, DEFAULT_CONFIG, figures)
        assert fast.base == pytest.approx(slow.base)
        assert fast.ledger == pytest.approx(slow.ledger)
        assert fast.infeasible == slow.infeasible


def test_disabling_the_pass_reproduces_the_beam() -> None:
    matrix = build(CLIMB)
    assert hands_of(matrix, refine={"enabled": False}) == hands_of(
        matrix, method={"method": "beam"}
    )


def test_the_split_is_still_an_exact_partition() -> None:
    matrix = build(CLIMB)
    result = infer_hands(matrix, DEFAULT_CONFIG)
    recombined = result.right_grid + result.left_grid
    assert np.array_equal(recombined, matrix.grid)
