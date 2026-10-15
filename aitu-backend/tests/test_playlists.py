"""Songs playlists of the Private Library (implementation 02, Phase 10, plan section 14.2).

A songs playlist points at songs and the version chosen for each, optionally a stretch of it;
nothing in it is a copy. These tests make the songs directly in the tables (the save flow is
tested in ``test_library.py``).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aitu_backend.db import users
from aitu_backend.db.database import session
from aitu_backend.db.models import PrivateVersion
from aitu_backend.library import rows
from aitu_backend.main import create_app
from aitu_backend.storage import bundle


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def song(title: str, artist: str, versions: list[str]) -> tuple[int, list[str]]:
    """A song of the master user's library with a project per version."""
    owner = users.ensure_master_user()
    projects = [
        bundle.create_project(owner_id=owner, title=title, layer="private").id for _ in versions
    ]
    with session() as db:
        row = rows.make_song(db, owner, title, artist)
        for name, project in zip(versions, projects):
            db.add(PrivateVersion(song_id=row.id, version_name=name, project_id=project))
        return row.id, projects


def test_a_playlist_is_made_from_songs_and_changed(client: TestClient) -> None:
    clocks, (clocks_easy, clocks_hard) = song("Clocks", "Coldplay", ["easy", "hard"])
    yellow, (yellow_one,) = song("Yellow", "Coldplay", ["original"])

    made = client.post(
        "/playlists",
        json={"title": " Live set ", "items": [{"songId": clocks}, {"songId": yellow}]},
    )
    assert made.status_code == 201, made.text
    body = made.json()
    playlist = body["id"]
    assert body["title"] == "Live set"
    # Each song on its first version; every version offered.
    assert [(i["songTitle"], i["versionName"], i["projectId"]) for i in body["items"]] == [
        ("Clocks", "easy", clocks_easy),
        ("Yellow", "original", yellow_one),
    ]
    assert body["items"][0]["artists"] == ["Coldplay"]
    assert [v["name"] for v in body["items"][0]["versions"]] == ["easy", "hard"]
    assert body["items"][0]["parts"] == [clocks_easy]
    listed = client.get("/playlists").json()
    assert [(row["title"], row["songs"]) for row in listed] == [("Live set", 2)]

    first, second = (item["id"] for item in body["items"])
    # Another version, then a stretch of it, then the whole song again.
    changed = client.patch(f"/playlists/{playlist}/items/{first}", json={"projectId": clocks_hard})
    assert changed.json()["items"][0]["versionName"] == "hard"
    stretch = client.patch(
        f"/playlists/{playlist}/items/{first}", json={"fromMs": 12000, "toMs": 65000}
    ).json()["items"][0]
    assert (stretch["fromMs"], stretch["toMs"], stretch["versionName"]) == (12000, 65000, "hard")
    whole = client.patch(f"/playlists/{playlist}/items/{first}", json={"whole": True}).json()
    assert whole["items"][0]["fromMs"] is None
    # A version of another song, or a stretch that ends before it starts, is refused.
    assert (
        client.patch(
            f"/playlists/{playlist}/items/{first}", json={"projectId": yellow_one}
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/playlists/{playlist}/items/{first}", json={"fromMs": 5000, "toMs": 4000}
        ).status_code
        == 422
    )

    reordered = client.patch(
        f"/playlists/{playlist}", json={"order": [second, first], "title": "Encore"}
    )
    assert reordered.status_code == 200, reordered.text
    assert reordered.json()["title"] == "Encore"
    assert [i["songTitle"] for i in reordered.json()["items"]] == ["Yellow", "Clocks"]
    added = client.post(f"/playlists/{playlist}/items", json={"items": [{"songId": yellow}]})
    assert [i["songTitle"] for i in added.json()["items"]] == ["Yellow", "Clocks", "Yellow"]
    removed = client.delete(f"/playlists/{playlist}/items/{second}")
    assert [i["songTitle"] for i in removed.json()["items"]] == ["Clocks", "Yellow"]

    assert client.delete(f"/playlists/{playlist}").status_code == 204
    assert client.get(f"/playlists/{playlist}").status_code == 404
    # The songs and their versions are untouched.
    assert len(client.get(f"/library/songs/{clocks}").json()["versions"]) == 2


def test_a_deleted_version_or_song_leaves_the_playlist_whole(client: TestClient) -> None:
    clocks, (easy, hard) = song("Clocks", "Coldplay", ["easy", "hard"])
    yellow, _ = song("Yellow", "Coldplay", ["original"])
    playlist = client.post(
        "/playlists",
        json={"title": "Set", "items": [{"songId": clocks, "projectId": hard}, {"songId": yellow}]},
    ).json()["id"]
    hard_version = next(
        v["id"]
        for v in client.get(f"/library/songs/{clocks}").json()["versions"]
        if v["name"] == "hard"
    )
    assert client.delete(f"/library/versions/{hard_version}").status_code == 204
    items = client.get(f"/playlists/{playlist}").json()["items"]
    assert [(i["songTitle"], i["versionName"], i["projectId"]) for i in items][0] == (
        "Clocks",
        "easy",
        easy,
    )
    assert client.delete(f"/library/songs/{yellow}").status_code == 204
    assert [i["songTitle"] for i in client.get(f"/playlists/{playlist}").json()["items"]] == [
        "Clocks"
    ]


def test_a_playlist_needs_a_title_and_songs_of_the_library(client: TestClient) -> None:
    assert client.post("/playlists", json={"title": "  "}).status_code == 422
    assert (
        client.post("/playlists", json={"title": "Set", "items": [{"songId": 999}]}).status_code
        == 404
    )
    empty = client.post("/playlists", json={"title": "Empty"})
    assert empty.status_code == 201 and empty.json()["items"] == []
