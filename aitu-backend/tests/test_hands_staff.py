"""The ledger-line term: what an assignment costs the *page*, not the hands.

Every other cost in :mod:`aitu_backend.hands.costs` asks what a pianist can do.
This one asks what the result looks like once it is engraved, because the split
also decides which staff a note is drawn on — right on the treble, left on the
bass — and a hand parked on the wrong staff prints as a stack of ledger lines a
reader counts instead of reads.

The case that produced it is in :func:`test_the_passage_david_pointed_at`: a real
66-frame window of *Mr Blue Sky*, transcribed at 40 ms, in which the left hand
took Fa-5 (six ledger lines above the bass staff) while the right hand took Fa-2
(six below the treble) for three onsets, and then the two swapped back. The
fixture is the recording's own onsets, not a construction, so it also pins the
search bug that let the swap happen at all.
"""

import numpy as np
import pytest

from aitu_backend.hands import DEFAULT_CONFIG, infer_hands
from aitu_backend.hands.costs import LEFT, RIGHT, HandState, PairState, transition
from aitu_backend.hands.events import OnsetGroup, decode_matrix
from aitu_backend.hands.staff import (
    direction_of,
    ledger_excursion,
    ledger_lines,
    staff_step,
)
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep

# --------------------------------------------------------------------- geometry


@pytest.mark.parametrize(
    ("note", "hand", "step"),
    [
        # The five lines of each staff are steps 0, 2, 4, 6, 8.
        ("Mi-4", RIGHT, 0),  # E4, bottom line of the treble staff
        ("Fa-5", RIGHT, 8),  # F5, top line of the treble staff
        ("Sol-2", LEFT, 0),  # G2, bottom line of the bass staff
        ("La-3", LEFT, 8),  # A3, top line of the bass staff
        # Middle C is one ledger line either way — the two staves' shared note.
        ("Do-4", RIGHT, -2),
        ("Do-4", LEFT, 10),
    ],
)
def test_the_staff_steps_agree_with_the_engraver(note: str, hand: str, step: int) -> None:
    """These six anchors are the contract with ``grid-notation``'s ``pitch.ts``.

    That module computes the same steps for drawing. If one side moves without
    the other, the split optimises a page nobody will print.
    """
    assert staff_step(note_to_row(note) + 21, hand) == step


@pytest.mark.parametrize(
    ("note", "hand", "lines"),
    [
        ("Do-4", LEFT, 1),  # C4, first ledger above the bass staff
        ("Re-4", LEFT, 1),  # D4 sits in the space above that line — still one line
        ("Mi-4", LEFT, 2),
        ("Fa-5", LEFT, 6),  # the note in the picture
        ("La-0", LEFT, 6),  # ...and the bottom of the piano, also six. Direction decides.
        ("Do-4", RIGHT, 1),
        ("La-3", RIGHT, 2),
        ("Fa-2", RIGHT, 6),  # the other note in the picture
        ("Do-7", RIGHT, 5),
        ("Sol-4", RIGHT, 0),
        ("Re-3", LEFT, 0),
    ],
)
def test_ledger_lines_are_counted_as_lines_not_steps(note: str, hand: str, lines: int) -> None:
    assert ledger_lines(note_to_row(note) + 21, hand) == lines


def test_the_same_six_lines_mean_opposite_things() -> None:
    """La-0 and Fa-5 are both six ledger lines off the bass staff, and only one is a fault.

    This is the whole reason the term is direction-aware. The bottom octave of
    the piano lives six lines under the bass staff and every printed edition
    writes it there; a left hand six lines *above* it is reaching into the right
    hand's register.
    """
    low, high = note_to_row("La-0") + 21, note_to_row("Fa-5") + 21
    assert ledger_lines(low, LEFT) == ledger_lines(high, LEFT) == 6
    assert direction_of(low, LEFT) == "outward"
    assert direction_of(high, LEFT) == "across"
    # Mirrored for the right hand: high is its own register, low is the bass's.
    assert direction_of(note_to_row("Do-7") + 21, RIGHT) == "outward"
    assert direction_of(note_to_row("Fa-2") + 21, RIGHT) == "across"


def test_a_chord_pays_for_its_extremes_not_for_every_note() -> None:
    """One ledger line is drawn through the whole chord, so four notes cost what one does."""
    one = [note_to_row("Fa-5") + 21]
    four = [note_to_row(name) + 21 for name in ("Do-5", "Mi-5", "Sol-5", "Fa-5")]
    assert ledger_excursion(one, LEFT) == ledger_excursion(four, LEFT) == (6, 0)


