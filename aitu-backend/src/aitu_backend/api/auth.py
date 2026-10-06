"""``/auth``: sign in, sign out, who am I, change my password (implementation 02, plan section 9.2).

``POST /auth/login`` is the only route of the app (with ``/health``) that answers without a
session. Five wrong passwords for one username within a minute slow the next tries
(:mod:`aitu_backend.auth.throttle`). A wrong username and a wrong password get the same answer, so
the answer does not say which usernames exist.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from aitu_backend.auth import passwords, sessions, throttle
from aitu_backend.auth.context import CurrentUser
from aitu_backend.auth.dependencies import set_session_cookie, signed_in
from aitu_backend.db import users

router = APIRouter(prefix="/auth", tags=["auth"])

WRONG = "The username or the password is wrong."


class Me(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    username: str
    role: str
    is_master: bool = Field(..., alias="isMaster")


def _me(user: CurrentUser) -> Me:
    return Me(id=user.id, username=user.username, role=user.role, is_master=user.is_master)


class LoginIn(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=256)


class PasswordIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    current: str = Field(..., max_length=256)
    new: str = Field(..., max_length=256)


def _login(username: str, password: str) -> CurrentUser | None:
    user = users.find_by_username(username)
    if user is None or user.disabled or not passwords.verify(user.password_hash, password):
        return None
    return CurrentUser(user.id, user.username, user.role)


@router.post("/login", response_model=Me, response_model_by_alias=True)
async def login(body: LoginIn, response: Response) -> Me:
    wait = throttle.delay_for(body.username)
    if wait:
        await asyncio.sleep(wait)
    user = await run_in_threadpool(_login, body.username, body.password)
    if user is None:
        throttle.failed(body.username)
        raise HTTPException(status_code=401, detail=WRONG)
    throttle.clear(body.username)
    token = await run_in_threadpool(sessions.create, user.id)
    set_session_cookie(response, token)
    return _me(user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response) -> None:
    sessions.end(request.cookies.get(sessions.COOKIE_NAME))
    response.delete_cookie(sessions.COOKIE_NAME, path="/")


@router.get("/me", response_model=Me, response_model_by_alias=True)
def me(user: CurrentUser = Depends(signed_in)) -> Me:
    return _me(user)


@router.put("/password", status_code=204)
def change_password(
    body: PasswordIn, request: Request, user: CurrentUser = Depends(signed_in)
) -> None:
    """The user's own password. Their other sessions end; this one stays."""
    if _login(user.username, body.current) is None:
        raise HTTPException(status_code=403, detail="The current password is wrong.")
    try:
        users.set_password(
            user.id, body.new, keep_session=request.cookies.get(sessions.COOKIE_NAME)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
