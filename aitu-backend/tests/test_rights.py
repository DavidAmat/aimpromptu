"""The rights table of plan section 9.3, one test per row, with two users and the master user
(implementation 02, Phase 4). Every request signs in through `/auth`."""

from __future__ import annotations

import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile

from aitu_backend.auth import rights
from aitu_backend.auth.context import CurrentUser
from aitu_backend.db import users
from aitu_backend.db.database import session
from aitu_backend.db.models import LibraryShare, PrivateVersion, Request
from aitu_backend.library import rows
from aitu_backend.main import create_app
from aitu_backend.storage import bundle
from aitu_backend.transcription import jobs, pipeline
from aitu_backend.transcription.engine import NoteEvent

pytestmark = pytest.mark.real_login


def client_of(username: str, password: str) -> TestClient:
    client = TestClient(create_app())
    assert (
        client.post("/auth/login", json={"username": username, "password": password}).status_code
        == 200
    )
    return client


@pytest.fixture()
def people() -> dict[str, tuple[int, TestClient]]:
    """The master user and two users, each signed in."""
    master_id = users.ensure_master_user()
    users.set_password(master_id, "master-password")
    anna = users.create_user("anna", "anna-password")
    joan = users.create_user("joan", "joan-password")
    return {
        "master": (master_id, client_of("master", "master-password")),
        "anna": (anna.id, client_of("anna", "anna-password")),
        "joan": (joan.id, client_of("joan", "joan-password")),
    }


def project(owner: int, layer: str, title: str = "Piece") -> str:
    made = bundle.create_project(owner_id=owner, title=title, layer=layer)
    pipeline.save_note_events(made.id, [NoteEvent(midi_note=60, start=0.1, end=0.5)], 2.0, title)
    return made.id


def reads(client: TestClient, part: str) -> int:
    return client.get(f"/pieces/{part}/status").status_code


def writes(client: TestClient, part: str) -> int:
    return client.patch(f"/audio/{part}", json={"alias": "Renamed"}).status_code


# ------------------------------------------------------------------- one test per row


def test_row_1_a_project_in_a_personal_vault(people: dict) -> None:
    anna_id, anna = people["anna"]
    _, joan = people["joan"]
    _, master = people["master"]
    part = project(anna_id, "vault")
    assert (reads(anna, part), writes(anna, part)) == (200, 200)
    # Not hers: it does not exist for her, and not even the master user reads it.
    for other in (joan, master):
        assert (reads(other, part), writes(other, part)) == (404, 404)
        assert other.get(f"/sheet/{part}/words").status_code == 404
        assert other.get(f"/sheet/{part}").status_code == 404
        assert other.delete(f"/audio/{part}").status_code == 404


def test_row_2_a_project_in_a_private_library(people: dict) -> None:
    anna_id, anna = people["anna"]
    joan_id, joan = people["joan"]
    _, master = people["master"]
    part = project(anna_id, "private")
    # Anna reads her library and changes it only through a copy in her vault (Phase 6).
    assert (reads(anna, part), writes(anna, part)) == (200, 403)
    # The new sheet (implementation 03, Phase 5): drawn for her; Sonnet writes it only in a copy.
    assert anna.get(f"/sheet/{part}").status_code == 200
    assert anna.post(f"/sheet/{part}/llm").status_code == 403
    edit = anna.post(f"/projects/{part}/edit")
    assert edit.status_code == 200 and edit.json()["basedOn"] == part
    assert writes(anna, edit.json()["id"]) == 200
    assert (reads(joan, part), writes(joan, part)) == (404, 404)
    with session() as db:
        db.add(LibraryShare(owner_id=anna_id, shared_with_id=joan_id))
    # Shared with Joan: she reads it, plays it, and copies it into her own vault; she does not
    # change it.
    assert (reads(joan, part), writes(joan, part)) == (200, 403)
    assert joan.get(f"/audio/{part}").status_code == 200
    # Editing is for the owner: Joan duplicates instead.
    assert joan.post(f"/projects/{part}/edit").status_code == 409
    copy = joan.post(f"/projects/{part}/duplicate", json={})
    assert copy.status_code == 201
    assert writes(joan, copy.json()["id"]) == 200
    assert (reads(master, part), writes(master, part)) == (404, 404)
    # Anna's vault is never shared: only her library.
    vault = project(anna_id, "vault")
    assert reads(joan, vault) == 404