def test_a_wide_chord_can_leave_its_staff_in_both_directions() -> None:
    """Both numbers are reported because only the ``across`` half accuses the split."""
    spread = [note_to_row(name) + 21 for name in ("Do-2", "Fa-5")]
    assert ledger_excursion(spread, LEFT) == (6, 2)


# ------------------------------------------------------------------ the charge


def _group(names: list[str], time: float = 1.0, duration: int = 4) -> OnsetGroup:
    grid = np.zeros((KEY_COUNT, duration + 1), dtype=np.int8)
    for name in names:
        grid[note_to_row(name), 0] = 1
        grid[note_to_row(name), 1:duration] = -1
    matrix = PianoMatrix.time_based(grid, frame_ms=40.0)
    decoded = decode_matrix(matrix)
    return OnsetGroup(column=0, time_seconds=time, events=decoded.groups[0].events)


#: The term runs in the second pass, not in the search, so ``CostWeights.ledger`` is
#: zero and the weight that matters lives in :class:`RefineConfig`. See
#: :mod:`aitu_backend.hands.refine` for why it moved.
LEDGER_WEIGHT = DEFAULT_CONFIG.refine.ledger_weight


def _ledger_cost(names: list[str], assignment: tuple[str, ...]) -> float:
    """The weighted ledger charge for one group, from two rested hands.

    Two rested hands means the other staff is empty, so the gate is fully open and this
    measures the raw geometry. What happens when the other hand is *not* free is the
    subject of ``test_hands_refine.py``.
    """
    result = transition(
        PairState(), _group(names), assignment, DEFAULT_CONFIG.hand, DEFAULT_CONFIG.weights
    )
    assert result is not None
    return LEDGER_WEIGHT * result.breakdown.ledger


def test_the_deep_bass_is_free() -> None:
    """Six ledger lines under the bass staff is register, and register is not a mistake."""
    assert _ledger_cost(["La-0", "Do-1"], (LEFT, LEFT)) == 0.0
    assert _ledger_cost(["Do-7", "Mi-7"], (RIGHT, RIGHT)) == 0.0


def test_a_note_or_two_across_the_staff_is_free() -> None:
    """Up to Fa-4 in the bass and down to Sol-3 in the treble: the shared middle."""
    assert _ledger_cost(["Re-4"], (LEFT,)) == 0.0
    assert _ledger_cost(["Fa-4"], (LEFT,)) == 0.0
    assert _ledger_cost(["La-3"], (RIGHT,)) == 0.0
    assert _ledger_cost(["Sol-3"], (RIGHT,)) == 0.0
    # The third line is where the charge starts, and at the weight the second pass
    # runs at it is a real number rather than a nudge — 1.0, about the same as an
    # awkward relocation. What keeps an ordinary chord dipping below the treble from
    # being overruled is not the size of this number but the gate: unless the other
    # hand is genuinely free to take the notes, none of it is charged at all.
    assert _ledger_cost(["Fa-3"], (RIGHT,)) == pytest.approx(1.0)


def test_the_charge_grows_with_the_excursion() -> None:
    """Quadratic past the grace: a nudge at three lines, a verdict at six."""
    three = _ledger_cost(["Sol-4"], (LEFT,))
    six = _ledger_cost(["Fa-5"], (LEFT,))
    assert three == pytest.approx(1.0)
    assert six > 12.0
    # Quadratic, not linear — four times the excess is sixteen times the charge.
    assert six == pytest.approx(16 * three)


def test_the_charge_is_symmetric_between_the_two_hands() -> None:
    """A right hand under the treble staff is the same fault as a left hand over the bass."""
    assert _ledger_cost(["Fa-5"], (LEFT,)) == pytest.approx(_ledger_cost(["Fa-2"], (RIGHT,)))


