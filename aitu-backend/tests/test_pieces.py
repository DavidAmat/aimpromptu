"""The piece API, the revisions and the hand split as a step (implementation 08, Phase 5).

One test per row of the staleness table of the plan's section 8.3, then the operations of the
piano roll visualization, the old pieces that have no saved hands, and the quick rule for an added
note. **Predict hands** and the old sheet's ``stale`` state went with the vexflow-v2 sheet
(implementation 03, Phase 10): the hands are saved here as ``hand`` operations, and a stored sheet
is laid again on changed notes, so the Sheet step stays ready.
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
from aitu_backend.schemas.rhythm import SavedRhythm
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


def save_hands(client: TestClient, uuid: str) -> dict:
    """Every note given its hand (the melody from Do 5 up is the right hand), as one save."""
    base = notes(client, uuid)
    right = [i for i, key in zip(base["id"], base["key"]) if key + 21 >= 72]
    left = [i for i, key in zip(base["id"], base["key"]) if key + 21 < 72]
    return patch(
        client,
        uuid,
        [
            {"op": "hand", "ids": right, "hand": "r"},
            {"op": "hand", "ids": left, "hand": "l"},
        ],
    )


def write_sheet(client: TestClient, uuid: str) -> None:
    """The ``sheet.json`` the vexflow-v2 sheet saved: a part that has one counts as written."""
    pipeline.save_rhythm(uuid, SavedRhythm.model_validate(READING))


@pytest.fixture()
def ready(client: TestClient, piece: str) -> str:
    """The piece with its hands saved, and a sheet written: every step ready."""
    save_hands(client, piece)
    write_sheet(client, piece)
    body = status(client, piece)
    assert [step["state"] for step in body["steps"]] == ["ready"] * 4
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
        "sheet": ("missing", False),
    }
    assert body["resume"] == "audio"
    assert body["by"]["sheet"]["reason"] == "Transcribe first."
    assert client.get("/pieces/nope/status").status_code == 404


def test_a_transcribed_piece_opens_on_the_notes_tab_and_its_sheet_step_is_open(
    client: TestClient, piece: str
) -> None:
    """No Hands step since implementation 03, Phase 5: the Sheet step opens once the notes are ready."""
    body = status(client, piece)
    assert [step["step"] for step in body["steps"]] == ["source", "audio", "notes", "sheet"]
    assert body["by"]["notes"]["state"] == "ready"
    assert body["by"]["notes"]["details"]["noteCount"] == 37
    assert body["by"]["sheet"] == {
        "step": "sheet",
        "state": "missing",
        "enabled": True,
        "reason": "Not written yet.",
        "details": {"newSheet": False},
    }
    assert body["resume"] == "notes"


def test_the_notes_travel_as_columns_with_their_revisions(client: TestClient, piece: str) -> None:
    body = notes(client, piece)
    assert body["revision"] == 1 and body["handsRevision"] == 0
    assert body["durationMs"] == 8000 and body["stale"] is False
    assert len(body["id"]) == len(body["key"]) == len(body["onMs"]) == len(body["lenMs"]) == 37
    assert body["hand"] == "-" * 37 and body["guessed"] == []
    assert body["onMs"][:3] == [0, 0, 250] and body["lenMs"][0] in (200, 900)


def test_saved_hands_make_the_step_ready_and_the_sheet_uses_them_without_inference(
    client: TestClient, piece: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = save_hands(client, piece)
    assert saved["revision"] == 1 and saved["handsRevision"] == 1
    header = events_file.read_header(pipeline.events_path(piece))
    assert header.hands_notes_revision == 1

    body = status(client, piece)
    assert body["by"]["sheet"]["state"] == "missing" and body["by"]["sheet"]["enabled"] is True

    def no_inference(*args, **kwargs):
        raise AssertionError("the hand inference ran although every note has a saved hand")

    monkeypatch.setattr(time_pipeline, "split_hands", no_inference)
    split_cache.forget()
    split = pipeline.split_of(piece)
    assert all(row + 21 >= 72 for row in split.right.active_rows())
    assert all(row + 21 < 72 for row in split.left.active_rows())


def test_an_old_sheet_makes_the_sheet_step_ready(client: TestClient, piece: str) -> None:
    save_hands(client, piece)
    write_sheet(client, piece)
    body = status(client, piece)
    assert body["by"]["sheet"]["state"] == "ready" and body["resume"] == "sheet"
    assert body["revisions"] == {
        "audio": 0,
        "notes": 1,
        "notesAudio": 0,
        "hands": 1,
        "handsNotes": 1,
    }


# --------------------------------------------------------------------------- plan section 8.3


def test_row_1_a_new_selected_region_makes_every_later_step_stale(
    client: TestClient, ready: str, tmp_path: Path
) -> None:
    with_audio(ready, tmp_path, DURATION)
    store.set_cuts(ready, [(100, 200)])
    body = status(client, ready)
    assert body["by"]["notes"]["state"] == "stale"
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
    save_hands(client, uuid)
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
    # The old reading points at columns of the old notes, so it is not kept beside the new ones:
    # the Sheet tab asks for a new one, and the old one is in history (plan section 8.3).
    assert body["by"]["sheet"]["state"] == "missing"
    assert list(paths.part_history_dir(uuid).glob("v*/sheet.json"))


def test_row_3_a_moved_or_resized_rectangle_keeps_the_hands_and_the_sheet(
    client: TestClient, ready: str
) -> None:
    note_id = id_of(client, ready, 72, 0)
    result = patch(client, ready, [{"op": "move", "id": note_id, "onMs": 30, "lenMs": 150}])
    assert result["revision"] == 2 and result["handsRevision"] == 2
    assert "sheetStale" not in result
    body = status(client, ready)
    assert body["by"]["sheet"]["state"] == "ready" and body["by"]["sheet"]["enabled"] is True
    assert body["resume"] == "sheet"
    moved = notes(client, ready)
    index = moved["id"].index(note_id)
    assert (moved["onMs"][index], moved["lenMs"][index], moved["hand"][index]) == (
        30,
        150,
        "r",
    )


def test_row_4_an_added_rectangle_gets_a_guessed_hand_and_keeps_the_sheet(
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
    assert body["by"]["sheet"]["state"] == "ready"
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
    assert "hands" not in status(client, piece)["by"]


def test_row_5_a_deleted_rectangle_keeps_the_hands_and_the_sheet(
    client: TestClient, ready: str
) -> None:
    note_id = id_of(client, ready, 73, 250)
    patch(client, ready, [{"op": "delete", "ids": [note_id]}])
    assert note_id not in notes(client, ready)["id"]
    body = status(client, ready)
    assert body["by"]["sheet"]["state"] == "ready"

    patch(client, ready, [{"op": "restore", "ids": [note_id]}])
    back = notes(client, ready)
    assert back["hand"][back["id"].index(note_id)] == "r"


def test_row_6_a_hand_changed_on_the_notes_keeps_the_sheet(client: TestClient, ready: str) -> None:
    note_id = id_of(client, ready, 72, 0)
    result = patch(client, ready, [{"op": "hand", "ids": [note_id], "hand": "l"}])
    assert result["revision"] == 1, "a hand is not a notes change"
    assert result["handsRevision"] == 2
    body = status(client, ready)
    assert body["by"]["sheet"]["state"] == "ready"


def test_row_7_a_hand_changed_on_the_sheet_tab_keeps_the_sheet_ready(
    client: TestClient, ready: str
) -> None:
    before = events_file.read_header(pipeline.events_path(ready)).hands_revision
    response = client.post(f"/sheet/{ready}/hands", json={"notes": ["0:72"], "hand": "left"})
    assert response.status_code == 200, response.text
    assert (response.json()["moved"], response.json()["unmatched"]) == (1, 0)
    after = events_file.read_header(pipeline.events_path(ready))
    assert after.hands_revision == before + 1
    body = status(client, ready)
    assert body["by"]["sheet"]["state"] == "ready"
    moved = notes(client, ready)
    assert moved["hand"][moved["id"].index(id_of(client, ready, 72, 0))] == "l"


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
    assert body["by"]["sheet"]["state"] == "ready"
    assert body["resume"] == "sheet"


def test_the_first_hand_change_on_the_sheet_saves_every_hand_as_the_sheet_draws_it(
    client: TestClient, old_piece: str
) -> None:
    drawn = pipeline.split_of(old_piece, 40.0)
    response = client.post(f"/sheet/{old_piece}/hands", json={"notes": ["0:72"], "hand": "left"})
    assert response.status_code == 200, response.text
    assert (response.json()["moved"], response.json()["unmatched"]) == (1, 0)

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
