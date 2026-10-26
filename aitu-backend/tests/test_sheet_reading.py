"""The note and range tools of the new sheet (implementation 03, Phase 7): reading edits through the routes the page
calls (figures, fingers, beams, the grace note switch, ornaments, the armadura, clefs and 8va of a stretch), notes
taken off the page, the user's marks through a new AI run, and the AI writing a stretch again with the user's
words. Sonnet is a stand-in: no request leaves the machine.
"""

from __future__ import annotations

import re
import threading
import time

import pytest
from fastapi.testclient import TestClient

from aitu_backend.part_sheet import job, reading
from aitu_backend.part_sheet import store as sheet_store
from aitu_backend.sheet.llm import frames as llm
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet.sheet.data import Note, Sheet
from aitu_backend.transcription import pipeline
import test_part_sheet
from test_part_sheet import finish, sheet
from test_sheet_edits import enhance, move, walk

client = test_part_sheet.client
part = test_part_sheet.part


def edit(client: TestClient, uuid: str, status: int = 200, **body) -> dict:
    response = client.post(f"/sheet/{uuid}/reading", params={"width": 120}, json=body)
    assert response.status_code == status, response.text
    return response.json()


def notes_of(body: dict) -> dict[str, dict]:
    return {note["ref"]: note for note in body["notes"]}


def right_run(body: dict) -> list[str]:
    """The refs of the first right-hand run of eighths (A4 B4 C5 D5 E5 D5 C5 B4), one per column."""
    right = [n for n in body["notes"] if n["hand"] == "right" and n["figure"] == 8]
    return [n["ref"] for n in right[:8]]


def stored_sheet(uuid: str):
    kept = sheet_store.load(uuid)
    assert kept is not None
    return kept


def frame(ref: str) -> int:
    return int(ref.split(":")[0])


# ------------------------------------------------------------------ the note toolbox


def test_a_figure_set_by_hand_is_kept_by_the_rule_and_undone(client: TestClient, part: str) -> None:
    before = sheet(client, part)
    ref = right_run(before)[2]
    assert notes_of(before)[ref]["beam"] is not None

    after = edit(client, part, action="figure", notes=[ref], value=4)
    assert after["edited"] == "Write a chord as a negra"
    note = notes_of(after)[ref]
    # A negra has no beam: the rule cut the group around it.
    assert note["figure"] == 4 and note["fixed"] is True and note["beam"] is None
    # The algorithm's sheet is stored now, marked edited, and drawn as stored.
    kept = stored_sheet(part)
    assert kept.record.source == "algorithm" and kept.record.edited and not kept.record.enhanced
    assert not frames.check(f1.read(kept.text))
    assert after["llm"]["enhanced"] is False

    back = walk(client, part, "undo")
    assert back["walked"] == "Write a chord as a negra" and back["svg"] == before["svg"]
    again = walk(client, part, "redo")
    assert notes_of(again)[ref]["figure"] == 4

    rule = edit(client, part, action="figure", notes=[ref], value=None)
    assert rule["edited"] == "Give a chord back its figure"
    assert notes_of(rule)[ref]["figure"] == 8 and notes_of(rule)[ref]["fixed"] is False


def test_fingers_on_notes_and_on_one_chord_low_to_high(client: TestClient, part: str) -> None:
    body = sheet(client, part)
    ref = right_run(body)[0]
    one = edit(client, part, action="finger", notes=[ref], value=[3])
    assert notes_of(one)[ref]["finger"] == 3 and one["edited"] == "Finger 3 on a note"
    assert 'class="finger' in one["svg"] or "finger" in one["svg"]

    # The right hand's held chord (E4 A4) at the start: two numbers, low to high.
    chord = [n["ref"] for n in body["notes"] if n["hand"] == "right" and frame(n["ref"]) == 0]
    assert len(chord) == 2
    two = edit(client, part, action="finger", notes=chord, value=[4, 1])
    low, high = sorted(chord, key=lambda r: int(r.split(":")[1]))
    assert notes_of(two)[low]["finger"] == 1 and notes_of(two)[high]["finger"] == 4
    assert "fg1" in stored_sheet(part).text

    off = edit(client, part, action="finger", notes=chord, value=[])
    assert notes_of(off)[low]["finger"] is None and off["edited"] == "Remove the fingers"