def test_the_picture_costs_nothing_to_read_and_is_what_gets_chosen() -> None:
    """Fa-2 with Fa-5: the natural reading is free, and it is the one the model picks.

    Worth being precise about *which* term earns this. The swapped reading — Fa-2 on the
    treble staff, Fa-5 on the bass — is charged nothing, because the gate asks "could the
    other hand also take this note" and the answer is no: thirty-six semitones is beyond
    any hand. The gate cannot express "they should trade", and it is not asked to. The
    crossing and collision terms already refuse an inversion this wide, which is why the
    end-to-end answer is right; the ledger term's job starts where a hand is merely in
    the wrong place, not where the two are swapped outright.
    """
    assert _ledger_cost(["Fa-2", "Fa-5"], (LEFT, RIGHT)) == 0.0

    grid = np.zeros((KEY_COUNT, 4), dtype=np.int8)
    for name in ("Fa-2", "Fa-5"):
        grid[note_to_row(name), 0] = 1
        grid[note_to_row(name), 1:3] = -1
    matrix = PianoMatrix.from_dense(
        grid,
        granularity=Granularity.NEGRA,
        tempo_bpm=60.0,
        processing_step=MatrixProcessingStep.CLEAN,
    )
    chosen = {item.note: item.hand for item in infer_hands(matrix, DEFAULT_CONFIG).assignments}
    assert chosen == {"Fa-2": LEFT, "Fa-5": RIGHT}


def test_a_crossing_the_hands_are_committed_to_still_ends() -> None:
    """The term is a cost, not a veto: real hand-crossings survive it.

    Here the left hand is genuinely up at Sol-5 and the right is holding a chord
    that pins it; the crossed assignment is charged for its ledger lines and is
    still chosen, because the alternative is unplayable. A term that could
    overrule feasibility would have turned this package back into a pitch
    threshold, which is the thing it exists to replace.
    """
    pinned = PairState(
        left=HandState(center=79.0, notes=(79,), last_time=0.9, held=((79, 1.05),)),
        right=HandState(
            center=55.0,
            notes=(48, 52, 55, 59, 62),
            last_time=0.9,
            held=((48, 3.0), (52, 3.0), (55, 3.0), (59, 3.0), (62, 3.0)),
        ),
    )
    group = _group(["La-5"], time=1.2)
    to_left = transition(pinned, group, (LEFT,), DEFAULT_CONFIG.hand, DEFAULT_CONFIG.weights)
    to_right = transition(pinned, group, (RIGHT,), DEFAULT_CONFIG.hand, DEFAULT_CONFIG.weights)
    assert to_right is None, "the right hand has five keys down; it cannot take a sixth"
    assert to_left is not None
    # Still charged: the right hand is blocked by what it is *holding*, and a sustain
    # can be a decision made too early rather than a fact of the music, so the gate
    # does not excuse it. What protects the crossing is feasibility, not the size of
    # the penalty — the second pass will try to move La-5 to the right hand, find the
    # move infeasible, and leave the crossing exactly where it is.
    assert to_left.breakdown.ledger > 0.0


def test_zeroing_the_weight_removes_the_term() -> None:
    """Every term here is separately ablatable, and this one is no exception."""
    config = DEFAULT_CONFIG.with_weights(ledger=0.0)
    result = transition(PairState(), _group(["Fa-5"]), (LEFT,), config.hand, config.weights)
    assert result is not None
    assert result.breakdown.ledger > 0.0
    assert result.breakdown.weighted_dict(config.weights)["ledger"] == 0.0


# ------------------------------------------------------- the passage in the picture

#: *Mr Blue Sky*, segment 00:05.00–04:57.37, frames f1010–f1075 at 40 ms, exactly
#: as ``events_to_time_matrix`` produces them. ``(column, note, frames)``; columns
#: are relative, so column 31 is f1041 and column 34 is f1044.
#:
#: The passage is a right-hand melody over a repeated Fa octave in the bass. Its
#: last chord — column 51 — is the one that matters to the search: the right hand
#: is still holding Do-5 when five more keys are struck, so *no* partition of it
#: is playable and the beam has to fall back. What it did with that fallback is
#: what put the melody in the wrong hand three onsets earlier.
MR_BLUE_F1010 = [
    (0, "Do-2", 2),
    (0, "Do-3", 4),
    (0, "Do-5", 5),
    (0, "Mi-5", 7),
    (5, "La-4", 11),
    (5, "Do-5", 11),
    (5, "Fa-5", 26),
    (9, "Fa-2", 3),
    (9, "Fa-3", 5),
    (17, "Fa-2", 4),
    (17, "Fa-3", 5),
    (25, "Fa-2", 4),
    (25, "Fa-3", 4),
    (31, "Fa-5", 3),  # f1041 — printed in the left hand, six ledger lines up
    (34, "Fa-2", 4),  # f1044 — printed in the right hand, six ledger lines down
    (34, "Mi-5", 5),  # f1044 — printed in the left hand
    (39, "Do-5", 13),
    (42, "Do-2", 4),
    (42, "Do-3", 4),
    (51, "Do-2", 4),
    (51, "Do-3", 4),
    (51, "Fa-3", 4),
    (51, "La#-3", 4),
    (51, "Re-4", 1),
    (59, "Do-2", 4),
    (59, "Do-3", 4),
    (59, "Fa-3", 5),
    (59, "La#-3", 4),
    (59, "Re-4", 4),
]


