"""The hand split of each piece, computed once and shared (implementation 08, plan section 10.5).

The hand split is the expensive half of drawing a piece: 0.3 to 4.3 s on the Ubuntu machine, 0.56 s
median (Phase 2). Before this module it was cached only inside the piano sheet route, so:

* the transcription job computed it and threw it away, and the first sheet request paid it again;
* ``GET /matrix/{uuid}/events`` (the old piano roll) computed it on every call.

Now every reader asks this one cache. The key is ``(uuid, frameMs, mtime of events.json in ns)``,
so a new transcription or any saved edit is a new key and an old split is never served. The value
is shared: every caller treats it as read-only and copies before changing anything.

Two requests for the same key at the same time compute it once: the second waits for the first.
That matters right after a transcription, when the job warms the cache on a thread (:func:`warm`)
while the page, which has just received ``done``, already asks for the sheet.
"""

from __future__ import annotations

import collections
import threading
from typing import Callable, Hashable, TypeVar

__all__ = ["forget", "get", "size"]

T = TypeVar("T")

#: Pieces times frame lengths kept. A split of a 3.5-minute piece is a few MB.
MAX_ENTRIES = 8

#: ``(uuid, frameMs, mtime ns, ...)``: the piece is always first, so :func:`forget` can find it.
Key = tuple[Hashable, ...]

_lock = threading.Lock()
_values: "collections.OrderedDict[Key, object]" = collections.OrderedDict()
_computing: dict[Key, threading.Event] = {}


def get(key: Key, compute: Callable[[], T]) -> T:
    """The cached value of ``key``, or ``compute()`` stored under it. One computation per key."""
    while True:
        with _lock:
            if key in _values:
                _values.move_to_end(key)
                return _values[key]  # type: ignore[return-value]
            pending = _computing.get(key)
            if pending is None:
                pending = threading.Event()
                _computing[key] = pending
                owner = True
            else:
                owner = False
        if not owner:
            pending.wait()
            continue  # read the value, or compute it if the owner failed
        try:
            value = compute()
            with _lock:
                _values[key] = value
                _values.move_to_end(key)
                while len(_values) > MAX_ENTRIES:
                    _values.popitem(last=False)
            return value
        finally:
            with _lock:
                _computing.pop(key, None)
            pending.set()


def forget(audio_uuid: str | None = None) -> None:
    """Drop the cached splits of one piece, or of every piece. The keys already change with every
    save; this is for the writers that save twice within one tick of the file system's clock
    (about 4 ms on ext4), and for tests."""
    with _lock:
        if audio_uuid is None:
            _values.clear()
            return
        for key in [key for key in _values if key[0] == audio_uuid]:
            del _values[key]


def size() -> int:
    with _lock:
        return len(_values)
