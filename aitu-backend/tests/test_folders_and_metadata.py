"""Folders and metadata of My projects and My Library (implementation 04-3, Phase 1, plan sections 4.2
and 4.4): folders that nest, a parent folder made on top of folders, a move that cannot go into
itself, a folder deleted with its child folders and never an item; an item in several folders; the
metadata of a song and of a project, the suggestions, the info button's three cases; the metadata of
a song shared by all its versions and their edit copies; and the paths between the two pages (Add to
my library, Edit, Save to library, Duplicate).

Two users sign in through ``/auth``; the public rows come from the small download of
``test_public_import``."""

from __future__ import annotations

import shutil

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from aitu_backend.db.database import session
from aitu_backend.db.models import (
    Folder,
    FolderProject,
    PrivateTagValue,
    ProjectTag,
    SongTag,
    TagCategory,
    TagValue,
)
from aitu_backend.library import flow, public, rows
from aitu_backend.storage import bundle
from test_public import ALIVE, people, ready, song_id  # noqa: F401 - `people` is a fixture

pytestmark = pytest.mark.real_login

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")


def vault_project(owner: int, title: str = "Piece") -> str:
    return bundle.create_project(owner_id=owner, title=title).id


def private_song(owner: int, title: str, artist: str | None = None) -> int:
    with session() as db:
        return rows.make_song(db, owner, title, artist).id


def folder(client: TestClient, area: str, name: str, parent: int | None = None) -> int:
    answer = client.post("/folders", json={"area": area, "name": name, "parentId": parent})
    assert answer.status_code == 201, answer.text
    return answer.json()["id"]


def tree(client: TestClient, area: str) -> dict[str, int | None]:
    """``folder name -> the name of its parent`` (names are unique in these tests)."""
    found = client.get("/folders", params={"area": area}).json()
    names = {one["id"]: one["name"] for one in found}
    return {one["name"]: names.get(one["parentId"]) for one in found}  # type: ignore[misc]


def project_row(client: TestClient, project_id: str) -> dict:
    return next(one for one in client.get("/projects").json() if one["id"] == project_id)


def song_row(client: TestClient, song: int) -> dict:
    return next(one for one in client.get("/library/songs").json() if one["id"] == song)


# ------------------------------------------------------------------------ folders


def test_folders_nest_and_a_parent_folder_keeps_the_items(people: dict) -> None:  # noqa: F811
    anna_id, anna = people["anna"]
    piece = vault_project(anna_id, "Concerning Hobbits")
    films = folder(anna, "projects", "Films")
    rings = folder(anna, "projects", "The Lord of the Rings", films)
    assert anna.put(f"/folders/projects/{piece}", json={"folders": [rings]}).status_code == 200
    assert project_row(anna, piece)["folders"] == [rings]

    # Two folders with the same parent cannot have the same name (ignoring case); the other tree can.
    assert anna.post("/folders", json={"area": "projects", "name": "films"}).status_code == 409
    assert anna.post("/folders", json={"area": "library", "name": "Films"}).status_code == 201

    # A parent folder on top of "Films": the folder ids stay, so the project is still in its folder.
    made = anna.post(
        "/folders/parent", json={"area": "projects", "name": "Work", "children": [films]}
    )
    assert made.status_code == 201, made.text
    assert tree(anna, "projects") == {
        "Work": None,
        "Films": "Work",
        "The Lord of the Rings": "Films",
    }
    assert project_row(anna, piece)["folders"] == [rings]

    # A folder cannot go inside itself or inside one of its own folders; it can go to the top.
    work = made.json()["id"]
    assert anna.post(f"/folders/{work}/move", json={"parentId": rings}).status_code == 409
    assert anna.post(f"/folders/{work}/move", json={"parentId": work}).status_code == 409
    assert anna.post(f"/folders/{rings}/move", json={"parentId": None}).status_code == 200
    assert tree(anna, "projects")["The Lord of the Rings"] is None
    renamed = anna.patch(f"/folders/{rings}", json={"name": "LOTR"})
    assert renamed.status_code == 200 and renamed.json()["name"] == "LOTR"