def test_row_3_the_public_library(people: dict) -> None:
    master_id, master = people["master"]
    _, anna = people["anna"]
    part = project(master_id, "public")
    assert (reads(anna, part), writes(anna, part)) == (200, 403)
    assert (reads(master, part), writes(master, part)) == (200, 200)
    # The sheet is drawn for every reader; a read-only route that is a POST (a copy into her own
    # vault) is open to them too.
    assert anna.get(f"/sheet/{part}").status_code == 200
    assert anna.post(f"/projects/{part}/duplicate", json={}).status_code == 201


def test_row_4_a_request(people: dict) -> None:
    master_id = people["master"][0]
    anna_id = people["anna"][0]
    joan_id = people["joan"][0]
    master = CurrentUser(master_id, "master", "master")
    anna = CurrentUser(anna_id, "anna", "user")
    joan = CurrentUser(joan_id, "joan", "user")
    with session() as db:
        request = Request(kind="userVersion", author_id=anna_id, status="open")
        db.add(request)
    assert rights.can_read_request(anna, request) and rights.can_read_request(master, request)
    assert not rights.can_read_request(joan, request)
    assert rights.can_edit_request(anna, request) and not rights.can_edit_request(joan, request)
    assert rights.can_decide_request(master, request) and not rights.can_decide_request(
        anna, request
    )
    request.status = "accepted"
    assert not rights.can_edit_request(anna, request)  # reviewed: the author no longer changes it


def test_row_5_users_and_lab(people: dict) -> None:
    _, master = people["master"]
    _, anna = people["anna"]
    for path in ("/admin/users", "/frame-examples", "/frame-examples/score"):
        assert master.get(path).status_code == 200, path
        assert anna.get(path).status_code == 403, path
    assert (
        anna.post("/admin/users", json={"username": "x1", "password": "x" * 9}).status_code == 403
    )


# ------------------------------------------------------------- scoped lists, owners, jobs


def test_a_paste_reads_its_source_and_writes_its_target(people: dict) -> None:
    """Copy and paste across projects and layers (Phase 8): the source is read, the target is
    written, each with the rights of its row."""
    anna_id, anna = people["anna"]
    joan_id, joan = people["joan"]
    master_id, _ = people["master"]

    def paste(client: TestClient, target: str, source: str) -> int:
        body = {"source": {"part": source, "fromMs": 0, "toMs": 400}, "atMs": 0}
        return client.post(f"/sheet/{target}/paste", json=body).status_code

    mine = project(anna_id, "vault", "Mine")
    own_library = project(anna_id, "private", "My song")
    public = project(master_id, "public", "Everyone's")
    joans = project(joan_id, "vault", "Joan's")
    joans_library = project(joan_id, "private", "Joan's song")
    # From her own vault, her own library and the Public Library.
    assert paste(anna, mine, mine) == 200
    assert paste(anna, mine, own_library) == 200
    assert paste(anna, mine, public) == 200
    # Not from another user's work, which answers as if it did not exist.
    assert paste(anna, mine, joans) == 404
    assert paste(anna, mine, joans_library) == 404
    # From a library shared with her.
    with session() as db:
        db.add(LibraryShare(owner_id=joan_id, shared_with_id=anna_id))
    assert paste(anna, mine, joans_library) == 200
    # Never into a version of a library (it changes through Edit), nor into another user's work.
    assert paste(anna, own_library, mine) == 403
    assert paste(anna, joans, mine) == 404