def test_beams_are_cut_joined_and_taken_away(client: TestClient, part: str) -> None:
    body = sheet(client, part)
    run = right_run(body)
    group = notes_of(body)[run[0]]["beam"]
    members = [r for r in run if notes_of(body)[r]["beam"] == group]
    assert len(members) >= 3

    cut = edit(client, part, action="beam-break", notes=[members[2]])
    assert cut["edited"] == "Start a new beam here"
    beams = [notes_of(cut)[r]["beam"] for r in members]
    assert (
        beams[0] == beams[1] and beams[2] != beams[1] and beams[2] is not None or len(members) == 3
    )

    joined = edit(client, part, action="beam-break", notes=[members[2]])
    assert joined["edited"] == "Join the beam again"
    assert len({notes_of(joined)[r]["beam"] for r in members}) == 1

    # Two whole notes of the group alone: join makes them one group; pressed again, the beam goes away.
    pair = edit(client, part, action="beam-join", notes=members[:2])
    assert pair["edited"] == "Beam 2 notes as one group"
    assert notes_of(pair)[members[0]]["beam"] == notes_of(pair)[members[1]]["beam"]
    gone = edit(client, part, action="beam-join", notes=members[:2])
    assert gone["edited"] == "Remove the beam"
    assert notes_of(gone)[members[0]]["beam"] is None

    # A negra has no beam; notes of both hands are not one group.
    negra = [n["ref"] for n in body["notes"] if n["hand"] == "right" and n["figure"] <= 4][:1]
    refused = edit(client, part, 400, action="beam-join", notes=negra + members[:1])
    assert "one another" in refused["detail"] or "corchea" in refused["detail"]
    left = next(n["ref"] for n in body["notes"] if n["hand"] == "left")
    assert "one hand" in edit(client, part, 400, action="beam-join", notes=[left, run[0]])["detail"]


def test_the_grace_note_switch_overrides_the_rule(client: TestClient, part: str) -> None:
    body = sheet(client, part)
    ref = right_run(body)[3]
    on = edit(client, part, action="grace", notes=[ref], value="on")
    assert notes_of(on)[ref]["grace"] is True and notes_of(on)[ref]["graceRule"] == "on"
    off = edit(client, part, action="grace", notes=[ref], value="off")
    assert notes_of(off)[ref]["grace"] is False
    rule = edit(client, part, action="grace", notes=[ref], value=None)
    assert (
        notes_of(rule)[ref]["graceRule"] is None and rule["edited"] == "Grace note back to the rule"
    )

    # The last note of a hand has no note to lean on.
    last = max((n for n in body["notes"] if n["hand"] == "right"), key=lambda n: frame(n["ref"]))
    assert (
        "leans on"
        in edit(client, part, 400, action="grace", notes=[last["ref"]], value="on")["detail"]
    )


def test_a_trill_hides_the_onsets_inside_it_and_prints_them_again(
    client: TestClient, part: str
) -> None:
    body = sheet(client, part)
    run = right_run(body)[:4]
    trill = edit(client, part, action="ornament", notes=run, value="trill")
    assert trill["edited"] == "Write 4 notes as a trill"
    drawn = notes_of(trill)
    assert drawn[run[0]]["ornaments"] == ["trill"] and not any(r in drawn for r in run[1:])
    assert "orn" in stored_sheet(part).text
    # The onsets are still in the notes (the matrix): the round trip holds.
    kept = f1.read(stored_sheet(part).text)
    _, unmatched = frames.cells_of(kept, pipeline.starting_hands(part))
    assert unmatched == 0

    plain = edit(client, part, action="ornament", notes=[run[0]], value="trill")
    assert plain["edited"] == "Print the trill as notes"
    assert all(r in notes_of(plain) for r in run)

    chord = [n["ref"] for n in body["notes"] if n["hand"] == "right" and frame(n["ref"]) == 0]
    rolled = edit(client, part, action="ornament", notes=chord[:1], value="arpeggio")
    assert all(notes_of(rolled)[r]["ornaments"] == ["arpeggio"] for r in chord)
    flat = edit(client, part, action="ornament", notes=chord[:1], value="arpeggio")
    assert flat["edited"] == "Remove a rolled chord"


