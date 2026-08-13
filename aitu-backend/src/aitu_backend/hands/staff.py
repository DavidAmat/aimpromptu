"""Where a note lands on the staff its hand is printed on, in ledger lines.

The hand split decides which of two staves a note is **drawn** on: right prints
on the treble staff, left on the bass staff (``matrix/hands.py``). So an
assignment is not only an ergonomic claim, it is a typesetting one, and a hand
sent to the wrong staff shows up as a pile of ledger lines nobody can count.

This module is the small piece of engraving geometry the cost model needs to see
that. It deliberately mirrors ``@aimpromptu/grid-notation``'s
``src/notation/pitch.ts`` — the same diatonic step space, the same bottom-line
steps, the same ``-2`` / ``10`` ledger rule — so the number the split optimizes
is the number the renderer will actually draw. If one of the two changes, they
have to change together; ``test_hands_staff.py`` pins the shared cases.

**Direction matters more than distance.** A hand running *outward* — the left
below its staff, the right above it — is ordinary register. The bottom octave of
the piano is six ledger lines under the bass staff and nobody blinks. A hand
running *across* — the left **above** the bass staff, the right **below** the
treble staff — is the two staves reaching into each other's territory, and past
a line or two it is almost always a split that should have gone the other way.
:func:`ledger_excursion` reports both facts so the cost model can price them
differently.

**Spelling.** Ledger lines follow the written letter, not the pitch: B#3 and C4
sound alike and sit a ledger line apart on the bass staff. The split runs before
any key signature is chosen, so this module spells black keys as sharps — what
``pitchToStaffPosition`` does for C major, its default. The disagreement is at
most one ledger line on a black key, which is well inside the grace either way.
"""

from __future__ import annotations

from typing import Literal

#: Diatonic degree of each pitch class when black keys are spelled as sharps.
#: ``C C# D D# E F F# G G# A A# B`` -> ``0 0 1 1 2 3 3 4 4 5 5 6``.
_DEGREE = (0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6)

#: Diatonic step of each staff's bottom line, in the space :func:`staff_step` uses.
#: Treble bottom line is Mi-4 / E4, bass bottom line is Sol-2 / G2.
_BOTTOM_LINE = {"right": 4 * 7 + 2, "left": 2 * 7 + 4}

#: A staff is five lines at steps 0, 2, 4, 6, 8, so the first ledger line below
#: sits at ``-2`` and the first above at ``10``.
_FIRST_BELOW = -2
_FIRST_ABOVE = 10

#: Which way a hand has left its staff. ``across`` is the left hand above the
#: bass staff or the right hand below the treble staff — the two hands reaching
#: into each other's register. ``outward`` is either hand in its own direction.
Direction = Literal["across", "outward", "inside"]

LEFT = "left"
RIGHT = "right"


