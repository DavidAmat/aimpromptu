"""Playlists: ordered promotions, persisted, with Next walking the list."""

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from aitu_backend.main import create_app
from aitu_backend.matrix.keys import KEY_COUNT, note_to_row
from aitu_backend.matrix.model import PianoMatrix
from aitu_backend.schemas.matrix import MatrixProcessingStep
from aitu_backend.schemas.metadata import PlaylistItem
from aitu_backend.storage import paths, playlists, promotion, repository
from aitu_backend.storage.promotion import PromotionNotFound

DO4 = note_to_row("Do-4")


@pytest.fixture()
def temp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(paths, "backend_root", lambda: tmp_path)
    paths.ensure_data_tree()
    return tmp_path / "data"


@pytest.fixture()
def client(temp_store: Path) -> TestClient:
    return TestClient(create_app())


def matrix() -> PianoMatrix:
    grid = np.zeros((KEY_COUNT, 8), dtype=np.int8)
    grid[DO4, 0] = 1
    return PianoMatrix.time_based(grid, frame_ms=40, processing_step=MatrixProcessingStep.CLEAN)


def two_promotions() -> None:
    repository.save_version("Avicii", "Levels", matrix())
    repository.save_version("Avicii", "Levels", matrix())
    promotion.promote("avicii", "levels", "v1_f40", promotion_name="Levels (Chill) - Avicii")
    promotion.promote(
        "avicii",
        "levels",
        "v2_f40",
        promotion_name="Levels (Full speed) - Avicii",
        as_additional=True,
    )


def test_a_playlist_round_trips_and_survives_a_reread(temp_store: Path) -> None:
    two_promotions()
    created = playlists.create_playlist(
        "Sunday practice",
        description="Warm-up",
        items=[
            PlaylistItem(
                artist_slug="avicii",
                track_slug="levels",
                promotion_name="Levels (Chill) - Avicii",
            )
        ],
    )
    assert created.slug == "sunday-practice"
    assert playlists.read_playlist("sunday-practice").name == "Sunday practice"
    playlists.update_playlist("sunday-practice", name="Sunday set")
    reread = playlists.read_playlist("sunday-practice")
    assert reread.name == "Sunday set"
    assert reread.slug == "sunday-practice"
    assert reread.items[0].promotion_name == "Levels (Chill) - Avicii"


def test_an_unknown_promotion_is_refused(temp_store: Path) -> None:
    two_promotions()
    with pytest.raises(PromotionNotFound):
        playlists.create_playlist(
            "Bad",
            items=[
                PlaylistItem(
                    artist_slug="avicii",
                    track_slug="levels",
                    promotion_name="No such take",
                )
            ],
        )


def test_playlists_over_http(client: TestClient) -> None:
    two_promotions()
    created = client.post(
        "/library/playlists",
        json={
            "name": "Sunday practice",
            "items": [
                {
                    "artistSlug": "avicii",
                    "trackSlug": "levels",
                    "promotionName": "Levels (Chill) - Avicii",
                },
                {
                    "artistSlug": "avicii",
                    "trackSlug": "levels",
                    "promotionName": "Levels (Full speed) - Avicii",
                },
            ],
        },
    )
    assert created.status_code == 201
    slug = created.json()["slug"]
    assert client.get("/library/playlists").json()[0]["name"] == "Sunday practice"

    reordered = client.patch(
        f"/library/playlists/{slug}",
        json={
            "items": [
                {
                    "artistSlug": "avicii",
                    "trackSlug": "levels",
                    "promotionName": "Levels (Full speed) - Avicii",
                },
                {
                    "artistSlug": "avicii",
                    "trackSlug": "levels",
                    "promotionName": "Levels (Chill) - Avicii",
                },
            ]
        },
    ).json()
    assert [item["promotionName"] for item in reordered["items"]] == [
        "Levels (Full speed) - Avicii",
        "Levels (Chill) - Avicii",
    ]
    assert client.delete(f"/library/playlists/{slug}").status_code == 200
    assert client.get("/library/playlists").json() == []
    assert client.get(f"/library/playlists/{slug}").status_code == 404