def test_notes_taken_off_the_page_leave_the_notes_and_come_back(
    client: TestClient, part: str
) -> None:
    before = sheet(client, part)
    ref = right_run(before)[1]
    response = client.post(f"/sheet/{part}/remove", params={"width": 120}, json={"notes": [ref]})
    assert response.status_code == 200, response.text
    after = response.json()
    assert after["moved"] == 1 and ref not in notes_of(after)
    assert after["history"]["undo"] == "Take a note off the page"
    stored = pipeline.load_note_events(part)
    assert stored is not None and sum(e.removed for e in stored.events) == 1

    back = walk(client, part, "undo")
    assert ref in notes_of(back) and back["svg"] == before["svg"]
    stored = pipeline.load_note_events(part)
    assert stored is not None and not any(e.removed for e in stored.events)


# ------------------------------------------------------------------ the range toolbox


def test_the_armadura_of_a_stretch_and_the_one_with_fewest_signs(
    client: TestClient, part: str
) -> None:
    body = sheet(client, part)
    piece = body["reading"]["key"]
    cols = sorted({frame(n["ref"]) for n in body["notes"]})
    a, b = cols[10], cols[30]
    after = edit(client, part, action="key", start=a, end=b, value=piece + 2)
    assert [a, piece + 2] in after["reading"]["keyChanges"]
    assert [b, piece] in after["reading"]["keyChanges"]
    hint = client.get(f"/sheet/{part}/stretch", params={"start": a, "end": b}).json()
    assert hint["key"] == piece + 2 and hint["fewestSigns"] <= hint["signs"]

    back = edit(client, part, action="key", start=a, end=b, value=None)
    assert back["reading"]["keyChanges"] == body["reading"]["keyChanges"]


def test_clefs_and_octave_lines_of_one_hand_over_a_stretch(client: TestClient, part: str) -> None:
    body = sheet(client, part)
    cols = sorted({frame(n["ref"]) for n in body["notes"]})
    a, b = cols[4], cols[20]
    treble = edit(client, part, action="clef", start=a, end=b, staff="left", value="treble")
    assert [a, "left", "treble"] in treble["reading"]["clefChanges"]
    assert [b, "left", "bass"] in treble["reading"]["clefChanges"]
    assert (
        "right or the left"
        in edit(client, part, 400, action="clef", start=a, end=b, value="bass")["detail"]
    )

    rule = edit(client, part, action="clef-rule", start=a, end=b, staff="left")
    assert rule["reading"]["clefChanges"] == body["reading"]["clefChanges"]

    up = edit(client, part, action="ottava", start=a, end=b, staff="right", value=1)
    inside = [n for n in up["notes"] if n["hand"] == "right" and a <= frame(n["ref"]) < b]
    assert inside and all(n["ottava"] == 1 for n in inside)
    assert (
        "bass clef"
        in edit(client, part, 400, action="ottava", start=a, end=b, staff="left", value=1)["detail"]
    )
    down = edit(client, part, action="ottava", start=a, end=b, staff="right", value=0)
    assert all(
        n["ottava"] == 0 for n in down["notes"] if n["hand"] == "right" and a <= frame(n["ref"]) < b
    )


def test_a_reading_edit_stays_through_a_hand_move(client: TestClient, part: str) -> None:
    body = sheet(client, part)
    ref = right_run(body)[2]
    edit(client, part, action="figure", notes=[ref], value=2)
    other = right_run(body)[6]
    moved = move(client, part, [other], "left")
    # The edited algorithm sheet is laid again on the new hands, not computed again.
    assert notes_of(moved)[ref]["figure"] == 2 and notes_of(moved)[other]["hand"] == "left"
    assert moved["stale"] is False


# ------------------------------------------------------------------ the AI


