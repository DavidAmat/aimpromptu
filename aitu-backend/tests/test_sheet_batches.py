"""The model and the batches of Enhance with AI (the user, 2026-10-30): the batches of about the same time that the
dialog shows on the sheet (``frames.split_windows``, ``job.batch_plan``, ``GET /sheet/{uuid}/llm/batches``), the model
chosen (``job.MODELS``), and a stretch written in several batches. The AI is a stand-in: no request leaves the machine.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aitu_backend.part_sheet import job
from aitu_backend.sheet.llm import frames as llm
from aitu_backend.sheet.sheet.data import Note, Sheet
import test_part_sheet
from test_part_sheet import finish, sheet

client = test_part_sheet.client
part = test_part_sheet.part


def notes_every(step: int, count: int, *, staff: int = 1, beams: dict[int, int] | None = None) -> list[Note]:
    return [
        Note(time=None, staff=staff, step="CDEFG"[k % 5], alter=0, octave=4, figure=8, frame=f, beam=(beams or {}).get(f))
        for k, f in enumerate(range(0, step * count, step))
    ]


# ------------------------------------------------------------------ the cut


def test_the_batches_cover_the_stretch_with_about_the_same_time() -> None:
    s = Sheet(notes=notes_every(10, 100), clefs={1: "G", 2: "F"})
    wins = llm.split_windows(s, 4)
    assert len(wins) == 4 and wins[0][0] == 0 and wins[-1][1] == 991
    assert all(a < b for a, b in wins) and all(w[1] == n[0] for w, n in zip(wins, wins[1:]))
    sizes = [b - a for a, b in wins]
    assert max(sizes) - min(sizes) <= 0.4 * (991 / 4)
    # A range: its own frames, at the first and the last batch.
    ranged = llm.split_windows(s, 3, start=105, end=705)
    assert ranged[0][0] == 105 and ranged[-1][1] == 705 and len(ranged) == 3
    # Never more batches than columns; none without notes of the hand.
    assert len(llm.split_windows(s, 500)) == 100
    assert llm.split_windows(s, 3, staffs=(2,)) == []


def test_a_cut_does_not_split_a_beam_group_when_it_can_move() -> None:
    # A beam group over the frames 240-270 lies across the equal cut at 250 (two batches over 0-500).
    s = Sheet(notes=notes_every(10, 50, beams={240: 1, 250: 1, 260: 1, 270: 1}), clefs={1: "G", 2: "F"})
    (_, cut), _ = llm.split_windows(s, 2)
    assert not 240 < cut <= 270


def test_the_cut_follows_the_hands_rewritten() -> None:
    right = notes_every(10, 60)
    left = notes_every(10, 20, staff=2)  # the left hand plays only the first 200 frames
    s = Sheet(notes=right + left, clefs={1: "G", 2: "F"})
    assert llm.split_windows(s, 2, staffs=(2,))[-1][1] == 191
    assert llm.split_windows(s, 2)[-1][1] == 591


# ------------------------------------------------------------------ the plan the dialog shows


def test_the_route_answers_the_batches_and_the_cost_of_each_model(client: TestClient, part: str) -> None:
    sheet(client, part)
    plain = client.get(f"/sheet/{part}/llm/batches", params={"run": "all"}).json()
    assert plain["model"] == "gpt-6.1-terra" and plain["count"] == plain["default"] >= 1
    assert plain["min"] <= plain["count"] <= plain["max"]
    more = client.get(f"/sheet/{part}/llm/batches", params={"run": "all", "batches": plain["count"] + 1}).json()
    assert more["count"] == plain["count"] + 1 and len(more["windows"]) == more["count"]
    sonnet = client.get(
        f"/sheet/{part}/llm/batches", params={"run": "all", "model": "claude-sonnet-5-5"}
    ).json()
    assert sonnet["usd"] > plain["usd"] and sonnet["minutes"] >= plain["minutes"]
    cols = sorted({int(n["ref"].split(":")[0]) for n in sheet(client, part)["notes"]})
    stretch = client.get(
        f"/sheet/{part}/llm/batches",
        params={"run": "stretch", "start": cols[2], "end": cols[-2], "batches": 2},
    ).json()
    assert stretch["default"] == 1 and stretch["windows"][0][0] == cols[2] and stretch["windows"][-1][1] == cols[-2]
    assert client.get(f"/sheet/{part}/llm/batches", params={"run": "stretch"}).status_code == 400
    assert client.get(f"/sheet/{part}/llm/batches", params={"run": "all", "model": "gpt-9"}).status_code == 422


def test_the_routes_pass_the_model_and_the_batches(
    client: TestClient, part: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    sheet(client, part)
    calls: list[dict] = []

    def started(uuid: str, **kwargs: object):
        calls.append(kwargs)
        return type("J", (), {"id": "j", "status": "queued"})()

    monkeypatch.setattr(job, "start", started)
    monkeypatch.setattr(job, "start_stretch", started)
    monkeypatch.setattr(job, "available", lambda model=None: True)
    assert client.post(f"/sheet/{part}/llm").status_code == 202
    assert calls[-1] == {"model": None, "batches": None}
    assert client.post(f"/sheet/{part}/llm", json={"model": "gpt-6.1-sol", "batches": 7}).status_code == 202
    assert calls[-1] == {"model": "gpt-6.1-sol", "batches": 7}
    body = {"start": 10, "end": 200, "model": "claude-sonnet-5-5", "batches": 2}
    assert client.post(f"/sheet/{part}/llm/stretch", json=body).status_code == 202
    assert calls[-1]["model"] == "claude-sonnet-5-5" and calls[-1]["batches"] == 2
    assert client.post(f"/sheet/{part}/llm", json={"model": "gpt-9"}).status_code == 422


def test_each_model_gets_its_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    sonnet = job._complete("p", "stretch", "claude-sonnet-5-5")
    assert type(sonnet).__name__ == "ClaudeComplete" and sonnet.model == "claude-sonnet-5-5" and sonnet.effort == "high"
    sol = job._complete("p", "stretch", "gpt-6.1-sol")
    assert type(sol).__name__ == "OpenAIComplete" and sol.model == "gpt-6.1-sol"
    assert job._complete("p", "stretch").model == job.MODEL == "gpt-6.1-terra"
    with pytest.raises(ValueError):
        job.model_of("gpt-9")


# ------------------------------------------------------------------ a stretch in several batches


def test_a_stretch_in_two_batches_asks_each_one_after_the_other(client: TestClient, part: str) -> None:
    body = sheet(client, part)
    cols = sorted({int(n["ref"].split(":")[0]) for n in body["notes"]})
    asked: list[str] = []

    def refused(system: str, messages: list[dict]) -> str:
        asked.append(messages[0]["content"])
        return "no answer"  # every reply fails the check: each batch keeps its notes

    started = job.start_stretch(part, start=cols[1], end=cols[-1], batches=2, complete=lambda: refused)
    finish(started)
    assert started.summary["stretch"] == "failed"
    firsts = {content for content in asked}
    # Two batches, each with its own first request (then the replies of its check).
    assert len(firsts) == 2 and len(asked) == 2 * llm.MAX_CHECKS
    phases = [m for m in test_part_sheet.messages(started) if m.get("phase") == "batch"]
    assert [m["done"] for m in phases] == [1, 2] and all(m["total"] == 2 for m in phases)
    assert sheet(client, part)["svg"] == body["svg"]  # nothing stored


# ------------------------------------------------------------------ Stop and Revert (the user, 2026-10-30)


def test_stop_asks_nothing_more_and_keeps_what_was_written(client: TestClient, part: str) -> None:
    body = sheet(client, part)
    cols = sorted({int(n["ref"].split(":")[0]) for n in body["notes"]})
    asked: list[int] = []

    def stopped_at_once(system: str, messages: list[dict]) -> str:
        asked.append(1)
        assert client.post(f"/sheet/{part}/llm/stop").status_code == 202
        return "no answer"

    started = job.start_stretch(part, start=cols[1], end=cols[-1], batches=2, complete=lambda: stopped_at_once)
    finish(started)
    assert len(asked) == 1  # the reply it waited for came; no other request
    assert started.summary["stopped"] is True and started.summary["before"] >= 1
    assert client.post(f"/sheet/{part}/llm/stop").status_code == 409  # nothing runs now


def test_revert_puts_the_part_back_as_before_the_run_and_undo_brings_the_run_back(
    client: TestClient, part: str
) -> None:
    before = sheet(client, part)
    started = job.start(part, complete=lambda: test_part_sheet.oracle(test_part_sheet.song(test_part_sheet.SECONDS)))
    finish(started)
    after = sheet(client, part)
    assert after["llm"]["enhanced"] and after["svg"] != before["svg"]
    version = started.summary["before"]
    reverted = client.post(f"/sheet/{part}/llm/revert", params={"width": 120}, json={"version": version})
    assert reverted.status_code == 200, reverted.text
    assert reverted.json()["walked"] == "Revert the AI run"
    again = sheet(client, part)
    assert again["svg"] == before["svg"] and not again["llm"]["enhanced"]
    assert again["history"]["undo"] == "Revert the AI run"
    undone = client.post(f"/sheet/{part}/undo", params={"width": 120}).json()
    assert undone["svg"] == after["svg"] and undone["llm"]["enhanced"]
    assert client.post(f"/sheet/{part}/llm/revert", json={"version": 999}).status_code == 404
