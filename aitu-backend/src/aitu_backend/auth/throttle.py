"""The slow-down after wrong passwords (plan section 9.2).

Five wrong passwords for one username within a minute slow the next tries: each new try waits one
second more than the last (2 s, 3 s ... at most 10 s) before the password is even checked. The
count is per username and in memory; a correct password clears it. A restart clears it too, which
is acceptable on a home network.
"""

from __future__ import annotations

import threading
import time
from collections import deque

__all__ = ["FREE_TRIES", "MAX_DELAY_SECONDS", "WINDOW_SECONDS", "clear", "delay_for", "failed"]

WINDOW_SECONDS = 60.0
FREE_TRIES = 5
MAX_DELAY_SECONDS = 10.0

_lock = threading.Lock()
_failures: dict[str, deque[float]] = {}


def _recent(username: str, now: float) -> deque[float]:
    times = _failures.setdefault(username.lower(), deque())
    while times and now - times[0] > WINDOW_SECONDS:
        times.popleft()
    return times


def delay_for(username: str, now: float | None = None) -> float:
    """How long the next try for ``username`` waits, in seconds."""
    with _lock:
        count = len(_recent(username, time.monotonic() if now is None else now))
    if count < FREE_TRIES:
        return 0.0
    return min(MAX_DELAY_SECONDS, float(count - FREE_TRIES + 2))


def failed(username: str, now: float | None = None) -> None:
    with _lock:
        _recent(username, time.monotonic() if now is None else now).append(
            time.monotonic() if now is None else now
        )


def clear(username: str | None = None) -> None:
    with _lock:
        if username is None:
            _failures.clear()
        else:
            _failures.pop(username.lower(), None)
