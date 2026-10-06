"""Smoke tests for the restructured app: health, and the routes that exist."""

from fastapi.testclient import TestClient

from aitu_backend.main import create_app

client = TestClient(create_app())


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_the_text_notation_mvp_is_gone() -> None:
    """`/scores` and `/sequence` were deleted with the text-notation MVP (implementation 02, Q-4)."""
    assert client.get("/scores").status_code == 404
    assert client.post("/sequence", json={"sequence": ["*Do-4"]}).status_code in (
        404,
        405,
    )


def test_the_old_piano_library_is_gone() -> None:
    """The old `/library` router (playground, `.npz`, promotions, tags, playlists) was deleted in
    implementation 02, Phase 3; the Private Library takes the path in Phase 6."""
    assert client.get("/library/playlists").status_code == 404
    assert client.get("/library/tracks").status_code == 404


def test_notation_answers_404_for_an_unknown_artifact() -> None:
    """The notation router resolves an artifact id to a matrix, or says it cannot."""
    response = client.get("/notation/some-id/matrix")
    assert response.status_code == 404
