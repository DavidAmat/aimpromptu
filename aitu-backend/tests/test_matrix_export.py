"""Matrix JSON export and import — the round trip the Matrix tab depends on."""

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from aitu_backend.main import create_app
from aitu_backend.matrix.hands import split_hands
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import Granularity, MatrixProcessingStep
from aitu_backend.storage import paths
from aitu_backend.storage.matrix_store import save_matrix
from aitu_backend.transcription import pipeline

DO4, MI4, DO3 = note_to_row("Do-4"), note_to_row("Mi-4"), note_to_row("Do-3")


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


@pytest.fixture()
def client(temp_store: Path) -> TestClient:
    return TestClient(create_app())


def sample_matrix() -> PianoMatrix:
    """A low Do, a held Do-4 and a Mi-4 — one note per hand plus a sustain."""
    grid = np.zeros((KEY_COUNT, 6), dtype=np.int8)
    grid[DO3, 0] = 1
    grid[DO4, 1] = 1
    grid[DO4, 2] = -1
    grid[MI4, 4] = 1
    return PianoMatrix.from_dense(
        grid,
        granularity=Granularity.FUSA,
        tempo_bpm=72,
        processing_step=MatrixProcessingStep.RAW,
    )


def seed_audio(client: TestClient, matrix: PianoMatrix) -> str:
    """Put a matrix on disk as if it had been transcribed, and return its uuid."""
    from aitu_backend.audio import store
    from aitu_backend.schemas.metadata import AudioSource

    entry = store.create("Test piece", AudioSource.UPLOAD, "wav")
    save_matrix(pipeline.raw_path(entry.uuid), matrix.to_coo_payload())
    return entry.uuid


# ----------------------------------------------------------------- exporting


