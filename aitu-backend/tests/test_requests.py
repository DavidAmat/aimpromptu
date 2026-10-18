"""Requests to the Public Library, the review, and shared libraries (implementation 02, Phase 14,
plan sections 15.4 and 16). Three users sign in through ``/auth``: the master user, anna (who
publishes) and joan (another user); the public rows come from the small download of
``test_public_import``."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from aitu_backend.db import users
from aitu_backend.db.database import session
from aitu_backend.db.models import Artist, Project, Song, SongVersion, UserVersion
from aitu_backend.library import catalogue
from aitu_backend.library.public_import import import_library, read_source
from aitu_backend.library.requests import simple_name
from test_public import ALIVE, GIVE, client_of, ready, song_id
from test_public_import import ROWS, SOURCE_SCHEMA

pytestmark = [
    pytest.mark.real_login,
    pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed"),
]


@pytest.fixture()
def people(tmp_path: Path) -> dict[str, tuple[int, TestClient]]:
    source = tmp_path / "library.sqlite"
    with sqlite3.connect(source) as connection:
        connection.executescript(SOURCE_SCHEMA + ROWS)
    with session() as db:
        import_library(db, read_source(source), seed=None)
    catalogue.forget()
    master_id = users.ensure_master_user()
    users.set_password(master_id, "master-password")
    anna = users.create_user("anna", "anna-password")
    joan = users.create_user("joan", "joan-password")
    return {
        "master": (master_id, client_of("master", "master-password")),
        "anna": (anna.id, client_of("anna", "anna-password")),
        "joan": (joan.id, client_of("joan", "joan-password")),
    }


def saved(on: TestClient, **body: object) -> tuple[int, int, str]:
    """A ready project saved to the library: ``(song, version, project)``."""
    answer = on.post(f"/projects/{ready(on)}/library", json=body)
    assert answer.status_code == 201, answer.text
    song = on.get(f"/library/songs/{answer.json()['songId']}").json()
    version = song["versions"][-1]
    return song["id"], version["id"], version["projectId"]


def send(on: TestClient, **body: object) -> int:
    answer = on.post("/requests", json=body)
    assert answer.status_code == 201, answer.text
    return int(answer.json()["id"])


def decide(on: TestClient, request: int, *decisions: dict, comment: str | None = None) -> dict:
    answer = on.post(
        f"/admin/requests/{request}/decision", json={"items": list(decisions), "comment": comment}
    )
    assert answer.status_code == 200, answer.text
    return answer.json()


def items(on: TestClient, request: int) -> list[dict]:
    return on.get(f"/requests/{request}").json()["itemList"]


def accept_all(master: TestClient, request: int, **changes: dict) -> dict:
    return decide(
        master,
        request,
        *[
            {"id": one["id"], "decision": "accepted", "changes": changes.get(one["kind"], {})}
            for one in items(master, request)
            if one["decision"] is None
        ],
    )


def published(anna: TestClient, master: TestClient, public_song: int, name: str) -> str:
    """Anna's version published as her user version ``name``: its public project."""
    _, version, _ = saved(anna, publicSongId=public_song, version=name)
    request = send(
        anna, kind="userVersion", version=version, versionName=name, song={"publicId": public_song}
    )
    accept_all(master, request)
    return items(master, request)[-1]["payload"]["made"]["projectId"]


# ------------------------------------------------------------------ user version


