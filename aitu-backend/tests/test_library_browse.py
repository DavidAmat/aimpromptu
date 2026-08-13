"""Library browse: search real names, rhythm flags, and refusing old version folders."""

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from aitu_backend.audio import store
from aitu_backend.main import create_app
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import MatrixProcessingStep
from aitu_backend.schemas.metadata import (
    AudioReference,
    AudioSource,
    VersionHistoryEntry,
)
from aitu_backend.schemas.rhythm import SavedRhythm
from aitu_backend.schemas.time_matrix import FigureName
from aitu_backend.storage import paths, promotion, repository
from aitu_backend.transcription import pipeline

DO4 = note_to_row("Do-4")


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


@pytest.fixture()
def client(temp_store: Path) -> TestClient:
    return TestClient(create_app())


def matrix(frame_ms: float = 40, frames: int = 8) -> PianoMatrix:
    grid = np.zeros((KEY_COUNT, frames), dtype=np.int8)
    grid[DO4, 0] = 1
    grid[DO4, 1] = -1
    return PianoMatrix.time_based(
        grid, frame_ms=frame_ms, processing_step=MatrixProcessingStep.CLEAN
    )


def a_reading() -> SavedRhythm:
    return SavedRhythm(hand="right", frame_ms=40, anchor_figure=FigureName.NEGRA, anchor_ms=320)


def test_library_search_matches_promotion_names(temp_store: Path) -> None:
    repository.save_version("Avicii", "Levels", matrix())
    promotion.promote("avicii", "levels", "v1_f40", promotion_name="Levels (Chill) - Avicii")

    found = promotion.list_library_tracks(search="chill")
    assert [track.track_name for track in found] == ["Levels"]
    assert promotion.list_library_tracks(search="avicii")[0].track_name == "Levels"
    assert promotion.list_library_tracks(search="nobody") == []


def test_tag_chips_are_the_union_of_library_tags(temp_store: Path) -> None:
    repository.save_version("Avicii", "Levels", matrix())
    repository.save_version("Claude Debussy", "Clair de Lune", matrix())
    promotion.promote("avicii", "levels", "v1_f40")
    promotion.promote("claude-debussy", "clair-de-lune", "v1_f40")
    promotion.set_tags("avicii", "levels", ["edm", "easy"])
    promotion.set_tags("claude-debussy", "clair-de-lune", ["classical"])

    assert promotion.list_tags() == ["classical", "easy", "edm"]
    tagged = promotion.list_library_tracks(tag="edm", search="levels")
    assert [track.track_name for track in tagged] == ["Levels"]


def test_old_granularity_folders_are_omitted_from_the_playground_list(client: TestClient) -> None:
    """A leftover ``v2_gn`` folder is refused, not guessed into a wall-clock version."""
    repository.save_version("Avicii", "Levels", matrix())
    track = repository.read_track("avicii", "levels")
    leftover = VersionHistoryEntry(
        folder="v2_gn",
        comment="old scheme",
        frame_ms=40,
        matrix_processing_step=MatrixProcessingStep.CLEAN,
    )
    repository.write_track(track.model_copy(update={"versions": [*track.versions, leftover]}))
    leftover_dir = paths.playground_track_dir("avicii", "levels") / "v2_gn"
    leftover_dir.mkdir()
    (leftover_dir / "metadata.json").write_text(
        '{"version": 2, "frameMs": 40, "matrixProcessingStep": "clean"}\n',
        encoding="utf-8",
    )

    listed = client.get("/library/playground").json()
    assert [entry["folder"] for entry in listed[0]["versions"]] == ["v1_f40"]
    assert client.get("/library/playground/avicii/levels/v2_gn").status_code == 422


def test_a_saved_rhythm_is_flagged_on_the_library_list(client: TestClient) -> None:
    uuid = store.create("Levels", AudioSource.UPLOAD, "wav").uuid
    repository.save_version("Avicii", "Levels", matrix(), audio=AudioReference(audio_uuid=uuid))
    promotion.promote("avicii", "levels", "v1_f40")

    before = client.get("/library/tracks").json()[0]
    assert before["hasSavedRhythm"] is False
    assert before["promotions"][0]["hasSavedRhythm"] is False
    assert before["needsRederivation"] is None

    pipeline.save_rhythm(uuid, a_reading())
    after = client.get("/library/tracks").json()[0]
    assert after["hasSavedRhythm"] is True
    assert after["promotions"][0]["hasSavedRhythm"] is True
    assert after["promotions"][0]["audioUuid"] == uuid


def test_a_flagged_piece_is_marked_and_still_listed(client: TestClient) -> None:
    uuid = store.create("Levels", AudioSource.UPLOAD, "wav").uuid
    repository.save_version("Avicii", "Levels", matrix(), audio=AudioReference(audio_uuid=uuid))
    promotion.promote("avicii", "levels", "v1_f40")
    pipeline.mark_needs_rederivation(uuid, "Run transcription again.")

    row = client.get("/library/tracks").json()[0]
    assert row["needsRederivation"] == "Run transcription again."
    playground = client.get("/library/playground").json()[0]
    assert playground["needsRederivation"] == "Run transcription again."
    assert playground["versions"][0]["needsRederivation"] == "Run transcription again."


def test_tags_and_promotion_search_over_http(client: TestClient) -> None:
    client.post(
        "/library/playground",
        json={
            "artistName": "Avicii",
            "trackName": "Levels",
            "matrix": matrix().to_envelope().model_dump(by_alias=True, mode="json"),
        },
    )
    client.post(
        "/library/promote",
        json={
            "artistSlug": "avicii",
            "trackSlug": "levels",
            "versionFolder": "v1_f40",
            "promotionName": "Levels (Chill) - Avicii",
        },
    )
    client.post(
        "/library/tags",
        json={"artistSlug": "avicii", "trackSlug": "levels", "tags": ["edm", "easy"]},
    )

    assert client.get("/library/tags").json() == ["easy", "edm"]
    found = client.get("/library/tracks", params={"search": "chill", "tag": "edm"}).json()
    assert [row["trackName"] for row in found] == ["Levels"]
    renamed = client.patch(
        "/library/playground/avicii/levels",
        json={"trackName": "Levels (live)"},
    ).json()
    assert renamed["trackName"] == "Levels (live)"
    assert renamed["trackSlug"] == "levels"
    assert client.get("/library/playground/avicii/levels").json()["trackName"] == "Levels (live)"
