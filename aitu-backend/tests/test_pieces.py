"""The piece API, the revisions and the hand split as a step (implementation 08, Phase 5).

One test per row of the staleness table of the plan's section 8.3, then the operations of the
piano roll visualization, the prediction, the old pieces that have no saved hands, and the quick
rule for an added note.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile

from aitu_backend.audio import ingest, store
from aitu_backend.main import create_app
from aitu_backend.pmn import events_file
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline, saved_hands, split_cache, time_pipeline
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.events_to_matrix import events_to_time_matrix
from parts import with_audio

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")

DURATION = 8.0
READING = {"anchorFigure": "negra", "anchorMs": 500.0, "frameMs": 40.0}


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_database_tree()
    split_cache.forget()
    return tmp_path / "data"


@pytest.fixture()
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app())


def music() -> list[NoteEvent]:
    """A right hand melody every 250 ms over a left hand bass every second."""
    right = [
        NoteEvent(midi_note=72 + index % 5, start=index * 0.25, end=index * 0.25 + 0.2)
        for index in range(30)
    ]
    left = [
        NoteEvent(midi_note=36 + (index % 2) * 7, start=float(index), end=index + 0.9)
        for index in range(7)
    ]
    return sorted(right + left, key=lambda event: (event.start, event.midi_note))


@pytest.fixture()
def piece(data_dir: Path) -> str:
    """A transcribed piece: notes, no hands yet, no sheet."""
    uuid = store.create("Piece", AudioSource.UPLOAD, "wav").uuid
    store.update(uuid, duration_seconds=DURATION)
    pipeline.save_note_events(uuid, music(), DURATION, title="Piece")
    return uuid


def status(client: TestClient, uuid: str) -> dict:
    response = client.get(f"/pieces/{uuid}/status")
    assert response.status_code == 200, response.text
    body = response.json()
    body["by"] = {step["step"]: step for step in body["steps"]}
    return body


def notes(client: TestClient, uuid: str) -> dict:
    response = client.get(f"/pieces/{uuid}/notes")
    assert response.status_code == 200, response.text
    return response.json()


def patch(client: TestClient, uuid: str, ops: list[dict], **extra) -> dict:
    base = notes(client, uuid)
    response = client.patch(
        f"/pieces/{uuid}/notes",
        json={"baseRevision": base["revision"], "ops": ops, **extra},
    )
    assert response.status_code == 200, response.text
    return response.json()


def predict_and_save(client: TestClient, uuid: str) -> dict:
    base = notes(client, uuid)
    predicted = client.post(
        f"/pieces/{uuid}/hands/predict", json={"baseRevision": base["revision"]}
    ).json()
    right = [i for i, hand in zip(predicted["id"], predicted["hand"]) if hand == "r"]
    left = [i for i, hand in zip(predicted["id"], predicted["hand"]) if hand == "l"]
    return patch(
        client,
        uuid,
        [
            {"op": "hand", "ids": right, "hand": "r"},
            {"op": "hand", "ids": left, "hand": "l"},
        ],
    )


def write_sheet(client: TestClient, uuid: str) -> dict:
    response = client.put(f"/time/{uuid}/rhythm", json=READING)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture()
def ready(client: TestClient, piece: str) -> str:
    """The piece with its hands predicted and saved, and a sheet written: every step ready."""
    predict_and_save(client, piece)
    write_sheet(client, piece)
    body = status(client, piece)
    assert [step["state"] for step in body["steps"]] == ["ready"] * 5
    return piece


def id_of(client: TestClient, uuid: str, midi: int, on_ms: int) -> int:
    body = notes(client, uuid)
    for note_id, key, on in zip(body["id"], body["key"], body["onMs"]):
        if key == midi - 21 and on == on_ms:
            return note_id
    raise AssertionError(f"no note {midi} at {on_ms} ms")


# --------------------------------------------------------------------------- the steps


def test_a_piece_with_no_notes_opens_on_the_audio_tab(client: TestClient, data_dir: Path) -> None:
    uuid = store.create("Empty", AudioSource.UPLOAD, "wav").uuid
    # An audio and no notes. (A part with neither is a new empty project: Source first, Phase 5.)
    clip = data_dir.parent / "clip.wav"
    wavfile.write(clip, 16_000, np.zeros(16_000, dtype=np.int16))
    store.replace_original(uuid, clip, "wav", keep_cuts=False)
    body = status(client, uuid)
    states = {step["step"]: (step["state"], step["enabled"]) for step in body["steps"]}
    assert states == {
        "source": ("ready", True),
        "audio": ("ready", True),
        "notes": ("missing", True),
        "hands": ("missing", False),
        "sheet": ("missing", False),
    }
    assert body["resume"] == "audio"
    assert body["by"]["sheet"]["reason"] == "Transcribe first."
    assert client.get("/pieces/nope/status").status_code == 404


def test_a_transcribed_piece_opens_on_the_notes_tab_and_asks_for_the_hands(
    client: TestClient, piece: str
) -> None:
    body = status(client, piece)
    assert body["by"]["notes"]["state"] == "ready"
    assert body["by"]["notes"]["details"]["noteCount"] == 37
    assert body["by"]["hands"]["state"] == "missing"
    assert body["by"]["hands"]["enabled"] is True
    assert body["by"]["sheet"] == {
        "step": "sheet",
        "state": "missing",
        "enabled": False,
        "reason": "Predict hands first.",
        "details": {},
    }
    assert body["resume"] == "notes"


def test_the_notes_travel_as_columns_with_their_revisions(client: TestClient, piece: str) -> None:
    body = notes(client, piece)
    assert body["revision"] == 1 and body["handsRevision"] == 0
    assert body["durationMs"] == 8000 and body["stale"] is False
    assert len(body["id"]) == len(body["key"]) == len(body["onMs"]) == len(body["lenMs"]) == 37
    assert body["hand"] == "-" * 37 and body["guessed"] == []
    assert body["onMs"][:3] == [0, 0, 250] and body["lenMs"][0] in (200, 900)


def test_predict_gives_one_hand_per_note_in_the_order_of_the_notes_and_writes_nothing(
    client: TestClient, piece: str
) -> None:
    before = pipeline.events_path(piece).read_bytes()
    base = notes(client, piece)
    response = client.post(f"/pieces/{piece}/hands/predict", json={"baseRevision": 1})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == base["id"]
    assert len(body["hand"]) == 37 and body["changed"] == 37
    for key, hand in zip(base["key"], body["hand"]):
        assert hand == ("r" if key + 21 >= 72 else "l")
    assert pipeline.events_path(piece).read_bytes() == before

    old = client.post(f"/pieces/{piece}/hands/predict", json={"baseRevision": 0})
    assert old.status_code == 409


def test_predict_as_a_job_reports_its_progress_and_gives_the_same_answer(
    client: TestClient, piece: str
) -> None:
    import time

    from aitu_backend.transcription import jobs

    started = client.post(f"/pieces/{piece}/hands/predict/job", json={"baseRevision": 1})
    assert started.status_code == 202, started.text
    job = jobs.get(started.json()["jobId"])
    assert job is not None
    deadline = time.monotonic() + 20
    while not job.finished and time.monotonic() < deadline:
        time.sleep(0.02)
    assert job.status == "done", job.error

    hands = [
        payload
        for name, payload in job.frames
        if name is None and payload.get("stage") == "two-hands"
    ]
    assert len(hands) >= 2, "the inference reports more than its end"
    assert [frame["current"] for frame in hands] == sorted(frame["current"] for frame in hands)
    assert hands[-1]["current"] == hands[-1]["total"] == 100

    done = job.summary  # what the `done` frame of the stream carries
    direct = client.post(f"/pieces/{piece}/hands/predict", json={"baseRevision": 1}).json()
    assert done["id"] == direct["id"] and done["hand"] == direct["hand"]
    assert done["changed"] == direct["changed"] == 37

    old = client.post(f"/pieces/{piece}/hands/predict/job", json={"baseRevision": 0})
    assert old.status_code == 409


def test_predict_leaves_a_note_it_cannot_place_without_a_hand(
    client: TestClient, data_dir: Path
) -> None:
    uuid = store.create("Short note", AudioSource.UPLOAD, "wav").uuid
    store.update(uuid, duration_seconds=DURATION)
    # 10 ms: shorter than one column of the piano sheet (40 ms), so the split cannot place it.
    short = NoteEvent(midi_note=60, start=3.11, end=3.12)
    events = sorted([*music(), short], key=lambda event: (event.start, event.midi_note))
    pipeline.save_note_events(uuid, events, DURATION, title="Short note")
    base = notes(client, uuid)
    answer = client.post(f"/pieces/{uuid}/hands/predict", json={"baseRevision": 1}).json()
    unplaced = [note_id for note_id, hand in zip(answer["id"], answer["hand"]) if hand == "-"]
    position = base["onMs"].index(3110)
    assert unplaced == [base["id"][position]]
    assert answer["unplaced"] == 1
    assert answer["hand"].count("r") + answer["hand"].count("l") == len(base["id"]) - 1


def test_a_note_the_sheet_cannot_place_does_not_keep_the_hands_from_being_ready(
    client: TestClient, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The user's rule of 2026-10-01: once the prediction is saved, the Hands step is ready, even
    when a note the split could not place has no hand. That note stays without one (red), the
    quick rule does not guess it on a later save, and the sheet paints the saved hands.
    """
    uuid = store.create("Short note", AudioSource.UPLOAD, "wav").uuid
    store.update(uuid, duration_seconds=DURATION)
    short = NoteEvent(midi_note=60, start=3.11, end=3.12)  # 10 ms: shorter than one column
    events = sorted([*music(), short], key=lambda event: (event.start, event.midi_note))
    pipeline.save_note_events(uuid, events, DURATION, title="Short note")
    short_id = notes(client, uuid)["id"][notes(client, uuid)["onMs"].index(3110)]

    predict_and_save(client, uuid)
    body = status(client, uuid)
    assert body["by"]["hands"]["state"] == "ready"
    assert body["by"]["hands"]["details"]["unplaced"] == 1
    assert body["by"]["sheet"]["enabled"]
    assert events_file.read_header(pipeline.events_path(uuid)).hands_notes_revision == 1

    # A later edit: the quick rule runs (the hands were saved as a whole) but leaves that note.
    current = notes(client, uuid)
    first = current["id"][0]
    patch(
        client,
        uuid,
        [
            {
                "op": "move",
                "id": first,
                "onMs": current["onMs"][0] + 10,
                "lenMs": current["lenMs"][0],
            }
        ],
    )
    after = notes(client, uuid)
    assert after["hand"][after["id"].index(short_id)] == "-"

    def no_inference(*args: object, **kwargs: object) -> None:
        raise AssertionError("the sheet must paint the saved hands, not run the inference")

    monkeypatch.setattr(pipeline, "impose_granularity_and_split", no_inference)
    split_cache.forget()
    pipeline.split_of(uuid)