def test_a_user_version_is_sent_copied_reviewed_and_published(people: dict) -> None:
    anna_id, anna = people["anna"]
    _, joan = people["joan"]
    _, master = people["master"]
    alive = song_id(ALIVE)
    _, version, source = saved(anna, publicSongId=alive, version="Easy (left hand)")

    info = anna.get("/requests/publish-info", params={"version": version}).json()
    assert info["suggestedName"] == "easy-left-hand" and info["ready"]
    assert info["publicSongId"] == alive and info["publicSongTitle"] == "Stayin' Alive"

    # A public version name is a simple name.
    bad = anna.post(
        "/requests",
        json={
            "kind": "userVersion",
            "version": version,
            "versionName": "Easy!",
            "song": {"publicId": alive},
        },
    )
    assert bad.status_code == 422
    request = send(
        anna,
        kind="userVersion",
        version=version,
        versionName="easy",
        song={"publicId": alive},
        note="My first one",
    )
    again = anna.post(
        "/requests",
        json={
            "kind": "userVersion",
            "version": version,
            "versionName": "easy",
            "song": {"publicId": alive},
        },
    )
    assert again.status_code == 409

    # The project is copied when the request is sent, into the layer of requests.
    item = items(anna, request)[0]
    snapshot = item["payload"]["projectId"]
    assert snapshot != source and item["compare"]["current"] is None
    assert item["compare"]["proposed"]["parts"]
    with session() as db:
        row = db.get(Project, snapshot)
        assert row is not None and (row.layer, row.owner_id) == ("request", anna_id)
    # Its author and the master user read it; nobody writes it; another user does not see it.
    assert anna.get(f"/projects/{snapshot}").status_code == 200
    assert master.get(f"/projects/{snapshot}").status_code == 200
    assert joan.get(f"/projects/{snapshot}").status_code == 404
    assert anna.patch(f"/projects/{snapshot}", json={"title": "x"}).status_code == 403
    assert master.patch(f"/projects/{snapshot}", json={"title": "x"}).status_code == 403
    # The request: its author and the master user; another user gets 404 and cannot decide.
    assert joan.get(f"/requests/{request}").status_code == 404
    assert joan.post(f"/admin/requests/{request}/decision", json={"items": []}).status_code == 403
    assert [one["id"] for one in master.get("/admin/requests").json()] == [request]
    assert master.get("/requests/counts").json() == {"mine": 0, "review": 1}
    assert anna.get("/requests/counts").json() == {"mine": 0, "review": 0}

    # Every waiting item needs a decision.
    partial = master.post(f"/admin/requests/{request}/decision", json={"items": []})
    assert partial.status_code == 422
    done = accept_all(master, request)
    assert done["status"] == "accepted" and done["decidedAt"]
    made = done["itemList"][0]["payload"]["made"]
    assert made["songId"] == alive and made["projectId"] not in (snapshot, source)
    song = joan.get(f"/public/songs/{alive}").json()
    assert [(g["username"], [v["name"] for v in g["versions"]]) for g in song["others"]] == [
        ("anna", ["easy"])
    ]
    assert song["others"][0]["versions"][0]["creator"] == "anna"
    # Everyone plays it; the copy the request sent stays, as the record of the review.
    assert joan.get(f"/projects/{made['projectId']}").status_code == 200
    assert anna.get(f"/projects/{snapshot}").status_code == 200
    assert master.get("/admin/requests").json() == []
    assert [(c["kind"], c["body"]) for c in done["comments"]] == [
        ("comment", "My first one"),
        ("review", ""),
    ]
    assert done["comments"][1]["details"]["items"][0]["decision"] == "accepted"


def test_a_better_user_version_replaces_the_own_one_and_keeps_its_likes(people: dict) -> None:
    _, anna = people["anna"]
    _, joan = people["joan"]
    _, master = people["master"]
    alive = song_id(ALIVE)
    first = published(anna, master, alive, "easy")
    assert joan.put(f"/public/likes/{first}").json()["likes"] == 1

    _, version, _ = saved(anna, publicSongId=alive, version="easy, better")
    request = send(
        anna, kind="userVersion", version=version, versionName="easy", song={"publicId": alive}
    )
    compare = items(master, request)[0]["compare"]
    assert compare["current"]["projectId"] == first and compare["current"]["name"] == "easy"
    accept_all(master, request)
    versions = joan.get(f"/public/songs/{alive}").json()["others"][0]["versions"]
    assert len(versions) == 1 and versions[0]["projectId"] != first
    assert (versions[0]["likes"], versions[0]["liked"]) == (1, True)
    with session() as db:
        assert db.get(Project, first) is None


# ------------------------------------------------------- a new song, in part


