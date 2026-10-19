"""The Public Library (implementation 02, Phase 13, plan sections 15.1 to 15.3 and 15.6): the songs
list with search, filters and sort, the popularity of a decade, one song with its metadata and
versions, the artists, likes, **Add to my library** for a song, an artist and a playlist, and **Save
to library** on a public song or artist. Two users sign in through ``/auth``; the public rows come
from the small download of ``test_public_import``."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from aitu_backend.db import users
from aitu_backend.db.database import session
from aitu_backend.db.models import (
    Artist,
    AudioFile,
    Playlist,
    PlaylistItem,
    PrivateVersion,
    Project,
    Song,
)
from aitu_backend.library import catalogue, flow, public
from aitu_backend.library.public_import import external_key, import_library, read_source
from aitu_backend.main import create_app
from aitu_backend.storage import bundle
from test_library import make_ready, uploaded
from test_public_import import ROWS, SOURCE_SCHEMA

pytestmark = [
    pytest.mark.real_login,
    pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed"),
]


def client_of(username: str, password: str) -> TestClient:
    client = TestClient(create_app())
    answer = client.post("/auth/login", json={"username": username, "password": password})
    assert answer.status_code == 200
    return client


@pytest.fixture()
def people(tmp_path: Path) -> dict[str, tuple[int, TestClient]]:
    """The public rows of the small download, the master user and anna, each signed in."""
    source = tmp_path / "library.sqlite"
    with sqlite3.connect(source) as connection:
        connection.executescript(SOURCE_SCHEMA + ROWS)
    with session() as db:
        import_library(db, read_source(source), seed=None)
    catalogue.forget()
    master_id = users.ensure_master_user()
    users.set_password(master_id, "master-password")
    anna = users.create_user("anna", "anna-password")
    return {
        "master": (master_id, client_of("master", "master-password")),
        "anna": (anna.id, client_of("anna", "anna-password")),
    }


def song_id(path: str) -> int:
    with session() as db:
        found = db.scalar(select(Song.id).where(Song.external_key == external_key(path)))
    assert found is not None
    return found


ALIVE = "/singles/bee-gees/stayin-alive"
GIVE = "/singles/pitbull/give-me-everything"
BILLIE = "/singles/michael-jackson/billie-jean"


def ready(on: TestClient, seconds: float = 6.0) -> str:
    """A project of the Personal Vault with its piano sheet saved."""
    part = uploaded(seconds, on=on)
    make_ready(part, seconds, on=on)
    return part


def titles(answer: dict) -> list[str]:
    return [row["title"] for row in answer["rows"]]


# ----------------------------------------------------------------- the list


def test_the_songs_are_searched_filtered_and_sorted(people: dict) -> None:
    _, anna = people["anna"]
    every = anna.get("/public/songs").json()
    assert every["total"] == 5
    # By popularity first; a song with no week last.
    assert titles(every)[-1] == "What It's Like"
    assert every["rows"][0]["popularity"] >= every["rows"][1]["popularity"]
    # Words in any order, title and artists, case and accents ignored.
    assert titles(anna.get("/public/songs", params={"q": "alive GEES"}).json()) == ["Stayin' Alive"]
    assert titles(anna.get("/public/songs", params={"q": "ne-yo"}).json()) == ["Give Me Everything"]
    assert catalogue.fold("Beyoncé & Jay-Z") == "beyonce and jay z"
    assert anna.get("/public/songs", params={"q": "nothing like it"}).json()["total"] == 0
    # A decade, from the year; the facets count what each value would leave.
    seventies = anna.get("/public/songs", params={"decade": 1970}).json()
    assert titles(seventies) == ["Stayin' Alive"]
    decades = {f["label"]: f["count"] for f in seventies["facets"]["decades"]}
    assert decades == {"70s": 1, "80s": 1, "10s": 1}
    assert [f["value"] for f in seventies["facets"]["regions"]] == ["worldwide"]
    assert anna.get("/public/songs", params={"region": "worldwide"}).json()["total"] == 5
    # spain and catalan exist since revision 0006 (Phase 16); no song of this download is there
    assert anna.get("/public/songs", params={"region": "spain"}).json()["total"] == 0
    assert anna.get("/public/songs", params={"region": "mars"}).status_code == 422
    # By title, and by year with no year last both ways.
    by_title = anna.get("/public/songs", params={"sort": "title", "dir": "asc"}).json()
    assert titles(by_title)[:2] == ["Billie Jean", "Give Me Everything"]
    by_year = anna.get("/public/songs", params={"sort": "year", "dir": "desc"}).json()
    assert [row["year"] for row in by_year["rows"]] == [2011, 1983, 1977, None, None]
    # One page at a time.
    page = anna.get("/public/songs", params={"limit": 2, "offset": 2}).json()
    assert page["total"] == 5 and len(page["rows"]) == 2


def test_the_popularity_of_a_decade_counts_only_its_weeks(people: dict) -> None:
    _, anna = people["anna"]
    # Billie Jean has its 1983 weeks and the 2009 weeks of its re-entry (one song, Phase 12).
    all_time = next(
        row for row in anna.get("/public/songs").json()["rows"] if row["title"] == "Billie Jean"
    )
    eighties = anna.get("/public/songs", params={"decade": 1980}).json()["rows"][0]
    assert eighties["title"] == "Billie Jean"
    assert 0 < eighties["popularity"] < all_time["popularity"]


# ------------------------------------------------------------ song, artist


def test_one_song_has_its_metadata_and_no_version_yet(people: dict) -> None:
    _, anna = people["anna"]
    song = anna.get(f"/public/songs/{song_id(ALIVE)}").json()
    assert (song["title"], song["year"], song["decade"]) == ("Stayin' Alive", 1977, "70s")
    assert [a["name"] for a in song["artists"]] == ["Bee Gees"]
    assert [(a["title"], a["track"]) for a in song["albums"]] == [("Saturday Night Fever", 1)]
    assert song["regions"] == ["Worldwide"]
    chart = song["charts"][0]
    assert (chart["best"], chart["weeks"], chart["first"]) == (1, 2, "1977-12-10")
    assert song["hasLyrics"] is True
    assert anna.get(f"/public/songs/{song_id(ALIVE)}/lyrics").json()["text"].startswith("Well")
    assert (song["fixed"], song["others"], song["inLibrary"]) == ([], [], None)
    # A song with no version cannot be added to a library.
    answer = anna.post(f"/public/songs/{song_id(ALIVE)}/pull", json={})
    assert answer.status_code == 409
    assert answer.json()["detail"] == "This song has no version yet"
    assert anna.get("/public/songs/999999").status_code == 404


def test_an_artist_has_its_songs_and_albums_by_popularity(people: dict) -> None:
    _, anna = people["anna"]
    listed = anna.get("/public/artists", params={"q": "jackson"}).json()
    assert [row["name"] for row in listed["rows"]] == ["Michael Jackson"]
    artist = anna.get(f"/public/artists/{listed['rows'][0]['id']}").json()
    assert [one["title"] for one in artist["songs"]] == ["Billie Jean"]
    assert [one["title"] for one in artist["albums"]] == ["Thriller"]
    assert artist["withVersions"] == 0
    assert anna.post(f"/public/artists/{artist['id']}/pull").status_code == 409
    by_name = anna.get("/public/artists", params={"sort": "name", "dir": "asc"}).json()
    assert [row["name"] for row in by_name["rows"]][:2] == ["Bee Gees", "Bing Crosby"]


def test_suggestions_are_the_most_popular_matches(people: dict) -> None:
    _, anna = people["anna"]
    found = anna.get("/public/suggest", params={"q": "billie"}).json()
    assert [one["title"] for one in found["songs"]] == ["Billie Jean"]
    by_artist = anna.get("/public/suggest", params={"artist": "pitbull"}).json()
    assert [one["title"] for one in by_artist["songs"]] == ["Give Me Everything"]
    assert [
        one["name"] for one in anna.get("/public/suggest", params={"q": "bee"}).json()["artists"]
    ] == ["Bee Gees"]


# ------------------------------------------------------------- versions, likes


def test_a_public_version_is_a_copy_with_likes(people: dict) -> None:
    master_id, master = people["master"]
    anna_id, anna = people["anna"]
    source = ready(master)
    alive = song_id(ALIVE)
    hard = public.place_version(
        source, song_id=alive, name="hard", creator_id=master_id, user_version=False
    )
    public.place_version(
        ready(anna), song_id=alive, name="easy", creator_id=anna_id, user_version=True
    )
    # The source stays where it was, unchanged; the version is a copy in the public layer.
    assert hard != source
    with session() as db:
        assert db.get(Project, source).layer == "vault"  # type: ignore[union-attr]
        assert db.get(Project, hard).layer == "public"  # type: ignore[union-attr]
    with pytest.raises(ValueError):
        public.place_version(
            source, song_id=alive, name="Hard Version", creator_id=master_id, user_version=False
        )

    song = anna.get(f"/public/songs/{alive}").json()
    assert [(v["name"], v["creator"], v["ready"]) for v in song["fixed"]] == [
        ("hard", "master", True)
    ]
    assert [(g["username"], [v["name"] for v in g["versions"]]) for g in song["others"]] == [
        ("anna", ["easy"])
    ]
    assert song["defaultVersion"] == "hard"
    # The list counts the versions at once.
    row = next(r for r in anna.get("/public/songs").json()["rows"] if r["id"] == alive)
    assert row["versions"] == 2

    # A like once per user; a project that is not a public version cannot be liked.
    assert anna.put(f"/public/likes/{hard}").json() == {"likes": 1, "liked": True}
    assert anna.put(f"/public/likes/{hard}").json() == {"likes": 1, "liked": True}
    assert master.put(f"/public/likes/{hard}").json()["likes"] == 2
    assert anna.get(f"/public/songs/{alive}").json()["fixed"][0]["liked"] is True
    assert anna.delete(f"/public/likes/{hard}").json() == {"likes": 1, "liked": False}
    assert anna.put(f"/public/likes/{source}").status_code == 404

    # Every user reads a public version (and plays it); only the master user may write it.
    assert anna.get(f"/projects/{hard}").status_code == 200
    assert anna.get(f"/pieces/{hard}/status").status_code == 200
    assert anna.patch(f"/audio/{hard}", json={"alias": "Mine"}).status_code == 403


# ------------------------------------------------------------ add to my library


def test_a_song_is_added_with_its_default_version_once(people: dict) -> None:
    master_id, master = people["master"]
    anna_id, anna = people["anna"]
    alive = song_id(ALIVE)
    hard = public.place_version(
        ready(master), song_id=alive, name="hard", creator_id=master_id, user_version=False
    )
    easy = public.place_version(
        ready(master), song_id=alive, name="easy", creator_id=master_id, user_version=True
    )
    with session() as db:
        audio_files = db.scalar(select(func.count()).select_from(AudioFile))

    pulled = anna.post(f"/public/songs/{alive}/pull", json={}).json()
    assert (pulled["songs"], pulled["versions"], pulled["already"]) == (1, 1, 0)
    mine = anna.get(f"/library/songs/{pulled['id']}").json()
    assert (mine["title"], [a["name"] for a in mine["artists"]]) == ("Stayin' Alive", ["Bee Gees"])
    assert [v["name"] for v in mine["versions"]] == ["hard"]
    copy = mine["versions"][0]["projectId"]
    with session() as db:
        song = db.get(Song, pulled["id"])
        row = db.get(Project, copy)
        artist = db.scalar(select(Artist).where(Artist.owner_id == anna_id))
        assert song is not None and song.public_id == alive and song.year == 1977
        assert row is not None and (row.layer, row.owner_id, row.public_source_id) == (
            "private",
            anna_id,
            hard,
        )
        assert artist is not None and artist.public_id is not None
        # No audio bytes copied.
        assert db.scalar(select(func.count()).select_from(AudioFile)) == audio_files
    # The copy has its piano sheet, as every version of a library.
    assert flow.sheet_ready(bundle.read_project(copy))
    assert anna.get(f"/public/songs/{alive}").json()["inLibrary"] == pulled["id"]

    # Again: nothing new. Then the other version, by its name and its user.
    again = anna.post(f"/public/songs/{alive}/pull", json={}).json()
    assert (again["id"], again["versions"], again["already"]) == (pulled["id"], 0, 1)
    more = anna.post(f"/public/songs/{alive}/pull", json={"projects": [easy]}).json()
    assert more["versions"] == 1
    names = [v["name"] for v in anna.get(f"/library/songs/{pulled['id']}").json()["versions"]]
    assert names == ["hard", "easy (master)"]
    song = anna.get(f"/public/songs/{alive}").json()
    assert {v["name"]: v["inLibrary"] is not None for v in song["fixed"]} == {"hard": True}
    # Not a version of this song.
    assert (
        anna.post(f"/public/songs/{song_id(GIVE)}/pull", json={"projects": [hard]}).status_code
        == 404
    )


def test_an_artist_and_a_playlist_add_their_songs_with_a_version(people: dict) -> None:
    master_id, master = people["master"]
    anna_id, anna = people["anna"]
    alive = song_id(ALIVE)
    hard = public.place_version(
        ready(master), song_id=alive, name="hard", creator_id=master_id, user_version=False
    )
    bee_gees = anna.get("/public/artists", params={"q": "bee gees"}).json()["rows"][0]
    assert bee_gees["withVersions"] == 1

    added = anna.post(f"/public/artists/{bee_gees['id']}/pull").json()
    assert (added["songs"], added["versions"]) == (1, 1)
    assert anna.get(f"/library/artists/{added['id']}").json()["name"] == "Bee Gees"

    with session() as db:
        playlist = Playlist(scope="public", title="Disco")
        db.add(playlist)
        db.flush()
        db.add(
            PlaylistItem(
                playlist_id=playlist.id,
                position=0,
                song_id=alive,
                project_id=hard,
                from_ms=0,
                to_ms=2000,
            )
        )
        db.add(PlaylistItem(playlist_id=playlist.id, position=1, song_id=song_id(GIVE)))
        playlist_id = playlist.id
    listed = anna.get("/public/playlists").json()
    assert [(p["title"], p["songs"]) for p in listed] == [("Disco", 2)]
    shown = anna.get(f"/public/playlists/{playlist_id}").json()
    assert [(i["songTitle"], i["versionName"]) for i in shown["items"]] == [
        ("Stayin' Alive", "hard"),
        ("Give Me Everything", None),
    ]

    made = anna.post(f"/public/playlists/{playlist_id}/pull").json()
    # The song with no version is left out; the other was already in the library.
    assert (made["songs"], made["versions"], made["already"]) == (1, 0, 1)
    mine = anna.get(f"/playlists/{made['id']}").json()
    assert [(i["songTitle"], i["fromMs"], i["toMs"]) for i in mine["items"]] == [
        ("Stayin' Alive", 0, 2000)
    ]
    with session() as db:
        item_project = db.scalar(
            select(PlaylistItem.project_id).where(PlaylistItem.playlist_id == made["id"])
        )
        assert db.get(Project, item_project).public_source_id == hard  # type: ignore[union-attr]
    assert anna.post(f"/public/playlists/{playlist_id}/pull").json()["id"] == made["id"]


# ------------------------------------------------------- save to library


def test_save_to_library_on_a_public_song_or_artist_links_the_private_rows(people: dict) -> None:
    anna_id, anna = people["anna"]
    give = song_id(GIVE)
    first = anna.post(
        f"/projects/{ready(anna)}/library", json={"publicSongId": give, "version": "original"}
    )
    assert first.status_code == 201, first.text
    second = anna.post(
        f"/projects/{ready(anna)}/library", json={"publicSongId": give, "version": "easy"}
    ).json()
    assert second["songId"] == first.json()["songId"]
    mine = anna.get(f"/library/songs/{second['songId']}").json()
    assert [a["name"] for a in mine["artists"]] == ["Pitbull", "Ne-Yo"]
    assert [v["name"] for v in mine["versions"]] == ["original", "easy"]
    with session() as db:
        assert db.get(Song, second["songId"]).public_id == give  # type: ignore[union-attr]
    assert anna.get(f"/public/songs/{give}").json()["inLibrary"] == second["songId"]

    # A new song by a public artist: the private artist stands for it.
    jackson = anna.get("/public/artists", params={"q": "michael jackson"}).json()["rows"][0]["id"]
    saved = anna.post(
        f"/projects/{ready(anna)}/library",
        json={
            "song": "Piano medley",
            "artist": "Michael Jackson",
            "publicArtistId": jackson,
            "version": "v1",
        },
    ).json()
    song = anna.get(f"/library/songs/{saved['songId']}").json()
    assert [a["name"] for a in song["artists"]] == ["Michael Jackson"]
    assert (
        anna.get(f"/public/artists/{jackson}").json()["inLibrary"] == song["artists"][0]["artistId"]
    )


def test_an_own_song_of_the_same_title_and_artist_is_linked_not_copied(people: dict) -> None:
    master_id, master = people["master"]
    anna_id, anna = people["anna"]
    alive = song_id(ALIVE)
    hard = public.place_version(
        ready(master), song_id=alive, name="hard", creator_id=master_id, user_version=False
    )
    own = anna.post(
        f"/projects/{ready(anna)}/library",
        json={"song": "stayin' alive", "artist": "bee gees", "version": "mine"},
    ).json()
    pulled = anna.post(f"/public/songs/{alive}/pull", json={}).json()
    assert pulled["id"] == own["songId"]
    mine = anna.get(f"/library/songs/{own['songId']}").json()
    assert [v["name"] for v in mine["versions"]] == ["mine", "hard"]
    with session() as db:
        assert (
            db.scalar(select(func.count()).select_from(Song).where(Song.owner_id == anna_id)) == 1
        )
        assert db.scalar(select(func.count()).select_from(PrivateVersion)) == 2
        assert db.scalar(select(Project.public_source_id).where(Project.public_source_id == hard))


def test_the_list_sees_a_change_of_the_public_rows(people: dict) -> None:
    _, anna = people["anna"]
    assert (
        anna.get("/public/songs", params={"q": "white christmas"}).json()["rows"][0]["year"] is None
    )
    with session() as db:
        db.execute(update(Song).where(Song.title == "White Christmas").values(year=1942))
    assert (
        anna.get("/public/songs", params={"q": "white christmas"}).json()["rows"][0]["year"] == 1942
    )
