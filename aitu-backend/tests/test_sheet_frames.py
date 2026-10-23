"""The new sheet without compases (implementation 03, Phase 2): figures, spelling, the frames sheet, the algorithm.

The rules are the user's (plan section 3): plain figures from the note's own length and the reference figure, grace
notes by the two-step rule, the spelling rules 1 to 5, beam groups of at most 8 notes. The frames sheet keeps every
onset cell of each hand (the round trip with the matrix).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from aitu_backend.audio import store
from aitu_backend.pmn import HAND_LEFT, HAND_RIGHT, Notes
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.sheet.proposal import frames as algo
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet.sheet.data import Note, Sheet
from aitu_backend.sheet.sheet.figures import figure_of_ms, steps
from aitu_backend.sheet.sheet.spelling import check_rules, sign, spell
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent

R, L = HAND_RIGHT, HAND_LEFT


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_database_tree()
    return tmp_path


def notes_of(rows: list[tuple[int, float, float, int]]) -> Notes:
    """(midi, onset ms, length ms, hand) rows as notes."""
    midi, on, length, hand = (list(x) for x in zip(*rows))
    return Notes.build(key=np.array(midi) - 21, on_ms=on, len_ms=length, hand=hand)


def by_frame(sheet: Sheet, staff: int) -> dict[int, list[Note]]:
    out: dict[int, list[Note]] = {}
    for n in sheet.notes:
        if n.staff == staff:
            out.setdefault(n.frame, []).append(n)
    return dict(sorted(out.items()))


# ------------------------------------------------------------------ figures


def test_the_users_thresholds() -> None:
    # negra 200 ms: from the negra up the middle point, the corchea and shorter 70 % of the way
    assert figure_of_ms(300, 200) == 4 and figure_of_ms(310, 200) == 2
    assert figure_of_ms(90, 200) == 8 and figure_of_ms(75, 200) == 16
    assert figure_of_ms(10_000, 200) == 1 and figure_of_ms(1, 200) == 64
    assert figure_of_ms(160, 200) == 8  # the corchea-negra pair splits at 85 % of a negra
    assert steps(32, 8) == 2 and steps(4, 4) == 0


def test_a_figure_stops_at_the_next_onset_of_its_hand() -> None:
    # pedaled corcheas (negra 500 ms): each note sounds 1 s, the hand plays again after 250 ms
    rows = [(72 + i % 3, i * 250.0, 1000.0, R) for i in range(6)]
    sheet = algo.propose_frames(notes_of(rows), quarter_ms=500).sheet
    assert [n.figure for n in sheet.notes] == [8] * 5 + [2]  # the last note keeps its own length


def test_a_short_chord_keeps_its_figure_before_a_long_silence() -> None:
    rows = [(48, 0.0, 450.0, L), (52, 0.0, 450.0, L), (48, 3000.0, 450.0, L)]
    rows += [(76 + i % 2, i * 250.0, 240.0, R) for i in range(12)]
    sheet = algo.propose_frames(notes_of(rows), quarter_ms=500).sheet
    left = by_frame(sheet, 2)
    assert {n.figure for n in left[0]} == {4}  # a negra, not a redonda that fills the 3 s


def test_one_figure_per_chord_and_per_run_of_even_gaps() -> None:
    # a chord of three notes, two of them a corchea long: the chord is a corchea
    chord = [(60, 0.0, 240.0, R), (64, 0.0, 240.0, R), (67, 0.0, 60.0, R), (72, 2000.0, 400.0, R)]
    sheet = algo.propose_frames(notes_of(chord), quarter_ms=500).sheet
    assert {n.figure for n in by_frame(sheet, 1)[0]} == {8}
    # an even run whose lengths cross a threshold: one figure for the run
    run = [(72, i * 250.0, 240.0 if i % 3 else 150.0, R) for i in range(9)] + [
        (60, 9 * 250.0, 500.0, R)
    ]
    sheet = algo.propose_frames(notes_of(run), quarter_ms=500).sheet
    assert len({n.figure for n in sheet.notes if n.midi == 72}) == 1


def test_grace_notes_by_the_two_step_rule() -> None:
    q = 500.0
    # a fusa-length note 60 ms before a negra: a slashed grace note
    one = notes_of([(74, 1000.0, 50.0, R), (72, 1060.0, 500.0, R), (60, 3000.0, 500.0, R)])
    sheet = algo.propose_frames(one, quarter_ms=q).sheet
    grace = [n for n in sheet.notes if n.grace]
    assert [(n.midi, n.grace, n.figure) for n in grace] == [(74, "acc", 8)]
    # the same note 300 ms before: too slow to be a grace note
    slow = notes_of([(74, 1000.0, 50.0, R), (72, 1300.0, 500.0, R), (60, 3000.0, 500.0, R)])
    assert not any(n.grace for n in algo.propose_frames(slow, quarter_ms=q).sheet.notes)
    # an octave played unevenly: the same name, not a grace note
    octave = notes_of([(60, 1000.0, 50.0, R), (72, 1060.0, 500.0, R), (60, 3000.0, 500.0, R)])
    assert not any(n.grace for n in algo.propose_frames(octave, quarter_ms=q).sheet.notes)
    # four fast notes before the main note: a written run, not grace notes
    run = [(74 + i, 1000.0 + i * 50, 40.0, R) for i in range(4)] + [(72, 1200.0, 500.0, R)]
    assert not any(n.grace for n in algo.propose_frames(notes_of(run), quarter_ms=q).sheet.notes)


# ------------------------------------------------------------------ beams


def test_beam_groups_have_at_most_8_notes_and_cut_at_jumps_and_turns() -> None:
    q = 500.0
    scale = [(60 + 2 * i % 24, i * 250.0, 240.0, R) for i in range(12)]  # 12 rising corcheas
    sheet = algo.propose_frames(notes_of(scale), quarter_ms=q).sheet
    sizes = sorted(np.unique([n.beam for n in sheet.notes], return_counts=True)[1].tolist())
    assert sizes == [6, 6]  # 12 notes: two near-equal groups, not 8 + 4
    jump = [
        (60, 0.0, 240.0, R),
        (62, 250.0, 240.0, R),
        (76, 500.0, 240.0, R),
        (77, 750.0, 240.0, R),
    ]
    sheet = algo.propose_frames(notes_of(jump), quarter_ms=q).sheet
    assert len({n.beam for n in sheet.notes}) == 2  # cut at the jump of 14 semitones
    turn = [(60 + p, i * 250.0, 240.0, R) for i, p in enumerate([0, 2, 4, 5, 7, 5, 4, 2])]
    sheet = algo.propose_frames(notes_of(turn), quarter_ms=q).sheet
    groups = [
        [n.midi for n in sheet.notes if n.beam == b] for b in sorted({n.beam for n in sheet.notes})
    ]
    assert groups == [[60, 62, 64, 65, 67], [65, 64, 62]]  # the rise, then the fall


def test_no_beam_across_a_gap() -> None:
    rows = [
        (72, 0.0, 240.0, R),
        (74, 250.0, 240.0, R),
        (76, 1500.0, 240.0, R),
        (77, 1750.0, 240.0, R),
    ]
    sheet = algo.propose_frames(notes_of(rows), quarter_ms=500).sheet
    assert len({n.beam for n in sheet.notes}) == 2


# ------------------------------------------------------------------ spelling


def test_the_spelling_rules_give_one_name_for_every_armadura_and_key() -> None:
    assert check_rules() == []


def test_the_users_spelling_examples() -> None:
    # rule 4 in Mi mayor (4 sostenidos): the key Fa is Mi#, the key Do is Si#; Sol keeps a becuadro (no Fa##)
    assert spell(65, 4) == ("E", 1, 4) and spell(60, 4) == ("B", 1, 3)
    assert spell(67, 4) == ("G", 0, 4) and sign("G", 0, 4) == "n"
    # rule 3: no double sostenido (La## in Mi mayor is Si)
    assert spell(71, 4) == ("B", 0, 4) and sign("B", 0, 4) is None
    # rule 4 with bemoles: in Fa mayor the key Si is Dob; rule 5: the black keys follow the armadura
    assert spell(71, -1) == ("C", -1, 5)
    assert spell(70, 4) == ("A", 1, 4) and spell(61, -1) == ("D", -1, 4)
    # Do mayor: Do#, Mib, Fa#, Sol#, Sib
    assert [spell(m, 0)[:2] for m in (61, 63, 66, 68, 70)] == [
        ("C", 1),
        ("E", -1),
        ("F", 1),
        ("G", 1),
        ("B", -1),
    ]


def test_the_armadura_changes_for_a_long_passage() -> None:
    do = [60, 62, 64, 65, 67, 69, 71]
    mi = [64, 66, 68, 69, 71, 73, 75]
    rows = [(do[i % 7], i * 200.0, 180.0, R) for i in range(140)]
    rows += [(mi[i % 7], 28_000 + i * 200.0, 180.0, R) for i in range(140)]
    sheet = algo.propose_frames(notes_of(rows), quarter_ms=400).sheet
    assert sheet.key == 0 and [k for _, k in sheet.key_changes] == [4]
    assert frames.check(sheet) == []
    given = algo.propose_frames(notes_of(rows), quarter_ms=400, key=0).sheet
    assert given.key == 0 and given.key_changes == []


# ------------------------------------------------------------------ the frames sheet


def test_chords_are_grouped_on_raw_onsets_and_mapped_back_to_their_cells() -> None:
    # 30 ms apart (columns 0 and 1): one chord at column 0; 45 ms apart: two columns
    rows = [
        (60, 10.0, 400.0, L),
        (64, 40.0, 400.0, L),
        (72, 1000.0, 400.0, R),
        (76, 1045.0, 400.0, R),
    ]
    notes = notes_of(rows)
    sheet = frames.from_notes(notes)
    assert sorted((n.midi, n.frame) for n in sheet.notes) == [(60, 0), (64, 0), (72, 25), (76, 26)]
    got, lost = frames.cells_of(sheet, notes)
    assert lost == 0 and got == frames.matrix_cells(notes)
    assert (2, 64, 1) in got  # the note drawn at column 0 keeps its own cell, column 1


def test_the_frames_text_reads_back_with_every_tag() -> None:
    def n(staff, step, alter, octave, frame, figure, **kw) -> Note:
        return Note(
            time=None,
            staff=staff,
            step=step,
            alter=alter,
            octave=octave,
            frame=frame,
            figure=figure,
            **kw,
        )

    sheet = Sheet(
        notes=[
            n(1, "E", 1, 5, 10, 8, grace="acc"),
            n(1, "F", 1, 5, 12, 8, beam=1),
            n(1, "G", 1, 5, 18, 8, beam=1),
            n(2, "E", 0, 2, 12, 4),
            n(1, "A", 0, 6, 30, 4, ornaments=("trill",), ottava=1),
            n(1, "B", 0, 6, 32, 32, covered=True, ottava=1),
            n(1, "A", 0, 6, 34, 32, covered=True, ottava=1),
            n(2, "E", 0, 4, 40, 2),
            n(1, "B", -1, 4, 60, 4),
        ],
        clefs={1: "G2", 2: "F4"},
        clef_changes=[(40, 2, "G2")],
        key=4,
        key_changes=[(50, -1)],
        quarter_ms=480.0,
    ).sort()
    text = f1.write(sheet, mode="frames")
    assert text.splitlines()[0] == "F1 frames frameMs=40 quarterMs=480"
    assert "orn" in text and "tr" in text and "grace/" in text and "f50 key=1b" in text
    back = f1.read(text)
    assert f1.write(back, mode="frames") == text
    assert (
        back.quarter_ms == 480.0
        and back.key_changes == [(50, -1)]
        and back.clef_changes == [(40, 2, "G2")]
    )
    assert [(m.midi, m.frame, m.figure, m.covered, m.ottava) for m in back.notes] == [
        (m.midi, m.frame, m.figure, m.covered, m.ottava) for m in sheet.notes
    ]
    assert frames.check(back) == []


def test_check_lists_what_breaks_the_rules() -> None:
    def n(frame, midi_step, figure, **kw) -> Note:
        step, alter, octave = midi_step
        return Note(
            time=None,
            staff=kw.pop("staff", 1),
            step=step,
            alter=alter,
            octave=octave,
            frame=frame,
            figure=figure,
            **kw,
        )

    bad = Sheet(
        notes=[n(i, ("C", 0, 5), 8, beam=1) for i in range(9)]  # 9 notes in one beam group
        + [n(20, ("F", 0, 5), 4, dots=1)]  # a puntillo; and Fa natural must be Mi# in Mi mayor
        + [n(30, ("D", 0, 5), 8, grace="acc")]  # a grace note with nothing after it
        + [n(40, ("C", 0, 3), 4, staff=0)],  # no hand
        key=4,
    )
    problems = " | ".join(frames.check(bad))
    for part in ("at most 8", "puntillo", "is written E+1", "no note after it", "no hand"):
        assert part in problems


# ------------------------------------------------------------------ the algorithm on stored notes


def test_the_algorithm_writes_a_valid_sheet_that_keeps_every_onset() -> None:
    rng = np.random.default_rng(3)
    rows = []
    for i in range(160):
        t = 100 + i * 230.0 + rng.uniform(-15, 15)
        rows.append((int(rng.integers(64, 90)), t, float(rng.uniform(60, 900)), R))
        if i % 4 == 0:
            for k in (36, 43, 48):
                rows.append((k + int(rng.integers(0, 3)), t + rng.uniform(0, 30), 800.0, L))
    notes = notes_of(rows)
    prop = algo.propose_frames(notes)
    back = f1.read(f1.write(prop.sheet, mode="frames"))
    assert frames.check(back) == []
    got, lost = frames.cells_of(back, notes)
    assert lost == 0 and got == frames.matrix_cells(notes)


def test_starting_hands_keep_the_saved_hands_and_split_the_rest(data_dir: Path) -> None:
    uuid = store.create("Hands", AudioSource.UPLOAD, "wav").uuid
    events = []
    for i in range(24):
        hand = "right" if i < 12 else None
        events.append(
            NoteEvent(midi_note=72 + i % 5, start=i * 0.25, end=i * 0.25 + 0.2, hand=hand)
        )
        events.append(
            NoteEvent(
                midi_note=40 + i % 3,
                start=i * 0.25,
                end=i * 0.25 + 0.2,
                hand="left" if i < 12 else None,
            )
        )
    pipeline.save_note_events(uuid, events, 7.0)
    notes = pipeline.starting_hands(uuid)
    assert len(notes) == 48 and set(notes.hand.tolist()) == {R, L}
    saved = notes.on_ms < 3000
    assert (notes.hand[saved & (notes.key + 21 >= 72)] == R).all()
    assert (notes.hand[saved & (notes.key + 21 < 50)] == L).all()
    with pytest.raises(FileNotFoundError):
        pipeline.starting_hands("no-such-piece")
