"""The clef rule of implementation 04-7: a hand changes to its other clef only for a whole passage.

The user's answers (2026-11-03, plan ``04-7-plan.md`` section 2): a passage is 5 columns of the hand or more
(``CLEF_MIN``); a shorter stretch of the other clef goes back to the hand's own clef, with an 8va line in the bass
clef (left hand) or an 8vb line in the treble clef (right hand) for the notes too far for ledger lines; on a stored
sheet (the AI's) only the short stretches go; a clef the user set by hand stays; "never 8va in the bass clef" (03)
ended.
"""

from __future__ import annotations

import numpy as np
import pytest

from aitu_backend.part_sheet import build, reading
from aitu_backend.pmn import HAND_LEFT, HAND_RIGHT, Notes
from aitu_backend.sheet.proposal import frames as algo
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet.sheet.data import Sheet, cut_clef_marks

R, L = HAND_RIGHT, HAND_LEFT
STEP_MS = 480.0  # one negra a column: 12 frames apart


def notes_of(rows: list[tuple[int, int]], *, right: int | None = 76) -> Notes:
    """Left-hand ``(column number, midi)`` rows, one negra each; with ``right``, a right-hand note on every column
    (the hands of the stretch do not mix)."""
    midi, on, length, hand = [], [], [], []
    for k, m in rows:
        midi.append(m), on.append(k * STEP_MS), length.append(STEP_MS * 0.9), hand.append(L)
    if right is not None:
        for k in sorted({k for k, _ in rows}):
            midi.append(right), on.append(k * STEP_MS), length.append(STEP_MS * 0.9), hand.append(R)
    return Notes.build(key=np.array(midi) - 21, on_ms=on, len_ms=length, hand=hand)


def drawn(notes: Notes) -> Sheet:
    return algo.propose_frames(notes, key=0, quarter_ms=STEP_MS).sheet


def left_columns(sheet: Sheet) -> list[tuple[int, str, list[tuple[int, int]]]]:
    """``(frame, clef, [(midi, ottava)])`` of every left-hand column."""
    cols: dict[int, list[tuple[int, int]]] = {}
    for n in sheet.notes:
        if n.staff == 2:
            cols.setdefault(n.frame, []).append((n.midi, n.ottava))
    frames_ = sorted(cols)
    return [(f, c, sorted(cols[f])) for f, c in zip(frames_, build._clef_track(sheet, 2, frames_))]


def low_with(high: dict[int, int], n: int = 16) -> list[tuple[int, int]]:
    """A left hand of ``n`` columns around C3, and ``high`` notes (column -> midi) in place of some."""
    return [(k, high.get(k, 48 + (k % 3) * 2)) for k in range(n)]


# ------------------------------------------------------------------ the rule's sheet (sheets never enhanced)


def test_a_lone_high_note_stays_in_the_bass_clef_under_8va() -> None:
    sheet = drawn(notes_of(low_with({6: 74})))  # D5: five ledger lines above the bass staff
    cols = left_columns(sheet)
    assert all(clef == "F4" for _, clef, _ in cols), "no treble clef for one high note"
    assert [c for c in sheet.clef_changes if c[1] == 2] == []
    assert cols[6][2] == [(74, 1)], "the high note is written D4 under an 8va line"
    assert all(o == 0 for _, _, ns in cols[:6] + cols[7:] for _, o in ns)
    assert frames.check(sheet) == []


def test_a_high_note_readable_with_ledger_lines_takes_no_line() -> None:
    sheet = drawn(notes_of(low_with({6: 67})))  # G4: three ledger lines
    assert all(clef == "F4" and all(o == 0 for _, o in ns) for _, clef, ns in left_columns(sheet))


def test_four_high_columns_stay_in_the_bass_clef_five_are_a_passage() -> None:
    four = drawn(notes_of(low_with({k: 74 + (k % 2) for k in range(5, 9)})))
    assert [c for c in four.clef_changes if c[1] == 2] == []
    assert all(o == 1 for f, _, ns in left_columns(four)[5:9] for _, o in ns)
    five = drawn(notes_of(low_with({k: 74 + (k % 2) for k in range(5, 10)})))
    cols = left_columns(five)
    assert [clef for _, clef, _ in cols[5:10]] == ["G2"] * 5, "a passage of 5 columns reads in the treble clef"
    assert cols[4][1] == "F4" and cols[10][1] == "F4"
    assert all(o == 0 for _, _, ns in cols for _, o in ns)


