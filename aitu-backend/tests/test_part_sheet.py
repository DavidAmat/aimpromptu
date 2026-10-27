"""The new sheet of a part in the app (implementation 03, Phase 5): the drawing a page asks for, Sonnet writing it
in the background with a stand-in ``complete`` (no request leaves the machine), the hands it writes into
``notes.pmn``, the sheet laid again after a hand edit, and the algorithm kept when the requests fail.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aitu_backend.audio import store as audio_store
from aitu_backend.editing import history
from aitu_backend.main import create_app
from aitu_backend.part_sheet import build, job
from aitu_backend.part_sheet import store as sheet_store
from aitu_backend.pmn import events_file
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.sheet.proposal.frames import propose_frames
from aitu_backend.sheet.sheet import f1
from aitu_backend.storage import paths
from aitu_backend.transcription import jobs, pipeline, split_cache
from aitu_backend.transcription.engine import NoteEvent
from test_sheet_llm_frames import oracle, song

SECONDS = 40.0


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_database_tree()
    split_cache.forget()
    monkeypatch.setattr(job, "available", lambda: True)
    return TestClient(create_app())


@pytest.fixture()
def part(client: TestClient) -> str:
    """A transcribed part of 40 s: notes, no hands, no sheet of either kind."""
    notes = song(SECONDS)
    uuid = audio_store.create("Song", AudioSource.UPLOAD, "wav").uuid
    audio_store.update(uuid, duration_seconds=SECONDS + 4)
    events = [
        NoteEvent(midi_note=int(k) + 21, start=float(on) / 1000, end=float(on + length) / 1000)
        for k, on, length in zip(notes.key, notes.on_ms, notes.len_ms)
    ]
    pipeline.save_note_events(
        uuid, sorted(events, key=lambda e: (e.start, e.midi_note)), SECONDS + 4
    )
    return uuid


def sheet(client: TestClient, uuid: str, width: float = 120) -> dict:
    response = client.get(f"/sheet/{uuid}", params={"width": width})
    assert response.status_code == 200, response.text
    return response.json()


def finish(started: jobs.Job, seconds: float = 60.0) -> None:
    end = time.monotonic() + seconds
    while not started.finished and time.monotonic() < end:
        time.sleep(0.05)
    assert started.status == "done", started.error


def messages(started: jobs.Job) -> list[dict]:
    return [payload for name, payload in started.frames if name == job.EVENT]


def saved_hands(uuid: str) -> dict[tuple[int, int], str | None]:
    stored = pipeline.load_note_events(uuid)
    assert stored is not None
    return {(e.midi_note, round(e.start * 1000)): e.hand for e in stored.events}


def test_a_part_without_a_sheet_draws_the_algorithm_and_asks_for_sonnet(
    client: TestClient, part: str
) -> None:
    body = sheet(client, part)
    assert body["svg"].startswith("<svg") and 'data-note="' in body["svg"]
    assert body["columns"] and body["systems"] and body["width"] == pytest.approx(128, abs=1)
    assert body["source"] == "algorithm" and body["stale"] is False and body["segments"] == []
    assert body["llm"]["state"] == "none"
    # A part made before Phase 5 waits for the button; a new transcription asks Sonnet by itself.
    assert body["llm"]["auto"] is False and body["llm"]["canRun"] is True
    pipeline.clear_new_sheet(part)
    assert sheet(client, part)["llm"]["auto"] is True
    # The cursor map: one row per drawn column, in time order, each with its x on its system.
    ms = [column["ms"] for column in body["columns"]]
    assert ms == sorted(ms) and {column["system"] for column in body["columns"]} == set(
        range(len(body["systems"]))
    )
    # A narrower page draws more lines, the same columns.
    narrow = sheet(client, part, width=70)
    assert len(narrow["systems"]) > len(body["systems"])
    assert [c["frame"] for c in narrow["columns"]] == [c["frame"] for c in body["columns"]]
    # No hand colours before Sonnet decides the hands (Notes Falling).
    events = client.get(f"/matrix/{part}/events").json()["events"]
    assert {event["hand"] for event in events} == {None}


def test_sonnet_writes_the_sheet_window_by_window_and_its_hands_into_the_notes(
    client: TestClient, part: str
) -> None:
    pipeline.clear_new_sheet(part)
    started = job.start(part, complete=lambda: oracle(song(SECONDS)))
    finish(started)
    assert not sheet_store.asked(part), "the mark is used once Sonnet starts"
    phases = [m["phase"] for m in messages(started)]
    assert phases[0] == "reference" and phases[1] == "windows" and phases[-1] == "saved"
    windows = [m for m in messages(started) if m["phase"] == "window"]
    assert len(windows) >= 3 and [m["done"] for m in windows] == list(range(1, len(windows) + 1))

    stored = sheet_store.load(part)
    assert stored is not None and stored.record.source == "llm"
    assert [state for _, _, state in stored.record.windows] == ["llm"] * len(windows)
    header = events_file.read_header(pipeline.events_path(part))
    assert stored.record.hands_revision == header.hands_revision
    # The hands of the answers are in notes.pmn: the song's left hand plays its bass and chords below middle C.
    hands = saved_hands(part)
    assert set(hands.values()) == {"right", "left"}
    assert all(hand == "left" for (midi, _), hand in hands.items() if midi < 57)

    body = sheet(client, part)
    assert body["source"] == "llm" and body["stale"] is False
    assert [s["state"] for s in body["segments"]] == ["llm"] * len(windows)
    assert body["llm"]["state"] == "done" and body["llm"]["auto"] is False
    # Enhanced with AI, and offered again (at the user's own risk of the same result).
    assert body["llm"]["enhanced"] is True and body["llm"]["runs"] == 1
    assert body["llm"]["canRun"] is True
    status = client.get(f"/pieces/{part}/status").json()
    assert {s["step"]: s["state"] for s in status["steps"]}["sheet"] == "ready"
    events = client.get(f"/matrix/{part}/events").json()["events"]
    assert {event["hand"] for event in events} == {"right", "left"}


def test_while_sonnet_writes_the_page_sees_the_sheet_of_that_moment(
    client: TestClient, part: str
) -> None:
    good = oracle(song(SECONDS))
    seen: list[list[str]] = []

    def watched(system: str, messages_: list[dict]) -> str:
        run = job.live(part)
        assert run is not None
        seen.append([state for _, _, state in run.segments()])
        assert f1.read(run.text()).notes
        return good(system, messages_)

    finish(job.start(part, complete=lambda: watched))
    # The reference request: the first segment is at Sonnet; then each window in turn, the earlier ones decided.
    assert seen[0][0] == "working" and set(seen[0][1:]) <= {"waiting"}
    for k, states in enumerate(seen[1:]):
        assert states[:k] == ["llm"] * k and states[k] == "working"


def test_a_hand_moved_after_sonnet_lays_its_sheet_on_the_new_hands(
    client: TestClient, part: str
) -> None:
    finish(job.start(part, complete=lambda: oracle(song(SECONDS))))
    before = build.current(part)
    note = next(n for n in f1.read(before.text).notes if n.staff == 1 and not n.grace)
    current = client.get(f"/pieces/{part}/notes").json()
    ids = [
        i
        for i, k, on in zip(current["id"], current["key"], current["onMs"])
        if k + 21 == note.midi and abs(on - note.frame * 40) <= 40
    ]
    moved = client.patch(
        f"/pieces/{part}/notes",
        json={
            "baseRevision": current["revision"],
            "ops": [{"op": "hand", "ids": ids, "hand": "l"}],
        },
    )
    assert moved.status_code == 200, moved.text
    after = build.current(part)
    assert after.stale and after.source == "llm"
    laid = f1.read(after.text)
    assert any(n.frame == note.frame and n.midi == note.midi and n.staff == 2 for n in laid.notes)
    # Everything else keeps its hand.
    assert (
        sum(n.staff == 1 for n in laid.notes)
        == sum(n.staff == 1 for n in f1.read(before.text).notes) - 1
    )


def test_a_stored_sheet_is_drawn_with_the_grace_rule_of_today(
    client: TestClient, part: str
) -> None:
    # implementation 04, Phase 2: a sheet stored with an older grace rule (here a written note stored as a grace
    # note) is drawn with today's rule; the stored file stays as it is, and nothing else of the drawing changes
    finish(job.start(part, complete=lambda: oracle(song(SECONDS))))
    kept = sheet_store.load(part)
    assert kept is not None
    drawn = build.current(part)
    assert not drawn.stale and drawn.text == kept.text
    old = f1.read(kept.text)
    note = next(n for n in old.notes if n.staff == 1 and not n.grace and n.beam is None)
    note.grace, note.figure = "acc", 8
    older = f1.write(old, mode="frames")
    sheet_store.save(part, older, kept.record)
    build.forget(part)
    again = build.current(part)
    assert not again.stale and again.source == "llm"
    assert again.text == kept.text
    assert sheet_store.load(part).text == older


def test_two_grace_notes_of_a_stored_sheet_are_written_as_one_beam_group() -> None:
    # implementation 04, Phase 2: two semicorcheas before a blanca, stored as grace notes by the old rule and in no
    # beam group (the AI's groups never held a grace note), are drawn as two corcheas with one beam
    from test_sheet_frames import R, notes_of

    notes = notes_of([(74, 1000.0, 120.0, R), (76, 1125.0, 120.0, R), (72, 1250.0, 1000.0, R)])
    stored = propose_frames(notes, quarter_ms=500.0).sheet
    pair = [n for n in stored.notes if n.midi in (74, 76)]
    for n in pair:
        n.grace, n.figure, n.beam = "unacc", 16, None
    drawn = build.reapply(stored, notes)
    pair = [n for n in drawn.notes if n.midi in (74, 76)]
    assert [(n.grace, n.figure) for n in pair] == [(None, 8), (None, 8)]
    assert pair[0].beam is not None and pair[0].beam == pair[1].beam
    # a beam the user takes away afterwards stays away: the stored sheet holds written notes now
    for n in pair:
        n.beam = None
    again = build.reapply(drawn, notes)
    assert all(n.beam is None for n in again.notes if n.midi in (74, 76))


def test_without_credits_the_algorithm_and_the_hands_stay(client: TestClient, part: str) -> None:
    def no_credits(system: str, messages_: list[dict]) -> str:
        raise RuntimeError("credit balance is too low")

    finish(job.start(part, complete=lambda: no_credits))
    stored = sheet_store.load(part)
    assert stored is not None and stored.record.source == "algorithm"
    assert "credit balance" in (stored.record.note or "")
    assert set(saved_hands(part).values()) == {None}
    body = sheet(client, part)
    # Nothing alarming: the algorithm's sheet, the button to try again, and no start by itself.
    assert (
        body["source"] == "algorithm"
        and body["llm"]["auto"] is False
        and body["llm"]["canRun"] is True
    )


def test_a_new_set_of_notes_forgets_the_sheet_and_the_history_keeps_it(
    client: TestClient, part: str
) -> None:
    finish(job.start(part, complete=lambda: oracle(song(SECONDS))))
    version = history.snapshot_notes(part)
    assert (paths.history_version_dir(part, version - 1) / "sheet.f1").is_file()
    pipeline.clear_new_sheet(part)
    assert sheet_store.load(part) is None
    assert sheet(client, part)["source"] == "algorithm"


def test_an_old_sheet_json_keeps_its_key_and_a_figure_the_user_renamed(
    client: TestClient, part: str
) -> None:
    reading = {"anchorFigure": "corchea", "anchorMs": 240.0, "frameMs": 40.0, "keySignature": "D"}
    pipeline.rhythm_path(part).write_text(json.dumps(reading))
    assert build.reading_of(part) == build.Reading(key=2, key_changes=None, quarter_ms=480.0)
    drawn = build.current(part)
    assert drawn.quarter_ms == pytest.approx(480.0) and f1.read(drawn.text).key == 2
    # A pile named a negra was vexflow-v2's default: the pulse estimate decides.
    pipeline.rhythm_path(part).write_text(json.dumps({**reading, "anchorFigure": "negra"}))
    assert build.reading_of(part).quarter_ms is None
    # An old part (a saved sheet.json) does not start Sonnet by itself; the button stays.
    body = sheet(client, part)
    assert body["llm"]["auto"] is False and body["llm"]["canRun"] is True


def test_sonnet_is_refused_when_it_is_not_set_up(
    client: TestClient, part: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(job, "available", lambda: False)
    assert client.post(f"/sheet/{part}/llm").status_code == 409
    body = sheet(client, part)
    assert body["llm"]["available"] is False and body["llm"]["auto"] is False
    assert client.get("/sheet/nope").status_code == 404


def test_a_deleted_part_stops_the_requests(client: TestClient, part: str) -> None:
    good = oracle(song(SECONDS))
    calls: list[int] = []

    def then_deleted(system: str, messages_: list[dict]) -> str:
        calls.append(1)
        if len(calls) == 2:
            pipeline.events_path(part).unlink()
        return good(system, messages_)

    started = job.start(part, complete=lambda: then_deleted)
    finish(started)
    assert len(calls) == 2, "no request after the part was gone"
    assert started.summary["source"] == "gone" and sheet_store.load(part) is None


def test_a_blank_part_answers_an_empty_sheet(client: TestClient) -> None:
    uuid = audio_store.create("Blank", AudioSource.UPLOAD, "wav").uuid
    pipeline.save_note_events(uuid, [], 0.0)
    body = sheet(client, uuid)
    assert body["columns"] == [] and body["svg"] == "" and body["llm"]["auto"] is False


def test_the_projects_list_says_sonnet_is_writing(client: TestClient, part: str) -> None:
    good = oracle(song(SECONDS))
    release = threading.Event()

    def held(system: str, messages_: list[dict]) -> str:
        release.wait(30)
        return good(system, messages_)

    started = job.start(part, complete=lambda: held)
    try:
        rows = client.get("/projects").json()
        row = next(row for row in rows if part in row["parts"])
        assert row["running"] == "writing"
    finally:
        release.set()
    finish(started)
    row = next(row for row in client.get("/projects").json() if part in row["parts"])
    assert row["running"] is None


def test_enhanced_again_counts_the_runs_and_a_failed_run_keeps_the_ai_sheet(
    client: TestClient, part: str
) -> None:
    finish(job.start(part, complete=lambda: oracle(song(SECONDS))))
    first = sheet_store.load(part)
    assert first is not None and first.record.enhanced and first.record.runs == 1

    def no_credits(system: str, messages_: list[dict]) -> str:
        raise RuntimeError("credit balance is too low")

    finish(job.start(part, complete=lambda: no_credits))
    kept = sheet_store.load(part)
    assert kept is not None and kept.text == first.text
    assert (
        kept.record.enhanced
        and kept.record.runs == 1
        and "credit balance" in (kept.record.note or "")
    )

    # A hand moved later: the sheet is laid on the new hands and keeps its mark.
    current = client.get(f"/pieces/{part}/notes").json()
    client.patch(
        f"/pieces/{part}/notes",
        json={
            "baseRevision": current["revision"],
            "ops": [{"op": "hand", "ids": current["id"][:3], "hand": "l"}],
        },
    )
    body = sheet(client, part)
    assert body["stale"] is True and body["llm"]["enhanced"] is True

    finish(job.start(part, complete=lambda: oracle(song(SECONDS))))
    assert sheet_store.load(part).record.runs == 2


def test_the_projects_list_marks_a_project_the_ai_enhanced(client: TestClient, part: str) -> None:
    def row() -> dict:
        return next(row for row in client.get("/projects").json() if part in row["parts"])

    assert row()["enhanced"] is False
    finish(job.start(part, complete=lambda: oracle(song(SECONDS))))
    assert row()["enhanced"] is True
