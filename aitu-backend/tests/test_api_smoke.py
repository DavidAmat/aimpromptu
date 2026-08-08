"""Smoke tests for the restructured app: health, scores and sequence."""

from fastapi.testclient import TestClient

from aitu_backend.main import create_app

client = TestClient(create_app())


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scores_returns_a_list() -> None:
    response = client.get("/scores")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload, "data/example-scores.json should ship at least one score"
    # The portable format carries one timing, and it is a length of wall clock.
    # It used to carry a tempo and a time step, which said the same thing twice.
    assert "frameMs" in payload[0]
    assert "tempoBpm" not in payload[0]


def test_sequence_round_trip_one_hand() -> None:
    """Do Re Mi with one held Re: 4 frames, 4 active cells, one sustain."""
    response = client.post(
        "/sequence",
        json={
            "sequence": ["*Do-4", "*Re-4", "Re-4", "*Mi-4"],
            "frameMs": 1000,
            "title": "smoke",
        },
    )
    assert response.status_code == 200
    score = response.json()
    matrix = score["matrix"]
    assert matrix["format"] == "binary-coo"
    assert matrix["shape"] == [88, 4]
    assert matrix["cols"] == [0, 1, 2, 3]
    # Row 39 is Do-4 (La-0 .. Si-0 = 3 rows, then 3 full octaves = 36).
    assert matrix["rows"] == [39, 41, 41, 43]
    assert matrix["onset"] == [39, 41, -1, 43]


def test_sequence_two_hands_must_align() -> None:
    response = client.post(
        "/sequence",
        json={
            "sequence": ["*Do-4", "*Re-4"],
            "leftSequence": ["*Do-3"],
            "frameMs": 1000,
        },
    )
    assert response.status_code == 422


def test_sequence_rejects_unknown_note() -> None:
    response = client.post(
        "/sequence",
        json={
            "sequence": ["*Xy-4"],
            "frameMs": 1000,
        },
    )
    assert response.status_code == 422


def test_placeholder_endpoints_answer_501() -> None:
    """Routes whose epic has not landed yet exist and say so.

    `/audio` and `/youtube` went real in Epic 3, `/matrix` in Epics 4 and 7,
    most of `/library` in Epic 5 and `/notation` in Epic 9. Only playlists,
    which belong to Epic 10, are left.
    """
    for url in ("/library/playlists",):
        response = client.get(url)
        assert response.status_code == 501, url
        assert "Not implemented yet" in response.json()["detail"]


def test_notation_answers_404_for_an_unknown_artifact() -> None:
    """The notation router resolves an artifact id to a matrix, or says it cannot."""
    response = client.get("/notation/some-id/matrix")
    assert response.status_code == 404