def test_sparse_export_is_a_download_with_a_readable_name(client: TestClient) -> None:
    uuid = seed_audio(client, sample_matrix())

    response = client.get(
        f"/matrix/{uuid}/export",
        params={"step": "clean", "granularity": "fusa", "tempo_bpm": 72},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    disposition = response.headers["content-disposition"]
    assert "test-piece_clean_fusa_sparse.json" in disposition

    payload = response.json()
    assert payload["sparse"] is True
    assert payload["matrix"]["format"] == "binary-coo"
    assert payload["granularity"] == "fusa"
    assert payload["matrixProcessingStep"] == "clean"
    assert payload["tempoBpm"] == 72


def test_dense_export_carries_headers_and_timestamps(client: TestClient) -> None:
    """The dense form is the human-readable one, so it must be readable."""
    uuid = seed_audio(client, sample_matrix())

    payload = client.get(
        f"/matrix/{uuid}/export",
        params={"granularity": "fusa", "tempo_bpm": 72, "sparse": False},
    ).json()

    assert payload["sparse"] is False
    assert len(payload["columnHeaders"]) == KEY_COUNT
    assert payload["columnHeaders"][0] == {"es": "La-0", "en": "A0", "row": 0}
    assert payload["columnHeaders"][DO4]["en"] == "C4"

    grid = payload["denseMatrix"]
    assert len(grid) == 6  # frames as rows
    assert all(len(frame) == KEY_COUNT for frame in grid)
    assert [frame[DO4] for frame in grid] == [0, 1, -1, 0, 0, 0]

    # 6 frames of a fusa at 72 BPM.
    assert len(payload["rowTimestamps"]) == 6
    assert payload["rowTimestamps"][0] == 0.0
    assert payload["rowTimestamps"][1] == pytest.approx(60 / 72 * 0.125, abs=1e-4)


def test_a_two_hands_export_labels_both_hands(client: TestClient) -> None:
    uuid = seed_audio(client, sample_matrix())

    payload = client.get(
        f"/matrix/{uuid}/export",
        params={"step": "two-hands", "granularity": "fusa", "tempo_bpm": 72},
    ).json()

    assert payload["matrixProcessingStep"] == "two-hands"
    assert payload["rMatrix"] is not None
    assert payload["lMatrix"] is not None
    assert payload["matrix"] is None
    # Do-3 is below middle C, so it belongs to the left hand only.
    assert DO3 in payload["lMatrix"]["rows"]
    assert DO3 not in payload["rMatrix"]["rows"]


def test_exporting_an_untranscribed_audio_is_a_409(client: TestClient) -> None:
    from aitu_backend.audio import store
    from aitu_backend.schemas.metadata import AudioSource

    entry = store.create("No matrix", AudioSource.UPLOAD, "wav")
    assert client.get(f"/matrix/{entry.uuid}/export").status_code == 409


# ----------------------------------------------------------------- importing


def test_sparse_round_trip_is_identical(client: TestClient) -> None:
    """Export, re-import, and the grid must be the same."""
    uuid = seed_audio(client, sample_matrix())
    exported = client.get(
        f"/matrix/{uuid}/export", params={"granularity": "fusa", "tempo_bpm": 72}
    ).json()

    imported = client.post("/matrix/import", json=exported)
    assert imported.status_code == 201
    body = imported.json()
    assert body["frameCount"] == 6
    assert body["granularity"] == "fusa"
    assert body["matrixProcessingStep"] == "clean"
    assert body["normalizedCells"] == 0

    reloaded = client.get(
        f"/matrix/{body['audioUuid']}",
        params={"granularity": "fusa", "tempo_bpm": 72, "sparse": False},
    ).json()
    assert (
        reloaded["denseMatrix"]
        == client.get(
            f"/matrix/{uuid}", params={"granularity": "fusa", "tempo_bpm": 72, "sparse": False}
        ).json()["denseMatrix"]
    )


def test_dense_round_trip_is_identical(client: TestClient) -> None:
    uuid = seed_audio(client, sample_matrix())
    exported = client.get(
        f"/matrix/{uuid}/export",
        params={"granularity": "fusa", "tempo_bpm": 72, "sparse": False},
    ).json()

    body = client.post("/matrix/import", json=exported).json()
    reloaded = client.get(
        f"/matrix/{body['audioUuid']}",
        params={"granularity": "fusa", "tempo_bpm": 72, "sparse": False},
    ).json()

    assert reloaded["denseMatrix"] == exported["denseMatrix"]


def test_a_two_hands_export_re_imports_as_one_matrix(client: TestClient) -> None:
    """Both hands merge back on import; the split is recomputed on demand."""
    uuid = seed_audio(client, sample_matrix())
    exported = client.get(
        f"/matrix/{uuid}/export",
        params={"step": "two-hands", "granularity": "fusa", "tempo_bpm": 72},
    ).json()

    body = client.post("/matrix/import", json=exported).json()
    assert body["frameCount"] == 6

    hands = client.get(
        f"/matrix/{body['audioUuid']}",
        params={"step": "two-hands", "granularity": "fusa", "tempo_bpm": 72},
    ).json()
    assert DO3 in hands["lMatrix"]["rows"]
    assert DO4 in hands["rMatrix"]["rows"]


def test_an_import_normalizes_and_says_how_much(client: TestClient) -> None:
    """A hand-edited file with an orphan sustain loads, corrected, not refused."""
    uuid = seed_audio(client, sample_matrix())
    exported = client.get(
        f"/matrix/{uuid}/export",
        params={"granularity": "fusa", "tempo_bpm": 72, "sparse": False},
    ).json()

    # A sustain with nothing before it — illegal, and easy to type by hand.
    exported["denseMatrix"][0][MI4] = -1

    body = client.post("/matrix/import", json=exported).json()
    assert body["normalizedCells"] == 1

    reloaded = client.get(
        f"/matrix/{body['audioUuid']}",
        params={"granularity": "fusa", "tempo_bpm": 72, "sparse": False},
    ).json()
    # Promoted to an onset rather than dropped.
    assert reloaded["denseMatrix"][0][MI4] == 1


def test_a_malformed_import_is_a_422(client: TestClient) -> None:
    assert client.post("/matrix/import", json={"tempoBpm": 60}).status_code == 422
    assert client.post("/matrix/import", json={}).status_code == 422


def test_an_import_survives_a_file_round_trip(client: TestClient, tmp_path: Path) -> None:
    """What the user actually does: download a file, upload it later."""
    uuid = seed_audio(client, sample_matrix())
    exported = client.get(f"/matrix/{uuid}/export", params={"granularity": "fusa", "tempo_bpm": 72})

    saved = tmp_path / "matrix.json"
    saved.write_bytes(exported.content)

    body = client.post("/matrix/import", json=json.loads(saved.read_text())).json()
    assert body["frameCount"] == 6


def test_the_imported_matrix_can_be_recomputed(client: TestClient) -> None:
    """An import has no audio, but the imported step doubles as its raw source."""
    uuid = seed_audio(client, sample_matrix())
    exported = client.get(
        f"/matrix/{uuid}/export", params={"granularity": "fusa", "tempo_bpm": 72}
    ).json()
    body = client.post("/matrix/import", json=exported).json()

    coarser = client.get(
        f"/matrix/{body['audioUuid']}",
        params={"granularity": "semicorchea", "tempo_bpm": 72, "sparse": False},
    )
    assert coarser.status_code == 200
    assert len(coarser.json()["denseMatrix"]) == 3  # 6 columns collapsed once


def test_hands_from_a_split_export_match_a_local_split(client: TestClient) -> None:
    """Sanity: the endpoint's split is the same one Task 2.4.1 does."""
    matrix = sample_matrix()
    uuid = seed_audio(client, matrix)
    local = split_hands(matrix)

    payload = client.get(
        f"/matrix/{uuid}/export",
        params={"step": "two-hands", "granularity": "fusa", "tempo_bpm": 72},
    ).json()

    assert payload["rMatrix"] == local.right.to_coo_payload().model_dump(by_alias=True)
    assert payload["lMatrix"] == local.left.to_coo_payload().model_dump(by_alias=True)
