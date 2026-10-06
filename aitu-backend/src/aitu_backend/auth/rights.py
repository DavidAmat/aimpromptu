"""Who can read and write what (implementation 02, plan section 9.3).

=========================================  =================================  ==================================
Thing                                      Read                               Write
=========================================  =================================  ==================================
A project in a Personal Vault              its owner                          its owner
A project in a Private Library             its owner; users it is shared      its owner (*)
                                           with (``library_shares``)
The Public Library                         every user                         the master user
A request                                  its author and the master user     its author until it is reviewed;
                                                                              the master user (the decision)
Users, Lab                                 the master user                    the master user
=========================================  =================================  ==================================

(*) The plan writes a library project "through a copy in the vault" (section 10.6). That flow
arrives in Phase 6; until then the owner edits their Private Library projects in place, as before
Phase 3, so the 30 migrated songs stay editable. Phase 6 changes this one line.

The master user has no extra right over another user's private projects: an Admin who can read
every library would make "private" a promise the app does not keep.
"""

from __future__ import annotations

from enum import IntEnum

from sqlalchemy import select

from aitu_backend.auth.context import CurrentUser
from aitu_backend.db.database import session
from aitu_backend.db.models import LibraryShare, Request
from aitu_backend.storage import locate

__all__ = [
    "Access",
    "REVIEWED",
    "can_decide_request",
    "can_edit_request",
    "can_read_request",
    "is_admin_thing",
    "part_access",
    "project_access",
]


class Access(IntEnum):
    NONE = 0
    READ = 1
    WRITE = 2


def _shared_with(owner_id: int, user_id: int) -> bool:
    with session() as db:
        return (
            db.scalar(
                select(LibraryShare.owner_id).where(
                    LibraryShare.owner_id == owner_id, LibraryShare.shared_with_id == user_id
                )
            )
            is not None
        )


def _access(user: CurrentUser, where: locate.Location) -> Access:
    if where.layer == "public":
        return Access.WRITE if user.is_master else Access.READ
    if where.owner_id == user.id:
        return Access.WRITE
    if where.layer == "private" and _shared_with(where.owner_id, user.id):
        return Access.READ
    return Access.NONE


def project_access(user: CurrentUser, project_id: str) -> Access:
    """What the user may do with a project. An unknown project is ``NONE``."""
    try:
        return _access(user, locate.project(project_id))
    except locate.NotFound:
        return Access.NONE


def part_access(user: CurrentUser, part_id: str) -> Access:
    """What the user may do with the project of a part. An unknown part is ``NONE``."""
    try:
        return _access(user, locate.part(part_id))
    except locate.NotFound:
        return Access.NONE


#: The statuses of a request once the master user has decided.
REVIEWED = ("accepted", "partlyAccepted", "refused")


def can_read_request(user: CurrentUser, request: Request) -> bool:
    return user.is_master or request.author_id == user.id


def can_edit_request(user: CurrentUser, request: Request) -> bool:
    """The author changes or withdraws a request until it is reviewed."""
    return request.author_id == user.id and request.status not in REVIEWED


def can_decide_request(user: CurrentUser, request: Request) -> bool:
    return user.is_master


def is_admin_thing(user: CurrentUser) -> bool:
    """Users and Lab: the master user only."""
    return user.is_master