def diatonic_index(midi: int) -> int:
    """Diatonic degrees above C0, spelling black keys as sharps.

    The clef-independent half of :func:`staff_step`: ``Do-4`` / C4 is 28, and
    every letter step is 1 whatever the accidental. The ``- 1`` is scientific
    pitch numbering — MIDI 60 is C**4**, not C5 — and it is the same arithmetic
    ``pitchToStaffPosition`` does, which is what keeps the two in step.
    """
    return (midi // 12 - 1) * 7 + _DEGREE[midi % 12]


def staff_step(midi: int, hand: str) -> int:
    """Diatonic steps above the bottom line of the staff ``hand`` prints on.

    ``0`` is the bottom line, ``8`` the top line, odd numbers are spaces.
    Mi-4 / E4 is 0 on the treble staff; Sol-2 / G2 is 0 on the bass staff.
    """
    try:
        bottom = _BOTTOM_LINE[hand]
    except KeyError:  # pragma: no cover - defensive
        raise ValueError(f"Unknown hand {hand!r}; expected 'left' or 'right'") from None
    return diatonic_index(midi) - bottom


def ledger_lines(midi: int, hand: str) -> int:
    """How many ledger lines this note needs on its own staff.

    Counts lines, not steps: a note sitting in the space above the first ledger
    line still needs only that one line. Zero anywhere on the staff.
    """
    step = staff_step(midi, hand)
    if step <= _FIRST_BELOW:
        return -step // 2
    if step >= _FIRST_ABOVE:
        return (step - (_FIRST_ABOVE - 2)) // 2
    return 0


def direction_of(midi: int, hand: str) -> Direction:
    """Which side of its staff this note is on, named by what it means.

    ``across`` — the left hand above the bass staff, or the right hand below the
    treble staff. ``outward`` — either hand past its staff in its own direction.
    ``inside`` — on the staff.
    """
    step = staff_step(midi, hand)
    if _FIRST_BELOW < step < _FIRST_ABOVE:
        return "inside"
    above = step >= _FIRST_ABOVE
    reaching_across = above if hand == LEFT else not above
    return "across" if reaching_across else "outward"


def across_offenders(
    midis: tuple[int, ...] | list[int], hand: str, grace: float
) -> tuple[int, ...]:
    """The notes actually responsible for an ``across`` charge, for the gate to price.

    Only these are candidates for moving to the other hand; the rest of the chord is
    on its own staff and has no complaint.
    """
    return tuple(
        midi
        for midi in midis
        if direction_of(midi, hand) == "across" and ledger_lines(midi, hand) > grace
    )


def reach_gate(
    offenders: tuple[int, ...],
    other_struck: tuple[int, ...],
    other_held: tuple[int, ...],
    *,
    max_simultaneous: int,
    hard_span: float,
    free: float,
    busy: float,
    unreachable: float,
    sustained: float = 1.0,
) -> float:
    """How much of the ``across`` charge applies, given what the other hand is doing.

    Without this the term is charged whether or not anything could be done about it,
    and that is worse than useless. An unavoidable penalty is not merely wasted: it is
    a constant added to every candidate for that group, and it drags on decisions that
    have nothing to do with the note in question.

    So the question is not "how far outside its staff is this note" but "could the
    other hand have taken it":

    * the other hand strikes nothing and holds nothing — its staff is empty, the note
      is simply in the wrong place, and the charge applies in full;
    * the other hand is playing but could still absorb these notes — a real musical
      decision, priced at ``busy``;
    * the other hand cannot take them without a sixth finger or a span no hand has —
      nothing to decide, so ``unreachable`` (zero), and the ledger lines are accepted
      as the correct reading.

    That last case is the one that matters most in practice. It is what lets a left
    hand sit at Do-5 under a right hand already up at Sol-6, or hold a genuine
    crossing over a chord the right hand has all five fingers on, without the term
    quietly arguing against it for the rest of the bar.

    Measured on the research benchmark, gating this way is the difference between the
    term costing accuracy and earning it: ungated it moves 49 onsets away from the
    human labels against 34 towards, gated it moves 38 towards and 1 away.

    **Struck and sustained blockers are not the same thing**, and conflating them was a
    real bug. If the other hand is blocked by keys it is *striking now*, the situation is
    forced and there is nothing to price. If it is blocked only by what it is still
    *holding*, the block may be self-inflicted — an earlier group handed it a chord it
    did not have to take — and exempting it hides exactly the mistake worth finding. The
    closing cadence of *Mr Blue Sky* is this case: the right hand is pinned under its own
    sustains, so the ascent lands on the bass staff under seven ledger lines, and a gate
    that cannot tell the two apart reports nothing wrong. ``sustained`` therefore defaults
    to full charge; feasibility, not the gate, is what protects a genuine crossing, since
    a move into a hand that truly cannot take the notes is rejected as infeasible anyway.
    """
    blocked_by_struck = set(offenders) | set(other_struck)
    blocked_by_all = blocked_by_struck | set(other_held)

    def impossible(notes: set[int]) -> bool:
        return len(notes) > max_simultaneous or (
            bool(notes) and max(notes) - min(notes) > hard_span
        )

    if impossible(blocked_by_struck):
        return unreachable
    if impossible(blocked_by_all):
        return sustained
    if not other_struck and not other_held:
        return free
    return busy


def ledger_excursion(midis: tuple[int, ...] | list[int], hand: str) -> tuple[int, int]:
    """``(across, outward)`` ledger lines for a chord printed on one staff.

    The **extremes**, not a sum: a ledger line is drawn through the whole chord,
    so four notes six lines up cost the page the same six lines as one note does.
    Both numbers are reported because a wide chord can leave its staff in both
    directions at once, and only the ``across`` half says the split may be wrong.
    """
    across = outward = 0
    for midi in midis:
        lines = ledger_lines(midi, hand)
        if not lines:
            continue
        if direction_of(midi, hand) == "across":
            across = max(across, lines)
        else:
            outward = max(outward, lines)
    return across, outward


def ledger_charge(
    hand: str,
    assigned: tuple[int, ...],
    other_struck: tuple[int, ...],
    other_held: tuple[int, ...],
    model,
    relief: dict[int, float] | None = None,
) -> tuple[float, int]:
    """``(charge, across_lines)`` for one hand's notes in one onset group.

    The single implementation of the ledger term. :func:`aitu_backend.hands.costs.transition`
    calls it so the search and the diagnostics agree; the second pass calls it with a
    ``relief`` map so a note a figuration has already explained can be discounted
    without the geometry being restated anywhere.

    ``relief`` maps a MIDI number to a multiplier in ``[0, 1]``. It scales the *excess*,
    before the square — a note whose figuration explains it is treated as if it had
    barely left its staff, not as one that left and got a discount. The difference is
    not cosmetic: squaring afterwards leaves roughly twenty times more residual charge,
    which at this weight is enough to stop a climbing figure being reunited.
    """
    across, outward = ledger_excursion(assigned, hand)
    charge = 0.0
    for lines, grace, way in (
        (across, model.ledger_grace_across, "across"),
        (outward, model.ledger_grace_outward, "outward"),
    ):
        over = max(0.0, lines - grace)
        if over <= 0.0:
            continue
        scale = 1.0
        if way == "across":
            offenders = across_offenders(assigned, hand, model.ledger_grace_across)
            if model.ledger_gate:
                scale *= reach_gate(
                    offenders,
                    other_struck,
                    other_held,
                    max_simultaneous=model.max_simultaneous,
                    hard_span=model.hard_span,
                    free=model.ledger_gate_free,
                    busy=model.ledger_gate_busy,
                    unreachable=model.ledger_gate_unreachable,
                    sustained=model.ledger_gate_sustained,
                )
            if relief and offenders:
                # The least-explained note sets the discount: a ledger stack is drawn
                # once for the whole chord, so one unexplained note keeps it there.
                over *= max(relief.get(midi, 1.0) for midi in offenders)
        charge += scale * (over / model.ledger_reference) ** 2
    return charge, across


__all__ = [
    "LEFT",
    "RIGHT",
    "Direction",
    "across_offenders",
    "diatonic_index",
    "direction_of",
    "ledger_charge",
    "ledger_excursion",
    "ledger_lines",
    "reach_gate",
    "staff_step",
]
