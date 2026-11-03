"""The Enhance with AI dialog of implementation 04, Phase 4: a stretch of one hand (the other hand fixed), with
stand-ins for the AI (no request); the earlier passage like a batch (``like_before``, the level runs use it); the
dialog's costs. The Simplify run of that phase was removed in implementation 04-6."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from aitu_backend.part_sheet import job
from aitu_backend.sheet.llm import frames as llm
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.common import spn
import test_part_sheet
from test_part_sheet import finish, sheet
from test_sheet_edits import walk
from test_sheet_reading import frame, notes_of

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


# ------------------------------------------------------------------ the earlier passage like a batch


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


# ------------------------------------------------------------------ the dialog


def test_the_costs_of_the_dialog_and_no_simplify_route(client: TestClient, part: str) -> None:
    costs = client.get(f"/sheet/{part}/llm/costs").json()
    assert set(costs) == {"all", "stretch", "level-left", "level-right", "level-both", "models", "model"}
    assert client.post(f"/sheet/{part}/llm/simplify", json={"hand": "right"}).status_code in (404, 405)