def _mr_blue_window() -> PianoMatrix:
    grid = np.zeros((KEY_COUNT, 66), dtype=np.int8)
    for column, name, frames in MR_BLUE_F1010:
        row = note_to_row(name)
        grid[row, column] = 1
        grid[row, column + 1 : column + frames] = -1
    return PianoMatrix.time_based(grid, frame_ms=40.0)


def test_the_passage_david_pointed_at() -> None:
    """The melody stays in the right hand and the bass stays in the left.

    Before this change the three onsets at columns 31 and 34 came out swapped:
    Fa-5 and Mi-5 on the bass staff under six and five ledger lines, Fa-2 on the
    treble staff under six of its own, with the hands crossing back one onset
    later. Nothing about the music asks for that.
    """
    result = infer_hands(_mr_blue_window(), DEFAULT_CONFIG)
    hand = {assignment.onset_id: assignment.hand for assignment in result.assignments}

    assert hand[f"c31:r{note_to_row('Fa-5')}"] == RIGHT
    assert hand[f"c34:r{note_to_row('Mi-5')}"] == RIGHT
    assert hand[f"c34:r{note_to_row('Fa-2')}"] == LEFT
    # ...and the octave either side of it is untouched.
    assert hand[f"c25:r{note_to_row('Fa-2')}"] == LEFT
    assert hand[f"c42:r{note_to_row('Do-2')}"] == LEFT
    assert hand[f"c39:r{note_to_row('Do-5')}"] == RIGHT


def test_nothing_in_the_passage_is_printed_far_across_its_staff() -> None:
    """The property the term is really about, stated as a property.

    Asserting hands note by note pins one passage; asserting that no onset lands
    deep across its own staff is the thing a reader would check, and it keeps
    holding if the melody is respelled or the window moves.

    Four lines, not the grace of two: the closing chord puts Fa-3 in the right
    hand at three, which is what a right hand playing an F major triad does and
    is charged 0.08 for the trouble. The claim is that nothing is *far* across,
    not that the middle register is fenced off.
    """
    result = infer_hands(_mr_blue_window(), DEFAULT_CONFIG)
    offenders = [
        (item.note, item.hand, ledger_lines(item.midi, item.hand))
        for item in result.assignments
        if direction_of(item.midi, item.hand) == "across" and ledger_lines(item.midi, item.hand) > 4
    ]
    assert offenders == []


def test_an_impossible_chord_does_not_rewrite_the_music_before_it() -> None:
    """The search bug, stated as the property it violated.

    Column 51 is a chord no partition can play: the right hand is still holding
    Do-5 when five more keys are struck, so every candidate breaks the hard span
    and the beam has to relax the group. Relaxing is fine — an unplayable
    transcription has to appear in the output rather than vanish. What is not
    fine is that the fallback used to keep whichever surviving state happened to
    come last instead of the cheapest one, which let a chord at the end of the
    window decide the hands of the melody eleven onsets earlier.

    So: cut the impossible chord off and split the shorter window. Every onset
    the two windows share must land in the same hand.
    """
    full = infer_hands(_mr_blue_window(), DEFAULT_CONFIG)
    assert full.diagnostics.infeasible_groups >= 1, "column 51 should still be unplayable"
    assert any("no hand partition" in text and "reachable" in text for text in full.warnings)

    trimmed_grid = _mr_blue_window().grid[:, :50]
    trimmed = infer_hands(PianoMatrix.time_based(trimmed_grid, frame_ms=40.0), DEFAULT_CONFIG)

    before = {item.onset_id: item.hand for item in full.assignments if item.column < 50}
    after = {item.onset_id: item.hand for item in trimmed.assignments}
    assert before == after