def test_a_new_song_and_artist_are_accepted_and_the_piano_sheet_refused(people: dict) -> None:
    anna_id, anna = people["anna"]
    _, master = people["master"]
    own_song, version, _ = saved(anna, song="Lo malo", artist="Aitana", version="original")
    own_artist = anna.get(f"/library/songs/{own_song}").json()["artists"][0]["artistId"]
    proposal = {
        "kind": "userVersion",
        "version": version,
        "versionName": "original",
        "song": {
            "privateId": own_song,
            "new": {
                "title": "Lo malo",
                "year": 2018,
                "artists": [{"newName": "Aitana", "privateId": own_artist}],
                "genres": ["pop", "latin"],
            },
        },
    }
    too_many = {**proposal, "song": {"new": {**proposal["song"]["new"], "genres": ["pop", "latin", "rock"]}}}  # type: ignore[dict-item]
    assert anna.post("/requests", json=too_many).status_code == 422
    known = {**proposal, "song": {"new": {**proposal["song"]["new"], "artists": [{"newName": "Bee Gees"}]}}}  # type: ignore[dict-item]
    assert anna.post("/requests", json=known).status_code == 409
    request = send(anna, **proposal)
    found = items(master, request)
    assert [one["kind"] for one in found] == ["newArtist", "newSong", "project"]
    artist_item, song_item, project_item = found
    assert song_item["payload"]["artists"][0]["name"] == "Aitana"
    assert song_item["payload"]["artists"][0]["isNew"] is True
    assert project_item["payload"]["song"] == {
        "ref": song_item["payload"]["ref"],
        "privateId": own_song,
        "title": "Lo malo",
        "isNew": True,
    }

    # An item cannot be accepted without what it needs.
    refused_artist = master.post(
        f"/admin/requests/{request}/decision",
        json={
            "items": [
                {"id": artist_item["id"], "decision": "refused"},
                {"id": song_item["id"], "decision": "accepted"},
                {"id": project_item["id"], "decision": "refused"},
            ]
        },
    )
    assert refused_artist.status_code == 409
    assert "artist" in refused_artist.json()["detail"]
    done = decide(
        master,
        request,
        {"id": artist_item["id"], "decision": "accepted"},
        {"id": song_item["id"], "decision": "accepted", "changes": {"title": "Lo Malo"}},
        {"id": project_item["id"], "decision": "refused", "comment": "The left hand is wrong"},
    )
    assert done["status"] == "partlyAccepted"
    public_song = done["itemList"][1]["payload"]["made"]["songId"]
    public_artist = done["itemList"][0]["payload"]["made"]["artistId"]
    song = anna.get(f"/public/songs/{public_song}").json()
    assert (song["title"], song["year"], song["genres"]) == ("Lo Malo", 2018, ["pop", "latin"])
    assert [a["name"] for a in song["artists"]] == ["Aitana"]
    assert song["regions"] == ["Worldwide"] and song["fixed"] == [] and song["others"] == []
    assert anna.get(f"/public/artists/{public_artist}").json()["inLibrary"] == own_artist
    with session() as db:
        row = db.get(Artist, public_artist)
        assert row is not None and (row.scope, row.owner_id) == ("public", None)
        assert db.get(Song, public_song).popularity == 0.0  # type: ignore[union-attr]
    assert done["itemList"][2]["comment"] == "The left hand is wrong"
    # Reviewed: the author can no longer withdraw it, nor send it again.
    assert anna.post(f"/requests/{request}/withdraw").status_code == 409
    assert anna.put(f"/requests/{request}", json=proposal).status_code == 409
    assert anna_id