def test_saved_hands_make_the_step_ready_and_the_sheet_uses_them_without_inference(
    client: TestClient, piece: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = predict_and_save(client, piece)
    assert saved["revision"] == 1 and saved["handsRevision"] == 1
    header = events_file.read_header(pipeline.events_path(piece))
    assert header.hands_notes_revision == 1

    body = status(client, piece)
    assert body["by"]["hands"]["state"] == "ready"
    assert body["by"]["hands"]["details"] == {
        "withoutHand": 0,
        "unplaced": 0,
        "guessed": 0,
        "saved": True,
    }
    assert body["by"]["sheet"]["state"] == "missing" and body["by"]["sheet"]["enabled"] is True

    def no_inference(*args, **kwargs):
        raise AssertionError("the hand inference ran although every note has a saved hand")

    monkeypatch.setattr(time_pipeline, "split_hands", no_inference)
    split_cache.forget()
    score = client.get(f"/time/{piece}/score", params={"anchorMs": 500})
    assert score.status_code == 200
    printed = score.json()["notes"]
    assert {note["hand"] for note in printed if note["row"] + 21 >= 72} == {"right"}
    assert {note["hand"] for note in printed if note["row"] + 21 < 60} == {"left"}


def test_writing_the_sheet_records_the_hands_revision(client: TestClient, piece: str) -> None:
    predict_and_save(client, piece)
    reading = write_sheet(client, piece)
    assert reading["handsRevision"] == 1
    reading = client.put(f"/time/{piece}/rhythm", json={**READING, "handsRevision": 99}).json()
    assert reading["handsRevision"] == 1, "the client's value is ignored"
    body = status(client, piece)
    assert body["by"]["sheet"]["state"] == "ready" and body["resume"] == "sheet"
    assert body["revisions"] == {
        "audio": 0,
        "notes": 1,
        "notesAudio": 0,
        "hands": 1,
        "handsNotes": 1,
        "sheetHands": 1,
    }


# --------------------------------------------------------------------------- plan section 8.3


def test_row_1_a_new_selected_region_makes_every_later_step_stale(
    client: TestClient, ready: str, tmp_path: Path
) -> None:
    with_audio(ready, tmp_path, DURATION)
    store.set_cuts(ready, [(100, 200)])
    body = status(client, ready)
    assert body["by"]["notes"]["state"] == "stale"
    assert body["by"]["hands"]["state"] == "stale" and body["by"]["hands"]["enabled"] is False
    assert body["by"]["sheet"]["state"] == "stale" and body["by"]["sheet"]["enabled"] is False
    assert body["resume"] == "audio"
    assert notes(client, ready)["stale"] is True
    refused = client.patch(
        f"/pieces/{ready}/notes",
        json={"baseRevision": 1, "ops": [{"op": "delete", "ids": [0]}]},
    )
    assert refused.status_code == 409


@needs_ffmpeg
def test_row_2_a_new_transcription_makes_the_hands_missing_and_keeps_the_old_sheet_in_history(
    client: TestClient, data_dir: Path, tmp_path: Path
) -> None:
    rate = 16_000
    tone = (0.3 * np.sin(2 * np.pi * 220 * np.arange(rate * 8) / rate) * 32767).astype(np.int16)
    source = tmp_path / "tone.wav"
    wavfile.write(source, rate, tone)
    with source.open("rb") as handle:
        uuid = ingest.ingest_file(handle, "tone.wav", AudioSource.UPLOAD).uuid

    class Stub:
        name = "stub"

        def transcribe(self, wav_path: Path) -> list[NoteEvent]:
            return music()

    pipeline.transcribe_audio(uuid, engine=Stub())
    predict_and_save(client, uuid)
    write_sheet(client, uuid)
    before = events_file.read_header(pipeline.events_path(uuid))
    assert (
        before.notes_revision,
        before.hands_revision,
        before.hands_notes_revision,
    ) == (1, 2, 1)

    pipeline.transcribe_audio(uuid, engine=Stub())
    after = events_file.read_header(pipeline.events_path(uuid))
    assert after.notes_revision == 2
    assert after.hands_revision == 3
    assert after.hands_notes_revision == 0
    body = status(client, uuid)
    assert body["by"]["notes"]["state"] == "ready"
    assert body["by"]["hands"]["state"] == "missing"
    # The old reading points at columns of the old notes, so it is not kept beside the new ones:
    # the Sheet tab asks for a new one, and the old one is in history (plan section 8.3).
    assert body["by"]["sheet"]["state"] == "missing"
    assert list(paths.part_history_dir(uuid).glob("v*/sheet.json"))


def test_row_3_a_moved_or_resized_rectangle_keeps_the_hands_and_makes_the_sheet_stale(
    client: TestClient, ready: str
) -> None:
    note_id = id_of(client, ready, 72, 0)
    result = patch(client, ready, [{"op": "move", "id": note_id, "onMs": 30, "lenMs": 150}])
    assert result["revision"] == 2 and result["handsRevision"] == 2
    assert result["sheetStale"] is True
    body = status(client, ready)
    assert body["by"]["hands"]["state"] == "ready"
    assert body["by"]["sheet"]["state"] == "stale" and body["by"]["sheet"]["enabled"] is True
    assert body["resume"] == "sheet"
    moved = notes(client, ready)
    index = moved["id"].index(note_id)
    assert (moved["onMs"][index], moved["lenMs"][index], moved["hand"][index]) == (
        30,
        150,
        "r",
    )


def test_row_4_an_added_rectangle_gets_a_guessed_hand_and_makes_the_sheet_stale(
    client: TestClient, ready: str
) -> None:
    result = patch(
        client,
        ready,
        [{"op": "add", "tempId": -1, "key": 40, "onMs": 2100, "lenMs": 250}],
    )
    [added] = result["added"]
    assert added["tempId"] == -1 and added["id"] == 37
    assert result["changed"]["id"] == [37] and result["changed"]["hand"] == "r"
    assert result["changed"]["guessed"] == [37]

    body = status(client, ready)
    assert body["by"]["hands"]["state"] == "ready"
    assert body["by"]["hands"]["details"]["guessed"] == 1
    assert body["by"]["sheet"]["state"] == "stale"
    assert notes(client, ready)["guessed"] == [37]

    confirmed = patch(client, ready, [{"op": "hand", "ids": [37], "hand": "r"}])
    assert confirmed["revision"] == result["revision"]
    assert notes(client, ready)["guessed"] == []


def test_row_4_without_saved_hands_an_added_rectangle_has_no_hand(
    client: TestClient, piece: str
) -> None:
    result = patch(
        client,
        piece,
        [{"op": "add", "tempId": -7, "key": 40, "onMs": 2100, "lenMs": 250}],
    )
    assert result["changed"]["hand"] == "-"
    assert status(client, piece)["by"]["hands"]["state"] == "missing"


def test_row_5_a_deleted_rectangle_keeps_the_hands_and_makes_the_sheet_stale(
    client: TestClient, ready: str
) -> None:
    note_id = id_of(client, ready, 73, 250)
    patch(client, ready, [{"op": "delete", "ids": [note_id]}])
    assert note_id not in notes(client, ready)["id"]
    body = status(client, ready)
    assert body["by"]["hands"]["state"] == "ready"
    assert body["by"]["sheet"]["state"] == "stale"

    patch(client, ready, [{"op": "restore", "ids": [note_id]}])
    back = notes(client, ready)
    assert back["hand"][back["id"].index(note_id)] == "r"


def test_row_6_a_hand_changed_on_the_hands_tab_makes_the_sheet_stale(
    client: TestClient, ready: str
) -> None:
    note_id = id_of(client, ready, 72, 0)
    result = patch(client, ready, [{"op": "hand", "ids": [note_id], "hand": "l"}])
    assert result["revision"] == 1, "a hand is not a notes change"
    assert result["handsRevision"] == 2
    body = status(client, ready)
    assert body["by"]["hands"]["state"] == "ready"
    assert body["by"]["sheet"]["state"] == "stale"


def test_row_7_a_hand_changed_on_the_sheet_tab_keeps_the_sheet_ready(
    client: TestClient, ready: str
) -> None:
    before = events_file.read_header(pipeline.events_path(ready)).hands_revision
    response = client.put(
        f"/time/{ready}/hands",
        json={
            "frameMs": 40,
            "notes": [{"startFrame": 0, "row": 72 - 21, "hand": "left"}],
        },
    )
    assert response.json() == {"assigned": 1, "unmatched": 0}
    after = events_file.read_header(pipeline.events_path(ready))
    assert after.hands_revision == before + 1
    body = status(client, ready)
    assert body["by"]["sheet"]["state"] == "ready"
    assert body["revisions"]["sheetHands"] == after.hands_revision
    moved = notes(client, ready)
    assert moved["hand"][moved["id"].index(id_of(client, ready, 72, 0))] == "l"


def test_a_sheet_tab_edit_does_not_make_a_stale_sheet_ready(client: TestClient, ready: str) -> None:
    patch(client, ready, [{"op": "delete", "ids": [id_of(client, ready, 73, 250)]}])
    client.put(
        f"/time/{ready}/hands",
        json={
            "frameMs": 40,
            "notes": [{"startFrame": 0, "row": 72 - 21, "hand": "left"}],
        },
    )
    assert status(client, ready)["by"]["sheet"]["state"] == "stale"


def test_saving_the_reading_then_taking_its_hidden_notes_off_keeps_it_ready(
    client: TestClient, ready: str
) -> None:
    """The Sheet tab saves the reading and then takes the hidden notes off the recording."""
    write_sheet(client, ready)
    response = client.put(
        f"/time/{ready}/removed",
        json={
            "frameMs": 40,
            "notes": [{"startFrame": 6, "row": 73 - 21}],
            "removed": True,
        },
    )
    assert response.json()["changed"] == 1
    assert status(client, ready)["by"]["sheet"]["state"] == "ready"


# --------------------------------------------------------------------------- the operations


def test_an_old_base_revision_is_refused_and_nothing_is_written(
    client: TestClient, ready: str
) -> None:
    before = pipeline.events_path(ready).read_bytes()
    stale = client.patch(
        f"/pieces/{ready}/notes",
        json={"baseRevision": 0, "ops": [{"op": "delete", "ids": [0]}]},
    )
    assert stale.status_code == 409 and "Reload" in stale.json()["detail"]
    hands = client.patch(
        f"/pieces/{ready}/notes",
        json={
            "baseRevision": 1,
            "baseHandsRevision": 0,
            "ops": [{"op": "delete", "ids": [0]}],
        },
    )
    assert hands.status_code == 409
    assert pipeline.events_path(ready).read_bytes() == before


@pytest.mark.parametrize(
    ("ops", "words"),
    [
        ([{"op": "move", "id": 999, "onMs": 0, "lenMs": 10}], "no note 999"),
        ([{"op": "move", "id": 0, "onMs": 7900, "lenMs": 500}], "after the end"),
        (
            [
                {"op": "add", "tempId": -1, "key": 10, "onMs": 100, "lenMs": 50},
                {"op": "add", "tempId": -1, "key": 11, "onMs": 100, "lenMs": 50},
            ],
            "used twice",
        ),
        ([{"op": "add", "tempId": -1, "key": 51, "onMs": 0, "lenMs": 50}], "same time"),
    ],
)
def test_an_operation_that_cannot_be_applied_is_refused_with_its_reason(
    client: TestClient, piece: str, ops: list[dict], words: str
) -> None:
    before = pipeline.events_path(piece).read_bytes()
    response = client.patch(f"/pieces/{piece}/notes", json={"baseRevision": 1, "ops": ops})
    assert response.status_code == 422
    assert words in response.json()["detail"]
    assert pipeline.events_path(piece).read_bytes() == before


def test_a_deleted_note_cannot_be_moved(client: TestClient, piece: str) -> None:
    patch(client, piece, [{"op": "delete", "ids": [0]}])
    response = client.patch(
        f"/pieces/{piece}/notes",
        json={
            "baseRevision": 2,
            "ops": [{"op": "move", "id": 0, "onMs": 0, "lenMs": 10}],
        },
    )
    assert response.status_code == 422 and "Restore it first" in response.json()["detail"]


def test_one_key_sounds_one_note_at_a_time(client: TestClient, piece: str) -> None:
    """A move that runs into the next onset of its key shortens the earlier note."""
    first = id_of(client, piece, 72, 0)  # 72 again at 1250 ms
    result = patch(client, piece, [{"op": "move", "id": first, "onMs": 1000, "lenMs": 600}])
    changed = result["changed"]
    assert changed["id"] == [first]
    assert (changed["onMs"], changed["lenMs"]) == ([1000], [250])


def test_operations_that_change_nothing_write_nothing(client: TestClient, ready: str) -> None:
    before = pipeline.events_path(ready).read_bytes()
    note_id = id_of(client, ready, 72, 0)
    result = patch(client, ready, [{"op": "hand", "ids": [note_id], "hand": "r"}])
    assert result["saved"] is False and result["handsRevision"] == 1
    assert pipeline.events_path(ready).read_bytes() == before


def test_predict_keeps_the_hands_the_user_set_unless_asked_to_replace_them(
    client: TestClient, ready: str
) -> None:
    note_id = id_of(client, ready, 72, 0)
    patch(client, ready, [{"op": "hand", "ids": [note_id], "hand": "l"}])
    kept = client.post(f"/pieces/{ready}/hands/predict", json={"baseRevision": 1}).json()
    assert kept["hand"][kept["id"].index(note_id)] == "l" and kept["changed"] == 0
    fresh = client.post(
        f"/pieces/{ready}/hands/predict", json={"baseRevision": 1, "replace": True}
    ).json()
    assert fresh["hand"][fresh["id"].index(note_id)] == "r" and fresh["changed"] == 1


# --------------------------------------------------------------------------- old pieces


@pytest.fixture()
def old_piece(data_dir: Path) -> str:
    """A piece saved before implementation 08: no ids, no header, one pinned hand, and a sheet."""
    uuid = store.create("Old", AudioSource.UPLOAD, "wav").uuid
    rows = [
        {
            "midiNote": event.midi_note,
            "start": event.start,
            "end": event.end,
            "velocity": 64,
            **({"hand": "left"} if index == 5 else {}),
        }
        for index, event in enumerate(music())
    ]
    path = pipeline.events_path(uuid)
    # An `events.json` of the old layout, read as it is (pmn/events_file.py).
    path.write_text(
        json.dumps({"schemaVersion": "1.0", "durationSeconds": DURATION, "events": rows})
    )
    pipeline.rhythm_path(uuid).write_text(json.dumps(READING))
    return uuid


def test_an_old_piece_with_a_sheet_keeps_opening_on_the_sheet(
    client: TestClient, old_piece: str
) -> None:
    body = status(client, old_piece)
    assert body["by"]["hands"]["state"] == "ready"
    assert body["by"]["hands"]["details"]["saved"] is False
    assert "Predict hands" in body["by"]["hands"]["reason"]
    assert body["by"]["sheet"]["state"] == "ready"
    assert body["resume"] == "sheet"


def test_the_first_hand_change_on_the_sheet_saves_every_hand_as_the_sheet_draws_it(
    client: TestClient, old_piece: str
) -> None:
    drawn = pipeline.split_of(old_piece, 40.0)
    response = client.put(
        f"/time/{old_piece}/hands",
        json={
            "frameMs": 40,
            "notes": [{"startFrame": 0, "row": 72 - 21, "hand": "left"}],
        },
    )
    assert response.json() == {"assigned": 1, "unmatched": 0}

    stored = pipeline.load_note_events(old_piece)
    assert stored is not None and saved_hands.hands_complete(stored.events)
    assert stored.header.hands_notes_revision == 1
    after = pipeline.split_of(old_piece, 40.0)
    moved_cells = (after.right.grid != drawn.right.grid).sum()
    assert moved_cells == 5, "only the one note (an onset and four sustain cells) changed hand"
    assert np.array_equal(after.right.grid + after.left.grid, drawn.right.grid + drawn.left.grid)
    assert status(client, old_piece)["by"]["sheet"]["state"] == "ready"


# --------------------------------------------------------------------------- the pieces


def test_the_saved_hands_paint_the_same_cells_as_the_inference() -> None:
    events = [event.model_copy(update={"id": index}) for index, event in enumerate(music())]
    events[5] = events[5].model_copy(update={"hand": "left"})
    inferred = time_pipeline.impose_granularity_and_split(events, DURATION, frame_ms=40.0)
    hands = saved_hands.hands_of_split(inferred, events)
    saved = [event.model_copy(update={"hand": hands[index]}) for index, event in enumerate(events)]
    painted = saved_hands.split_with_saved_hands(saved, DURATION, frame_ms=40.0)
    assert np.array_equal(painted.right.grid, inferred.right.grid)
    assert np.array_equal(painted.left.grid, inferred.left.grid)


def test_the_build_records_the_id_of_the_note_that_owns_each_onset_cell() -> None:
    events = [
        NoteEvent(id=4, midi_note=60, start=0.105, end=0.5),
        NoteEvent(id=3, midi_note=60, start=0.101, end=0.3),
        NoteEvent(id=9, midi_note=64, start=0.52, end=0.9),
    ]
    build = events_to_time_matrix(events, 1.0, frame_ms=40.0, leakage=None, artifacts=None)
    assert build.event_ids == {(3, 39): 3, (13, 43): 9}


def test_the_quick_rule_copies_the_closest_pitch_around_the_note_then_uses_middle_c() -> None:
    reference = [
        NoteEvent(midi_note=40, start=1.0, end=4.0, hand="left"),
        NoteEvent(midi_note=76, start=1.0, end=1.2, hand="right"),
    ]
    assert saved_hands.quick_hand(45, 1.1, reference) == "left"
    assert saved_hands.quick_hand(64, 1.1, reference) == "right"
    assert saved_hands.quick_hand(64, 3.0, reference) == "left", "only the bass is around"
    assert saved_hands.quick_hand(59, 9.0, reference) == "left"
    assert saved_hands.quick_hand(60, 9.0, reference) == "right"