def test_deleting_a_folder_deletes_its_folders_and_never_an_item(
    people: dict,
) -> None:  # noqa: F811
    anna_id, anna = people["anna"]
    piece = vault_project(anna_id)
    other = vault_project(anna_id, "Other")
    films = folder(anna, "projects", "Films")
    rings = folder(anna, "projects", "Rings", films)
    kept = folder(anna, "projects", "Kept")
    # One project in two folders, one inside the folder that goes.
    assert (
        anna.put(f"/folders/projects/{piece}", json={"folders": [rings, kept]}).status_code == 200
    )
    assert anna.put(f"/folders/projects/{other}", json={"folders": [films]}).status_code == 200

    assert anna.delete(f"/folders/{films}").status_code == 204
    assert tree(anna, "projects") == {"Kept": None}
    assert project_row(anna, piece)["folders"] == [kept]
    assert project_row(anna, other)["folders"] == []
    with session() as db:
        assert db.scalar(select(func.count()).select_from(Folder)) == 1
        assert db.scalar(select(func.count()).select_from(FolderProject)) == 1


def test_a_song_is_in_several_folders_of_my_library(people: dict) -> None:  # noqa: F811
    anna_id, anna = people["anna"]
    song = private_song(anna_id, "May It Be", "Enya")
    films = folder(anna, "library", "Films")
    calm = folder(anna, "library", "Calm")
    assert anna.put(f"/folders/songs/{song}", json={"folders": [films, calm]}).status_code == 200
    assert sorted(song_row(anna, song)["folders"]) == sorted([films, calm])
    assert sorted(anna.get(f"/library/songs/{song}").json()["folders"]) == sorted([films, calm])
    # A folder of the other tree is not one of My Library's.
    project_folder = folder(anna, "projects", "Films")
    answer = anna.put(f"/folders/songs/{song}", json={"folders": [project_folder]})
    assert answer.status_code == 404
    # Deleting the song deletes its links.
    assert anna.delete(f"/library/songs/{song}").status_code == 204
    assert anna.get("/folders", params={"area": "library"}).status_code == 200


# ----------------------------------------------------------------------- metadata


def test_the_metadata_of_a_song_and_of_a_project(people: dict) -> None:  # noqa: F811
    anna_id, anna = people["anna"]
    song = private_song(anna_id, "May It Be", "Enya")
    piece = vault_project(anna_id)
    tags = [
        {"category": "films", "value": "The Lord of the Rings"},
        {"category": "tv_shows", "value": "Rings of Power"},
    ]
    answer = anna.put(f"/metadata/songs/{song}", json={"tags": tags})
    assert answer.status_code == 200, answer.text
    assert song_row(anna, song)["tags"] == tags
    # The project's value is typed again in other letters: it is the same secondary key.
    same = [{"category": "films", "value": "the lord of the rings"}]
    assert anna.put(f"/metadata/projects/{piece}", json={"tags": same}).status_code == 200
    assert project_row(anna, piece)["tags"] == [tags[0]]
    with session() as db:
        assert db.scalar(select(func.count()).select_from(PrivateTagValue)) == 2

    # An unknown primary key is refused; an empty list takes every row away, and a secondary key
    # no item uses any more is forgotten.
    bad = anna.put(f"/metadata/songs/{song}", json={"tags": [{"category": "books", "value": "x"}]})
    assert bad.status_code == 422
    assert anna.put(f"/metadata/songs/{song}", json={"tags": []}).status_code == 200
    with session() as db:
        values = list(db.scalars(select(PrivateTagValue.value)))
    assert values == ["The Lord of the Rings"]


