"""The levels in the app (implementation 04-3, Phase 4): the catalog of patterns, a level run of the job with a
stand-in for the AI (no request), its storing in ``notes.pmn`` and ``sheet.f1`` as one step of undo, and the routes of
the Enhance with AI dialog. The check of an answer is Phase 3's (``test_sheet_levels.py``): here it is replaced by a
stand-in that accepts every answer it can read, so that the storing is tested on any notes."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from aitu_backend.part_sheet import build, job
from aitu_backend.sheet.llm import levels as L
from aitu_backend.sheet.sheet import f1
from aitu_backend.sheet.sheet.data import Sheet
from aitu_backend.storage import bundle, locate
from aitu_backend.transcription import pipeline
import test_part_sheet
from test_part_sheet import finish, messages, sheet
from test_sheet_edits import walk
from test_sheet_reading import notes_of, stored_sheet

client = test_part_sheet.client
part = test_part_sheet.part


# ------------------------------------------------------------------ the catalog


def test_the_catalog_has_the_approved_patterns_and_the_defaults_of_each_level() -> None:
    patterns, defaults = L.catalog_rows()
    refs = {p["ref"] for p in patterns}
    assert len(patterns) == 113 and len(L.catalog()) == 113
    assert {"left easy 2", "left medium 15", "left hard 18", "right super hard 13"} <= refs
    # The sets approved in Phase 3, and a set for hard in the left hand.
    assert defaults["left"]["medium"] == ["left medium 15", "left medium 2", "left medium 10", "left medium 7"]
    assert defaults["right"]["hard"] == ["right hard 1", "right hard 17", "right hard 15", "right hard 4"]
    assert all(r in refs for hand in defaults.values() for level in hand.values() for r in level)
    # Every example reads, with both hands.
    for pattern in L.catalog().values():
        assert {n.staff for n in f1.read(pattern.example).notes} >= {1 if pattern.hand == "right" else 2}


def test_a_hand_with_no_pattern_selected_gets_its_level_set() -> None:
    both = L.run_refs({"right": "hard", "left": "medium"}, (1, 2), [])
    assert both == ["right hard 1", "right hard 17", "right hard 15", "right hard 4",
                    "left medium 15", "left medium 2", "left medium 10", "left medium 7"]
    # A selection or a pattern named in the words is kept, for its hand only; the other hand gets its set.
    picked = L.run_refs("easy", (1, 2), ["left easy 5", "right hard 99"], "at f300 use medium 2")
    assert picked[0] == "left easy 5" and set(picked[1:3]) == {"left medium 2", "right medium 2"}
    assert "right hard 99" not in picked and "left easy 2" not in picked
    # A run of one hand: the other hand's patterns are not used.
    assert L.run_refs("easy", (2,), ["right easy 1"]) == ["left easy 2", "left easy 1", "left easy 3", "left easy 12"]


def test_the_routes_of_the_catalog(client: TestClient) -> None:
    body = client.get("/sheet/levels/catalog").json()
    assert len(body["patterns"]) == 113 and body["defaults"]["left"]["easy"][0] == "left easy 2"
    one = body["patterns"][0]
    assert set(one) >= {"ref", "hand", "level", "number", "name", "line"}
    drawing = client.get("/sheet/levels/catalog/left/medium/2.svg")
    assert drawing.status_code == 200 and drawing.text.startswith("<svg")
    assert drawing.headers["content-type"].startswith("image/svg+xml")
    assert client.get("/sheet/levels/catalog/right/super-hard/1.svg").status_code == 200
    assert client.get("/sheet/levels/catalog/left/easy/999.svg").status_code == 404


# ------------------------------------------------------------------ a level run in the app


def target_of(prompt: str) -> Sheet:
    return f1.read(re.search(r"## Target.*?```\n(.*?)```", prompt, re.S).group(1))


def stand_in(prompts: list[str]):
    """The AI: a plan of one section, then each batch with the left hand in single notes (its lowest note) and its
    last note left out, the first right-hand note moved to the left hand, and a new note an octava under the first
    left-hand note."""

    def complete(system: str, messages: list[dict]) -> str:
        prompt = messages[-1]["content"]
        prompts.append(prompt)
        # the first pattern of each hand of the run (the system prompt lists them), for the hands it rewrites
        found = {h: re.search(rf"^### ({h} \w+ \d+):", system, re.M) for h in ("left", "right")}
        refs = {h: m.group(1) for h, m in found.items() if m}
        hands = list(refs)  # a run of one hand has the patterns of that hand only
        if prompt.startswith("# The plan of the song"):
            a, b = re.search(r"\(f(\d+)-f(\d+),", prompt).groups()
            said = " ".join(f"{h[0].upper()}={refs[h]}" for h in hands)
            return f"```\nS1 f{a}-f{b} {said} | one section\n```"
        target = target_of(prompt)
        a, b = re.search(r"batch \d+ of \d+ \(f(\d+)-f(\d+),", prompt).groups()
        lows: dict[int, int] = {}
        for n in target.notes:
            if n.staff == 2:
                lows[n.frame] = min(lows.get(n.frame, 999), n.midi)
        left = sorted(lows)
        kept = [n for n in target.notes if n.staff == 1 or (lows.get(n.frame) == n.midi and n.frame != left[-1])]
        right = [n for n in kept if n.staff == 1]
        moved = min(right, key=lambda n: (n.frame, n.midi)) if right else None
        out = [L.replace(n, staff=2) if n is moved else n for n in kept]
        low = next(n for n in kept if n.staff == 2 and n.frame == left[0])
        out.append(L.replace(low, octave=low.octave - 1, figure=4))
        text = f1.write(L._bare(L.replace(target, notes=out).sort()), mode="frames").strip()
        said = "\n".join(f"# pattern {h[0].upper()} f{a}-f{b}: {refs[h]}" for h in hands)
        return f"```\n{text}\n{said}\n```"

    return complete


@pytest.fixture()
def accepting(monkeypatch: pytest.MonkeyPatch):
    """The check accepts every answer that reads (the check itself is tested in ``test_sheet_levels.py``)."""

    def check(reply: str, target: Sheet, **_: object) -> L.Batch:
        sheet_ = f1.read(L._block(reply))
        sheet_.quarter_ms = target.quarter_ms
        return L.Batch([], sheet_, L.read_declared(reply))

    monkeypatch.setattr(L, "check_level", check)


def hands_agree(part_id: str) -> None:
    """Every live note of ``notes.pmn`` has the hand the stored sheet draws it in (the Notes tab shows the level:
    Phase 3 report, section 16)."""
    stored = pipeline.load_note_events(part_id)
    assert stored is not None
    drawn = f1.read(build.current(part_id).text)
    hands = build.hands_of_sheet(drawn, pipeline.starting_hands(part_id))
    live = [e for e in stored.events if not e.removed]
    assert live and all(e.hand == hands.get(e.id) and not e.hand_guessed for e in live)


def test_a_level_of_both_hands_stores_its_notes_and_hands_as_one_step(
    client: TestClient, part: str, accepting: None
) -> None:
    before = sheet(client, part)
    prompts: list[str] = []
    started = job.start_level(part, level="easy", hand="both", complete=lambda: stand_in(prompts))
    finish(started)
    summary = started.summary
    batches = len(prompts) - 1
    assert summary["level"] == "ok" and summary["batches"] == summary["total"] == batches >= 2
    phases = [m.get("phase") for m in messages(started)]
    assert phases[:2] == ["level", "plan"] and phases.count("batch") == batches and phases[-1] == "saved"
    assert prompts[0].startswith("# The plan of the song") and "Decided context" in prompts[2]

    after = sheet(client, part)
    was, now = notes_of(before), notes_of(after)
    assert any(n["hand"] == "left" for r, n in now.items() if r in was and was[r]["hand"] == "right")
    stored = pipeline.load_note_events(part)
    assert stored is not None
    removed = [e for e in stored.events if e.removed]
    assert len(removed) >= batches and len(stored.events) == len(was) + batches  # one left out, one new per batch
    assert len(set(now) - set(was)) == batches
    assert after["history"]["undo"] == "Level easy with AI, both hands"
    # The level is drawn by the app's rules: its corcheas in beam groups, as the rest of the sheet.
    level_notes = [n for r, n in now.items() if r not in was or now[r]["hand"] != was[r]["hand"]]
    assert any(n["beam"] is not None for n in now.values() if n["figure"] in (8, 16))
    drawn = f1.read(build.current(part).text)
    beams = [n.beam for n in drawn.notes if n.beam is not None]
    assert beams and level_notes
    assert after["llm"]["enhanced"] is True
    hands_agree(part)
    record = stored_sheet(part).record
    entry = record.levels[0]
    assert entry["level"] == "easy" and entry["hand"] == "both" and entry["range"] is False
    assert entry["patterns"][:2] == ["right easy 2", "right easy 1"] and entry["prompt"] == L.LEVEL_VERSION
    assert entry["plan"][0].startswith("S1 ") and "pattern L" in entry["declared"][0]

    back = walk(client, part, "undo")
    assert set(notes_of(back)) == set(was)
    assert {r: n["hand"] for r, n in notes_of(back).items()} == {r: n["hand"] for r, n in was.items()}
    again = walk(client, part, "redo")
    assert set(notes_of(again)) == set(now)


def test_a_level_of_one_hand_on_a_range_keeps_the_rest(client: TestClient, part: str, accepting: None) -> None:
    before = sheet(client, part)
    prompts: list[str] = []
    seen: list[list] = []
    write = stand_in(prompts)

    def watched(system: str, messages_: list[dict]) -> str:
        seen.append([(s["state"], s.get("staff")) for s in sheet(client, part)["segments"]])
        return write(system, messages_)

    started = job.start_level(part, level="medium", hand="left", start=100, end=400, complete=lambda: watched)
    finish(started)
    assert started.summary["level"] == "ok"
    assert all(staff == 2 for states in seen for _, staff in states)
    after = sheet(client, part)
    was, now = notes_of(before), notes_of(after)
    outside = {r for r in was if not 100 <= int(r.split(":")[0]) < 400}
    assert {r: was[r]["hand"] for r in outside} == {r: now[r]["hand"] for r in outside if r in now}
    assert outside <= set(now)
    right = {r for r, n in was.items() if n["hand"] == "right"}
    assert right <= set(now)  # a run of the left hand never takes a right-hand note off
    hands_agree(part)
    entry = stored_sheet(part).record.levels[0]
    assert entry["range"] is True and entry["hand"] == "left" and 100 <= entry["start"] < entry["end"] <= 400
    assert after["history"]["undo"] == "Level medium with AI, the left hand"


def test_a_level_whose_batches_all_fail_stores_nothing(client: TestClient, part: str) -> None:
    before = sheet(client, part)

    def wrong(system: str, messages_: list[dict]) -> str:
        if messages_[0]["content"].startswith("# The plan of the song"):
            a, b = re.search(r"\(f(\d+)-f(\d+),", messages_[0]["content"]).groups()
            return f"```\nS1 f{a}-f{b} L=left easy 2 R=right easy 2 | one\n```"
        return "no notes"

    started = job.start_level(part, level="easy", hand="both", complete=lambda: wrong)
    finish(started)
    assert started.summary["level"] == "failed"
    after = sheet(client, part)
    assert set(notes_of(after)) == set(notes_of(before)) and after["history"]["undo"] is None


def test_the_routes_of_the_levels(client: TestClient, part: str, monkeypatch: pytest.MonkeyPatch) -> None:
    costs = client.get(f"/sheet/{part}/llm/costs").json()
    assert {"level-both", "level-right", "level-left"} <= set(costs)
    assert costs["level-both"]["usd"] == pytest.approx(
        job.USD_LEVEL_PLAN + (costs["level-both"]["requests"] - 1) * job.USD_LEVEL_BATCH
    )
    ranged = client.get(f"/sheet/{part}/llm/costs", params={"start": 100, "end": 400}).json()
    assert 2 <= ranged["level-stretch-left"]["requests"] < costs["level-left"]["requests"]
    calls: list[dict] = []

    def started(uuid: str, **kwargs: object):
        calls.append({"uuid": uuid, **kwargs})
        return type("J", (), {"id": "j", "status": "queued"})()

    monkeypatch.setattr(job, "start_level", started)
    assert client.post(f"/sheet/{part}/llm/level", json={"right": "easy"}).status_code == 400  # no range
    answer = client.post(
        f"/sheet/{part}/llm/level",
        json={"right": "hard", "left": "medium", "hand": "both", "start": 50, "end": 300, "patterns": ["left medium 2"]},
    )
    assert answer.status_code == 202
    assert calls[-1] == {
        "uuid": part, "level": {"right": "hard", "left": "medium"}, "hand": "both", "start": 50, "end": 300,
        "patterns": ["left medium 2"], "words": "",
    }
    assert client.post(f"/sheet/{part}/llm/level", json={"right": "super hard", "start": 0, "end": 9}).status_code == 422

    # A level of the whole sheet: a new project, named with the level, where the run starts; the original stays.
    title = bundle.read_project(locate.part(part).project_id).title
    copy = client.post(f"/sheet/{part}/llm/level-copy", json={"right": "easy", "left": "easy", "hand": "left"})
    assert copy.status_code == 202, copy.text
    body = copy.json()
    assert body["title"] == f"{title} · Easy, left hand" and body["partId"] != part
    assert calls[-1]["uuid"] == body["partId"] and calls[-1]["level"] == "easy" and calls[-1]["start"] is None
    made = bundle.read_project(body["projectId"])
    assert made.level_of == locate.part(part).project_id and made.based_on is None
    assert pipeline.load_note_events(body["partId"]) is not None
    assert client.post(f"/sheet/{part}/llm/level-copy", json={"right": "hard", "left": "medium"}).json()[
        "title"
    ] == f"{title} · Right hard, left medium"
