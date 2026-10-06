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
from aitu_backend.db.models import LibraryShare, Request
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
        assert other.get(f"/time/{part}/rhythm").status_code == 404
        assert other.delete(f"/audio/{part}").status_code == 404


def test_row_2_a_project_in_a_private_library(people: dict) -> None:
    anna_id, anna = people["anna"]
    joan_id, joan = people["joan"]
    _, master = people["master"]
    part = project(anna_id, "private")
    assert (reads(anna, part), writes(anna, part)) == (200, 200)
    assert (reads(joan, part), writes(joan, part)) == (404, 404)
    with session() as db:
        db.add(LibraryShare(owner_id=anna_id, shared_with_id=joan_id))
    # Shared with Joan: she reads it, plays it, and copies it into her own vault; she does not
    # change it.
    assert (reads(joan, part), writes(joan, part)) == (200, 403)
    assert joan.get(f"/audio/{part}").status_code == 200
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
    # A read-only route that is a POST (a sheet for a reading) is open to every reader.
    reading = {"anchorFigure": "negra", "anchorMs": 500.0, "frameMs": 40.0}
    assert anna.post(f"/time/{part}/score", json=reading).status_code == 200


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