def test_from_other_projects_reads_every_source(people: dict) -> None:
    """From other projects (Phase 10): every passage is read with the rights of its row, and the
    project made is the user's own."""
    anna_id, anna = people["anna"]
    joan_id, _ = people["joan"]

    def compose(*sources: str) -> int:
        body = {"title": "Mix", "passages": [{"part": one} for one in sources]}
        return anna.post("/projects/compose", json=body).status_code

    mine = project(anna_id, "vault", "Mine")
    own_library = project(anna_id, "private", "My song")
    joans = project(joan_id, "vault", "Joan's")
    assert compose(mine, own_library) == 201
    assert compose(mine, joans) == 404
    made = [row for row in anna.get("/projects").json() if row["title"] == "Mix"]
    assert len(made) == 1
    # Its parts are hers to change; another user's are not even there.
    assert anna.get(f"/projects/{made[0]['id']}/parts").status_code == 200
    assert anna.get(f"/projects/{joans}/parts").status_code == 404


def test_a_playlist_is_its_owners(people: dict) -> None:
    """Songs playlists (Phase 10): only the owner's songs go in, and only the owner opens it."""
    anna_id, anna = people["anna"]
    joan_id, joan = people["joan"]
    joans_project = project(joan_id, "private", "Joan's song")
    with session() as db:
        joans_song = rows.make_song(db, joan_id, "Joan's song", None)
        db.add(PrivateVersion(song_id=joans_song.id, version_name="v", project_id=joans_project))
        joans_song_id = joans_song.id
    assert (
        anna.post(
            "/playlists", json={"title": "x", "items": [{"songId": joans_song_id}]}
        ).status_code
        == 404
    )
    made = joan.post(
        "/playlists", json={"title": "Joan's set", "items": [{"songId": joans_song_id}]}
    )
    assert made.status_code == 201
    playlist = made.json()["id"]
    assert anna.get(f"/playlists/{playlist}").status_code == 404
    assert anna.delete(f"/playlists/{playlist}").status_code == 404
    assert anna.get("/playlists").json() == []
    assert [row["title"] for row in joan.get("/playlists").json()] == ["Joan's set"]


def test_folders_and_metadata_are_their_owners(people: dict) -> None:
    """Folders and metadata (implementation 04-3, Phase 1): only the owner sees and changes them,
    and only on their own items; a library version changes through the song, never the project."""
    anna_id, anna = people["anna"]
    joan_id, joan = people["joan"]
    annas_project = project(anna_id, "vault", "Anna's")
    annas_version = project(anna_id, "private", "Anna's song")
    with session() as db:
        annas_song = rows.make_song(db, anna_id, "Anna's song", None)
        db.add(PrivateVersion(song_id=annas_song.id, version_name="v", project_id=annas_version))
        song_id = annas_song.id
    made = anna.post("/folders", json={"area": "projects", "name": "Films"})
    assert made.status_code == 201
    folder_id = made.json()["id"]
    tags = {"tags": [{"category": "films", "value": "Shrek"}]}

    # Joan does not see Anna's folders, and nothing of Anna's is there for her to change.
    assert joan.get("/folders", params={"area": "projects"}).json() == []
    assert joan.patch(f"/folders/{folder_id}", json={"name": "Mine"}).status_code == 404
    assert joan.post(f"/folders/{folder_id}/move", json={"parentId": None}).status_code == 404
    assert joan.delete(f"/folders/{folder_id}").status_code == 404
    assert (
        joan.post("/folders", json={"area": "projects", "name": "x", "parentId": folder_id})
    ).status_code == 404
    joans = joan.post("/folders", json={"area": "projects", "name": "Joan's"}).json()["id"]
    assert (
        joan.put(f"/folders/projects/{annas_project}", json={"folders": [joans]}).status_code == 404
    )
    assert (
        anna.put(f"/folders/projects/{annas_project}", json={"folders": [joans]}).status_code == 404
    )
    assert joan.put(f"/folders/songs/{song_id}", json={"folders": []}).status_code == 404
    assert joan.put(f"/metadata/projects/{annas_project}", json=tags).status_code == 404
    assert joan.put(f"/metadata/songs/{song_id}", json=tags).status_code == 404
    assert joan.get(f"/metadata/info/{annas_project}").status_code == 404

    # Anna's own: her project, her song; a version of her library is read only as a project.
    assert (
        anna.put(f"/folders/projects/{annas_project}", json={"folders": [folder_id]}).status_code
        == 200
    )
    assert anna.put(f"/metadata/projects/{annas_project}", json=tags).status_code == 200
    assert anna.put(f"/metadata/songs/{song_id}", json=tags).status_code == 200
    assert anna.put(f"/metadata/projects/{annas_version}", json=tags).status_code == 403
    assert anna.put(f"/folders/projects/{annas_version}", json={"folders": []}).status_code == 403

    # Shared with Joan: she reads the song's metadata on the info button, and cannot change it.
    with session() as db:
        db.add(LibraryShare(owner_id=anna_id, shared_with_id=joan_id))
    seen = joan.get(f"/metadata/info/{annas_version}")
    assert seen.status_code == 200
    assert (seen.json()["kind"], seen.json()["editable"], seen.json()["folders"]) == (
        "song",
        False,
        [],
    )
    assert seen.json()["tags"] == tags["tags"]


