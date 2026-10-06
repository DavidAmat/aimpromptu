"""The master user, made on the first start (implementation 02, plan section 9.1).

Until the login exists (Phase 4) every request acts as the master user: :func:`current_user_id`
is the one place that says so, and Phase 4 replaces it with the user of the session.
"""

from __future__ import annotations

from sqlalchemy import select

from aitu_backend import config
from aitu_backend.db.database import session
from aitu_backend.db.models import User

__all__ = ["current_user_id", "ensure_master_user", "master_user_id"]


def ensure_master_user() -> int:
    """The id of the master user, made from ``AITU_MASTER_USERNAME`` when there is none.

    The password comes with the login (Phase 4); until then the row has no password hash.
    """
    with session() as db:
        found = db.scalar(select(User.id).where(User.role == "master").order_by(User.id))
        if found is not None:
            return int(found)
        user = User(username=config.master_username(), role="master")
        db.add(user)
        db.flush()
        return int(user.id)


def master_user_id() -> int:
    return ensure_master_user()


def current_user_id() -> int:
    """The user a request acts as. Phase 3: always the master user (there is no login yet)."""
    return ensure_master_user()