def test_the_suggestions_and_the_public_library_stay_apart(people: dict) -> None:  # noqa: F811
    anna_id, anna = people["anna"]
    song = private_song(anna_id, "May It Be")
    with session() as db:
        films = db.scalar(select(TagCategory.id).where(TagCategory.name == "films"))
        db.add(TagValue(category_id=films, value="Shrek"))
        public_values = db.scalar(select(func.count()).select_from(TagValue))
    mine = [{"category": "films", "value": "The Lord of the Rings"}]
    assert anna.put(f"/metadata/songs/{song}", json={"tags": mine}).status_code == 200

    keys = anna.get("/metadata/keys").json()
    assert keys["categories"] == ["films", "video_games", "tv_shows", "adverts"]
    offered = {(one["value"], one["mine"]) for one in keys["suggestions"]}
    assert {("The Lord of the Rings", True), ("Shrek", False)} <= offered
    # The private value is not a public one, and the public list of tags does not show it.
    with session() as db:
        assert db.scalar(select(func.count()).select_from(TagValue)) == public_values
    facets = anna.get("/public/songs").json()["facets"]["tags"]
    assert all(one["label"] != "The Lord of the Rings" for one in facets)
    # A deleted song's values are not suggested any more.
    assert anna.delete(f"/library/songs/{song}").status_code == 204
    after = {
        one["value"] for one in anna.get("/metadata/keys").json()["suggestions"] if one["mine"]
    }
    assert "The Lord of the Rings" not in after
    assert (
        anna.put(
            f"/metadata/songs/{private_song(anna_id, 'Again')}", json={"tags": mine}
        ).status_code
        == 200
    )
    # Another user sees neither the value nor the song's metadata.
    _, master = people["master"]
    assert all(
        one["value"] != "The Lord of the Rings"
        for one in master.get("/metadata/keys").json()["suggestions"]
    )


# ------------------------------------------------------- the paths between the two pages


@needs_ffmpeg
def test_the_metadata_is_the_songs_for_every_version(people: dict) -> None:  # noqa: F811
    """The user, 2026-10-29: the metadata belongs to the song, never to one version of it."""
    anna_id, anna = people["anna"]
    first = anna.post(
        f"/projects/{ready(anna)}/library",
        json={"song": "Song of Storms", "artist": "Koji", "version": "Original"},
    ).json()
    song = first["songId"]
    second = anna.post(
        f"/projects/{ready(anna)}/library", json={"songId": song, "version": "Easy"}
    ).json()
    storms = [{"category": "video_games", "value": "Zelda"}]
    assert anna.put(f"/metadata/songs/{song}", json={"tags": storms}).status_code == 200
    for version in (first, second):
        info = anna.get(f"/metadata/info/{version['projectId']}").json()
        assert (info["kind"], info["songId"], info["tags"]) == ("song", song, storms)

    # Edit the Easy version: the copy's info button and its row are the song's, and a change made
    # there is every version's.
    copy = anna.post(f"/projects/{second['projectId']}/edit").json()["id"]
    assert project_row(anna, copy)["tags"] == storms
    both = [{"category": "films", "value": "Ocarina"}] + storms
    assert anna.put(f"/metadata/projects/{copy}", json={"tags": both}).status_code == 200
    assert anna.get(f"/metadata/info/{first['projectId']}").json()["tags"] == both
    assert song_row(anna, song)["tags"] == both
    with session() as db:
        assert db.scalar(select(func.count()).select_from(ProjectTag)) == 0

    # A duplicate of the copy edits the same version: the song's metadata, with no rows of its own.
    twin = anna.post(f"/projects/{copy}/duplicate", json={}).json()["id"]
    info = anna.get(f"/metadata/info/{twin}").json()
    assert (info["kind"], info["songId"], info["tags"]) == ("song", song, both)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(ProjectTag)) == 0

    # The copy saved as a version of another song: that song gets the metadata, this one keeps it.
    other = anna.post(
        f"/projects/{copy}/library", json={"song": "Saria", "artist": "Koji", "version": "v1"}
    ).json()["songId"]
    assert song_row(anna, other)["tags"] == both
    assert song_row(anna, song)["tags"] == both

    # The version an edit copy edits is deleted: the copy keeps the song's metadata as its own.
    orphan = anna.post(f"/projects/{first['projectId']}/edit").json()["id"]
    assert anna.delete(f"/library/versions/{first['versionId']}").status_code == 204
    assert anna.get(f"/metadata/info/{orphan}").json()["kind"] == "project"
    assert project_row(anna, orphan)["tags"] == both
    assert anna.put(f"/metadata/projects/{orphan}", json={"tags": []}).status_code == 200
    assert song_row(anna, song)["tags"] == both