def test_changes_asked_are_made_and_the_request_sent_again(people: dict) -> None:
    _, anna = people["anna"]
    _, master = people["master"]
    own_song, version, _ = saved(anna, song="1973", artist="James Blunt", version="Mine")
    request = send(
        anna,
        kind="userVersion",
        version=version,
        versionName="mine",
        song={"new": {"title": "1973", "artists": [{"newName": "James Blunt"}]}},
    )
    artist_item, song_item, project_item = items(master, request)
    done = decide(
        master,
        request,
        {"id": artist_item["id"], "decision": "accepted"},
        {"id": song_item["id"], "decision": "changesAsked", "comment": "Its year, please"},
        {"id": project_item["id"], "decision": "changesAsked", "comment": "Call it hard"},
        comment="Nearly there",
    )
    assert done["status"] == "changesAsked"
    assert anna.get("/requests/counts").json()["mine"] == 1
    assert master.get("/admin/requests").json() == []
    # The proposal to send again names the accepted artist by its public row.
    proposal = anna.get(f"/requests/{request}").json()["proposal"]
    public_artist = done["itemList"][0]["payload"]["made"]["artistId"]
    assert proposal["song"]["new"]["artists"] == [{"publicId": public_artist}]
    assert proposal["version"] == version and proposal["versionName"] == "mine"
    old_snapshot = project_item["payload"]["projectId"]

    proposal["song"]["new"]["year"] = 2004
    proposal["versionName"] = "hard"
    proposal["note"] = "Year added"
    again = anna.put(f"/requests/{request}", json=proposal)
    assert again.status_code == 200, again.text
    assert again.json()["status"] == "open"
    kinds = [(one["kind"], one["decision"]) for one in again.json()["itemList"]]
    assert kinds == [("newArtist", "accepted"), ("newSong", None), ("project", None)]
    with session() as db:
        assert db.get(Project, old_snapshot) is None
    final = accept_all(master, request, project={"versionName": "hard-left"})
    assert final["status"] == "accepted"
    made_song = final["itemList"][1]["payload"]["made"]["songId"]
    song = anna.get(f"/public/songs/{made_song}").json()
    assert song["year"] == 2004 and [a["name"] for a in song["artists"]] == ["James Blunt"]
    assert [v["name"] for v in song["others"][0]["versions"]] == ["hard-left"]
    # The author's song now stands for the public one.
    assert anna.get(f"/library/songs/{own_song}").json()["publicId"] == made_song
    assert [(c["kind"], c["body"]) for c in final["comments"]] == [
        ("review", "Nearly there"),
        ("sentAgain", "Year added"),
        ("review", ""),
    ]
    first_review = final["comments"][0]["details"]["items"]
    assert [(one["kind"], one["decision"]) for one in first_review] == [
        ("newArtist", "accepted"),
        ("newSong", "changesAsked"),
        ("project", "changesAsked"),
    ]


def test_a_request_is_withdrawn_until_it_is_reviewed(people: dict) -> None:
    _, anna = people["anna"]
    _, joan = people["joan"]
    _, master = people["master"]
    _, version, _ = saved(anna, publicSongId=song_id(GIVE), version="easy")
    request = send(
        anna,
        kind="userVersion",
        version=version,
        versionName="easy",
        song={"publicId": song_id(GIVE)},
    )
    assert joan.post(f"/requests/{request}/withdraw").status_code == 404
    withdrawn = anna.post(f"/requests/{request}/withdraw").json()
    assert withdrawn["status"] == "withdrawn"
    assert master.get("/admin/requests").json() == []
    assert [
        one["status"] for one in master.get("/admin/requests", params={"everything": True}).json()
    ] == ["withdrawn"]
    assert (
        master.post(
            f"/admin/requests/{request}/decision",
            json={"items": [{"id": items(master, request)[0]["id"], "decision": "accepted"}]},
        ).status_code
        == 409
    )


# ---------------------------------------------------------------- metadata


def test_a_change_of_a_song_and_of_an_artist(people: dict) -> None:
    _, anna = people["anna"]
    _, master = people["master"]
    alive = song_id(ALIVE)
    song = anna.get(f"/public/songs/{alive}").json()
    bee_gees = song["artists"][0]["artistId"]
    same = {
        "title": "Stayin' Alive",
        "year": 1977,
        "artists": [{"publicId": bee_gees}],
        "regions": ["worldwide"],
    }
    unchanged = anna.post(
        "/requests", json={"kind": "metadata", "song": {"publicId": alive}, "changes": same}
    )
    assert unchanged.status_code == 422
    request = send(
        anna,
        kind="metadata",
        song={"publicId": alive},
        changes={
            **same,
            "genres": ["pop", "r&b and soul"],
            "tags": [{"category": "films", "value": "Saturday Night Fever"}],
        },
    )
    item = items(master, request)[0]
    assert item["payload"]["before"]["genres"] == [] and item["payload"]["after"]["genres"] == [
        "pop",
        "r&b and soul",
    ]
    assert accept_all(master, request)["status"] == "accepted"
    song = anna.get(f"/public/songs/{alive}").json()
    assert song["genres"] == ["pop", "r&b and soul"]
    assert song["tags"] == [["films", "Saturday Night Fever"]]
    assert [a["name"] for a in song["artists"]] == ["Bee Gees"]
    # The Genre and Tag filters of the songs list see them.
    facets = anna.get("/public/songs").json()["facets"]
    assert [f["label"] for f in facets["tags"]] == ["Saturday Night Fever"]

    jackson = anna.get("/public/artists", params={"q": "michael jackson"}).json()["rows"][0]["id"]
    taken = anna.post(
        "/requests",
        json={
            "kind": "metadata",
            "artist": {"publicId": bee_gees, "addNames": ["Michael Jackson"]},
        },
    )
    assert taken.status_code == 409
    request = send(
        anna,
        kind="metadata",
        artist={"publicId": bee_gees, "name": "The Bee Gees", "addNames": ["Bee Gees", "BeeGees"]},
    )
    payload = items(master, request)[0]["payload"]
    assert (payload["name"], payload["addNames"]) == ("The Bee Gees", ["BeeGees"])
    accept_all(master, request)
    artist = anna.get(f"/public/artists/{bee_gees}").json()
    assert artist["name"] == "The Bee Gees" and artist["otherNames"] == ["BeeGees"]
    assert anna.get(f"/public/songs/{alive}").json()["artists"][0]["name"] == "The Bee Gees"
    assert jackson