def test_a_new_ai_run_keeps_the_fingers_and_figures_and_writes_its_own_kinds_again(
    client: TestClient, part: str
) -> None:
    body = sheet(client, part)
    run = right_run(body)
    edit(client, part, action="finger", notes=[run[0]], value=[2])
    edit(client, part, action="figure", notes=[run[2]], value=4)
    edit(client, part, action="beam-break", notes=[run[1]])
    enhance(part)
    after = sheet(client, part)
    assert after["llm"]["enhanced"] is True
    assert notes_of(after)[run[0]]["finger"] == 2
    assert notes_of(after)[run[2]]["figure"] == 4 and notes_of(after)[run[2]]["fixed"] is True
    # The AI (the stand-in answers the algorithm's groups) wrote the beam the user cut again.
    assert notes_of(after)[run[0]]["beam"] == notes_of(after)[run[1]]["beam"]


def stretch_stand_in(log: list):
    """A ``complete`` that answers a stretch with every note of the target in the right hand."""

    def complete(system: str, messages: list[dict]) -> str:
        text = messages[0]["content"]
        log.append(text)
        block = re.search(r"## Target.*?```\n(.*?)```", text, re.S).group(1)
        target = f1.read(block)
        for n in target.notes:
            n.staff = 1
        return "```\n" + f1.write(target, mode="frames") + "```\n"

    return complete


def test_the_ai_writes_a_stretch_again_with_the_users_words_as_one_step(
    client: TestClient, part: str
) -> None:
    before = sheet(client, part)
    cols = sorted({frame(n["ref"]) for n in before["notes"]})
    a, b = cols[2], cols[8]
    log: list[str] = []
    finish(
        job.start_stretch(
            part,
            start=a,
            end=b,
            instruction="all these notes are in the right hand",
            staff=2,
            complete=lambda: stretch_stand_in(log),
        )
    )
    assert len(log) == 1
    prompt = log[0]
    assert "A stretch of song" in prompt and "all these notes are in the right hand" in prompt
    assert "now in the left hand (L:)" in prompt and "fg" not in prompt.split("## Target")[1]

    after = sheet(client, part)
    inside = [n for n in after["notes"] if a <= frame(n["ref"]) < b]
    outside = {n["ref"]: n["hand"] for n in after["notes"] if not a <= frame(n["ref"]) < b}
    assert inside and all(n["hand"] == "right" for n in inside)
    assert outside == {n["ref"]: n["hand"] for n in before["notes"] if not a <= frame(n["ref"]) < b}
    assert after["history"]["undo"] == "Enhance a stretch with AI"
    assert after["llm"]["enhanced"] is True
    assert {"start": a, "end": b, "state": "llm"} in after["segments"]
    kept = stored_sheet(part)
    assert kept.record.source == "mixed" and kept.record.stretches[0][:3] == [
        a,
        b,
        "all these notes are in the right hand",
    ]
    assert not frames.check(f1.read(kept.text))

    back = walk(client, part, "undo")
    assert {n["ref"]: n["hand"] for n in back["notes"]} == {
        n["ref"]: n["hand"] for n in before["notes"]
    }


def test_a_stretch_the_ai_cannot_write_leaves_the_sheet_as_it_was(
    client: TestClient, part: str
) -> None:
    before = sheet(client, part)
    cols = sorted({frame(n["ref"]) for n in before["notes"]})

    def broken(system: str, messages: list[dict]) -> str:
        return "```\nF1 frames frameMs=40\nkey=0 clefs: R=treble L=bass\n```"

    started = job.start_stretch(part, start=cols[2], end=cols[8], complete=lambda: broken)
    finish(started)
    assert started.summary["stretch"] == "failed"
    after = sheet(client, part)
    assert after["svg"] == before["svg"] and after["history"]["undo"] is None
    assert sheet_store.load(part) is None


def test_no_edit_and_no_second_stretch_while_the_ai_writes(client: TestClient, part: str) -> None:
    gate = threading.Event()

    def slow(system: str, messages: list[dict]) -> str:
        gate.wait(10)
        raise RuntimeError("stopped by the test")

    body = sheet(client, part)
    cols = sorted({frame(n["ref"]) for n in body["notes"]})
    started = job.start_stretch(part, start=cols[2], end=cols[8], complete=lambda: slow)
    try:
        # The job registers the stretch as it starts (the page reads the sheet again at its first message).
        while not any(
            message.get("phase") == "stretch" for message in test_part_sheet.messages(started)
        ):
            time.sleep(0.02)
        working = sheet(client, part)
        assert working["llm"]["state"] == "running" and working["editable"] is False
        assert {"start": cols[2], "end": cols[8], "state": "working"} in working["segments"]
        assert edit(client, part, 409, action="finger", notes=[body["notes"][0]["ref"]], value=[1])
        again = client.post(f"/sheet/{part}/llm/stretch", json={"start": cols[2], "end": cols[8]})
        assert again.status_code == 409
    finally:
        gate.set()
        finish(started)
    assert started.summary["stretch"] == "failed"


