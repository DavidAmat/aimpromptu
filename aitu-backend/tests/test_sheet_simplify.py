"""The Enhance with AI dialog of implementation 04, Phase 4: a stretch of one hand (the other hand fixed) and Simplify
(the rules of simplicity over the whole song, batch after batch, each batch seeing the changes made before it), with
stand-ins for the AI (no request)."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from aitu_backend.part_sheet import job
from aitu_backend.sheet.llm import frames as llm
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.sheet.sheet.common import spn
from aitu_backend.transcription import pipeline
import test_part_sheet
from test_part_sheet import finish, messages, sheet
from test_sheet_edits import walk
from test_sheet_reading import frame, notes_of, stored_sheet

client = test_part_sheet.client
part = test_part_sheet.part

HEAD = "F1 frames frameMs=40 quarterMs=500\nkey=0 clefs: R=treble L=bass\n"


def target_of(prompt: str):
    return f1.read(re.search(r"## Target.*?```\n(.*?)```", prompt, re.S).group(1))


# ------------------------------------------------------------------ a stretch of one hand


def test_a_stretch_of_one_hand_refuses_a_note_in_the_other_hand() -> None:
    target = f1.read(HEAD + "f0 R: C4:8\nf6 R: E4:8\n")
    fine = "```\n" + HEAD + "f0 R: C4:8 b1\nf6 R: E4:8 b1\n```"
    moved = "```\n" + HEAD + "f0 L: C4:8\nf6 R: E4:8\n```"
    assert llm.check_answer(fine, target, hand=1)[0] == []
    errs = llm.check_answer(moved, target, hand=1)[0]
    assert any("left hand is fixed" in e and "write only R:" in e for e in errs)
    # Both hands: a note may move.
    assert llm.check_answer(moved, target)[0] == []


def test_a_stretch_of_one_hand_shows_the_other_hand_apart_and_keeps_it_as_it_is(
    client: TestClient, part: str
) -> None:
    before = sheet(client, part)
    cols = sorted({frame(n["ref"]) for n in before["notes"]})
    a, b = cols[2], cols[20]
    log: list[str] = []

    def right_only(system: str, messages: list[dict]) -> str:
        text = messages[0]["content"]
        log.append(text)
        target = target_of(text)
        # The highest right-hand note of the stretch is taken off, as asked.
        top = max(target.notes, key=lambda n: (n.midi, n.frame))
        target.notes = [n for n in target.notes if n is not top]
        return "```\n" + f1.write(target, mode="frames") + "```\n"

    finish(
        job.start_stretch(
            part,
            start=a,
            end=b,
            instruction="leave out the highest note",
            staff=1,
            complete=lambda: right_only,
        )
    )
    prompt = log[0]
    target = prompt.split("## Target")[1].split("```")[1]
    assert "R:" in target and "L:" not in target
    assert "## The left hand in this stretch (fixed" in prompt
    assert "The user chose the right hand only" in prompt
    after = sheet(client, part)

    def left(body: dict) -> dict:
        return {
            n["ref"]: (n["figure"], n["beam"] is not None)
            for n in body["notes"]
            if n["hand"] == "left"
        }

    assert left(after) == left(before)
    gone = set(notes_of(before)) - set(notes_of(after))
    assert len(gone) == 1 and notes_of(before)[gone.pop()]["hand"] == "right"
    assert after["history"]["undo"] == "Enhance a stretch with AI"
    back = walk(client, part, "undo")
    assert set(notes_of(back)) == set(notes_of(before))


def test_splice_keeps_the_notes_beams_and_clefs_of_the_fixed_hand() -> None:
    current = f1.read(
        HEAD + "f0 L: C3:8 b1  R: C5:4\nf6 L: E3:8 b1\nf12 L: clef=treble G3:8 b2  R: E5:4\n"
        "f18 L: B3:8 b2\nf24 L: C3:4  R: G5:4\n"
    )
    answer = f1.read(HEAD.replace("L=bass", "L=treble") + "f6 L: E4:4\nf12 R: E5:8\n")
    out = llm.splice(current, answer, 6, 24, keep=2)
    left = [(n.frame, spn(n.step, n.alter, n.octave), n.beam) for n in out.notes if n.staff == 2]
    assert left == [(0, "C3", 1), (6, "E3", 1), (12, "G3", 2), (18, "B3", 2), (24, "C3", None)]
    assert [(n.frame, n.figure) for n in out.notes if n.staff == 1] == [(0, 4), (12, 8), (24, 4)]
    assert (12, 2, "G2") in out.clef_changes and not any(
        st == 2 and f == 6 for f, st, _ in out.clef_changes
    )


# ------------------------------------------------------------------ Simplify: the core


def test_the_simplify_checker_reads_the_change_lines_and_their_reasons() -> None:
    target = f1.read(
        HEAD
        + "f0 L: D2,D3:16\nf3 L: D2,D3:16\nf6 L: D3:16\nf9 L: D2,D3:16\nf12 L: G2,G3:16\nf15 L: Bb3,D4:4\n"
    )
    reply = (
        "Two places.\n```\n# add f6 D2: D3 alone in a run of D2+D3 octaves (simple.1)\n"
        "# leave out f12 G2 - the quick octave makes the hand jump\n```"
    )
    errs, changes = llm.check_simplify(reply, target)
    assert errs == []
    assert [(c.frame, c.midi, c.staff, c.added, c.why) for c in changes] == [
        (12, 43, 2, False, "the quick octave makes the hand jump"),
        (6, 38, 2, True, "D3 alone in a run of D2+D3 octaves (simple.1)"),
    ]
    assert changes[1].line() == "- f6 add D2 (L): D3 alone in a run of D2+D3 octaves (simple.1)"
    assert llm.check_simplify("```\n# no change\n```", target) == ([], [])
    assert "change lines" in llm.check_simplify("```\n" + HEAD + "f0 L: D2:16\n```", target)[0][0]
    wrong = "```\n# leave out f6 D2: x\n# add f7 D2: x\n# add f3 D3: x\n```"
    errs = llm.check_simplify(wrong, target)[0]
    assert any("f6 D2 is left out, but it is not a note" in e for e in errs)
    assert any("f7 D2 is added where the target has no note" in e for e in errs)
    assert any("f3 D3 is added, but the target already has it" in e for e in errs)
    # The limits of prompt 6: a column of a hand is never emptied; an added note completes a pattern.
    assert any(
        "no note of its column stays" in e
        for e in llm.check_simplify("```\n# leave out f6 D3: x\n```", target)[0]
    )
    assert any(
        "not the missing note of a pattern" in e
        for e in llm.check_simplify("```\n# add f6 F#2: x\n```", target)[0]
    )


def test_an_earlier_passage_like_the_batch_is_found_and_a_new_one_is_not() -> None:
    def run(keys: list[int], start: int) -> str:
        return "".join(f"f{start + 6 * i} L: {k}:8\n" for i, k in enumerate(keys))

    chorus = ["C3", "E3", "G3", "C4", "G3", "E3", "C3", "G2", "A2", "C3"]
    other = ["D3", "F3", "A3", "D4", "A3", "F3", "D3", "A2", "B2", "D3"]
    bridge = ["E3", "B3", "E4", "G#3", "B3", "E3", "F#3", "A3", "C#4", "E3"]
    sheet = f1.read(HEAD + run(chorus, 0) + run(other, 100) + run(chorus, 200) + run(bridge, 300))
    assert llm.like_before(sheet, 2, 200, 260, 190) == (0, 55)
    assert llm.like_before(sheet, 2, 300, 360, 290) is None
    assert llm.like_before(sheet, 1, 200, 260, 190) is None  # no right hand


def test_a_note_changes_its_name_only_as_the_earlier_passage_like_it_has_it() -> None:
    # 7 Years at 2:09.56: the left hand's A2+A3 where the chorus has A2+F3 every other time.
    def run(chords: list[str], start: int) -> str:
        return "".join(f"f{start + 6 * i} L: {c}:8\n" for i, c in enumerate(chords))

    chorus = ["A2,F3", "C3", "F3", "A2,F3", "C3", "F3", "A2,F3", "C3", "F3", "A2,F3"]
    again = chorus[:3] + ["A2,A3"] + chorus[4:]
    sheet = f1.read(HEAD + run(chorus, 0) + run(again, 200))
    target = f1.read(HEAD + run(again, 200))
    like = llm.like_before(sheet, 2, 200, 260, 190)
    assert like == (0, 55)
    aligned = llm.like_columns(sheet, 2, 200, 260, like)
    assert aligned[218] == [18, 36]  # the chorus repeats every three columns
    earlier = f1.read(HEAD + run(chorus, 0))
    reply = "```\n# leave out f218 A3: the chorus has A2+F3 here\n# add f218 F3: as in the earlier chorus\n```"

    errs, changes = llm.check_simplify(reply, target, like=earlier, aligned=aligned)
    assert errs == [] and [(c.frame, c.midi, c.added) for c in changes] == [
        (218, 57, False),
        (218, 53, True),
    ]
    # Without the earlier passage, or when it does not have the new note there, the name stays.
    assert any(
        "takes the place of a note of another name" in e
        for e in llm.check_simplify(reply, target)[0]
    )
    other = f1.read(HEAD + run(again[:6] + ["A2,A3"] + again[7:], 0))  # A3 at both places
    errs = llm.check_simplify(reply, target, like=other, aligned=aligned)[0]
    assert any("f218 F3 takes the place" in e for e in errs)


def stand_in(prompts: list[str], *, every: bool = True):
    """A ``complete`` for Simplify: the first single note of each target (or only of the first) gets the note an
    octave below it, as the missing note of an octave."""

    def complete(system: str, messages: list[dict]) -> str:
        text = messages[0]["content"]
        prompts.append(text)
        if not every and len(prompts) > 1:
            return "```\n# no change\n```"
        target = target_of(text)
        columns: dict[int, list] = {}
        for n in target.notes:
            columns.setdefault(n.frame, []).append(n)
        f, (n,) = next((f, ns) for f, ns in sorted(columns.items()) if len(ns) == 1)
        low = spn(n.step, n.alter, n.octave - 1)
        return f"```\n# add f{f} {low}: {spn(n.step, n.alter, n.octave)} alone, the octave below added\n```"

    return complete


def test_simplify_goes_batch_after_batch_and_each_batch_sees_the_changes_before_it() -> None:
    notes = test_part_sheet.song(90)
    sheet = llm.propose_frames(notes, quarter_ms=500.0).sheet
    prompts: list[str] = []
    out = llm.write_simplify(sheet, notes, stand_in(prompts), staff=2, sid="s1")
    assert len(prompts) == len(out.windows) >= 3
    assert all(w.status == "ok" for w in out.windows)
    first = out.windows[0]
    assert (first.end - first.start) * 40 > llm.WINDOW_MS[1]  # longer than a window of a whole run
    assert "R:" not in prompts[0].split("## Target")[1].split("```")[1]
    assert "## The simplifications so far" not in prompts[0]
    lines = prompts[2].split("## The simplifications so far")[1]
    assert out.changes[0].line() in lines and out.changes[1].line() in lines
    assert "## Decided context (the end of the previous batch, as simplified)" in prompts[1]
    # The note added in batch 1 is in the context batch 2 sees when it is near its end: the sheet is the simplified one.
    assert len(out.changes) == len(prompts) and all(c.added and c.staff == 2 for c in out.changes)
    for c in out.changes:
        added = [n for n in out.sheet.notes if (n.frame, n.midi, n.staff) == (c.frame, c.midi, 2)]
        assert len(added) == 1 and added[0].len_ms and added[0].figure
    assert {(n.frame, n.midi) for n in out.added} == {(c.frame, c.midi) for c in out.changes}
    right = [(n.frame, n.midi) for n in sheet.notes if n.staff == 1]
    assert [(n.frame, n.midi) for n in out.sheet.notes if n.staff == 1] == right


def test_the_song_like_passage_and_its_changes_reach_a_later_batch() -> None:
    notes = test_part_sheet.song(120)
    sheet = llm.propose_frames(notes, quarter_ms=500.0).sheet
    prompts: list[str] = []
    llm.write_simplify(sheet, notes, stand_in(prompts), staff=2, sid="s1")
    later = [p for p in prompts if "## An earlier passage like this one" in p]
    assert later, "the left hand repeats: a later batch sees an earlier one like it"
    assert "Its changes:" in later[0].split("## An earlier passage like this one")[1]


# ------------------------------------------------------------------ Simplify in the app


def test_simplify_left_stores_the_notes_as_one_step_and_keeps_the_right_hand(
    client: TestClient, part: str
) -> None:
    before = sheet(client, part)
    prompts: list[str] = []
    started = job.start_simplify(part, hand="left", complete=lambda: stand_in(prompts))
    finish(started)
    summary = started.summary
    assert (
        summary["simplify"] == "ok" and summary["added"] == len(prompts) and summary["leftOut"] == 0
    )
    phases = [m.get("phase") for m in messages(started)]
    assert (
        phases[0] == "simplify" and phases.count("batch") == len(prompts) and phases[-1] == "saved"
    )

    after = sheet(client, part)
    new = set(notes_of(after)) - set(notes_of(before))
    assert len(new) == len(prompts) and all(notes_of(after)[r]["hand"] == "left" for r in new)
    right = {r: n["figure"] for r, n in notes_of(before).items() if n["hand"] == "right"}
    assert {r: n["figure"] for r, n in notes_of(after).items() if n["hand"] == "right"} == right
    assert after["history"]["undo"] == "Simplify the left hand with AI"
    assert after["llm"]["enhanced"] is True
    kept = stored_sheet(part)
    assert kept.record.source == "mixed"
    assert kept.record.simplified[0][:3] == ["left", len(prompts), 0]
    lines = kept.record.simplified[0][5]
    assert len(lines) == len(prompts) and all(" add " in line and "alone" in line for line in lines)
    assert not frames.check(f1.read(kept.text))
    stored = pipeline.load_note_events(part)
    assert stored is not None and len(stored.events) == len(before["notes"]) + len(prompts)

    back = walk(client, part, "undo")
    assert set(notes_of(back)) == set(notes_of(before))
    again = walk(client, part, "redo")
    assert new <= set(notes_of(again))


def test_while_one_hand_is_simplified_the_segments_name_its_staff(
    client: TestClient, part: str
) -> None:
    prompts: list[str] = []
    seen: list[list] = []
    write = stand_in(prompts)

    def watched(system: str, messages: list[dict]) -> str:
        seen.append([(s["state"], s.get("staff")) for s in sheet(client, part)["segments"]])
        return write(system, messages)

    finish(job.start_simplify(part, hand="left", complete=lambda: watched))
    assert seen and all(staff == 2 for states in seen for _, staff in states)
    assert all(("working", 2) in states for states in seen)
    # After the run, and for a run of both hands, no staff: the page veils the whole line.
    assert all("staff" not in s for s in sheet(client, part)["segments"])


def test_simplify_that_changes_nothing_stores_only_the_run(client: TestClient, part: str) -> None:
    before = sheet(client, part)

    def nothing(system: str, messages: list[dict]) -> str:
        return "```\n# no change\n```"

    started = job.start_simplify(part, hand="both", complete=lambda: nothing)
    finish(started)
    assert started.summary["simplify"] == "none"
    after = sheet(client, part)
    assert set(notes_of(after)) == set(notes_of(before))
    assert after["history"]["undo"] is None and after["llm"]["enhanced"] is False
    assert stored_sheet(part).record.simplified[0][:3] == ["both", 0, 0]


def test_the_routes_of_the_dialog(client: TestClient, part: str, monkeypatch) -> None:
    costs = client.get(f"/sheet/{part}/llm/costs").json()
    assert set(costs) == {"all", "stretch", "simplify-left", "simplify-right", "simplify-both"}
    assert 0 < costs["simplify-left"]["requests"] < costs["all"]["requests"]
    monkeypatch.setattr(job, "available", lambda: True)
    assert client.post(f"/sheet/{part}/llm/simplify", json={"hand": "middle"}).status_code == 422
    started: list[str] = []
    monkeypatch.setattr(
        job,
        "start_simplify",
        lambda uuid, hand: started.append(hand) or type("J", (), {"id": "j", "status": "queued"})(),
    )
    answer = client.post(f"/sheet/{part}/llm/simplify", json={"hand": "right"})
    assert answer.status_code == 202 and started == ["right"]