def test_a_new_song_alone_is_a_metadata_request(people: dict) -> None:
    _, anna = people["anna"]
    _, master = people["master"]
    request = send(
        anna,
        kind="metadata",
        song={"new": {"title": "Grace Kelly", "artists": [{"newName": "Mika"}], "year": 2007}},
    )
    summary = anna.get("/requests").json()[0]
    assert (summary["title"], summary["subject"], summary["kind"]) == (
        "Grace Kelly",
        "new song",
        "metadata",
    )
    done = accept_all(master, request)
    made = done["itemList"][1]["payload"]["made"]["songId"]
    found = anna.get("/public/songs", params={"q": "grace kelly"}).json()
    assert [row["id"] for row in found["rows"]] == [made]


# ------------------------------------------------------------ fixed version


def test_a_fixed_version_points_at_an_accepted_user_version(people: dict) -> None:
    _, anna = people["anna"]
    _, joan = people["joan"]
    _, master = people["master"]
    alive = song_id(ALIVE)
    mine = published(anna, master, alive, "easy")
    # Only the author's own user version.
    assert (
        joan.post(
            "/requests", json={"kind": "fixedVersion", "userVersion": mine, "name": "hard"}
        ).status_code
        == 404
    )
    request = send(anna, kind="fixedVersion", userVersion=mine, name="hard")
    assert (
        anna.post(
            "/requests", json={"kind": "fixedVersion", "userVersion": mine, "name": "hard"}
        ).status_code
        == 409
    )
    item = items(master, request)[0]
    assert item["compare"]["current"] is None and item["compare"]["proposed"]["projectId"] == mine
    summary = master.get("/admin/requests").json()[0]
    assert (summary["title"], summary["subject"]) == ("Stayin' Alive", "easy as hard")
    accept_all(master, request)
    song = joan.get(f"/public/songs/{alive}").json()
    assert [(v["name"], v["creator"], v["projectId"]) for v in song["fixed"]] == [
        ("hard", "anna", mine)
    ]
    assert song["defaultVersion"] == "hard"
    with session() as db:
        assert db.scalar(select(SongVersion.creator_id).where(SongVersion.project_id == mine))
        assert db.scalar(select(UserVersion.id).where(UserVersion.project_id == mine))
    # Joan can now add it to her library: the default version.
    assert joan.post(f"/public/songs/{alive}/pull", json={}).status_code == 201
    assert (
        anna.post(
            "/requests", json={"kind": "fixedVersion", "userVersion": mine, "name": "hard"}
        ).status_code
        == 409
    )


# ----------------------------------------------------------------- playlist


