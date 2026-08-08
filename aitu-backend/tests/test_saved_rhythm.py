"""The reader's own decisions, saved with the piece and read back (P7.10, D-17, D-19, D-34).

Everything else about a score is derived from `events.json` on each request, so it can be thrown
away and rebuilt. What is stored here cannot be: nothing in a recording says which pile of gaps is
the beat, or where a phrase restarts. These tests pin that it survives a round trip, that it is one
per piece, and that a new transcription throws it away rather than pointing it at different notes.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aitu_backend.main import create_app
from aitu_backend.schemas.rhythm import KeyChange, SavedRhythm, SpeedChange
from aitu_backend.schemas.time_matrix import BeamBreak, FigureName, FigureOverride
from aitu_backend.storage import paths
from aitu_backend.transcription import pipeline
from aitu_backend.transcription.engine import NoteEvent


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


@pytest.fixture()
def client(temp_store: Path) -> TestClient:
    return TestClient(create_app())


def transcribed(uuid_alias: str = "Piece") -> str:
    """An audio with recorded notes but no matrices, which is the whole stored form now."""
    from aitu_backend.audio import store
    from aitu_backend.schemas.metadata import AudioSource

    entry = store.create(uuid_alias, AudioSource.UPLOAD, "wav")
    pipeline.save_note_events(
        entry.uuid,
        [
            NoteEvent(midi_note=60 + index % 5, start=index * 0.32, end=index * 0.32 + 0.2)
            for index in range(8)
        ],
        duration_seconds=3.0,
        title=uuid_alias,
    )
    return entry.uuid


def a_reading(anchor_ms: float = 320.0) -> SavedRhythm:
    return SavedRhythm(
        hand="right",
        frame_ms=40,
        anchor_figure=FigureName.NEGRA,
        anchor_ms=anchor_ms,
        speed_changes=[SpeedChange(start_frame=144, anchor_ms=674.0)],
        overrides=[
            FigureOverride(hand="right", row=39, start_frame=8, figure=FigureName.SEMICORCHEA)
        ],
        beam_breaks=[BeamBreak(hand="left", start_frame=24)],
        key_signature="Bb",
        key_changes=[
            KeyChange(from_column=40, key_signature="D"),
            KeyChange(from_column=80, key_signature="Bb"),
        ],
    )


# ------------------------------------------------------------------------------- the round trip


def test_a_reading_comes_back_exactly_as_it_was_saved(client: TestClient) -> None:
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    read = client.get(f"/time/{uuid}/rhythm").json()

    assert read["anchorFigure"] == "negra"
    assert read["anchorMs"] == 320.0
    assert read["frameMs"] == 40
    assert read["keySignature"] == "Bb"
    assert read["keyChanges"] == [
        {"fromColumn": 40, "keySignature": "D"},
        {"fromColumn": 80, "keySignature": "Bb"},
    ]
    assert read["speedChanges"] == [{"startFrame": 144, "anchorMs": 674.0}]
    assert read["overrides"] == [
        {"hand": "right", "row": 39, "startFrame": 8, "figure": "semicorchea"}
    ]
    assert read["beamBreaks"] == [{"hand": "left", "startFrame": 24}]


def test_a_piece_with_no_saved_reading_says_so_rather_than_inventing_one(
    client: TestClient,
) -> None:
    """The screen starts from the plot when it gets this, which is the right blank state."""
    uuid = transcribed()
    response = client.get(f"/time/{uuid}/rhythm")
    assert response.status_code == 404
    assert "Name a gap" in response.json()["detail"]


def test_saving_twice_replaces_rather_than_accumulating(client: TestClient) -> None:
    """A rhythm is a decision, not a version. What a reader wants back is the last one."""
    uuid = transcribed()
    client.put(f"/time/{uuid}/rhythm", json=a_reading(320.0).model_dump(by_alias=True, mode="json"))
    client.put(f"/time/{uuid}/rhythm", json=a_reading(337.0).model_dump(by_alias=True, mode="json"))

    assert client.get(f"/time/{uuid}/rhythm").json()["anchorMs"] == 337.0
    assert len(list(pipeline.matrices_dir(uuid).glob("rhythm*.json"))) == 1


def test_a_reading_can_be_forgotten(client: TestClient) -> None:
    uuid = transcribed()
    client.put(f"/time/{uuid}/rhythm", json=a_reading().model_dump(by_alias=True, mode="json"))
    assert client.delete(f"/time/{uuid}/rhythm").status_code == 204
    assert client.get(f"/time/{uuid}/rhythm").status_code == 404


# ------------------------------------------------------------------------------- the guards


def test_a_rhythm_for_an_unknown_audio_is_a_404(client: TestClient) -> None:
    assert client.get("/time/nope/rhythm").status_code == 404
    assert (
        client.put("/time/nope/rhythm", json=a_reading().model_dump(by_alias=True, mode="json"))
    ).status_code == 404


def test_a_rhythm_cannot_be_saved_for_a_piece_that_was_never_transcribed(
    client: TestClient,
) -> None:
    """There would be nothing for the column numbers in it to refer to."""
    from aitu_backend.audio import store
    from aitu_backend.schemas.metadata import AudioSource

    entry = store.create("Silent", AudioSource.UPLOAD, "wav")
    response = client.put(
        f"/time/{entry.uuid}/rhythm", json=a_reading().model_dump(by_alias=True, mode="json")
    )
    assert response.status_code == 409
    assert "not been transcribed" in response.json()["detail"]


def test_transcribing_again_throws_the_reading_away(temp_store: Path) -> None:
    """The columns in a saved reading describe the notes that were there before.

    A new transcription is a different set of notes, so keeping the numbers would point them at
    music nobody chose. Better to ask the reader to name the gap again than to show them a reading
    that is quietly about something else.
    """
    uuid = transcribed()
    pipeline.save_rhythm(uuid, a_reading())
    assert pipeline.load_rhythm(uuid) is not None

    class OneNote:
        name = "stub"

        def transcribe(self, wav_path: Path) -> list[NoteEvent]:
            return [NoteEvent(midi_note=60, start=0.0, end=0.5)]

    from aitu_backend.audio import store

    entry = store.get(uuid)
    entry.directory.mkdir(parents=True, exist_ok=True)
    entry.normalized_path.write_bytes(b"")

    pipeline.transcribe_audio(uuid, engine=OneNote())
    assert pipeline.load_rhythm(uuid) is None


def test_a_file_written_by_an_older_shape_reads_as_nothing_saved(temp_store: Path) -> None:
    """Losing a reading is a nuisance; refusing to open the piece over it would be worse."""
    uuid = transcribed()
    pipeline.rhythm_path(uuid).parent.mkdir(parents=True, exist_ok=True)
    pipeline.rhythm_path(uuid).write_text('{"anchorFigure": "negra"}', encoding="utf-8")
    assert pipeline.load_rhythm(uuid) is None


def test_the_reading_describes_itself_for_a_log(temp_store: Path) -> None:
    text = a_reading().describe()
    assert "negra = 320 ms at 40 ms/col" in text
    assert "1 speed change(s)" in text
    assert "1 note(s) renamed" in text
    assert "1 beam break(s)" in text


def test_a_reading_saved_before_keys_existed_still_loads(client: TestClient) -> None:
    """A stored file with no `keySignature` is not a broken file.

    The field was added after readings were already on disk, and a piece read in C is exactly what
    those readings were drawn in, so the absent value and C mean the same thing.
    """
    uuid = transcribed()
    body = a_reading().model_dump(by_alias=True, mode="json")
    del body["keySignature"]
    del body["keyChanges"]

    assert client.put(f"/time/{uuid}/rhythm", json=body).status_code == 200
    read = client.get(f"/time/{uuid}/rhythm").json()

    assert read["keySignature"] is None
    assert read["keyChanges"] == []
    assert read["anchorMs"] == 320.0