def test_the_list_of_projects_is_the_users_own(people: dict) -> None:
    anna_id, anna = people["anna"]
    joan_id, joan = people["joan"]
    mine = project(anna_id, "vault", "Anna's")
    project(joan_id, "private", "Joan's")
    assert [entry["uuid"] for entry in anna.get("/audio/").json()] == [mine]
    assert [entry["alias"] for entry in joan.get("/audio/").json()] == ["Joan's"]


def test_an_upload_belongs_to_the_user_who_sent_it(people: dict, tmp_path) -> None:
    joan_id, joan = people["joan"]
    rate = 16_000
    buffer = io.BytesIO()
    wavfile.write(buffer, rate, (np.zeros(rate) * 0).astype(np.int16))
    buffer.seek(0)
    answer = joan.post("/audio/upload", files={"file": ("tone.wav", buffer, "audio/wav")})
    assert answer.status_code == 201, answer.text
    assert bundle.read_project(answer.json()["uuid"]).owner_id == joan_id
    assert reads(people["anna"][1], answer.json()["uuid"]) == 404


def test_a_job_is_followed_by_its_owner_and_the_master_user_only(people: dict) -> None:
    anna_id, anna = people["anna"]
    _, joan = people["joan"]
    _, master = people["master"]
    part = project(anna_id, "vault")
    started = anna.post("/matrix/transcribe", json={"audioUuid": part, "force": False})
    assert started.status_code == 202, started.text
    job_id = started.json()["jobId"]
    found = jobs.get(job_id)
    assert found is not None and found.owner_id == anna_id
    assert anna.get(f"/matrix/jobs/{job_id}").status_code == 200
    assert master.get(f"/matrix/jobs/{job_id}").status_code == 200
    assert joan.get(f"/matrix/jobs/{job_id}").status_code == 404
    assert joan.get(f"/matrix/progress/{job_id}").status_code == 404
    # Joan cannot start a transcription of Anna's project either.
    assert joan.post("/matrix/transcribe", json={"audioUuid": part}).status_code == 404


def test_a_job_makes_its_piece_for_the_user_who_started_it(people: dict) -> None:
    from aitu_backend.auth import context
    from aitu_backend.db.users import current_user_id

    joan_id = people["joan"][0]
    token = context.set_current(CurrentUser(joan_id, "joan", "user"))
    try:
        job = jobs.submit(lambda reporter: current_user_id())
    finally:
        context.reset(token)
    for _ in range(200):
        if job.finished:
            break
        import time

        time.sleep(0.01)
    assert job.result == joan_id and job.owner_id == joan_id
