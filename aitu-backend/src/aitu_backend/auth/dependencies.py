"""The check every route runs before anything else (implementation 02, plan sections 9.2 and 9.3).

:func:`signed_in` reads the session cookie, answers **401** without a valid one, sends the cookie
again when the session was renewed, and sets the user of the request (:mod:`.context`). It is
``async`` on purpose: a value set in the request's own task is copied into the worker thread of a
plain route, so every function below the route sees the user.

:func:`project_rights` then applies the rights table to the project the route names, by its path
parameter: ``audio_uuid`` (the id of a part) or ``project_id``. A project the user may not read
answers **404**, so its existence is not told; one they may read but not write answers **403**. A
``GET`` reads; every other method writes, except the few ``POST`` routes in :data:`READ_ROUTES`,
which compute an answer and change nothing.

:func:`master_only` guards the master user's pages (Lab, Users). :func:`require_job` checks the
owner of a background job.

``main.py`` adds the first two to every router except ``/auth``, and the third to ``/admin`` and
``/frame-examples``.
"""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from aitu_backend.auth import context, rights, sessions
from aitu_backend.auth.context import CurrentUser

__all__ = [
    "READ_ROUTES",
    "master_only",
    "project_rights",
    "require_job",
    "require_part",
    "set_session_cookie",
    "signed_in",
]

#: Set by the tests: every request acts as this user, with no cookie. Always ``None`` in the app.
test_user: Callable[[], CurrentUser] | None = None

#: ``POST`` routes that read a project and change nothing in it: a sheet computed for a reading, a
#: preview, a prediction shown before it is saved, a copy made into the user's own vault (a
#: duplicate, or the copy that edits a version of the Private Library).
READ_ROUTES = frozenset(
    {
        "/time/{audio_uuid}/score",
        "/time/{audio_uuid}/ladder-preview",
        "/pieces/{audio_uuid}/hands/predict",
        "/audio/{audio_uuid}/trim",
        "/projects/{project_id}/duplicate",
        "/projects/{project_id}/edit",
    }
)

SIGN_IN_FIRST = "Sign in first."


def set_session_cookie(response: Response, token: str) -> None:
    """``HttpOnly`` (no script reads it), ``SameSite=Lax``, 30 days. Not ``Secure``: the app is
    plain HTTP on the home network (context/08-security.md)."""
    response.set_cookie(
        sessions.COOKIE_NAME,
        token,
        max_age=int(sessions.LIFETIME.total_seconds()),
        httponly=True,
        samesite="lax",
        path="/",
    )


async def signed_in(request: Request, response: Response) -> CurrentUser:
    if test_user is not None:
        user = test_user()
    else:
        token = request.cookies.get(sessions.COOKIE_NAME)
        resolved = await run_in_threadpool(sessions.resolve, token)
        if resolved is None:
            raise HTTPException(status_code=401, detail=SIGN_IN_FIRST)
        if resolved.renewed and token:
            set_session_cookie(response, token)
        user = resolved.user
    context.set_current(user)
    request.state.user = user
    return user


def _is_write(request: Request) -> bool:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return False
    route = request.scope.get("route")
    return getattr(route, "path", "") not in READ_ROUTES


def _check(access: rights.Access, write: bool, item: str) -> None:
    if access is rights.Access.NONE:
        raise HTTPException(status_code=404, detail=f"No audio with uuid '{item}'")
    if write and access < rights.Access.WRITE:
        raise HTTPException(status_code=403, detail="You can open this project but not change it.")


async def project_rights(request: Request, user: CurrentUser = Depends(signed_in)) -> None:
    params = request.path_params
    write = _is_write(request)
    if "audio_uuid" in params:
        part_id = params["audio_uuid"]
        _check(await run_in_threadpool(rights.part_access, user, part_id), write, part_id)
    elif "project_id" in params:
        project_id = params["project_id"]
        _check(await run_in_threadpool(rights.project_access, user, project_id), write, project_id)


def require_part(part_id: str, *, write: bool) -> None:
    """The same check, for a route that names its part in the body (``POST /matrix/transcribe``)."""
    user = context.current()
    if user is None:
        return
    _check(rights.part_access(user, part_id), write, part_id)


async def master_only(user: CurrentUser = Depends(signed_in)) -> None:
    if not rights.is_admin_thing(user):
        raise HTTPException(status_code=403, detail="Only the master user can open this.")


def require_job(owner_id: int | None, job_id: str) -> None:
    """A job is followed by the user who started it, and by the master user."""
    user = context.current()
    if user is None or owner_id is None or user.is_master or user.id == owner_id:
        return
    raise HTTPException(status_code=404, detail=f"No job with id '{job_id}'")