# ------------------------------------------------------ the term deciding on its own

#: *Mr Blue Sky*, the closing cadence: frames f7140–f7249 at 40 ms. Column 0 is
#: the Mib chord already sounding when the window opens, then the Mib triad is
#: struck three times, climbing an octave.
#:
#: What makes this the ledger term's own case: the triad at column 19 is compact
#: enough for one hand, and every *ergonomic* term prefers giving it to the right
#: hand entire. Doing that pins the right hand under its own sustains, so when the
#: same triad arrives an octave higher at column 44 the only hand left to take it
#: is the left — and the whole ascent prints on the bass staff under five, six and
#: seven ledger lines. The term's answer is to split the first triad instead:
#: Re#-4 and Sol-4 sit one and three lines above the bass staff, which is ordinary
#: writing, and the right hand stays free for the notes that need it.
#:
#: David reached the same conclusion by hand. The six onsets at f7184 and f7209 are
#: in this piece's saved ``handOverrides``, all of them moved to the right.
MR_BLUE_F7140 = [
    (0, "Re#-2", 19),
    (0, "Re#-3", 19),
    (0, "Re#-4", 19),
    (0, "Sol-4", 19),
    (0, "Do-5", 43),
    (19, "Re#-4", 91),
    (19, "Sol-4", 28),
    (19, "La#-4", 50),
    (44, "Re#-5", 25),  # f7184 — the reader moved these three to the right hand
    (44, "Sol-5", 25),
    (44, "La#-5", 66),
    (69, "La#-4", 41),  # f7209 — and these three
    (69, "Re#-5", 41),
    (69, "Sol-5", 41),
]


def _cadence_window() -> PianoMatrix:
    grid = np.zeros((KEY_COUNT, 110), dtype=np.int8)
    for column, name, frames in MR_BLUE_F7140:
        row = note_to_row(name)
        grid[row, column] = 1
        grid[row, column + 1 : column + frames] = -1
    return PianoMatrix.time_based(grid, frame_ms=40.0)


def _across_lines(result, column: int) -> list[int]:
    return [
        ledger_lines(item.midi, item.hand)
        for item in result.assignments
        if item.column == column and direction_of(item.midi, item.hand) == "across"
    ]


def test_without_the_term_the_closing_ascent_lands_on_the_bass_staff() -> None:
    """The ablation. With the second pass off, the search still writes David's picture.

    This is the honest half of the pair: the term is not decoration on a split that was
    already right. Turn the pass off and the last six onsets of the piece go to the left
    hand, three to seven ledger lines above its staff.

    Note *which* half of the design does the work here. The right hand is pinned under
    sustains it took at column 19, so at column 44 no single move can help — the fix is
    to have split that earlier chord, which only a re-solve over the window can find.
    An in-search charge cannot find it either once the gate is honest, because the gate
    correctly reports that the right hand is unavailable. What makes this case work is
    that a *sustained* blocker is still charged: the pin is self-inflicted, and saying so
    is what gives the window re-solve something to improve.
    """
    result = infer_hands(_cadence_window(), DEFAULT_CONFIG.with_refine(enabled=False))
    hand = {(item.column, item.note): item.hand for item in result.assignments}
    assert hand[(44, "Sol-5")] == LEFT
    assert hand[(69, "Sol-5")] == LEFT
    assert max(_across_lines(result, 44)) == 7


def test_the_term_keeps_the_ascent_on_its_own_staff() -> None:
    """And the same window with the second pass on, which is what ships.

    The first triad is split so the right hand stays free; nothing in the cadence then
    prints more than three ledger lines across its staff.
    """
    result = infer_hands(_cadence_window(), DEFAULT_CONFIG)
    hand = {(item.column, item.note): item.hand for item in result.assignments}
    for column in (44, 69):
        for name in ("Re#-5", "Sol-5"):
            assert hand[(column, name)] == RIGHT, f"c{column} {name}"
    assert hand[(44, "La#-5")] == RIGHT
    assert hand[(69, "La#-4")] == RIGHT
    # The price paid for it: two notes of the first triad sit just above the bass
    # staff, which is what a pianist writes.
    assert hand[(19, "Re#-4")] == LEFT
    assert hand[(19, "Sol-4")] == LEFT
    assert max(_across_lines(result, 19)) == 3
    assert _across_lines(result, 44) == []
    assert _across_lines(result, 69) == []