@needs_ffmpeg
def test_metadata_follows_the_work_between_the_two_pages(people: dict) -> None:  # noqa: F811
    master_id, master = people["master"]
    anna_id, anna = people["anna"]
    alive = song_id(ALIVE)
    public.place_version(
        ready(master), song_id=alive, name="hard", creator_id=master_id, user_version=False
    )
    with session() as db:
        films = db.scalar(select(TagCategory.id).where(TagCategory.name == "films"))
        fever = TagValue(category_id=films, value="Saturday Night Fever")
        db.add(fever)
        db.flush()
        db.add(SongTag(song_id=alive, tag_value_id=fever.id))
    # Add to my library: the song arrives with its film; the public rows do not change.
    pulled = anna.post(f"/public/songs/{alive}/pull", json={}).json()
    film = {"category": "films", "value": "Saturday Night Fever"}
    assert anna.get(f"/library/songs/{pulled['id']}").json()["tags"] == [film]
    with session() as db:
        assert db.scalar(select(func.count()).select_from(SongTag)) == 1

    # Edit: the copy in My projects shows the song's metadata on its info button.
    version = anna.get(f"/library/songs/{pulled['id']}").json()["versions"][0]
    copy = anna.post(f"/projects/{version['projectId']}/edit").json()
    info = anna.get(f"/metadata/info/{copy['id']}").json()
    assert (info["kind"], info["songId"], info["editable"]) == ("song", pulled["id"], True)
    assert (info["tags"], info["artists"]) == ([film], ["Bee Gees"])
    # One more row from the copy is the song's at once; the copy goes into a folder.
    more = [film, {"category": "adverts", "value": "Disco"}]
    assert anna.put(f"/metadata/projects/{copy['id']}", json={"tags": more}).status_code == 200
    assert anna.get(f"/library/songs/{pulled['id']}").json()["tags"] == [film, more[1]]
    folder_id = folder(anna, "projects", "Disco")
    assert (
        anna.put(f"/folders/projects/{copy['id']}", json={"folders": [folder_id]}).status_code
        == 200
    )
    saved = anna.post(f"/projects/{copy['id']}/library", json={"replace": True})
    assert saved.status_code == 201, saved.text
    assert anna.get(f"/library/songs/{pulled['id']}").json()["tags"] == [film, more[1]]
    with session() as db:
        assert db.scalar(select(func.count()).select_from(FolderProject)) == 0

    # The info button on the version of My Library and on the public version.
    mine = anna.get(f"/metadata/info/{version['projectId']}").json()
    assert (mine["kind"], mine["songId"], mine["editable"]) == ("song", pulled["id"], True)
    hard = anna.get(f"/public/songs/{alive}").json()["fixed"][0]["projectId"]
    seen = anna.get(f"/metadata/info/{hard}").json()
    assert (seen["kind"], seen["editable"], seen["tags"]) == ("public", False, [film])


@needs_ffmpeg
def test_save_to_library_and_duplicate_carry_the_metadata(people: dict) -> None:  # noqa: F811
    anna_id, anna = people["anna"]
    # A project made by the app has the id of its first part.
    piece = ready(anna)
    tags = [{"category": "video_games", "value": "Zelda"}]
    assert anna.put(f"/metadata/projects/{piece}", json={"tags": tags}).status_code == 200
    games = folder(anna, "projects", "Games")
    assert anna.put(f"/folders/projects/{piece}", json={"folders": [games]}).status_code == 200

    # Duplicate: the copy has the metadata and stays in the folder.
    copy = anna.post(f"/projects/{piece}/duplicate", json={}).json()
    assert project_row(anna, copy["id"])["tags"] == tags
    assert project_row(anna, copy["id"])["folders"] == [games]

    # Save to library: the song gets the metadata; the project leaves the folders of My projects.
    saved = anna.post(
        f"/projects/{piece}/library",
        json={"song": "Song of Storms", "artist": "Koji", "version": "v1"},
    )
    assert saved.status_code == 201, saved.text
    assert anna.get(f"/library/songs/{saved.json()['songId']}").json()["tags"] == tags
    with session() as db:
        assert list(db.scalars(select(FolderProject.project_id))) == [copy["id"]]


