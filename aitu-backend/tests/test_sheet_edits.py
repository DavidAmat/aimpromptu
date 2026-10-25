"""Editing the new sheet (implementation 03, Phase 6): notes moved to the other hand in ``notes.pmn``, the stored sheet
laid again on the new hands, and undo and redo from the part's log, through the routes the page calls. Sonnet is the
stand-in ``oracle`` of the Phase 4 tests: no request leaves the machine.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aitu_backend.part_sheet import build, edits, job
from aitu_backend.part_sheet import store as sheet_store
from aitu_backend.pmn import events_file
from aitu_backend.sheet.proposal.frames import BASS_LIMIT, _ledger
from aitu_backend.sheet.sheet import f1, frames
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline
import test_part_sheet
from test_part_sheet import SECONDS, finish, sheet
from test_sheet_llm_frames import oracle, song

# The fixtures of the Phase 5 tests: a 40 s transcribed part and a client on a temporary database.
client = test_part_sheet.client
part = test_part_sheet.part


def hands_of(body: dict) -> dict[str, str]:
    return {note["ref"]: note["hand"] for note in body["notes"]}


def a_right_hand_run(body: dict, count: int = 3) -> list[str]:
    """Refs of consecutive right-hand notes of the run (the song's right hand runs in eighths every other bar)."""
    right = [
        note["ref"]
        for note in body["notes"]
        if note["hand"] == "right" and int(note["ref"].split(":")[1]) >= 71
    ]
    return right[:count]


def move(client: TestClient, uuid: str, refs: list[str], hand: str) -> dict:
    response = client.post(
        f"/sheet/{uuid}/hands", params={"width": 120}, json={"notes": refs, "hand": hand}
    )
    assert response.status_code == 200, response.text
    return response.json()


def walk(client: TestClient, uuid: str, to: str) -> dict:
    response = client.post(f"/sheet/{uuid}/{to}", params={"width": 120})
    assert response.status_code == 200, response.text
    return response.json()


def enhance(uuid: str) -> None:
    finish(job.start(uuid, complete=lambda: oracle(song(SECONDS))))


def test_the_drawing_names_each_notehead_with_its_hand_and_printed_name(
    client: TestClient, part: str
) -> None:
    body = sheet(client, part)
    refs = {
        ref for ref in body["svg"].split('data-note="')[1:] for ref in ref.split('"')[0].split(" ")
    }
    assert refs == set(hands_of(body))
    assert all(
        note["pitch"][0] in "ABCDEFG" and note["pitch"][-1].isdigit() for note in body["notes"]
    )
    assert body["editable"] is True and body["history"] == {"undo": None, "redo": None}


def test_a_hand_move_on_the_algorithms_sheet_is_written_into_the_notes_and_undone(
    client: TestClient, part: str
) -> None:
    before = sheet(client, part)
    refs = a_right_hand_run(before)
    after = move(client, part, refs, "left")
    assert after["moved"] == 3 and after["unmatched"] == 0
    assert all(hands_of(after)[ref] == "left" for ref in refs)
    assert after["history"] == {"undo": "Move 3 notes to the left hand", "redo": None}
    # The hands were never saved: every note now keeps the hand the sheet drew, the three moved ones the new one.
    stored = pipeline.load_note_events(part)
    assert stored is not None and all(
        e.hand in ("right", "left") and not e.hand_guessed for e in stored.events
    )
    unchanged = {ref: hand for ref, hand in hands_of(before).items() if ref not in refs}
    assert {ref: hands_of(after)[ref] for ref in unchanged} == unchanged
    # The algorithm's sheet is not stored: it is a function of the notes and their hands.
    assert sheet_store.load(part) is None

    back = walk(client, part, "undo")
    assert back["walked"] == "Move 3 notes to the left hand"
    assert hands_of(back) == hands_of(before) and back["svg"] == before["svg"]
    assert back["history"] == {"undo": None, "redo": "Move 3 notes to the left hand"}
    # The hands nobody had saved are unsaved again (``save_edit``'s quick rule marks them guessed: the split decides).
    stored = pipeline.load_note_events(part)
    assert stored is not None and all(e.hand is None or e.hand_guessed for e in stored.events)

    again = walk(client, part, "redo")
    assert hands_of(again) == hands_of(after) and again["svg"] == after["svg"]
    assert walk(client, part, "redo")["walked"] is None


def test_a_hand_move_on_the_ais_sheet_keeps_it_stored_current_and_enhanced(
    client: TestClient, part: str
) -> None:
    enhance(part)
    kept = sheet_store.load(part)
    assert kept is not None and kept.record.enhanced
    before = sheet(client, part)
    refs = a_right_hand_run(before, 2)

    after = move(client, part, refs, "left")
    assert all(hands_of(after)[ref] == "left" for ref in refs)
    assert after["source"] == "llm" and after["stale"] is False and after["llm"]["enhanced"] is True
    moved = sheet_store.load(part)
    header = events_file.read_header(pipeline.events_path(part))
    assert moved is not None and moved.record.hands_revision == header.hands_revision
    assert moved.text != kept.text and moved.record.windows == kept.record.windows

    back = walk(client, part, "undo")
    assert back["svg"] == before["svg"] and back["stale"] is False
    restored = sheet_store.load(part)
    assert restored is not None and restored.text == kept.text
    assert walk(client, part, "redo")["svg"] == after["svg"]
    again = sheet_store.load(part)
    assert again is not None and again.text == moved.text


def test_undo_leaves_a_hand_that_something_else_changed_since(
    client: TestClient, part: str
) -> None:
    enhance(part)
    refs = a_right_hand_run(sheet(client, part), 2)
    move(client, part, refs, "left")
    # The old sheet moves the first note back to the right hand (``PUT /time/{uuid}/hands`` writes notes.pmn).
    frame, midi = (int(x) for x in refs[0].split(":"))
    stored = pipeline.load_note_events(part)
    assert stored is not None
    for event in stored.events:
        if event.midi_note == midi and abs(event.start * 1000 - frame * 40) < 80:
            event.hand = "right"
    pipeline.save_edit(
        part,
        stored.events,
        stored.duration_seconds,
        stored.title,
        notes_changed=False,
        hands_changed=True,
    )
    back = walk(client, part, "undo")
    # Both are on the right again, the second by the undo; the sheet is laid again on the hands, not patched.
    assert hands_of(back)[refs[0]] == "right" and hands_of(back)[refs[1]] == "right"
    assert back["stale"] is True and back["llm"]["enhanced"] is True


def test_an_ai_run_starts_the_steps_again_and_reads_the_current_hands_on_a_run_again(
    client: TestClient, part: str
) -> None:
    first: list = []
    finish(job.start(part, complete=lambda: oracle(song(SECONDS), log=first)))
    # A first run reads the notes without hands.
    assert "R:" not in first[1][0]["content"].split("## Target")[1].split("## Look-ahead")[0]
    refs = a_right_hand_run(sheet(client, part), 2)
    move(client, part, refs, "left")
    assert paths.part_frames_edits_path(part).is_file()

    again: list = []
    finish(job.start(part, complete=lambda: oracle(song(SECONDS), log=again)))
    target = [m[0]["content"] for m in again if "## Target" in m[0]["content"]]
    # A run again shows the current hands, the moved notes among them, as a suggestion.
    assert target and all("R:" in t or "L:" in t for t in target)
    assert all("Read them as a suggestion" in t for t in target)
    assert sheet_store.load(part).record.prompt.endswith("+hands")  # type: ignore[union-attr]
    # The AI may change them (the user's answer): the stand-in answers with the algorithm's hands, so they are back.
    body = sheet(client, part)
    assert all(hands_of(body)[ref] == "right" for ref in refs)
    assert body["history"] == {"undo": None, "redo": None}


def test_no_edit_while_the_ai_writes_the_sheet(
    client: TestClient, part: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    refs = a_right_hand_run(sheet(client, part), 1)
    monkeypatch.setattr(job, "job_of", lambda part_id: object())
    monkeypatch.setattr(job, "live", lambda part_id: None)
    response = client.post(f"/sheet/{part}/hands", json={"notes": refs, "hand": "left"})
    assert response.status_code == 409
    assert client.post(f"/sheet/{part}/undo").status_code == 409


def test_notes_the_sheet_does_not_hold_are_counted_not_moved(client: TestClient, part: str) -> None:
    body = move(client, part, ["1:20", "nonsense"], "left")
    assert body["moved"] == 0 and body["unmatched"] == 2
    assert body["history"] == {"undo": None, "redo": None}
    assert edits.history(part) == {"undo": None, "redo": None}


def test_a_high_run_moved_to_the_left_hand_gets_the_treble_clef_for_its_stretch_only(
    client: TestClient, part: str
) -> None:
    enhance(part)
    before = sheet_store.load(part)
    assert before is not None
    stored = f1.read(before.text)
    # The first run of the right hand (A4 to E5, eighths): far above the bass staff.
    run = sorted({n.frame for n in stored.notes if n.staff == 1 and n.midi >= 71})[:8]
    refs = [f"{n.frame}:{n.midi}" for n in stored.notes if n.staff == 1 and n.frame in run]
    move(client, part, refs, "left")
    moved = sheet_store.load(part)
    assert moved is not None
    now = f1.read(moved.text)
    assert frames.check(now) == []
    left = [n for n in now.notes if n.staff == 2 and n.frame in run]
    clef = dict(zip(run, build._clef_track(now, 2, run)))
    assert left and all(
        clef[n.frame] == "G2" for n in left
    ), "the left hand reads them in the treble clef"
    # Nothing far above the bass staff, and the clefs of the rest of the song are the ones the AI wrote.
    assert all(
        _ledger(n, clef, n.ottava)[1] < BASS_LIMIT
        for n, clef in zip(
            (n for n in now.notes if n.staff == 2),
            build._clef_track(now, 2, [n.frame for n in now.notes if n.staff == 2]),
        )
    )
    after_run = max(run) + 200
    assert [c for c in now.clef_changes if c[0] > after_run] == [
        c for c in stored.clef_changes if c[0] > after_run
    ]
    assert walk(client, part, "undo")["stale"] is False
    assert sheet_store.load(part).text == before.text  # type: ignore[union-attr]