def test_the_stretch_request_names_what_the_user_picked() -> None:
    words = llm.stretch_request("share them  between the hands", picked=["f10 C4", "f12 E4"])
    assert "f10 C4, f12 E4" in words and "> share them between the hands" in words
    assert "both hands" in llm.stretch_request("")
    assert "no words" in llm.stretch_request("")


def test_every_action_of_the_page_is_planned() -> None:
    # The sheet's own actions (Phase 8: the sheet toolbox) name no notes and no stretch.
    whole = {"titles", "piece-key", "line-space", "lyrics", "figures"}
    for action in reading.ACTIONS:
        if action in whole:
            continue
        with pytest.raises(reading.Refused):
            reading.plan(action)
    for action, value in (
        ("titles", {"title": "T"}),
        ("piece-key", 2),
        ("line-space", None),
        ("lyrics", {"pieces": []}),
        ("figures", 1),
    ):
        change, holds = reading.plan(action, value=value)
        assert callable(change) and holds is None


def test_chord_fingers_run_from_the_thumb_in_the_right_hand_and_from_the_little_finger_in_the_left() -> (
    None
):
    def chord(staff: int) -> Sheet:
        notes = [
            Note(time=None, staff=staff, step=step, alter=0, octave=octave, figure=4, frame=10)
            for step, octave in (("C", 3), ("E", 3), ("G", 3))
        ]
        return Sheet(notes=notes, clefs={1: "G2", 2: "F4"}, key=0)

    refs = ["10:48", "10:52", "10:55"]
    for staff, low_to_high in ((1, [1, 3, 5]), (2, [5, 3, 1])):
        sheet = chord(staff)
        assert reading.set_fingers(sheet, refs, [5, 1, 3]).startswith("Fingers")
        assert [n.finger for n in sorted(sheet.notes, key=lambda n: n.midi)] == low_to_high


def test_a_stretch_with_words_may_leave_notes_out_and_undo_brings_them_back(
    client: TestClient, part: str
) -> None:
    before = sheet(client, part)
    chords = {}
    for n in before["notes"]:
        chords.setdefault((n["hand"], frame(n["ref"])), []).append(n["ref"])
    held = sorted(f for (hand, f), refs in chords.items() if hand == "right" and len(refs) == 2)
    a = held[0]
    b = min(f for f in sorted({frame(n["ref"]) for n in before["notes"]}) if f > a + 40)
    lows = [
        min(chords[("right", f)], key=lambda r: int(r.split(":")[1])) for f in held if a <= f < b
    ]
    log: list[str] = []

    def single_notes(system: str, messages: list[dict]) -> str:
        text = messages[0]["content"]
        log.append(text)
        block = re.search(r"## Target.*?```\n(.*?)```", text, re.S).group(1)
        target = f1.read(block)
        drop = {tuple(int(x) for x in r.split(":")) for r in lows}
        target.notes = [n for n in target.notes if (n.frame, n.midi) not in drop]
        return "```\n" + f1.write(target, mode="frames") + "```\n"

    finish(
        job.start_stretch(
            part,
            start=a,
            end=b,
            instruction="make the chords single notes",
            complete=lambda: single_notes,
        )
    )
    assert "utmost importance" in log[0] and "take notes off the sheet" in log[0]
    assert " b1" in log[0].split("## Target")[1].split("```")[1]  # the target shows its beam groups
    after = sheet(client, part)
    assert lows and not any(r in notes_of(after) for r in lows)
    stored = pipeline.load_note_events(part)
    assert stored is not None and sum(e.removed for e in stored.events) == len(lows)
    assert after["history"]["undo"] == "Enhance a stretch with AI"

    back = walk(client, part, "undo")
    assert all(r in notes_of(back) for r in lows)
    stored = pipeline.load_note_events(part)
    assert stored is not None and not any(e.removed for e in stored.events)


