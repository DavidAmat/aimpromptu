"""How far the hand inference is, for a progress bar (implementation 08, the Hands tab).

The inference is a loop over the groups of onsets (the beam search) and then rounds of a second
pass (:mod:`.refine`). On a long piece it takes several seconds, and the page wants to show how far
it is. Passing a reporter through every function of this package would change all their
signatures, so the loops call :func:`report` instead, and whoever wants to hear it wraps the call
in :func:`listening`. With no listener, :func:`report` does nothing.

The listener is held in a context variable, so two inferences on two threads never hear each other.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Iterator

__all__ = ["listening", "report"]

#: ``callback(part, fraction)``: ``part`` is ``"beam"`` or ``"refine"``, ``fraction`` 0 to 1.
Listener = Callable[[str, float], None]

_listener: ContextVar[Listener | None] = ContextVar("aitu_hands_progress", default=None)


@contextmanager
def listening(callback: Listener) -> Iterator[None]:
    """Call ``callback`` with the progress of every inference run inside the block."""
    token = _listener.set(callback)
    try:
        yield
    finally:
        _listener.reset(token)


def report(part: str, fraction: float) -> None:
    """Say how far ``part`` is (0 to 1). Cheap when nobody listens."""
    callback = _listener.get()
    if callback is not None:
        callback(part, min(1.0, max(0.0, fraction)))