def test_a_playlist_is_published_with_its_songs_that_have_a_public_version(people: dict) -> None:
    anna_id, anna = people["anna"]
    _, joan = people["joan"]
    _, master = people["master"]
    alive = song_id(ALIVE)
    published(anna, master, alive, "easy")
    alive_own = anna.get(f"/public/songs/{alive}").json()["inLibrary"]
    alive_project = anna.get(f"/library/songs/{alive_own}").json()["versions"][0]["projectId"]
    other_song, _, other_project = saved(anna, song="Not public", artist="Nobody", version="v1")
    made = anna.post(
        "/playlists",
        json={
            "title": "Evening",
            "items": [
                {"songId": alive_own, "projectId": alive_project},
                {"songId": other_song, "projectId": other_project},
            ],
        },
    )
    assert made.status_code == 201, made.text
    playlist = made.json()["id"]
    info = anna.get("/requests/playlist-info", params={"playlist": playlist}).json()
    assert [one["title"] for one in info["items"]] == ["Stayin' Alive"]
    assert info["left"] == ["Not public"] and info["items"][0]["versionName"] == "easy"
    assert joan.get("/requests/playlist-info", params={"playlist": playlist}).status_code == 404
    request = send(anna, kind="playlist", playlist=playlist, title="Evening songs")
    accept_all(master, request, playlist={"title": "Evening hits"})
    public_lists = joan.get("/public/playlists").json()
    assert [one["title"] for one in public_lists] == ["Evening hits"]
    shown = joan.get(f"/public/playlists/{public_lists[0]['id']}").json()
    assert [(one["songTitle"], one["versionName"]) for one in shown["items"]] == [
        ("Stayin' Alive", "easy")
    ]
    assert other_song and anna_id


# ------------------------------------------------------------------ sharing


def test_a_library_is_shared_read_only_and_its_songs_added(people: dict) -> None:
    anna_id, anna = people["anna"]
    joan_id, joan = people["joan"]
    _, master = people["master"]
    own_song, _, project = saved(anna, song="1973", artist="James Blunt", version="original")
    assert joan.get(f"/shared/{anna_id}/songs").status_code == 404
    assert joan.get(f"/projects/{project}").status_code == 404

    shares = anna.put(f"/shares/{joan_id}").json()
    assert shares["sharedWith"] == [joan_id]
    assert {one["username"] for one in shares["people"]} == {"master", "joan"}
    mine = joan.get("/shares").json()["sharedWithMe"]
    assert [(one["username"], one["songs"]) for one in mine] == [("anna", 1)]
    library = joan.get(f"/shared/{anna_id}/songs").json()
    assert library["owner"] == "anna" and [s["title"] for s in library["songs"]] == ["1973"]
    song = joan.get(f"/shared/songs/{own_song}").json()
    assert [v["name"] for v in song["versions"]] == ["original"]
    # Read only: she plays it and copies from it, she does not change it.
    assert joan.get(f"/projects/{project}").status_code == 200
    assert joan.patch(f"/projects/{project}", json={"title": "x"}).status_code == 403
    # The master user has no right over it: it is not shared with them.
    assert master.get(f"/shared/songs/{own_song}").status_code == 404
    assert master.get(f"/projects/{project}").status_code == 404

    added = joan.post(f"/shared/songs/{own_song}/pull", json={})
    assert added.status_code == 201, added.text
    assert (added.json()["versions"], added.json()["already"]) == (1, 0)
    hers = joan.get(f"/library/songs/{added.json()['songId']}").json()
    assert (hers["title"], [a["name"] for a in hers["artists"]]) == ("1973", ["James Blunt"])
    assert [v["name"] for v in hers["versions"]] == ["original (anna)"]
    assert hers["versions"][0]["projectId"] != project
    again = joan.post(f"/shared/songs/{own_song}/pull", json={}).json()
    assert (again["versions"], again["already"]) == (0, 1)
    assert joan.get(f"/shared/songs/{own_song}").json()["inLibrary"] == hers["id"]

    anna.delete(f"/shares/{joan_id}")
    assert joan.get(f"/shared/songs/{own_song}").status_code == 404
    assert joan.get(f"/projects/{project}").status_code == 404
    assert joan.get("/shares").json()["sharedWithMe"] == []
    # Her own copy stays hers.
    assert joan.get(f"/projects/{hers['versions'][0]['projectId']}").status_code == 200


def test_the_simple_form_of_a_version_name() -> None:
    assert simple_name("Easy (left hand)") == "easy-left-hand"
    assert simple_name("Acústica  2") == "acustica-2"
    assert simple_name("--") == ""
    assert simple_name("a" * 40) == "a" * 24


