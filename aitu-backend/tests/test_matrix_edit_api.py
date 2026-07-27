"""Validator-backed Matrix-tab editing and persistence."""

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from aitu_backend.audio import store
from aitu_backend.main import create_app
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep
from aitu_backend.schemas.metadata import AudioSource
from aitu_backend.storage import paths
from aitu_backend.storage.matrix_store import save_matrix
from aitu_backend.transcription import pipeline

DO4 = note_to_row("Do-4")
RE4 = note_to_row("Re-4")


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return TestClient(create_app())


def seed(client: TestClient) -> str:
    del client
    grid = np.zeros((KEY_COUNT, 8), dtype=np.int8)
    grid[DO4, 0:3] = [1, -1, -1]
    matrix = PianoMatrix.from_dense(
        grid,
        granularity=Granularity.FUSA,
        tempo_bpm=60,
        processing_step=MatrixProcessingStep.RAW,
    )
    entry = store.create("Editable scale", AudioSource.UPLOAD, "wav")
    save_matrix(pipeline.raw_path(entry.uuid), matrix.to_coo_payload())
    return entry.uuid


def test_preview_adds_an_onset_without_touching_disk(client: TestClient) -> None:
    uuid = seed(client)
    response = client.post(
        f"/matrix/{uuid}/edit",
        json={
            "tempoBpm": 60,
            "granularity": "fusa",
            "edits": [{"frame": 4, "key": RE4, "value": 1}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["persisted"] is False
    assert body["envelope"]["denseMatrix"][4][RE4] == 1

    unchanged = client.get(
        f"/matrix/{uuid}",
        params={"granularity": "fusa", "tempo_bpm": 60, "sparse": False},
    ).json()
    assert unchanged["denseMatrix"][4][RE4] == 0


def test_orphan_sustain_is_rejected_with_a_visible_reason(client: TestClient) -> None:
    uuid = seed(client)
    response = client.post(
        f"/matrix/{uuid}/edit",
        json={
            "tempoBpm": 60,
            "granularity": "fusa",
            "edits": [{"frame": 4, "key": RE4, "value": -1}],
        },
    )

    assert response.status_code == 422
    assert "nothing is sounding" in response.json()["detail"]


def test_deleting_an_onset_removes_its_sustain_chain(client: TestClient) -> None:
    uuid = seed(client)
    body = client.post(
        f"/matrix/{uuid}/edit",
        json={
            "tempoBpm": 60,
            "granularity": "fusa",
            "edits": [{"frame": 0, "key": DO4, "value": 0}],
        },
    ).json()

    assert [frame[DO4] for frame in body["envelope"]["denseMatrix"][:3]] == [0, 0, 0]


def test_save_replaces_working_raw_and_keeps_the_parent(client: TestClient) -> None:
    uuid = seed(client)
    response = client.post(
        f"/matrix/{uuid}/edit",
        json={
            "tempoBpm": 60,
            "granularity": "semicorchea",
            "edits": [{"frame": 1, "key": RE4, "value": 1}],
            "persist": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["persisted"] is True
    assert pipeline.edit_parent_path(uuid).is_file()

    reloaded = client.get(
        f"/matrix/{uuid}",
        params={"granularity": "semicorchea", "tempo_bpm": 60, "sparse": False},
    ).json()
    assert reloaded["denseMatrix"][1][RE4] == 1


def test_edit_coordinates_and_values_are_validated(client: TestClient) -> None:
    uuid = seed(client)
    bad_key = client.post(
        f"/matrix/{uuid}/edit",
        json={"edits": [{"frame": 0, "key": 88, "value": 1}]},
    )
    bad_value = client.post(
        f"/matrix/{uuid}/edit",
        json={"edits": [{"frame": 0, "key": 0, "value": 2}]},
    )

    assert bad_key.status_code == 422
    assert bad_value.status_code == 422
