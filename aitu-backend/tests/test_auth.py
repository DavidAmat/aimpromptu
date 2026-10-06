"""Sign in, the session cookie, the slow-down, the master user, Admin → Users (implementation 02,
Phase 4, plan sections 9.1 and 9.2). Every test signs in through `/auth`, as the browser does."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from aitu_backend.api import auth as auth_api
from aitu_backend.auth import passwords, sessions, throttle
from aitu_backend.db import users
from aitu_backend.db.database import session
from aitu_backend.db.models import Session, User
from aitu_backend.main import create_app

pytestmark = pytest.mark.real_login

MASTER_PASSWORD = "master-password-1"


@pytest.fixture()
def master() -> int:
    master_id = users.ensure_master_user()
    users.set_password(master_id, MASTER_PASSWORD)
    return master_id


def client_of(username: str, password: str) -> TestClient:
    client = TestClient(create_app())
    answer = client.post("/auth/login", json={"username": username, "password": password})
    assert answer.status_code == 200, answer.text
    return client


def test_without_a_session_every_route_but_signing_in_answers_401() -> None:
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    for method, path in [
        ("GET", "/audio/"),
        ("GET", "/auth/me"),
        ("GET", "/matrix/engine"),
        ("POST", "/projects/x/duplicate"),
        ("GET", "/admin/users"),
        ("GET", "/frame-examples"),
    ]:
        answer = client.request(method, path)
        assert answer.status_code == 401, (method, path)
        assert answer.json()["detail"] == "Sign in first."


def test_signing_in_sets_an_httponly_cookie_and_answers_who_i_am(master: int) -> None:
    client = TestClient(create_app())
    answer = client.post("/auth/login", json={"username": "MASTER", "password": MASTER_PASSWORD})
    assert answer.status_code == 200
    assert answer.json() == {"id": master, "username": "master", "role": "master", "isMaster": True}
    cookie = answer.headers["set-cookie"]
    assert cookie.startswith(f"{sessions.COOKIE_NAME}=")
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Max-Age=2592000" in cookie
    assert client.get("/auth/me").json()["username"] == "master"
    assert client.get("/audio/").status_code == 200
    with session() as db:
        stored = db.scalar(select(Session))
    token = client.cookies[sessions.COOKIE_NAME]
    assert stored.token_hash != token and len(stored.token_hash) == 64


def test_a_wrong_password_and_an_unknown_user_get_the_same_answer(master: int) -> None:
    client = TestClient(create_app())
    wrong = client.post("/auth/login", json={"username": "master", "password": "nope-nope"})
    unknown = client.post("/auth/login", json={"username": "nobody", "password": "nope-nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": auth_api.WRONG}
    assert "set-cookie" not in wrong.headers


def test_five_wrong_passwords_in_a_minute_slow_the_next_tries(
    master: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    waited: list[float] = []

    async def no_wait(seconds: float) -> None:
        waited.append(seconds)

    monkeypatch.setattr(auth_api.asyncio, "sleep", no_wait)
    client = TestClient(create_app())
    for _ in range(7):
        client.post("/auth/login", json={"username": "master", "password": "wrong-one"})
    assert waited == [2.0, 3.0]
    assert throttle.delay_for("Master") == 4.0
    client.post("/auth/login", json={"username": "master", "password": MASTER_PASSWORD})
    assert throttle.delay_for("master") == 0.0


def test_the_slow_down_forgets_after_a_minute() -> None:
    for _ in range(5):
        throttle.failed("anna", now=0.0)
    assert throttle.delay_for("anna", now=30.0) == 2.0
    assert throttle.delay_for("anna", now=61.0) == 0.0


def test_signing_out_ends_the_session(master: int) -> None:
    client = client_of("master", MASTER_PASSWORD)
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401
    with session() as db:
        assert list(db.scalars(select(Session))) == []


def test_a_session_is_renewed_on_use_and_ends_when_it_expires(master: int) -> None:
    client = client_of("master", MASTER_PASSWORD)
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    with session() as db:
        row = db.scalar(select(Session))
        row.last_used_at = old
        row.expires_at = old + timedelta(days=1)
    answer = client.get("/auth/me")
    assert sessions.COOKIE_NAME in answer.headers.get("set-cookie", "")
    with session() as db:
        expires = db.scalar(select(Session)).expires_at.replace(tzinfo=timezone.utc)
    assert expires > datetime.now(timezone.utc) + timedelta(days=29)

    with session() as db:
        db.scalar(select(Session)).expires_at = old
    assert client.get("/auth/me").status_code == 401


def test_signing_in_deletes_the_expired_sessions(master: int) -> None:
    client_of("master", MASTER_PASSWORD)
    with session() as db:
        db.scalar(select(Session)).expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    client_of("master", MASTER_PASSWORD)
    with session() as db:
        assert len(list(db.scalars(select(Session)))) == 1


def test_changing_my_password(master: int) -> None:
    here = client_of("master", MASTER_PASSWORD)
    elsewhere = client_of("master", MASTER_PASSWORD)
    wrong = here.put("/auth/password", json={"current": "nope-nope", "new": "a-new-password"})
    assert wrong.status_code == 403
    short = here.put("/auth/password", json={"current": MASTER_PASSWORD, "new": "short"})
    assert short.status_code == 422 and "8 characters" in short.json()["detail"]
    done = here.put("/auth/password", json={"current": MASTER_PASSWORD, "new": "a-new-password"})
    assert done.status_code == 204
    assert here.get("/auth/me").status_code == 200  # this session stays
    assert elsewhere.get("/auth/me").status_code == 401  # every other one ends
    assert (
        TestClient(create_app())
        .post("/auth/login", json={"username": "master", "password": MASTER_PASSWORD})
        .status_code
        == 401
    )
    client_of("master", "a-new-password")


def test_the_master_user_takes_its_first_password_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AITU_MASTER_USERNAME", "david")
    monkeypatch.setenv("AITU_MASTER_PASSWORD", "from-the-env-file")
    master_id = users.ensure_master_user()
    client_of("david", "from-the-env-file")
    users.set_password(master_id, "changed-in-the-app")
    users.ensure_master_user()  # the next start: .env does not overwrite it
    client_of("david", "changed-in-the-app")


def test_a_user_with_no_password_cannot_sign_in() -> None:
    users.ensure_master_user()  # no AITU_MASTER_PASSWORD
    answer = TestClient(create_app()).post(
        "/auth/login", json={"username": "master", "password": "anything-at-all"}
    )
    assert answer.status_code == 401


# --------------------------------------------------------------------------- Admin → Users


def test_the_master_user_manages_the_users(master: int) -> None:
    admin = client_of("master", MASTER_PASSWORD)
    made = admin.post("/admin/users", json={"username": "anna", "password": "anna-password"})
    assert made.status_code == 201
    anna_id = made.json()["id"]
    assert made.json()["role"] == "user" and made.json()["hasPassword"] is True
    assert (
        admin.post("/admin/users", json={"username": "Anna", "password": "x" * 9}).status_code
        == 409
    )
    bad = admin.post("/admin/users", json={"username": "a b", "password": "x" * 9})
    assert bad.status_code == 422
    assert [user["username"] for user in admin.get("/admin/users").json()] == ["master", "anna"]

    anna = client_of("anna", "anna-password")
    assert anna.get("/auth/me").json()["isMaster"] is False
    assert anna.get("/admin/users").status_code == 403
    assert anna.get("/frame-examples").status_code == 403

    reset = admin.patch(f"/admin/users/{anna_id}", json={"password": "reset-password"})
    assert reset.status_code == 200
    assert anna.get("/auth/me").status_code == 401  # a reset ends her sessions
    anna = client_of("anna", "reset-password")
    assert admin.patch(f"/admin/users/{anna_id}", json={"disabled": True}).json()["disabled"]
    assert anna.get("/auth/me").status_code == 401
    refused = TestClient(create_app()).post(
        "/auth/login", json={"username": "anna", "password": "reset-password"}
    )
    assert refused.status_code == 401
    assert admin.patch(f"/admin/users/{master}", json={"disabled": True}).status_code == 422
    assert admin.patch("/admin/users/999", json={"disabled": True}).status_code == 404


def test_passwords_are_argon2() -> None:
    user = users.create_user("joan", "joan-password")
    with session() as db:
        stored = db.get(User, user.id).password_hash
    assert stored.startswith("$argon2id$")
    assert passwords.verify(stored, "joan-password")
    assert not passwords.verify(stored, "Joan-password")
