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
    assert client.post("/sequence", json={"sequence": ["*Do-4"]}).status_code in (404, 405)


def test_playlists_are_a_list() -> None:
    """Playlists landed in Epic 10; the list is real even when it is empty."""
    response = client.get("/library/playlists")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_notation_answers_404_for_an_unknown_artifact() -> None:
    """The notation router resolves an artifact id to a matrix, or says it cannot."""
    response = client.get("/notation/some-id/matrix")
    assert response.status_code == 404
