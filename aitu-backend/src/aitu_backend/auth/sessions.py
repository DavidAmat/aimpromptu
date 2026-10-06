"""The login session: a random token in an ``HttpOnly`` cookie, its SHA-256 in the ``sessions``
table (plan section 9.2).

A session lasts 30 days and is renewed on use: a request more than an hour after the last renewal
moves the expiry 30 days ahead and sends the cookie again. Only the hash of the token is stored, so
a copy of the database does not hold a usable session. A disabled user's sessions stop working at
once.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from aitu_backend.auth.context import CurrentUser
from aitu_backend.db.database import session
from aitu_backend.db.models import Session, User

__all__ = [
    "COOKIE_NAME",
    "LIFETIME",
    "Resolved",
    "create",
    "end",
    "end_all_of",
    "resolve",
]

COOKIE_NAME = "aitu_session"
LIFETIME = timedelta(days=30)
RENEW_AFTER = timedelta(hours=1)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(moment: datetime) -> datetime:
    """SQLite gives the stored times back without their zone; they were written in UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create(user_id: int) -> str:
    """A new session for the user; the token goes in the cookie and nowhere else. The expired
    sessions of every user are deleted on the way (a script signs in on every run)."""
    token = secrets.token_urlsafe(32)
    moment = _now()
    with session() as db:
        db.execute(delete(Session).where(Session.expires_at <= moment))
        db.add(
            Session(
                token_hash=_hash(token),
                user_id=user_id,
                created_at=moment,
                expires_at=moment + LIFETIME,
                last_used_at=moment,
            )
        )
    return token


@dataclass(frozen=True)
class Resolved:
    user: CurrentUser
    #: True when the expiry moved, so the cookie is sent again with the new date.
    renewed: bool


def resolve(token: str | None) -> Resolved | None:
    """The user of a session token, or ``None`` when it is unknown, expired, or its user disabled."""
    if not token:
        return None
    moment = _now()
    with session() as db:
        found = db.execute(
            select(Session, User)
            .join(User, Session.user_id == User.id)
            .where(Session.token_hash == _hash(token))
        ).first()
        if found is None:
            return None
        row, user = found
        if _aware(row.expires_at) <= moment or user.disabled:
            db.delete(row)
            return None
        renewed = row.last_used_at is None or moment - _aware(row.last_used_at) > RENEW_AFTER
        if renewed:
            row.last_used_at = moment
            row.expires_at = moment + LIFETIME
        return Resolved(CurrentUser(user.id, user.username, user.role), renewed)


def end(token: str | None) -> None:
    if token:
        with session() as db:
            db.execute(delete(Session).where(Session.token_hash == _hash(token)))


def end_all_of(user_id: int, *, keep: str | None = None) -> None:
    """End every session of a user (a password reset, a disabled user), except ``keep``."""
    with session() as db:
        query = delete(Session).where(Session.user_id == user_id)
        if keep:
            query = query.where(Session.token_hash != _hash(keep))
        db.execute(query)