def test_the_8va_line_joins_the_columns_between_two_marked_ones() -> None:
    # D5, then C4 (written C3 under the line: inside the staff), then E5: one line over the three columns.
    sheet = drawn(notes_of(low_with({6: 74, 7: 60, 8: 76})))
    cols = left_columns(sheet)
    assert [ns for _, _, ns in cols[6:9]] == [[(74, 1)], [(60, 1)], [(76, 1)]]
    assert all(clef == "F4" for _, clef, _ in cols)


def test_a_chord_too_wide_for_the_line_keeps_its_treble_clef() -> None:
    # C2 and D5 in one column: in the bass clef D5 needs the 8va line, under it C2 is written C1 (far below).
    rows = low_with({}) + [(6, 36), (6, 74)]
    rows = [r for r in rows if r != (6, 48)]
    sheet = drawn(notes_of(rows))
    info = algo.short_clefs(sheet)
    cols = left_columns(sheet)
    assert cols[6][1] == "G2", "the stretch stays as it is: no clef reads it with or without the line"
    assert info["short clef stretches"] == 0 and info["short stretches kept"] >= 1


def test_the_right_hand_keeps_its_treble_clef_for_a_short_low_stretch() -> None:
    def right_hand(low: dict[int, int], n: int = 16) -> Notes:
        rows = [(k, low.get(k, 76 + (k % 3))) for k in range(n)]
        midi = [m for _, m in rows]
        on = [k * STEP_MS for k, _ in rows]
        return Notes.build(
            key=np.array(midi) - 21, on_ms=on, len_ms=[STEP_MS * 0.9] * n, hand=[R] * n
        )

    one = algo.propose_frames(right_hand({6: 48}), key=0, quarter_ms=STEP_MS).sheet  # C3: 4 ledger lines below
    right = sorted((n.frame, n.midi, n.ottava) for n in one.notes if n.staff == 1)
    assert [c for c in one.clef_changes if c[1] == 1] == [] and one.clefs[1] == "G2"
    assert right[6][1:] == (48, -1), "written C4 under an 8vb line"
    assert all(o == 0 for _, m, o in right if m != 48)
    passage = algo.propose_frames(
        right_hand({k: 43 + (k % 2) for k in range(5, 11)}), key=0, quarter_ms=STEP_MS
    ).sheet
    assert any(c[1] == 1 and c[2] == "F4" for c in passage.clef_changes), "a low passage reads in the bass clef"


# ------------------------------------------------------------------ a stored sheet (the AI's) laid again


def stored_with_treble(notes: Notes, stretches: list[tuple[int, int]]) -> Sheet:
    """The rule's sheet with treble-clef stretches of the left hand ``[a, b)`` (column numbers) as the AI wrote
    them, written and read back as F1."""
    sheet = drawn(notes)
    frames_ = sorted({n.frame for n in sheet.notes if n.staff == 2})
    for a, b in stretches:
        sheet.clef_changes.append((frames_[a], 2, "G2"))
        sheet.clef_changes.append((frames_[b], 2, "F4"))
    for n in sheet.notes:
        n.ottava = 0
    sheet.clef_changes.sort()
    return f1.read(f1.write(sheet, mode="frames"))


def without_clefs(text: str) -> list[str]:
    """The F1 text without the clefs and the octave lines: what must not change."""
    out = []
    for line in text.splitlines():
        words = [w for w in line.split() if not w.startswith("clef=") and w not in ("8va", "8vb")]
        if line.startswith("key=") or line.startswith("clefset"):
            continue
        out.append(" ".join(words))
    return out