def test_a_level_copy_shares_the_songs_metadata_and_is_not_an_edit_copy(people: dict) -> None:  # noqa: F811
    """Implementation 04-3, Phase 4 (the user, 2026-10-30): a level of the whole sheet is a new project linked to the
    project it was written from (``level_of``), never a second edit copy of the version."""
    anna_id, anna = people["anna"]
    saved = anna.post(
        f"/projects/{ready(anna)}/library",
        json={"song": "99 Red Balloons", "artist": "Nena", "version": "Original"},
    ).json()
    song = saved["songId"]
    copy = anna.post(f"/projects/{saved['projectId']}/edit").json()["id"]
    films = [{"category": "films", "value": "Atomic Blonde"}]
    assert anna.put(f"/metadata/songs/{song}", json={"tags": films}).status_code == 200

    # A level of the edit copy, and a level of the version itself (from My Library): both share the song's.
    easy, _ = flow.level_copy(copy, owner=anna_id, title="99 Red Balloons · Easy")
    hard, _ = flow.level_copy(saved["projectId"], owner=anna_id, title="99 Red Balloons · Hard")
    for level in (easy, hard):
        info = anna.get(f"/metadata/info/{level}").json()
        assert (info["kind"], info["songId"], info["tags"]) == ("song", song, films)
        row = project_row(anna, level)
        assert row["tags"] == films and row["basedOn"] is None and row["editing"] is None
        assert row["levelSong"]["songId"] == song and row["levelSong"]["artists"] == ["Nena"]
    assert project_row(anna, easy)["levelOf"] == copy
    # A level of a level points at the same original.
    again, _ = flow.level_copy(easy, owner=anna_id, title="99 Red Balloons · Easy 2")
    assert project_row(anna, again)["levelOf"] == copy
    # Edit on the version still opens the user's own copy, never a level copy.
    assert anna.post(f"/projects/{saved['projectId']}/edit").json()["id"] == copy
    # A change made from a level copy is the song's.
    both = films + [{"category": "tv_shows", "value": "Dark"}]
    assert anna.put(f"/metadata/projects/{easy}", json={"tags": both}).status_code == 200
    assert song_row(anna, song)["tags"] == both
    with session() as db:
        assert db.scalar(select(func.count()).select_from(ProjectTag)) == 0

    # A project with no song: its level copy shares the project's own rows, and keeps them when it is deleted.
    plain = vault_project(anna_id, "Sketch")
    assert anna.put(f"/metadata/projects/{plain}", json={"tags": films}).status_code == 200
    sketch, _ = flow.level_copy(plain, owner=anna_id, title="Sketch · Medium")
    assert anna.get(f"/metadata/info/{sketch}").json()["tags"] == films
    assert anna.put(f"/metadata/projects/{sketch}", json={"tags": both}).status_code == 200
    assert project_row(anna, plain)["tags"] == both
    assert anna.delete(f"/projects/{plain}").status_code == 204
    row = project_row(anna, sketch)
    assert row["levelOf"] is None and row["tags"] == both
    assert bundle.read_project(sketch).level_of is None

    # Save to library: the level copy becomes a version of the song and stops being a copy.
    out = anna.post(f"/projects/{hard}/library", json={"songId": song, "version": "Hard"}).json()
    assert out["songId"] == song and bundle.read_project(hard).level_of is None
    assert song_row(anna, song)["tags"] == both

    # Nobody else makes a level of anna's song.
    with pytest.raises(flow.Refused):
        flow.level_copy(copy, owner=people["master"][0], title="no")