def test_a_window_must_keep_every_note_and_a_stretch_with_words_may_leave_some_out() -> None:
    target = f1.read(
        "F1 frames frameMs=40\nkey=0 clefs: R=treble L=bass\nf0 R: C4,E4:8\nf6 R: G4:8\n"
    )
    answer = "```\nF1 frames frameMs=40\nkey=0 clefs: R=treble L=bass\nf0 R: E4:8\nf6 R: G4:8\n```"
    assert any("missing" in e for e in llm.check_answer(answer, target)[0])
    assert llm.check_answer(answer, target, drop=True)[0] == []
    empty = "```\nF1 frames frameMs=40\nkey=0 clefs: R=treble L=bass\n```"
    assert llm.check_answer(empty, target, drop=True)[0]


def test_a_stretch_with_words_may_change_pitches_add_notes_and_set_figures(
    client: TestClient, part: str
) -> None:
    before = sheet(client, part)
    held = sorted(
        {frame(n["ref"]) for n in before["notes"] if n["hand"] == "right" and n["figure"] <= 4}
    )
    a = held[0]
    b = min(f for f in sorted({frame(n["ref"]) for n in before["notes"]}) if f > a + 40)
    low = min(
        (n for n in before["notes"] if n["hand"] == "right" and frame(n["ref"]) == a),
        key=lambda n: int(n["ref"].split(":")[1]),
    )["ref"]
    added = (a + 3, 72)

    def simpler(system: str, messages: list[dict]) -> str:
        block = re.search(r"## Target.*?```\n(.*?)```", messages[0]["content"], re.S).group(1)
        target = f1.read(block)
        target.notes = [n for n in target.notes if f"{n.frame}:{n.midi}" != low]
        for n in target.notes:
            if n.frame == a and n.staff == 1:
                n.figure = 4  # a negra (the target shows a redonda), whatever its length says
        target.notes.append(
            Note(time=None, staff=1, step="C", alter=0, octave=5, figure=4, frame=added[0])
        )
        return "```\n" + f1.write(target.sort(), mode="frames") + "```\n"

    finish(
        job.start_stretch(
            part, start=a, end=b, instruction="simpler, please", complete=lambda: simpler
        )
    )
    after = sheet(client, part)
    drawn = notes_of(after)
    assert low not in drawn and f"{added[0]}:{added[1]}" in drawn
    assert drawn[f"{added[0]}:{added[1]}"]["figure"] == 4
    kept = [n for n in after["notes"] if n["hand"] == "right" and frame(n["ref"]) == a]
    assert kept and all(n["figure"] == 4 and n["fixed"] and not n["grace"] for n in kept)
    stored = pipeline.load_note_events(part)
    assert stored is not None
    new = [
        e
        for e in stored.events
        if e.midi_note == 72 and not e.removed and a * 0.04 <= e.start < b * 0.04
    ]
    assert len(new) == 1 and abs(new[0].start - added[0] * 0.04) < 0.041

    back = walk(client, part, "undo")
    assert low in notes_of(back) and f"{added[0]}:{added[1]}" not in notes_of(back)
    assert {n["ref"]: n["figure"] for n in back["notes"]} == {
        n["ref"]: n["figure"] for n in before["notes"]
    }
    again = walk(client, part, "redo")
    assert f"{added[0]}:{added[1]}" in notes_of(again)


def test_a_stretch_answer_may_add_notes_only_inside_the_stretch() -> None:
    target = f1.read(
        "F1 frames frameMs=40\nkey=0 clefs: R=treble L=bass\nf10 R: C4:8\nf16 R: G4:8\n"
    )
    head = "```\nF1 frames frameMs=40\nkey=0 clefs: R=treble L=bass\n"
    inside = head + "f10 R: C4:8\nf13 R: E4:8\nf16 R: G4:8\n```"
    outside = head + "f10 R: C4:8\nf16 R: G4:8\nf30 R: E4:8\n```"
    assert llm.check_answer(inside, target, drop=True, free=(10, 20))[0] == []
    assert any(
        "outside the stretch" in e
        for e in llm.check_answer(outside, target, drop=True, free=(10, 20))[0]
    )
    assert any("not in the target" in e for e in llm.check_answer(inside, target)[0])
