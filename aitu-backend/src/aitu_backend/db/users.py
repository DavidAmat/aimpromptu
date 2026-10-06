"""The users (implementation 02, plan section 9.1).

* **The master user** is made on the first start from ``AITU_MASTER_USERNAME`` (default
  ``master``). Its password is set from ``AITU_MASTER_PASSWORD`` while it has none, so a password
  changed later from the user menu is never overwritten by ``.env``.
* **Other users** are made by the master user in Admin → Users (P-7): a username and a first
  password, which the user changes from the user menu. The master user can disable a user and reset
  a password. There is no sign-up.

:func:`current_user_id` is the user a request acts as (:mod:`aitu_backend.auth.context`), or the
master user outside a request (the migration, the scripts, most tests).
"""

from __future__ import annotations

import re

from sqlalchemy import func, select

from aitu_backend import config
from aitu_backend.auth import context, passwords, sessions
from aitu_backend.db.database import session
from aitu_backend.db.models import User

__all__ = [
    "USERNAME_PATTERN",
    "UserExists",
    "create_user",
    "current_user_id",
    "ensure_master_user",
    "find_by_username",
    "list_users",
    "master_user_id",
    "set_disabled",
    "set_password",
]

#: Letters, digits, dot, dash, underscore; 2 to 32 characters. The name other users see.
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{2,32}$")


class UserExists(ValueError):
    pass


def ensure_master_user() -> int:
    """The id of the master user, made when the database has none; its password from ``.env``
    while it has none."""
    with session() as db:
        user = db.scalar(select(User).where(User.role == "master").order_by(User.id))
        if user is None:
            user = User(username=config.master_username(), role="master")
            db.add(user)
            db.flush()
        if user.password_hash is None and config.master_password():
            user.password_hash = passwords.hash_password(config.master_password() or "")
        return int(user.id)


def master_user_id() -> int:
    return ensure_master_user()


def current_user_id() -> int:
    """The user a request or a job acts as; the master user outside one."""
    user = context.current()
    return user.id if user is not None else ensure_master_user()


def find_by_username(username: str) -> User | None:
    with session() as db:
        return db.scalar(select(User).where(func.lower(User.username) == username.strip().lower()))


def list_users() -> list[User]:
    with session() as db:
        return list(db.scalars(select(User).order_by(User.id)))


def create_user(username: str, password: str) -> User:
    """A plain user. Raises ``ValueError`` on a refused name or password, :class:`UserExists`."""
    name = username.strip()
    if not USERNAME_PATTERN.match(name):
        raise ValueError(
            "A username has 2 to 32 letters, digits, dots, dashes or underscores, and no space"
        )
    passwords.check_new(password)
    if find_by_username(name) is not None:
        raise UserExists(f"The username {name} is taken")
    with session() as db:
        user = User(username=name, role="user", password_hash=passwords.hash_password(password))
        db.add(user)
        db.flush()
        return user


def set_password(user_id: int, password: str, *, keep_session: str | None = None) -> None:
    """A new password. Every other session of the user ends."""
    passwords.check_new(password)
    with session() as db:
        user = db.get(User, user_id)
        if user is None:
            raise KeyError(user_id)
        user.password_hash = passwords.hash_password(password)
    sessions.end_all_of(user_id, keep=keep_session)


def set_disabled(user_id: int, disabled: bool) -> User:
    """Disable or enable a user. A disabled user's sessions end. The master user stays enabled."""
    with session() as db:
        user = db.get(User, user_id)
        if user is None:
            raise KeyError(user_id)
        if user.role == "master" and disabled:
            raise ValueError("The master user cannot be disabled")
        user.disabled = disabled
    if disabled:
        sessions.end_all_of(user_id)
    return user