def test_a_stored_sheet_loses_only_its_short_stretches() -> None:
    notes = notes_of(low_with({k: 69 for k in (3, 4)} | {k: 74 for k in range(8, 14)}))
    stored = stored_with_treble(notes, [(3, 5), (8, 14)])
    laid = build.reapply(stored, notes)
    cols = left_columns(laid)
    assert [clef for _, clef, _ in cols[3:5]] == ["F4", "F4"], "the AI's two treble columns go back to the bass clef"
    assert [clef for _, clef, _ in cols[8:14]] == ["G2"] * 6, "the AI's passage of six columns stays"
    assert cols[3][2] == [(69, 0)], "A4 reads with ledger lines (three), no line"
    assert without_clefs(f1.write(laid, mode="frames")) == without_clefs(f1.write(stored, mode="frames"))
    # Laid again, it stays the same: the step is settled.
    assert f1.write(build.reapply(laid, notes), mode="frames") == f1.write(laid, mode="frames")


def test_a_clef_the_user_set_by_hand_stays_and_its_mark_is_stored() -> None:
    notes = notes_of(low_with({}))
    sheet = drawn(notes)
    frames_ = sorted({n.frame for n in sheet.notes if n.staff == 2})
    label = reading.set_clef(sheet, frames_[6], frames_[8], 2, "treble")
    assert label == "Treble clef for a stretch of the left hand"
    assert sheet.user_clefs == [(frames_[6], frames_[8], 2, "G2")]
    text = f1.write(sheet, mode="frames")
    assert f"clefset L f{frames_[6]} f{frames_[8]} treble" in text
    back = f1.read(text)
    assert back.user_clefs == sheet.user_clefs
    laid = build.reapply(back, notes)
    cols = left_columns(laid)
    assert [clef for _, clef, _ in cols[6:8]] == ["G2", "G2"], "two columns, but the user's: they stay"
    assert laid.user_clefs == sheet.user_clefs
    # Clefs and 8va by the rule over the stretch: the mark goes, and the rule takes the stretch back to bass.
    reading.clef_rule(laid, frames_[5], frames_[9], [2])
    assert laid.user_clefs == []
    assert all(clef == "F4" for _, clef, _ in left_columns(build.reapply(laid, notes)))


def test_a_bass_clef_set_by_hand_takes_away_the_mark() -> None:
    sheet = drawn(notes_of(low_with({})))
    frames_ = sorted({n.frame for n in sheet.notes if n.staff == 2})
    reading.set_clef(sheet, frames_[4], frames_[10], 2, "treble")
    reading.set_clef(sheet, frames_[6], frames_[8], 2, "bass")
    assert sheet.user_clefs == [
        (frames_[4], frames_[6], 2, "G2"),
        (frames_[8], frames_[10], 2, "G2"),
    ]


def test_cut_clef_marks_keeps_the_outer_pieces() -> None:
    marks = [(10, 50, 2, "G2"), (60, 70, 2, "G2"), (10, 50, 1, "F4")]
    assert cut_clef_marks(marks, 20, 65, [2]) == [(10, 20, 2, "G2"), (10, 50, 1, "F4"), (65, 70, 2, "G2")]
    assert cut_clef_marks(marks, 0, 100, [1, 2]) == []


# ------------------------------------------------------------------ 8va in the bass clef (the 03 rule ended)


def test_8va_in_the_bass_clef_is_allowed_15ma_is_not() -> None:
    sheet = drawn(notes_of(low_with({})))
    frames_ = sorted({n.frame for n in sheet.notes if n.staff == 2})
    assert reading.set_ottava(sheet, frames_[2], frames_[4], 2, 1) == "8va over a stretch of the left hand"
    assert frames.check(sheet) == []
    with pytest.raises(reading.Refused, match="no 15ma"):
        reading.set_ottava(sheet, frames_[2], frames_[4], 2, 2)
    for n in sheet.notes:
        if n.staff == 2 and n.frame == frames_[2]:
            n.ottava = 2
    assert any("15ma in the bass clef" in p for p in frames.check(sheet))


def test_a_bass_clef_set_by_hand_keeps_the_8va() -> None:
    sheet = drawn(notes_of(low_with({})))
    frames_ = sorted({n.frame for n in sheet.notes if n.staff == 2})
    reading.set_clef(sheet, frames_[2], frames_[6], 2, "treble")
    reading.set_ottava(sheet, frames_[2], frames_[6], 2, 1)
    reading.set_clef(sheet, frames_[2], frames_[6], 2, "bass")
    assert all(n.ottava == 1 for n in sheet.notes if n.staff == 2 and frames_[2] <= n.frame < frames_[6])
