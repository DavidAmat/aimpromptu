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


__all__ = [
    "LEFT",
    "RIGHT",
    "Direction",
    "diatonic_index",
    "direction_of",
    "ledger_excursion",
    "ledger_lines",
    "staff_step",
]