def test_the_check_fixture_removes_a_user_and_what_they_made(people: dict) -> None:
    from aitu_backend.db.models import Request, User
    from aitu_backend.library import public_fixture

    anna_id, anna = people["anna"]
    _, master = people["master"]
    alive = song_id(ALIVE)
    mine = published(anna, master, alive, "easy")
    request = send(
        anna,
        kind="metadata",
        song={"new": {"title": "Grace Kelly", "artists": [{"newName": "Mika"}]}},
    )
    done = accept_all(master, request)
    new_song = done["itemList"][1]["payload"]["made"]["songId"]
    new_artist = done["itemList"][0]["payload"]["made"]["artistId"]

    assert public_fixture.main(["remove-song", "--id", str(new_song)]) == 0
    assert public_fixture.main(["remove-artist", "--id", str(new_artist)]) == 0
    assert public_fixture.main(["remove-user", "--username", "anna"]) == 0
    with session() as db:
        assert db.get(User, anna_id) is None
        assert db.get(Project, mine) is None
        assert db.scalar(select(Project.id).where(Project.owner_id == anna_id)) is None
        assert db.scalar(select(Request.id).where(Request.author_id == anna_id)) is None
        assert db.get(Song, new_song) is None and db.get(Artist, new_artist) is None
    assert master.get(f"/public/songs/{alive}").json()["others"] == []
    with pytest.raises(SystemExit):
        public_fixture.main(["remove-user", "--username", "master"])


def test_the_conversation_of_a_request(people: dict) -> None:
    anna_id, anna = people["anna"]
    _, joan = people["joan"]
    _, master = people["master"]
    alive = song_id(ALIVE)
    _, version, _ = saved(anna, publicSongId=alive, version="easy")
    request = send(
        anna,
        kind="userVersion",
        version=version,
        versionName="easy",
        song={"publicId": alive},
        note="First line\n\nSecond line",
    )
    item = items(master, request)[0]
    part = item["compare"]["proposed"]["parts"][0]

    # A comment on a stretch of the proposed sheet keeps a project of just that stretch.
    on = master.post(
        f"/requests/{request}/comments",
        json={
            "body": "The left hand here",
            "itemId": item["id"],
            "partId": part,
            "fromMs": 1000,
            "toMs": 3000,
        },
    )
    assert on.status_code == 201, on.text
    stretch = on.json()["comments"][-1]
    details = stretch["details"]
    assert (stretch["kind"], stretch["itemId"], details["partId"]) == ("comment", item["id"], part)
    assert details["fromMs"] <= 1000 and details["toMs"] >= 2960
    with session() as db:
        excerpt = db.get(Project, details["excerpt"])
        assert excerpt is not None
        assert (excerpt.layer, excerpt.owner_id, excerpt.kind) == ("request", anna_id, "passage")
    status = anna.get(f"/pieces/{details['excerptPart']}/status").json()
    sheet = next(one for one in status["steps"] if one["step"] == "sheet")
    assert sheet["state"] == "ready", status
    assert master.get(f"/projects/{details['excerpt']}").status_code == 200
    assert joan.get(f"/projects/{details['excerpt']}").status_code == 404

    # The author replies; a reply to a reply joins the same thread.
    reply = anna.post(
        f"/requests/{request}/comments", json={"body": "Fixed it", "parentId": stretch["id"]}
    ).json()["comments"][-1]
    assert reply["parentId"] == stretch["id"]
    again = master.post(
        f"/requests/{request}/comments", json={"body": "Thanks", "parentId": reply["id"]}
    ).json()["comments"][-1]
    assert again["parentId"] == stretch["id"]
    # The note keeps its lines.
    assert (
        anna.get(f"/requests/{request}").json()["comments"][0]["body"]
        == "First line\n\nSecond line"
    )

    # Refused: another user, an empty comment, a part that is not proposed, a long stretch.
    assert joan.post(f"/requests/{request}/comments", json={"body": "hi"}).status_code == 404
    assert anna.post(f"/requests/{request}/comments", json={"body": "  "}).status_code == 422
    assert (
        master.post(
            f"/requests/{request}/comments",
            json={"body": "x", "itemId": item["id"], "partId": "nope", "fromMs": 0, "toMs": 1000},
        ).status_code
        == 404
    )
    assert (
        master.post(
            f"/requests/{request}/comments",
            json={"body": "x", "itemId": item["id"], "partId": part, "fromMs": 0, "toMs": 200_000},
        ).status_code
        == 422
    )
    # The timeline's events: withdrawn.
    anna.post(f"/requests/{request}/withdraw")
    kinds = [c["kind"] for c in anna.get(f"/requests/{request}").json()["comments"]]
    assert kinds == ["comment", "comment", "comment", "comment", "withdrawn"]
