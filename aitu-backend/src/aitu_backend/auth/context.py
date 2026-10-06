"""The user a request acts as.

The session check (:mod:`.dependencies`) sets it at the start of every request; a job copies it to
its thread (:mod:`aitu_backend.transcription.jobs`), so a project made by a job belongs to the user
who started it. Code that runs outside a request (the migration, the scripts, most tests) has no
user set and acts as the master user.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

__all__ = ["CurrentUser", "current", "reset", "set_current"]


@dataclass(frozen=True)
class CurrentUser:
    id: int
    username: str
    role: str

    @property
    def is_master(self) -> bool:
        return self.role == "master"


_current: ContextVar[CurrentUser | None] = ContextVar("aitu_current_user", default=None)


def current() -> CurrentUser | None:
    """The user of this request or job, or ``None`` outside one."""
    return _current.get()


def set_current(user: CurrentUser | None) -> Token[CurrentUser | None]:
    return _current.set(user)


def reset(token: Token[CurrentUser | None]) -> None:
    _current.reset(token)
