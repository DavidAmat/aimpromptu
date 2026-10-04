"""The live notes of a transcription, as ``chunk`` messages on the progress stream (plan section 9.3).

MuScriptor cuts the audio into 5-second chunks. Its events arrive token by token while a chunk is
decoded (Phase 1: one every 22 ms), and a ``ProgressEvent`` closes each chunk. :class:`LiveNotes`
reads the same events as :class:`~aitu_backend.pmn.muscriptor.MuScriptorAssembler` and sends a
message:

* when a chunk ends, with ``done`` equal to the chunks finished;
* inside a chunk, at most every ``flush_seconds`` (0.25 s), when a note started or ended since the
  last message;
* once more at the end (:meth:`LiveNotes.finish`), for the notes MuScriptor closes after its last
  progress event. A chunk takes about 0.7 s on the RTX 4090, so the piano roll visualization grows
The messages inside a chunk make the piano roll visualization grow three or four times per chunk
(a chunk takes about 0.7 s on the RTX 4090) instead of once. This is an addition to the plan, which
named one message per chunk; ``done`` still counts whole chunks.

One message::

    {"type": "chunk", "done": 3, "total": 38, "upToMs": 15000, "durationMs": 189160,
     "open":   {"id": [41, 42], "key": [40, 52], "onMs": [14210, 14800]},
     "closed": {"id": [30, 31], "key": [39, 44], "onMs": [9900, 11000], "lenMs": [1200, 800]}}

``closed`` holds only the rectangles that ended since the previous message. ``open`` holds every
rectangle still sounding, which the page draws up to ``upToMs`` and replaces when its end arrives
in a later ``closed``. The ids are the ids of the saved notes. The times are the engine's own, in
whole milliseconds of the piece, before the lag correction: the correction is known only at the
end, and the saved notes the page reads after the ``done`` frame carry it.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from aitu_backend.pmn.muscriptor import MuScriptorAssembler, event_kind

__all__ = ["CHUNK_EVENT", "CHUNK_MS", "LiveNotes"]

#: The SSE event name of a message.
CHUNK_EVENT = "chunk"
#: MuScriptor's chunk, in ms.
CHUNK_MS = 5000
#: The shortest time between two messages inside a chunk.
FLUSH_SECONDS = 0.25


def _ms(seconds: float) -> int:
    return int(round(float(seconds) * 1000.0))


class LiveNotes:
    """Watches the events given to an assembler and sends the ``chunk`` messages."""

    def __init__(
        self,
        assembler: MuScriptorAssembler,
        send: Callable[[str, dict[str, Any]], None],
        duration_ms: float,
        *,
        flush_seconds: float = FLUSH_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._assembler = assembler
        self._send = send
        self._duration_ms = int(round(duration_ms))
        self._flush_seconds = flush_seconds
        self._clock = clock
        self._last_sent = clock()
        self._closed_position = 0
        self._started_at_last = assembler.next_id
        self._up_to = 0
        #: Messages sent, for the tests and the job's report.
        self.sent = 0

    def observe(self, event: Any) -> None:
        """Call after ``assembler.add(event)``."""
        kind = event_kind(event)
        if kind == "ProgressEvent":
            done = self._assembler.completed
            self._up_to = max(self._up_to, min(done * CHUNK_MS, self._duration_ms))
            self._flush()
            return
        for name in ("start_time", "end_time"):
            value = event.get(name) if isinstance(event, dict) else getattr(event, name, None)
            if value is not None:
                self._up_to = max(self._up_to, min(_ms(value), self._duration_ms))
        changed = (
            self._assembler.closed_count != self._closed_position
            or self._assembler.next_id != self._started_at_last
        )
        if changed and self._clock() - self._last_sent >= self._flush_seconds:
            self._flush()

    def finish(self) -> None:
        """Send the last message, after the last event.

        MuScriptor closes the notes still sounding at the end of the audio after its last progress
        event, so those ends need one more message. A note never closed ends at the end of the
        piece here, as it does in the saved notes, so the last message has no open rectangle.
        """
        self._up_to = self._duration_ms
        self._flush(final=True)

    def _flush(self, final: bool = False) -> None:
        assembler = self._assembler
        closed = assembler.closed_since(self._closed_position)
        self._closed_position = assembler.closed_count
        self._started_at_last = assembler.next_id
        opened = assembler.open_notes
        if final:
            closed = closed + [
                (note_id, key, on_ms, max(10, self._duration_ms - on_ms))
                for note_id, key, on_ms in opened
            ]
            opened = []
        self._send(
            CHUNK_EVENT,
            {
                "type": CHUNK_EVENT,
                "done": assembler.completed,
                "total": assembler.total,
                "upToMs": self._up_to,
                "durationMs": self._duration_ms,
                "open": {
                    "id": [note[0] for note in opened],
                    "key": [note[1] for note in opened],
                    "onMs": [note[2] for note in opened],
                },
                "closed": {
                    "id": [note[0] for note in closed],
                    "key": [note[1] for note in closed],
                    "onMs": [note[2] for note in closed],
                    "lenMs": [note[3] for note in closed],
                },
            },
        )
        self._last_sent = self._clock()
        self.sent += 1
