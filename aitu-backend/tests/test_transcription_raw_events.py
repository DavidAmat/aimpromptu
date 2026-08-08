"""`GET /matrix/{id}/events` — the transcription in seconds, served verbatim.

This route is the only one in the API that is *upstream* of the grid, and that is
the whole reason it exists: every other answer is derived from these numbers, so
when one of them looks wrong this is what it gets compared against. What is
guarded here is that nothing is snapped, rounded or re-ordered on the way out.

Until P4.2 this file also guarded the ``raw-granularity.txt`` sidecar, which
recorded which granularity a stored ``raw.npz`` had been written at. Neither the
grid nor the sidecar is stored any more: a column is 40 ms of wall clock (D-01),
so there is no granularity to record, and the grid is a function of the file this
route serves.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aitu_backend.audio import store
from aitu_backend.main import create_app
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return TestClient(create_app())


def seeded_audio() -> str:
    """An audio entry with nothing transcribed yet."""
    return store.create("Seeded", AudioSource.UPLOAD, "wav").uuid


def test_the_events_route_returns_them_verbatim(client: TestClient) -> None:
    uuid = seeded_audio()
    events = [
        NoteEvent(midi_note=60, start=0.2501, end=0.7502, velocity=71),
        NoteEvent(midi_note=64, start=0.2503, end=0.9004, velocity=64),
    ]
    pipeline.save_note_events(uuid, events, duration_seconds=2.0, title="Two notes")

    response = client.get(f"/matrix/{uuid}/events")

    assert response.status_code == 200
    body = response.json()
    assert body["audioUuid"] == uuid
    assert body["title"] == "Two notes"
    assert body["durationSeconds"] == pytest.approx(2.0)
    # Sub-millisecond differences survive: 0.2501 and 0.2503 are two attacks,
    # and telling them apart is the point of serving seconds instead of columns.
    assert [event["start"] for event in body["events"]] == [0.2501, 0.2503]
    assert [event["midiNote"] for event in body["events"]] == [60, 64]
    assert [event["velocity"] for event in body["events"]] == [71, 64]


def test_a_note_too_short_to_have_been_played_is_flagged_not_hidden(client: TestClient) -> None:
    """The filter has to be visible here, or it cannot be checked.

    A phantom Fa-1 under a played Fa-2/Fa-3 octave never reaches the grid, but it
    is still in ``events.json`` because that file is the engine's own output. The
    route says which notes the pipeline refused and why.
    """
    uuid = seeded_audio()
    pipeline.save_note_events(
        uuid,
        [
            NoteEvent(midi_note=29, start=11.0240, end=11.0297, velocity=72),  # 5.7 ms
            NoteEvent(midi_note=41, start=11.0243, end=11.4800, velocity=78),
            NoteEvent(midi_note=53, start=11.0251, end=11.4900, velocity=76),
        ],
        duration_seconds=13.0,
    )

    body = client.get(f"/matrix/{uuid}/events").json()

    assert body["artifactCount"] == 1
    assert body["octavePhantomCount"] == 1
    assert len(body["events"]) == 3  # nothing was removed from the answer
    flagged = [event for event in body["events"] if event["artifact"]]
    assert [event["midiNote"] for event in flagged] == [29]
    assert flagged[0]["octaveBelow"] == 12


def test_the_events_route_is_a_409_when_there_are_none(client: TestClient) -> None:
    uuid = seeded_audio()
    response = client.get(f"/matrix/{uuid}/events")
    assert response.status_code == 409
    assert "no stored note events" in response.json()["detail"]


def test_the_events_route_is_a_404_for_an_unknown_audio(client: TestClient) -> None:
    assert client.get("/matrix/not-an-audio/events").status_code == 404


def test_the_stored_file_is_the_only_thing_the_pipeline_writes(client: TestClient) -> None:
    """P4.2's whole claim, in one assertion.

    A matrix on disk could disagree with what the screen shows, because the screen
    rebuilds it from these events on every request. So there is no matrix on disk.
    """
    del client
    uuid = seeded_audio()
    pipeline.save_note_events(
        uuid,
        [NoteEvent(midi_note=60, start=0.0, end=1.0)],
        duration_seconds=2.0,
    )

    folder = pipeline.matrices_dir(uuid)
    assert [path.name for path in sorted(folder.iterdir())] == ["events.json"]
    assert pipeline.has_events(uuid)
