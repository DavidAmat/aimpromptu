"""``/admin``: the master user's pages (implementation 02, plan section 16.3). Phase 4: **Users**;
Phase 14: **Review**.

The master user creates a user with a username and a first password, disables or enables a user,
and resets a password (P-7: no sign-up). They review the requests to the Public Library: the open
ones, oldest first, and a decision for every item of one (:mod:`aitu_backend.library.requests`).
``main.py`` puts the whole router behind :func:`aitu_backend.auth.dependencies.master_only`.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from aitu_backend.api.requests import DetailOut, SummaryOut, detail_out, summary_out
from aitu_backend.db import users
from aitu_backend.db.models import User
from aitu_backend.db.users import current_user_id
from aitu_backend.library import flow, rows
from aitu_backend.library import requests as library_requests

router = APIRouter(prefix="/admin", tags=["admin"])


class UserOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    username: str
    role: str
    disabled: bool
    created_at: datetime = Field(..., alias="createdAt")
    #: False until a first password is set (the master user before ``AITU_MASTER_PASSWORD``).
    has_password: bool = Field(..., alias="hasPassword")


def _out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        disabled=user.disabled,
        created_at=user.created_at,
        has_password=user.password_hash is not None,
    )


class UserIn(BaseModel):
    username: str = Field(..., max_length=64)
    password: str = Field(..., max_length=256)


class UserPatch(BaseModel):
    disabled: bool | None = None
    #: A new password, which the user then changes from their own menu.
    password: str | None = Field(None, max_length=256)


@router.get("/users", response_model=list[UserOut], response_model_by_alias=True)
def list_users() -> list[UserOut]:
    return [_out(user) for user in users.list_users()]


@router.post("/users", response_model=UserOut, response_model_by_alias=True, status_code=201)
def create_user(body: UserIn) -> UserOut:
    try:
        return _out(users.create_user(body.username, body.password))
    except users.UserExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/users/{user_id}", response_model=UserOut, response_model_by_alias=True)
def change_user(user_id: int, body: UserPatch) -> UserOut:
    try:
        if body.password is not None:
            users.set_password(user_id, body.password)
        if body.disabled is not None:
            users.set_disabled(user_id, body.disabled)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"No user with id {user_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    found = next((user for user in users.list_users() if user.id == user_id), None)
    if found is None:
        raise HTTPException(status_code=404, detail=f"No user with id {user_id}")
    return _out(found)


# --------------------------------------------------------------------- review


class DecisionIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    #: A decision for every item still waiting.
    items: list[library_requests.ItemDecision]
    #: A few words for the author, beside the decisions of the items.
    comment: str | None = Field(None, max_length=2000)


@router.get("/requests", response_model=list[SummaryOut], response_model_by_alias=True)
def review_list(everything: bool = False) -> list[SummaryOut]:
    """The open requests, oldest first; with ``everything``, every request, newest first."""
    return [summary_out(one) for one in library_requests.for_review(everything)]


@router.post(
    "/requests/{request_id}/decision", response_model=DetailOut, response_model_by_alias=True
)
def decide(request_id: int, body: DecisionIn) -> DetailOut:
    """Accept, refuse or ask for a change on every waiting item. What is accepted is published at
    once, in one transaction."""
    try:
        library_requests.decide(request_id, current_user_id(), body.items, body.comment)
        return detail_out(request_id)
    except rows.NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (rows.Conflict, flow.Refused) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
